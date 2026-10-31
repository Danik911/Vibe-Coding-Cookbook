"""A claim agent on plain Amazon Bedrock (the Converse API), with its tools from the gateway.

This is the agent's side of what AgentCore Gateway gave the course's claim agent: one MCP
endpoint with every tool, a policy in front of them, and no secrets in the agent. It needs
only `bedrock:InvokeModel` on the model you choose, and no AgentCore permission at all.

This example is its own uv project because `langchain-mcp-adapters` needs the `mcp` 1.x
SDK, while the gateway runs on FastMCP 4 and `mcp` 2.x: the two talk over the protocol.

  cd examples/agent
  uv run --env-file ../../.env agent_bedrock.py --tools-only         # no model call
  uv run --env-file ../../.env agent_bedrock.py --claim CLM-1002     # needs BEDROCK_MODEL_ID and AWS credentials
"""

from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Awaitable, Callable, Generator

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult, TextContent

INSTRUCTIONS = """You are the UnderCover claim agent. Decide the claim you're given: read it,
its policy and the plan, work out the payout with calculate_payout, record your decision with
a reason and the section relied on, and pay an approval with pay_claim. When the gateway
refuses a call, don't retry it: say the claim is left for a handler's sign-off."""


class GatewaySigV4(httpx.Auth):
    """Signs each MCP request for a gateway behind a Lambda Function URL with AWS_IAM auth."""

    requires_request_body = True

    def __init__(self, region: str, service: str = "lambda") -> None:
        self._session = boto3.Session(region_name=region)
        self._region = region
        self._service = service

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        credentials = self._session.get_credentials()
        if credentials is None:
            raise RuntimeError("no AWS credentials to sign the gateway request")
        signed = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers={"Host": request.url.netloc.decode(), "Content-Type": request.headers.get("content-type", "")},
        )
        SigV4Auth(credentials.get_frozen_credentials(), self._service, self._region).add_auth(signed)
        for name in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token"):
            if name in signed.headers:
                request.headers[name] = signed.headers[name]
        yield request


async def policy_refusals(
    request: MCPToolCallRequest, handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]]
) -> MCPToolCallResult:
    """Turns the gateway's policy refusal (a protocol error) into a refusal the model reads.

    The agent's work goes on, and the model is told not to retry: the refusal is a routing
    signal, as the course's claim agent treats AgentCore Policy's "Tool Execution Denied".
    """
    try:
        return await handler(request)
    except McpError as error:
        if "Tool Execution Denied" not in str(error):
            raise
        text = f"{error}. This is final: leave the claim for a handler's sign-off."
        return CallToolResult(content=[TextContent(type="text", text=text)], isError=True)


def gateway_connection(url: str, region: str | None) -> dict:
    if region:
        return {"transport": "streamable_http", "url": url, "auth": GatewaySigV4(region)}
    token = os.environ["GATEWAY_CLAIM_AGENT_KEY"]
    return {"transport": "streamable_http", "url": url, "headers": {"Authorization": f"Bearer {token}"}}


async def main() -> None:
    parser = argparse.ArgumentParser(description="A claim agent on Bedrock with tools from the gateway")
    parser.add_argument("--gateway", default=os.environ.get("GATEWAY_URL", "http://127.0.0.1:8210/mcp"))
    parser.add_argument("--claim", default="CLM-1002")
    parser.add_argument("--iam-region", help="sign requests with SigV4 for a gateway behind an AWS_IAM Function URL")
    parser.add_argument("--tools-only", action="store_true", help="list and try the tools without a model call")
    args = parser.parse_args()

    client = MultiServerMCPClient(
        {"gateway": gateway_connection(args.gateway, args.iam_region)}, tool_interceptors=[policy_refusals]
    )
    tools = await client.get_tools()
    print("Tools:", ", ".join(tool.name for tool in tools))

    if args.tools_only:
        by_name = {tool.name: tool for tool in tools}
        print(await by_name["undercover-app___get_claim"].ainvoke({"claim_id": args.claim}))
        print(await by_name["undercover-app___pay_claim"].ainvoke({"claim_id": args.claim, "amount": 4800}))
        return

    model = ChatBedrockConverse(
        model=os.environ["BEDROCK_MODEL_ID"],
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        temperature=0,
    )
    agent = create_agent(model, tools, system_prompt=INSTRUCTIONS)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": f"Work claim {args.claim}."}]})
    for message in result["messages"]:
        calls = getattr(message, "tool_calls", None)
        print(f"[{message.type}]", calls or str(message.content)[:400])


if __name__ == "__main__":
    asyncio.run(main())

"""The gateway end to end over HTTP: inbound auth, targets, policy and audit."""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any

import httpx2
import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.auth.providers.jwt import RSAKeyPair
from mcp.shared.exceptions import MCPError
from starlette.types import ASGIApp, Receive, Scope, Send

from diy_gateway.app import Upstreams, build_gateway, build_http_app
from diy_gateway.config import GatewayConfig
from examples.demo_upstreams import app as demo_app
from examples.demo_upstreams.context_server import context
from tests.conftest import AGENT_KEY, audit_records, with_changes

APP_TOOLS = {
    "undercover-app___get_claim",
    "undercover-app___get_policy",
    "undercover-app___get_claim_history",
    "undercover-app___calculate_payout",
    "undercover-app___record_decision",
    "undercover-app___pay_claim",
}
CONTEXT_TOOLS = {"undercover-context___lookup_term", "undercover-context___get_plan"}


def start_gateway(serve: Callable[[Any], str], config: GatewayConfig, upstreams: Upstreams, audit: io.StringIO) -> str:
    gateway = build_gateway(config, upstreams=upstreams, audit_stream=audit)
    return serve(build_http_app(gateway)) + "/mcp"


def client(url: str, token: str | None = AGENT_KEY) -> Client:
    return Client(StreamableHttpTransport(url, auth=token))


async def test_lists_every_targets_tools_with_its_prefix(serve, demo_config, upstreams, audit, spec_requests):
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with client(url) as mcp:
        names = {tool.name for tool in await mcp.list_tools()}
    assert names == APP_TOOLS | CONTEXT_TOOLS
    assert spec_requests[0]["x-api-key"]


async def test_an_app_tool_reaches_the_app_with_the_gateways_key(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with client(url) as mcp:
        result = await mcp.call_tool("undercover-app___get_claim", {"claim_id": "CLM-1001"})
    assert result.structured_content["customer_id"] == "CUS-3001"


async def test_a_context_tool_goes_through_the_proxy(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with client(url) as mcp:
        result = await mcp.call_tool("undercover-context___get_plan", {"plan": "economy"})
    assert result.structured_content["deductible"] == 100


async def test_enforce_refuses_a_payment_over_the_limit_before_the_app(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with client(url) as mcp:
        with pytest.raises(MCPError, match="Tool Execution Denied") as refusal:
            await mcp.call_tool("undercover-app___pay_claim", {"claim_id": "CLM-1002", "amount": 4800})
    assert refusal.value.error.data == {"retryable": False, "policies": ["payment-limit"]}
    assert demo_app.PAYMENTS == {}
    decision = audit_records(audit)[-1]
    assert (decision["decision"], decision["enforced"], decision["policies"]) == ("DENY", True, ["payment-limit"])


async def test_log_only_records_the_refusal_and_lets_the_app_refuse(serve, demo_config, upstreams, audit):
    config = with_changes(demo_config, policy={"mode": "log_only"})
    url = start_gateway(serve, config, upstreams, audit)
    async with client(url) as mcp:
        result = await mcp.call_tool(
            "undercover-app___pay_claim", {"claim_id": "CLM-1002", "amount": 4800}, raise_on_error=False
        )
    assert result.is_error
    assert "approval limit" in result.content[0].text
    decision, call = audit_records(audit)[-2:]
    assert (decision["decision"], decision["enforced"]) == ("DENY", False)
    assert call["outcome"] == "error"


async def test_a_payment_within_the_limit_is_paid(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    decision = {"decision": "approve", "payout": 400, "section": "4.2", "reason": "Bag lost by the airline"}
    async with client(url) as mcp:
        await mcp.call_tool("undercover-app___record_decision", {"claim_id": "CLM-1001", **decision})
        await mcp.call_tool("undercover-app___pay_claim", {"claim_id": "CLM-1001", "amount": 400})
    assert demo_app.PAYMENTS == {"CLM-1001": 400}


async def raw_list_tools(url: str, token: str) -> httpx2.Response:
    """A tools/list request without an MCP client, to see the HTTP status."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    async with httpx2.AsyncClient() as http:
        return await http.post(url, json=body, headers=headers)


async def test_a_wrong_key_never_reaches_the_tools(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    response = await raw_list_tools(url, "not-the-key")
    assert response.status_code == 401
    assert audit.getvalue() == ""


async def test_health_needs_no_token(serve, demo_config, upstreams, audit):
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with httpx2.AsyncClient() as http:
        response = await http.get(url.removesuffix("/mcp") + "/health")
    assert response.json() == {"healthy": True}


async def test_a_signed_in_user_sees_and_calls_only_the_context_layer(
    serve, demo_config, upstreams, audit, rsa_key: RSAKeyPair
):
    jwt = {"public_key": rsa_key.public_key, "issuer": "https://idp.test", "audience": "undercover-gateway"}
    config = with_changes(demo_config, inbound={"jwt": jwt})
    url = start_gateway(serve, config, upstreams, audit)
    token = rsa_key.create_token(subject="handler-dana", issuer="https://idp.test", audience="undercover-gateway")
    async with client(url, token=token) as mcp:
        names = {tool.name for tool in await mcp.list_tools()}
        with pytest.raises(MCPError, match="no policy permits it"):
            await mcp.call_tool("undercover-app___get_claim", {"claim_id": "CLM-1001"})
    assert names == CONTEXT_TOOLS
    assert audit_records(audit)[-1]["principal"] == "User::handler-dana"


async def test_a_token_for_another_audience_is_refused(serve, demo_config, upstreams, audit, rsa_key: RSAKeyPair):
    jwt = {"public_key": rsa_key.public_key, "issuer": "https://idp.test", "audience": "undercover-gateway"}
    url = start_gateway(serve, with_changes(demo_config, inbound={"jwt": jwt}), upstreams, audit)
    token = rsa_key.create_token(subject="handler-dana", issuer="https://idp.test", audience="undercover-app")
    response = await raw_list_tools(url, token)
    assert response.status_code == 401


class HeaderRecorder:
    """Wraps an ASGI app and records the headers of each request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.seen: list[str | None] = []
        self.headers: list[dict[str, str]] = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {key.decode(): value.decode() for key, value in scope["headers"]}
            self.headers.append(headers)
            self.seen.append(headers.get("authorization"))
        await self.app(scope, receive, send)


async def test_the_app_gets_only_the_gateways_headers_not_the_callers(serve, demo_config, upstreams, audit):
    recorder = HeaderRecorder(demo_app.app)
    upstreams.http["undercover-app"] = httpx2.ASGITransport(app=recorder)
    url = start_gateway(serve, demo_config, upstreams, audit)
    caller_headers = {"X-User-Id": "handler-admin", "X-API-Key": "caller-chosen-key"}
    transport = StreamableHttpTransport(url, auth=AGENT_KEY, headers=caller_headers)
    async with Client(transport) as mcp:
        await mcp.call_tool("undercover-app___get_claim", {"claim_id": "CLM-1001"})
    sent = recorder.headers[-1]
    assert "x-user-id" not in sent
    assert "authorization" not in sent
    assert sent["x-api-key"] != "caller-chosen-key"


async def test_the_callers_token_never_reaches_an_upstream_mcp_server(serve, demo_config, upstreams, audit):
    recorder = HeaderRecorder(context.http_app(path="/mcp", stateless_http=True, json_response=True))
    context_url = serve(recorder) + "/mcp"
    targets = [t.model_dump(mode="json") for t in demo_config.targets]
    targets[1]["url"] = context_url
    config = with_changes(demo_config, targets=targets)
    url = start_gateway(serve, config, Upstreams(http=upstreams.http, spec_http=upstreams.spec_http), audit)
    async with client(url) as mcp:
        await mcp.call_tool("undercover-context___lookup_term", {"term": "deductible"})
    assert recorder.seen
    assert all(header is None for header in recorder.seen)


@pytest.mark.parametrize("mode", ["log_only", "enforce"])
@pytest.mark.parametrize("name", ["lookup_term", "a47f31b20058_lookup_term", "undercover-context__lookup_term"])
async def test_a_name_outside_the_targets_prefixes_is_refused_in_any_mode(
    serve, demo_config, upstreams, audit, mode, name
):
    url = start_gateway(serve, with_changes(demo_config, policy={"mode": mode}), upstreams, audit)
    async with client(url) as mcp:
        with pytest.raises(MCPError, match="is not a tool of this gateway"):
            await mcp.call_tool(name, {"term": "deductible"})
    last = audit_records(audit)[-1]
    assert (last["event"], last["tool"]) == ("refused", name)


async def test_an_upstreams_resources_and_prompts_stay_behind_the_gateway(serve, demo_config, upstreams, audit):
    upstream = FastMCP("upstream-with-extras")

    @upstream.tool
    def lookup_term(term: str) -> str:
        """A term's definition."""
        return term

    @upstream.resource("data://secret")
    def secret() -> str:
        return "not for callers"

    @upstream.prompt
    def leak() -> str:
        """A prompt."""
        return "not for callers"

    upstreams.mcp["undercover-context"] = upstream
    url = start_gateway(serve, demo_config, upstreams, audit)
    async with client(url) as mcp:
        assert await mcp.list_resources() == []
        assert await mcp.list_prompts() == []
        with pytest.raises(MCPError):
            await mcp.read_resource("data://secret")

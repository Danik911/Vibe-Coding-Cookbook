"""Calls the running gateway as the claim agent: lists the tools, reads a claim and the
context layer, pays within the limit, and shows the policy refusing a payment over it.

Run (with run_demo.py going): uv run --env-file .env examples/call_gateway.py
"""

from __future__ import annotations

import asyncio
import os

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp.shared.exceptions import MCPError

GATEWAY = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8210/mcp")


async def main() -> None:
    transport = StreamableHttpTransport(GATEWAY, auth=os.environ["GATEWAY_CLAIM_AGENT_KEY"])
    async with Client(transport) as gateway:
        tools = await gateway.list_tools()
        print("Tools:", ", ".join(sorted(tool.name for tool in tools)))

        claim = await gateway.call_tool("undercover-app___get_claim", {"claim_id": "CLM-1001"})
        print("Claim:", claim.structured_content)
        plan = await gateway.call_tool("undercover-context___get_plan", {"plan": "economy"})
        print("Plan:", plan.structured_content)

        decision = {"decision": "approve", "payout": 300, "section": "4.2", "reason": "Bag lost by the airline"}
        await gateway.call_tool("undercover-app___record_decision", {"claim_id": "CLM-1001", **decision})
        paid = await gateway.call_tool("undercover-app___pay_claim", {"claim_id": "CLM-1001", "amount": 300})
        print("Paid:", paid.structured_content)

        try:
            await gateway.call_tool("undercover-app___pay_claim", {"claim_id": "CLM-1002", "amount": 4800})
        except MCPError as refusal:
            print("Refused:", refusal.error.message, refusal.error.data)


if __name__ == "__main__":
    asyncio.run(main())

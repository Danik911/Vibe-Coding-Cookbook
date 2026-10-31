"""The middleware that checks every tool call against the policy and records it."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from time import perf_counter
from typing import Any

import mcp_types as mt
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import Tool, ToolResult
from mcp.shared.exceptions import MCPError

from diy_gateway.audit import AuditLog
from diy_gateway.config import PolicyMode, PolicySettings
from diy_gateway.inbound import Principal, current_principal
from diy_gateway.policy import Decision, PolicyEngine, ToolCall

logger = logging.getLogger(__name__)

DENIED = "Tool Execution Denied"
POLICY_DENIED_CODE = -32003


class PolicyMiddleware(Middleware):
    """Decides every tool call before it reaches a target, as AgentCore Policy does.

    - `off`: no decisions, every call goes through and is still audited.
    - `log_only`: decisions are recorded and nothing is refused.
    - `enforce`: a call the policy doesn't allow never reaches its target.
    """

    def __init__(
        self,
        *,
        engine: PolicyEngine | None,
        settings: PolicySettings,
        inbound_mode: str,
        separator: str,
        targets: tuple[str, ...],
        audit: AuditLog,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._inbound_mode = inbound_mode
        self._separator = separator
        self._targets = targets
        self._audit = audit

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        tool = context.message.name
        principal = current_principal(self._inbound_mode)
        if principal is None:
            self._audit.refused(tool, "no authenticated caller")
            raise self._denial(f"{DENIED}: no authenticated caller")
        call = self._call(principal, tool, dict(context.message.arguments or {}))
        if call is None:
            # Only <target><separator><tool> names are served. FastMCP also resolves other
            # forms (such as hashed backend names) that skip the prefix, and with it the
            # target the policy would see, so they're refused whatever the mode.
            self._audit.refused(tool, "not a gateway tool name")
            raise self._denial(f"{DENIED}: {tool} is not a tool of this gateway")
        mode = self._settings.mode
        if mode is not PolicyMode.OFF:
            decision = await self._decide(call)
            enforced = mode is PolicyMode.ENFORCE
            self._audit.decision(call, decision, mode, enforced=enforced)
            if enforced and not decision.allowed:
                rules = ", ".join(decision.policy_ids) or "no policy permits it"
                raise self._denial(f"{DENIED}: {tool} refused by policy ({rules})", decision.policy_ids)
        started = perf_counter()
        try:
            result = await call_next(context)
        except Exception:
            self._audit.tool_result(call, outcome="error", elapsed_ms=(perf_counter() - started) * 1000)
            raise
        outcome = "error" if result.is_error else "ok"
        self._audit.tool_result(call, outcome=outcome, elapsed_ms=(perf_counter() - started) * 1000)
        return result

    async def on_list_tools(
        self,
        context: MiddlewareContext[mt.ListToolsRequest],
        call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]],
    ) -> Sequence[Tool]:
        """Leaves out the tools the caller may never call, when the policy is enforced.

        Cedar's partial evaluation decides it with the input unknown: a tool is hidden
        only when no input could be allowed. Every call is still decided in full.
        """
        tools = await call_next(context)
        if self._settings.mode is not PolicyMode.ENFORCE or not self._settings.hide_unpermitted_tools:
            return tools
        principal = current_principal(self._inbound_mode)
        if principal is None or self._engine is None:
            return []
        engine = self._engine
        calls = [self._call(principal, tool.name, {}) for tool in tools]
        try:
            visible = await asyncio.to_thread(lambda: [call is not None and engine.may_allow(call) for call in calls])
        except Exception as error:  # Listing never decides a call, so show the tools rather than fail.
            logger.warning("policy engine failed while listing tools: %s", type(error).__name__)
            return tools
        return [tool for tool, shown in zip(tools, visible, strict=True) if shown]

    def _call(self, principal: Principal, tool: str, arguments: dict[str, Any]) -> ToolCall | None:
        """The call, attributed to the one target whose prefix the name has, or None."""
        targets = [target for target in self._targets if tool.startswith(target + self._separator)]
        if len(targets) != 1:
            return None
        return ToolCall(principal=principal, target=targets[0], tool=tool, arguments=arguments)

    async def _decide(self, call: ToolCall) -> Decision:
        if self._engine is None:
            return Decision(allowed=False, errors=("no policy engine",))
        try:
            decision = await asyncio.to_thread(self._engine.evaluate, call)
        except Exception as error:  # A policy engine that can't answer must not let calls through.
            logger.warning("policy engine failed: %s", type(error).__name__)
            return Decision(allowed=False, errors=(f"policy engine failed: {type(error).__name__}",))
        if decision.allowed and decision.errors and self._settings.deny_on_evaluation_errors:
            return Decision(allowed=False, policy_ids=decision.policy_ids, errors=decision.errors)
        return decision

    def _denial(self, message: str, policy_ids: tuple[str, ...] = ()) -> Exception:
        """A refusal the agent should route to a person, not retry.

        As a protocol error (the default, as AgentCore does it) the MCP client raises it;
        as a tool error the model reads it as the tool's result.
        """
        if self._settings.denial == "tool_error":
            return ToolError(message)
        data = {"retryable": False, "policies": list(policy_ids)}
        return MCPError(code=POLICY_DENIED_CODE, message=message, data=data)

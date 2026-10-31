"""The audit trail: one JSON line per policy decision and per tool call.

On Lambda or ECS, stdout goes to CloudWatch Logs. With `emf_metrics`, each decision
line is also in CloudWatch's Embedded Metric Format, so CloudWatch counts
`AllowDecisions` and `DenyDecisions` by mode, as it does for AgentCore Policy.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO

from diy_gateway.config import AuditSettings, PolicyMode
from diy_gateway.policy import Decision, ToolCall


class AuditLog:
    def __init__(self, settings: AuditSettings, stream: TextIO | None = None) -> None:
        self._settings = settings
        self._stream = stream
        self._lock = threading.Lock()

    def decision(self, call: ToolCall, decision: Decision, mode: PolicyMode, *, enforced: bool) -> None:
        record: dict[str, Any] = {
            "event": "policy_decision",
            "principal": f"{call.principal.type}::{call.principal.id}",
            "tool": call.tool,
            "target": call.target,
            "decision": "ALLOW" if decision.allowed else "DENY",
            "mode": mode.value,
            "enforced": enforced,
            "policies": list(decision.policy_ids),
            "errors": list(decision.errors),
            "input": self._input(call.arguments),
        }
        if self._settings.emf_metrics:
            record |= self._emf(mode, allowed=decision.allowed)
        self._write(record)

    def tool_result(self, call: ToolCall, *, outcome: str, elapsed_ms: float) -> None:
        self._write(
            {
                "event": "tool_call",
                "principal": f"{call.principal.type}::{call.principal.id}",
                "tool": call.tool,
                "target": call.target,
                "outcome": outcome,
                "elapsed_ms": round(elapsed_ms, 1),
            }
        )

    def refused(self, tool: str, reason: str) -> None:
        self._write({"event": "refused", "tool": tool, "reason": reason})

    def _input(self, arguments: dict[str, Any]) -> dict[str, Any] | list[str]:
        if self._settings.log_argument_values:
            return arguments
        return sorted(arguments)

    def _emf(self, mode: PolicyMode, *, allowed: bool) -> dict[str, Any]:
        return {
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [
                    {
                        "Namespace": self._settings.metrics_namespace,
                        "Dimensions": [["Mode"]],
                        "Metrics": [
                            {"Name": "AllowDecisions", "Unit": "Count"},
                            {"Name": "DenyDecisions", "Unit": "Count"},
                        ],
                    }
                ],
            },
            "Mode": mode.value,
            "AllowDecisions": int(allowed),
            "DenyDecisions": int(not allowed),
        }

    def _write(self, record: dict[str, Any]) -> None:
        line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}, default=str)
        with self._lock:
            if self._stream is not None:
                self._stream.write(line + "\n")
                self._stream.flush()
            elif self._settings.destination == "stdout":
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
            else:
                with Path(self._settings.destination).open("a", encoding="utf-8") as file:
                    file.write(line + "\n")

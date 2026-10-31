"""Per-tool-call policy: what AgentCore Policy does with Cedar.

Every tool call is a Cedar request:

- principal: the caller, such as `Mcp::Agent::"claim-agent"` or `Mcp::User::"<sub>"`
- action: the tool, `Mcp::Action::"<target>___<tool>"`, in the action group
  `Mcp::Action::"<target>"`, so one rule can cover a whole target
- resource: the gateway, `Mcp::Gateway::"<resource_id>"`
- context: `{"input": <the tool's arguments>, "target": ..., "tool": ...}`

As on AgentCore, a JSON number in the input reads as a Cedar decimal, so a rule
compares it with `greaterThan(decimal("1000.0"))`, not `>`. Two engines evaluate the
same requests: Cedar in-process with `cedarpy`, or Amazon Verified Permissions.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from cedarpy import Decision as CedarDecision
from cedarpy import PolicySet, Schema, is_authorized, is_authorized_partial, validate_policies

from diy_gateway.inbound import Principal

DECIMAL_LIMIT = Decimal("922337203685477.5807")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    policy_ids: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCall:
    principal: Principal
    target: str
    tool: str
    arguments: dict[str, Any]


class PolicyEngine(Protocol):
    def evaluate(self, call: ToolCall) -> Decision: ...

    def may_allow(self, call: ToolCall) -> bool:
        """Whether some input could make the call allowed. Only for listing tools, never to decide."""
        ...


CEDAR_RESERVED_KEYS = frozenset({"__extn", "__entity", "__expr"})


def to_cedar(value: Any) -> Any:
    """A JSON value as Cedar JSON: numbers become decimals, lists become sets.

    Keys Cedar's JSON format reserves are refused, so a caller can't hand the policy a
    typed value of its own choosing, such as `{"__extn": {"fn": "decimal", "arg": "1.0"}}`.
    """
    if isinstance(value, bool | str):
        return value
    if isinstance(value, int | float):
        return {"__extn": {"fn": "decimal", "arg": _decimal_text(value)}}
    if isinstance(value, dict):
        reserved = CEDAR_RESERVED_KEYS & value.keys()
        if reserved:
            raise ValueError(f"the input uses a key Cedar reserves: {', '.join(sorted(reserved))}")
        return {str(key): to_cedar(item) for key, item in value.items() if item is not None}
    if isinstance(value, list | tuple):
        return [to_cedar(item) for item in value if item is not None]
    raise ValueError(f"unsupported value of type {type(value).__name__}")


def _decimal_text(number: float) -> str:
    """The number as a Cedar decimal, refused rather than rounded past four places,
    so 1000.00004 can't slip under a limit of 1000."""
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError("a number in the input is not finite")
    exact = Decimal(str(number))
    try:
        cedar = exact.quantize(Decimal("0.0001"))
    except InvalidOperation as error:
        raise ValueError("a number in the input can't be a Cedar decimal") from error
    if cedar != exact:
        raise ValueError("a number in the input has more than four decimal places")
    if abs(cedar) > DECIMAL_LIMIT:
        raise ValueError("a number in the input is outside Cedar's decimal range")
    return f"{cedar:.4f}"


class CedarRequestBuilder:
    """Builds the Cedar request and entities for a tool call, shared by both engines."""

    def __init__(self, namespace: str, resource_id: str) -> None:
        self.namespace = namespace
        self.resource_id = resource_id

    def uid(self, entity_type: str, entity_id: str) -> dict[str, str]:
        return {"type": f"{self.namespace}::{entity_type}", "id": entity_id}

    def literal(self, entity_type: str, entity_id: str) -> str:
        """The entity in Cedar's own syntax, as partial evaluation wants it."""
        return f"{self.namespace}::{entity_type}::{json.dumps(entity_id)}"

    def request(self, call: ToolCall) -> dict[str, Any]:
        return {
            "principal": self.uid(call.principal.type, call.principal.id),
            "action": self.uid("Action", call.tool),
            "resource": self.uid("Gateway", self.resource_id),
            "context": {
                "input": to_cedar(call.arguments),
                "target": call.target,
                "tool": call.tool,
            },
        }

    def entities(self, call: ToolCall, *, include_action: bool = True) -> list[dict[str, Any]]:
        """The principal and the gateway, and the action in its target's group.

        Verified Permissions takes action groups from its schema, so it leaves the action out.
        """
        principal_attrs = {
            key: to_cedar(value) for key, value in call.principal.attributes.items() if value is not None
        }
        entities = [
            {"uid": self.uid(call.principal.type, call.principal.id), "attrs": principal_attrs, "parents": []},
            {"uid": self.uid("Gateway", self.resource_id), "attrs": {}, "parents": []},
        ]
        if include_action:
            entities.append(
                {"uid": self.uid("Action", call.tool), "attrs": {}, "parents": [self.uid("Action", call.target)]}
            )
        return entities


class CedarEngine:
    """Evaluates Cedar in the gateway's own process: no network call and no per-request cost.

    With a schema, the policies are validated when the engine is built, and a call to a
    tool the schema doesn't declare is never allowed.
    """

    def __init__(self, policies: str, builder: CedarRequestBuilder, schema: str | None = None) -> None:
        self._policies = PolicySet.from_str(policies)
        self._schema = _schema(schema) if schema else None
        self._builder = builder
        if self._schema is not None:
            validation = validate_policies(policies, self._schema)
            if not validation.validation_passed:
                raise ValueError(f"the policies don't match the schema: {validation.errors}")

    def evaluate(self, call: ToolCall) -> Decision:
        try:
            request = self._builder.request(call)
        except ValueError as error:
            return Decision(allowed=False, errors=(str(error),))
        result = is_authorized(request, self._policies, self._builder.entities(call), schema=self._schema)
        annotations = result.diagnostics.id_annotations_by_reason or {}
        ids = tuple(annotations.get(reason, reason) for reason in result.diagnostics.reasons)
        errors = tuple(str(error) for error in result.diagnostics.errors)
        return Decision(allowed=result.decision == CedarDecision.Allow, policy_ids=ids, errors=errors)

    def may_allow(self, call: ToolCall) -> bool:
        """Cedar's partial evaluation with the input unknown: false only when no input could be allowed."""
        request = {
            "principal": self._builder.literal(call.principal.type, call.principal.id),
            "action": self._builder.literal("Action", call.tool),
            "resource": self._builder.literal("Gateway", self._builder.resource_id),
            "context": None,
        }
        try:
            result = is_authorized_partial(request, self._policies, self._builder.entities(call))
        except (ValueError, TypeError):
            return True
        return result.decision != CedarDecision.Deny


class VerifiedPermissionsEngine:
    """Evaluates the same request with Amazon Verified Permissions (`IsAuthorized`).

    The policies live in an AVP policy store, managed and audited in AWS. Each call is
    a network round trip and is billed per request.
    """

    def __init__(self, client: Any, policy_store_id: str, builder: CedarRequestBuilder) -> None:
        self._client = client
        self._policy_store_id = policy_store_id
        self._builder = builder

    def evaluate(self, call: ToolCall) -> Decision:
        try:
            request = self._builder.request(call)
        except ValueError as error:
            return Decision(allowed=False, errors=(str(error),))
        response = self._client.is_authorized(
            policyStoreId=self._policy_store_id,
            principal=_avp_uid(request["principal"]),
            action={"actionType": request["action"]["type"], "actionId": request["action"]["id"]},
            resource=_avp_uid(request["resource"]),
            context={"cedarJson": json.dumps(request["context"])},
            entities={"cedarJson": json.dumps(self._builder.entities(call, include_action=False))},
        )
        ids = tuple(policy["policyId"] for policy in response.get("determiningPolicies", []))
        errors = tuple(error["errorDescription"] for error in response.get("errors", []))
        return Decision(allowed=response["decision"] == "ALLOW", policy_ids=ids, errors=errors)

    def may_allow(self, call: ToolCall) -> bool:
        """Verified Permissions has no partial evaluation, so every tool is listed; calls are still decided."""
        return True


def _schema(text: str) -> Schema:
    """A Cedar schema in either of Cedar's formats: JSON (as Verified Permissions takes it) or Cedar."""
    return Schema.from_json_str(text) if text.lstrip().startswith("{") else Schema.from_str(text)


def _avp_uid(uid: dict[str, str]) -> dict[str, str]:
    return {"entityType": uid["type"], "entityId": uid["id"]}

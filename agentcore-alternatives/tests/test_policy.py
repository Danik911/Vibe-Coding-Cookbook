"""The policy engines: Cedar in-process and Amazon Verified Permissions, on the same requests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from diy_gateway.inbound import Principal
from diy_gateway.policy import CedarEngine, CedarRequestBuilder, ToolCall, VerifiedPermissionsEngine, to_cedar

ROOT = Path(__file__).resolve().parents[1]
AGENT = Principal("Agent", "claim-agent")
HANDLER = Principal("User", "handler-dana")
PAY = "undercover-app___pay_claim"


@pytest.fixture
def builder() -> CedarRequestBuilder:
    return CedarRequestBuilder("Mcp", "undercover-gateway")


@pytest.fixture
def engine(builder: CedarRequestBuilder) -> CedarEngine:
    return CedarEngine((ROOT / "policies" / "gateway.cedar").read_text(encoding="utf-8"), builder)


def call(principal: Principal, tool: str, **arguments: Any) -> ToolCall:
    return ToolCall(principal=principal, target=tool.split("___", maxsplit=1)[0], tool=tool, arguments=arguments)


def test_numbers_become_cedar_decimals_and_lists_become_sets():
    converted = to_cedar({"amount": 1000, "rate": 0.5, "ok": True, "tags": ["a"], "skip": None})
    assert converted == {
        "amount": {"__extn": {"fn": "decimal", "arg": "1000.0000"}},
        "rate": {"__extn": {"fn": "decimal", "arg": "0.5000"}},
        "ok": True,
        "tags": ["a"],
    }


@pytest.mark.parametrize("number", [float("nan"), float("inf"), 10**16, 1000.00004])
def test_numbers_cedar_cant_hold_exactly_are_refused(number: float):
    with pytest.raises(ValueError, match="number"):
        to_cedar({"amount": number})


@pytest.mark.parametrize("key", ["__extn", "__entity", "__expr"])
def test_keys_cedar_reserves_are_refused_so_a_caller_cant_forge_a_value(key: str):
    with pytest.raises(ValueError, match="reserves"):
        to_cedar({"amount": {key: {"fn": "decimal", "arg": "1.0000"}}})


@pytest.mark.parametrize(("amount", "allowed"), [(400, True), (1000, True), (1000.01, False), (4800, False)])
def test_the_payment_limit(engine: CedarEngine, amount: float, allowed: bool):
    decision = engine.evaluate(call(AGENT, PAY, claim_id="CLM-1", amount=amount))
    assert decision.allowed is allowed
    if not allowed:
        assert decision.policy_ids == ("payment-limit",)


def test_a_payment_with_no_amount_is_refused(engine: CedarEngine):
    decision = engine.evaluate(call(AGENT, PAY, claim_id="CLM-1"))
    assert (decision.allowed, decision.policy_ids) == (False, ("payment-needs-amount",))


def test_an_amount_that_isnt_a_number_is_reported_as_an_error(engine: CedarEngine):
    decision = engine.evaluate(call(AGENT, PAY, claim_id="CLM-1", amount="5000"))
    assert decision.errors


def test_a_handler_may_read_the_context_layer_but_not_call_the_app(engine: CedarEngine):
    assert engine.evaluate(call(HANDLER, "undercover-context___lookup_term", term="deductible")).allowed
    assert not engine.evaluate(call(HANDLER, "undercover-app___get_claim", claim_id="CLM-1")).allowed


def test_listing_hides_only_tools_no_input_could_unlock(engine: CedarEngine):
    assert engine.may_allow(call(AGENT, PAY))
    assert not engine.may_allow(call(HANDLER, PAY))
    assert engine.may_allow(call(HANDLER, "undercover-context___get_plan"))


def test_the_shipped_schema_refuses_unknown_tools_and_unexpected_arguments(builder: CedarRequestBuilder):
    schema = (ROOT / "policies" / "gateway.schema.json").read_text(encoding="utf-8")
    engine = CedarEngine((ROOT / "policies" / "gateway.cedar").read_text(encoding="utf-8"), builder, schema)
    assert engine.evaluate(call(AGENT, "undercover-app___get_claim", claim_id="CLM-1")).allowed
    assert not engine.evaluate(call(AGENT, PAY, claim_id="CLM-1", amount=4800)).allowed
    assert not engine.evaluate(call(AGENT, "undercover-app___drop_database")).allowed
    assert not engine.evaluate(call(AGENT, "undercover-app___get_claim", claim_id="CLM-1", extra="x")).allowed
    assert not engine.evaluate(call(AGENT, PAY, claim_id="CLM-1", amount="5000")).allowed


def test_the_shipped_schema_takes_principals_from_jwts(builder: CedarRequestBuilder):
    schema = (ROOT / "policies" / "gateway.schema.json").read_text(encoding="utf-8")
    policies = (ROOT / "policies" / "gateway.cedar").read_text(encoding="utf-8")
    policies += '\npermit (principal == Mcp::Agent::"cognito-client", action, resource);'
    engine = CedarEngine(policies, builder, schema)
    cognito_agent = Principal("Agent", "cognito-client", {"scopes": ["undercover-gateway/tools"]})
    handler = Principal("User", "handler-dana", {"scopes": []})
    assert engine.evaluate(call(cognito_agent, "undercover-app___get_claim", claim_id="CLM-1")).allowed
    assert engine.evaluate(call(handler, "undercover-context___lookup_term", term="deductible")).allowed


class FakeVerifiedPermissions:
    def __init__(self, decision: str) -> None:
        self.decision = decision
        self.requests: list[dict[str, Any]] = []

    def is_authorized(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return {"decision": self.decision, "determiningPolicies": [{"policyId": "p-123"}], "errors": []}


def test_verified_permissions_gets_the_same_request_as_cedar(builder: CedarRequestBuilder):
    avp = FakeVerifiedPermissions("DENY")
    decision = VerifiedPermissionsEngine(avp, "store-1", builder).evaluate(call(AGENT, PAY, amount=4800))
    request = avp.requests[0]
    assert (decision.allowed, decision.policy_ids) == (False, ("p-123",))
    assert request["policyStoreId"] == "store-1"
    assert request["principal"] == {"entityType": "Mcp::Agent", "entityId": "claim-agent"}
    assert request["action"] == {"actionType": "Mcp::Action", "actionId": PAY}
    assert json.loads(request["context"]["cedarJson"])["input"]["amount"] == {
        "__extn": {"fn": "decimal", "arg": "4800.0000"}
    }
    assert all(entity["uid"]["type"] != "Mcp::Action" for entity in json.loads(request["entities"]["cedarJson"]))

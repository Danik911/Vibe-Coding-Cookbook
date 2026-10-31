"""A stand-in for UnderCover's app: the claim agent's six operations behind an API key.

It serves the agent's own OpenAPI document at /api/agent/openapi.json, as UnderCover's
backend does from Week 3 Day 2, with no `servers` entry: the gateway adds the address.
A human-only route (the sign-off) is left out of that document, so no agent can reach it.

Run: uv run --env-file .env -m uvicorn examples.demo_upstreams.app:app --port 8200
"""

from __future__ import annotations

import os
import secrets
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

APPROVAL_LIMIT = 1000.0
AGENT_OPERATIONS = (
    "get_claim",
    "get_policy",
    "get_claim_history",
    "calculate_payout",
    "record_decision",
    "pay_claim",
)

app = FastAPI(title="UnderCover stand-in")

CLAIMS: dict[str, dict] = {
    "CLM-1001": {"customer_id": "CUS-3001", "policy_id": "POL-2001", "benefit": "baggage", "claimed": 400.0},
    "CLM-1002": {"customer_id": "CUS-3002", "policy_id": "POL-2002", "benefit": "medical", "claimed": 4800.0},
}
POLICIES = {
    "POL-2001": {"plan": "economy", "customer_id": "CUS-3001"},
    "POL-2002": {"plan": "premium", "customer_id": "CUS-3002"},
}
DECISIONS: dict[str, dict] = {}
PAYMENTS: dict[str, float] = {}


def agent_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.environ.get("DEMO_APP_API_KEY", "")
    if not expected or not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="This route needs the agent's API key")


AgentKey = Depends(agent_key)


class PayoutRequest(BaseModel):
    amount_claimed: float = Field(description="The amount the customer claimed, in US dollars")
    deductible: float = Field(description="The plan's deductible, in US dollars")


class DecisionRequest(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: float
    section: str
    reason: str


class PaymentRequest(BaseModel):
    amount: float = Field(description="The amount to pay, in US dollars")


def claim_or_404(claim_id: str) -> dict:
    if claim_id not in CLAIMS:
        raise HTTPException(status_code=404, detail=f"No claim {claim_id}")
    return CLAIMS[claim_id]


@app.get("/api/claims/{claim_id}", operation_id="get_claim", dependencies=[AgentKey])
def get_claim(claim_id: str) -> dict:
    """A claim with its customer, policy, benefit and amount claimed."""
    return {"claim_id": claim_id, **claim_or_404(claim_id), "decision": DECISIONS.get(claim_id)}


@app.get("/api/policies/{policy_id}", operation_id="get_policy", dependencies=[AgentKey])
def get_policy(policy_id: str) -> dict:
    """A policy with its plan and customer."""
    if policy_id not in POLICIES:
        raise HTTPException(status_code=404, detail=f"No policy {policy_id}")
    return {"policy_id": policy_id, **POLICIES[policy_id]}


@app.get("/api/customers/{customer_id}/claims", operation_id="get_claim_history", dependencies=[AgentKey])
def get_claim_history(customer_id: str) -> list[dict]:
    """The customer's earlier claims."""
    return [{"claim_id": cid, **c} for cid, c in CLAIMS.items() if c["customer_id"] == customer_id]


@app.post("/api/claims/{claim_id}/payout", operation_id="calculate_payout", dependencies=[AgentKey])
def calculate_payout(claim_id: str, body: PayoutRequest) -> dict:
    """The payout for a claim: the amount claimed less the deductible."""
    claim_or_404(claim_id)
    return {"claim_id": claim_id, "payout": max(body.amount_claimed - body.deductible, 0.0)}


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision", dependencies=[AgentKey])
def record_decision(claim_id: str, body: DecisionRequest) -> dict:
    """Record the decision on a claim, with its payout, section and reason."""
    claim_or_404(claim_id)
    DECISIONS[claim_id] = body.model_dump()
    return {"claim_id": claim_id, "recorded": True}


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim", dependencies=[AgentKey])
def pay_claim(claim_id: str, body: PaymentRequest) -> dict:
    """Pay an approved claim, up to the approval limit."""
    if body.amount > APPROVAL_LIMIT:
        raise HTTPException(
            status_code=403, detail=f"Payments over the approval limit of ${APPROVAL_LIMIT:,.0f} need a sign-off"
        )
    claim_or_404(claim_id)
    decision = DECISIONS.get(claim_id)
    if not decision or decision["decision"] != "approve":
        raise HTTPException(status_code=409, detail=f"{claim_id} has no approval to pay")
    if claim_id in PAYMENTS:
        raise HTTPException(status_code=409, detail=f"{claim_id} is already paid")
    PAYMENTS[claim_id] = body.amount
    return {"claim_id": claim_id, "paid": body.amount}


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str) -> dict:
    """A handler's sign-off. Human-only: it isn't in the agent's API document."""
    raise HTTPException(status_code=401, detail="Sign in as a handler to sign off")


@app.get("/api/agent/openapi.json", include_in_schema=False, dependencies=[AgentKey])
def agent_openapi() -> dict:
    """The agent's own API document: only its operations, and no `servers`."""
    routes = [route for route in app.routes if getattr(route, "operation_id", None) in AGENT_OPERATIONS]
    spec = get_openapi(title="UnderCover agent API", version="1.0.0", routes=routes)
    spec.pop("servers", None)
    return spec


@app.get("/api/health")
def health() -> dict:
    return {"healthy": True}

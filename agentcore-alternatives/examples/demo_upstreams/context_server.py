"""A stand-in for UnderCover's context layer: a read-only FastMCP server.

Every answer names its source, as data governance's files in `context/` do.
Run: uv run python -m examples.demo_upstreams.context_server   (serves 127.0.0.1:8206/mcp)
"""

from __future__ import annotations

import uvicorn
from fastmcp import FastMCP

SOURCE = {"system": "Policy administration", "owner": "Data governance", "reviewed": "2026-09-30"}
GLOSSARY = {
    "pre-existing condition": "A condition diagnosed or treated in the 90 days before the policy started.",
    "deductible": "The part of each claim the customer pays before the policy pays.",
}
PLANS = {
    "economy": {"medical_limit": 50000, "baggage_limit": 1000, "deductible": 100},
    "premium": {"medical_limit": 250000, "baggage_limit": 2500, "deductible": 50},
}

context = FastMCP("undercover-context")


@context.tool
def lookup_term(term: str) -> dict:
    """A term's definition in the policy wording."""
    definition = GLOSSARY.get(term.lower())
    if definition is None:
        return {"error": f"Unknown term. Defined terms: {', '.join(sorted(GLOSSARY))}", "source": SOURCE}
    return {"term": term, "definition": definition, "source": SOURCE}


@context.tool
def get_plan(plan: str) -> dict:
    """One plan's limits and deductible: economy or premium."""
    if plan not in PLANS:
        return {"error": f"Unknown plan. Plans: {', '.join(PLANS)}", "source": SOURCE}
    return {"plan": plan, **PLANS[plan], "source": SOURCE}


def main() -> None:
    app = context.http_app(path="/mcp", stateless_http=True, json_response=True)
    uvicorn.run(app, host="127.0.0.1", port=8206)


if __name__ == "__main__":
    main()

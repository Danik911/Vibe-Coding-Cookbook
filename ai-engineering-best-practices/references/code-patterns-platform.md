# Code patterns: backend and platform

> When to read this: you are writing or reviewing the **non-agent** code around an agent: backend auth, money limits, the OpenAPI document that becomes Gateway tools, Lambda packaging, a context-layer MCP server, an IAM-protected internal Lambda and the single-run lock. Snippets are minimal and written for this skill, not copied from the course. Sibling pattern files: AgentCore Gateway/Identity/Policy/Memory/Runtime setup, IAM, budgets and teardown in [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md); agent-side snippets in [code-patterns-agents.md](code-patterns-agents.md); LangGraph graphs, pauses and dispatch in [code-patterns-langgraph.md](code-patterns-langgraph.md). `<project>`, `<region>`, `<account-id>` are placeholders; never hard-code real keys, accounts, ARNs or URLs.

## Contents

| # | Pattern | Use when |
|---|---|---|
| 1 | [API-key dependency](#1-api-key-dependency-for-agent-routes) | One backend serves an agent and people |
| 2 | [Sign-in (JWT) and role check](#2-sign-in-jwt-and-role-check) | Only some users may approve over a limit |
| 3 | [Money and limits](#3-money-and-limits-in-the-backend) | An agent can cause a payment |
| 4 | [OpenAPI for the agent](#4-openapi-document-for-the-agents-operations) | A Gateway turns your API into tools |
| 5 | [FastAPI on Lambda](#5-fastapi-on-lambda-with-mangum) | Deploying the backend to Lambda |
| 6 | [Context layer (FastMCP)](#6-context-layer-as-a-fastmcp-server-with-provenance) | Owners' files become read-only tools |
| 7 | [Lambda behind IAM auth](#7-internal-lambda-behind-iam-auth) | A service only the Gateway may call |
| 8 | [Run lock + heartbeat](#8-single-run-lock-and-heartbeat) | One piece of agent work at a time |

Gateway, Cedar, Runtime, `agentcore.json`, invoking a Runtime, AgentCore Memory and IAM/budget/teardown are in [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md).

## Versions (as taught in the course, Oct 2026; re-check before use)

| Item | Reference build |
|---|---|
| Python; Lambda runtime | 3.12; `python3.12` |
| `fastapi` / `mangum` / `mcp` / `pyjwt[crypto]` / `sqlalchemy` | `>=0.141.1` / `>=0.22.0` / `>=1.30.0` / `>=2.15.1` / `>=2.1.3` |
| `boto3` | `>=1.43.108` |

## Key principles

1. **Enforce in the backend, not the prompt, and fail closed.** Limits, roles and "who may call" live in code the model cannot argue with; no key configured matches nothing; a Gateway policy is a second layer.
2. **The agent's key is not a user.** A key proves "the agent's side"; it must never satisfy a user-only route, or an injected agent could approve its own work.
3. **Whatever the Gateway can see, the agent can call.** The OpenAPI document is the allow-list; keep human-only actions out of it.
4. **New IAM roles and permissions propagate slowly:** wrap first calls in a retry loop.

---

## 1. API-key dependency for agent routes

**Use when:** one backend serves a dashboard (users) and an agent (machine) and some routes are agent-only.

```python
import os, secrets
from typing import Annotated
from fastapi import Depends, Header, HTTPException
from fastapi.security import APIKeyHeader

key_header = APIKeyHeader(name="X-API-Key", auto_error=False)    # we raise the 401 ourselves

def is_agents_key(given: str | None) -> bool:
    expected = os.getenv("AGENT_API_KEY", "")                    # read per request; UnderCover names it UNDERCOVER_API_KEY
    if not expected or given is None:                            # unset key: nothing matches
        return False
    return secrets.compare_digest(given.encode(), expected.encode())

def agent_only(given: Annotated[str | None, Depends(key_header)]) -> None:
    if not is_agents_key(given):
        raise HTTPException(401, "This needs the agent's API key", headers={"WWW-Authenticate": "APIKey"})

@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision",
          dependencies=[Depends(agent_only)])
def record_decision(claim_id: str, request: DecisionRequest): ...

# On every user route: a request that ALSO carries the agent's key is refused.
def refuse_agent_key(key: Annotated[str | None, Header(alias="X-API-Key", include_in_schema=False)] = None):
    if is_agents_key(key):
        raise HTTPException(403, "A request with the agent's key is the agent's, not a user's")

def test_every_operation_declares_its_gate(app):          # a new route without a gate fails CI
    assert {r.operation_id for r in app.routes if isinstance(r, APIRoute)} == OPEN | AGENT_ONLY | SHARED | USER_ONLY
```

**Pitfalls:** use a random key of 32+ letters and digits (`secrets.token_hex(32)`), never printed; `==` leaks timing. Shared reads accept the key *or* a sign-in (401 for neither); `/health` stays open. The backend may start without the key (users still work) but the agent's service should refuse to start without it.

**Source:** `origin/week3day5-end:backend/api_key.py`, `backend/dependencies.py`, `backend/tests/gates.py`; `labs/week3day2_product_SECURE.md` Step 1.

## 2. Sign-in (JWT) and role check

**Use when:** users sign in with a hosted provider (Supabase Auth in the course) and only a senior role may act over a limit.

```python
import os
from functools import cache
import jwt                                                   # pyjwt[crypto]

@cache
def jwks() -> jwt.PyJWKClient:                               # caches keys; refetches for an unseen key id
    return jwt.PyJWKClient(f"{os.environ['SUPABASE_URL']}/auth/v1/.well-known/jwks.json")   # UnderCover names it VITE_SUPABASE_URL

def email_of(token: str) -> str:                             # NotSignedIn / KeysUnreachable are our own exceptions
    try:
        key = jwks().get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key, algorithms=[key.algorithm_name], audience="authenticated",
                            leeway=30, options={"require": ["exp", "email"]})
    except jwt.PyJWKClientConnectionError as e:
        raise KeysUnreachable(str(e)) from e                 # -> 503: the token may be fine
    except jwt.PyJWTError as e:
        raise NotSignedIn(str(e)) from e                     # -> 401
    return claims["email"]

def signed_in(creds: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())], db: Database) -> User:
    try:
        email = email_of(creds.credentials)
    except NotSignedIn:
        raise HTTPException(401, "Please sign in again", headers={"WWW-Authenticate": "Bearer"})
    except KeysUnreachable:
        raise HTTPException(503, "Sign-in can't be checked right now")
    user = find_user_by_email(db, email)
    if user is None:                                         # authenticated is not authorised
        raise HTTPException(403, "That sign-in isn't one of our handlers")
    return user

def senior(action: str):
    def check(user: Annotated[User, Depends(signed_in)]) -> User:
        if not user.can_approve_over_limit:                  # the role comes from OUR table, not the token
            raise HTTPException(403, f"Only a senior handler can {action}. {user.name} can't.")
        return user
    return check

@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off(claim_id: str, user: Annotated[User, Depends(senior("sign this off"))], db: Database): ...
```

**Pitfalls:** always verify signature, `exp`, audience and algorithm. Hiding a button is not enforcement; check on the route. Name the action in the 403 so the UI can explain. Keep sign-off off the agent's OpenAPI document. A user's token handed to an agent must never be logged or saved ([copilot-pattern.md](copilot-pattern.md)).

**Source:** `origin/week3day5-end:backend/auth.py`, `backend/dependencies.py` (`senior`), `backend/main.py` (`sign_off_claim`).

## 3. Money and limits in the backend

**Use when:** any route moves money or crosses a business threshold.

```python
from decimal import Decimal, ROUND_HALF_UP

def cents(value) -> Decimal:                                 # exact; never add up binary floats
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim", dependencies=[Depends(agent_only)])
def pay_claim(claim_id: str, request: PaymentRequest, db: Database) -> Claim:
    amount, limit = cents(request.amount), current_limit(db)       # limit from the settings in force
    if amount > limit:                                             # BEFORE reading the claim: same answer on any claim
        raise HTTPException(403, f"A payout over {usd(limit)} needs a handler's sign-off")
    claim = find_claim(db, claim_id)
    if claim.decision != "approve":
        raise HTTPException(409, "Not approved")
    if claim.paid_at:                                              # pay once; the same call is a no-op
        if amount == claim.amount:
            return claim
        raise HTTPException(409, "Already paid")
    if amount != claim.approved_payout:
        raise HTTPException(422, f"Amount must be the approved {usd(claim.approved_payout)}")
    record_payment(db, claim)
```

**Pitfalls:** the reference build keeps amounts as floats rounded to the cent (`round(x, 2)`); fine for a demo, but a new system should store integer cents or `NUMERIC`/`Decimal`. Store the limit in force **on the decision** so a settings change never rewrites history. Keep the field name the Gateway policy reads (`amount`); renaming silently disables the Cedar rule (pattern 2 of [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)). A human sign-off records the payment inside the sign-off so it does not need the agent. Validate decision records in code (reason, section relied on, who decided) and answer 422 naming the rule so the model can fix its call.

**Source:** `origin/week3day5-end:backend/main.py` (`pay_claim`, `record_decision`), `backend/payout.py`, `backend/records.py`.

## 4. OpenAPI document for the agent's operations

**Use when:** a Gateway (or any tool bridge) should expose only some routes as tools.

```python
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, iter_route_contexts    # newer FastAPI; (verify) older: filter app.routes

AGENT_OPERATIONS = {"get_claim", "get_policy", "get_claim_history",
                    "calculate_payout", "record_decision", "pay_claim"}

def agent_document(app) -> dict:
    routes = [c for c in iter_route_contexts(app.routes)
              if isinstance(c.route, APIRoute) and c.route.operation_id in AGENT_OPERATIONS]
    doc = get_openapi(title=f"{app.title} agent", version=app.version, routes=routes)
    doc["components"].pop("securitySchemes", None)           # a Gateway OpenAPI target does not support them
    for operations in doc["paths"].values():
        for operation in operations.values():
            operation.pop("security", None)                  # the credential provider sends the key instead
    return doc                                               # no "servers": the deployment adds the address

@app.get("/api/agent/openapi.json", operation_id="get_agent_api", dependencies=[HandlerOrAgent])
def get_agent_api() -> dict: return agent_document(app)
```

Route conventions: every operation has an `operation_id` (the tool name, `<target>___<operation_id>` on the Gateway), a one-line docstring (the description) and no optional inputs.

**Pitfalls:** the Gateway makes a tool of **every** operation in the document, so build from an explicit allow-list and test the exact set and that `servers` is absent. At deploy time fetch it with the key, set `doc["servers"] = [{"url": app_url}]`, upload inline (pattern 1 of [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)), and re-upload after route changes.

**Source:** `origin/week3day5-end:backend/agent_api.py`; `labs/week3day2_product_SECURE.md` Step 3; `labs/week3day2_lab2.ipynb`.

## 5. FastAPI on Lambda with Mangum

**Use when:** the same app runs on a laptop (uvicorn) and on Lambda behind a Function URL.

```python
from mangum import Mangum
app = FastAPI(lifespan=seed_if_empty)                       # seeding is for the laptop
handler = Mangum(app, lifespan="off")                       # Lambda Handler = "backend.main.handler"

def engine_for(url, on_lambda):                             # on_lambda: "AWS_LAMBDA_FUNCTION_NAME" in os.environ
    if on_lambda:                                           # one connection per request, none kept
        return create_engine(url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    return create_engine(url, pool_size=4, max_overflow=0, pool_pre_ping=True)
```
```bash
uv export --only-group server --no-hashes --no-emit-project --output-file build/requirements.txt
uv pip install --target build/lambda --python-platform x86_64-manylinux2014 --python-version 3.12 --only-binary :all: -r build/requirements.txt
```
```python
logs.create_log_group(logGroupName=f"/aws/lambda/{NAME}")    # create it first with retention, else logs live forever
logs.put_retention_policy(logGroupName=f"/aws/lambda/{NAME}", retentionInDays=7)
lam.create_function(FunctionName=NAME, Role=role_arn, Code={"ZipFile": zip_bytes}, Runtime="python3.12",
    Handler="backend.main.handler", Timeout=30, MemorySize=1024, Tags={"project": "<project>"},
    Environment={"Variables": {"DATABASE_URL": pooled_url, "SUPABASE_URL": auth_url, "AGENT_API_KEY": key}})
    # UnderCover names: VITE_SUPABASE_URL, UNDERCOVER_API_KEY
    # retry on InvalidParameterValueException: a new role is not visible at once
lam.create_function_url_config(FunctionName=NAME, AuthType="NONE")                   # public HTTPS address
for sid, extra in [("public-url", {"Action": "lambda:InvokeFunctionUrl", "FunctionUrlAuthType": "NONE"}),
                   ("public-invoke", {"Action": "lambda:InvokeFunction", "InvokedViaFunctionUrl": True})]:
    lam.add_permission(FunctionName=NAME, StatementId=sid, Principal="*", **extra)   # both, or every call is 403
```

**Pitfalls:** `AuthType="NONE"` is **public**: every route needs its own gate (patterns 1-2); use `AWS_IAM` for internal services (pattern 7). The file system is read-only and each concurrent request is its own copy: no writes, no pooled connections, no prepared statements through a transaction pooler (port 6543). Keep a `server` dependency group equal to what the backend imports and check it in an isolated env. Build for Linux; the zip limit taught was 50 MB. Updating in place keeps the URL; deleting the function loses it.

**Source:** `origin/week3day5-end:backend/main.py` (end), `backend/database.py` (`engine_for`); `labs/week3day2_lab2.ipynb`, `labs/week3day4_aws.py` (`deploy_app`); SECURE brief Step 4.

## 6. Context layer as a FastMCP server with provenance

**Use when:** data owners' files (glossary, plans, rules, documents) reach agents as read-only tools whose every answer says where it came from.

```python
# files.py. Each owner's file starts with front matter:  source: {system: ..., owner: ..., reviewed: "YYYY-MM-DD"}
FILES = {name: read_yaml(name) for name in ("glossary.yaml", "plans.yaml")}   # read once at import, own folder only
PlanName = Literal["economy", "premium", "first"]                             # Literal => constrained input schema

def sources_of(file: str) -> list[dict]:
    return [{"file": file} | FILES[file]["source"]]           # file + system + owner + review date

def get_plan(plan: PlanName) -> dict:
    found = next(p for p in FILES["plans.yaml"]["plans"] if p["plan"] == plan)
    return {"plan": found, "sources": sources_of("plans.yaml")}               # a search with no hit has sources: []

# server.py
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

def build_server(security=None) -> FastMCP:
    server = FastMCP("<project>-context", port=8006, stateless_http=True, json_response=True,
                     transport_security=security)
    @server.tool(annotations=ToolAnnotations(readOnlyHint=True))
    def get_plan(plan: files.PlanName) -> dict:
        """Get a plan's limits, waiting periods and deductible."""
        return files.get_plan(plan)
    return server
```

**Pitfalls:** provenance (owner, review date) is the product: it lets the agent cite and a human judge staleness; never attach a source to an empty result. Only this server reads the owners' files; the backend seeds from them through one module. Serves at `/mcp` (laptop: port 8006). Ownership and governance: [context-layer-and-integrations.md](context-layer-and-integrations.md).

**Source:** `origin/week3day5-end:context/server.py`, `context/files.py`; `context/plans.yaml` (front matter).

## 7. Internal Lambda behind IAM auth

**Use when:** a service (the context layer) must be reachable only by the Gateway and your own IAM identities.

```python
def handler(event, context):                                # fresh server per request: Mangum runs startup/shutdown each time
    app = build_server(TransportSecuritySettings(enable_dns_rebinding_protection=False)).streamable_http_app()
    return Mangum(app, lifespan="auto")(event, context)     # DNS-rebinding guard would refuse the Function URL host; IAM guards instead

url = lam.create_function_url_config(FunctionName=CONTEXT_FN, AuthType="AWS_IAM")["FunctionUrl"]
```
Callers sign each request with SigV4 using the **callee's service name** (`"lambda"` for a Function URL, `"bedrock-agentcore"` for a Gateway):

```python
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

class Sign(httpx.Auth):
    requires_request_body = True
    def __init__(self, session, service):
        self.creds, self.region, self.service = session.get_credentials(), session.region_name, service
    def auth_flow(self, request):
        signed = AWSRequest(method=request.method, url=str(request.url), data=request.content,
            headers={"Host": request.url.netloc.decode(), "Content-Type": request.headers.get("content-type", "")})
        SigV4Auth(self.creds.get_frozen_credentials(), self.service, self.region).add_auth(signed)
        for h in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token"):
            if h in signed.headers:
                request.headers[h] = signed.headers[h]
        yield request
```
Gateway role permission (resource-scoped): `{"Action": ["lambda:InvokeFunctionUrl", "lambda:InvokeFunction"], "Resource": "arn:aws:lambda:<region>:<account-id>:function:<project>-context"}`.

**Pitfalls:** test both ways: unsigned POST to `/mcp` is refused, signed lists the tools. The function needs no env vars or keys (everything served is packaged); the Gateway's role is the credential. A new role/permission can take about a minute; early calls may fail with "Failed to obtain execution role credentials": retry.

**Source:** `origin/week3day5-end:context/server.py` (`handler`); `labs/week3day3.ipynb` Parts 2-3; `labs/week3day4_aws.py` (`deploy_context`).

## 8. Single-run lock and heartbeat

**Use when:** only one piece of agent work may run at a time (batch dispatch, evaluation) and crashed work must not block forever.

```python
QUIET = timedelta(minutes=5)                                # the agent beats every 60 s

def take_lock(db):                                          # one-row table; the transaction's FIRST write
    got = db.execute(update(locks).where(locks.c.name == "agent_work").values(taken_at=now()))
    if got.rowcount != 1:                                   # Postgres locks only a row the UPDATE finds
        raise RuntimeError("Lock row missing: reseed")

def clear_the_way(db):                                      # a concurrent start waits here, then sees our work
    take_lock(db)
    db.execute(update(runs).where(runs.c.status == "running", runs.c.heard_at < stamp(now_utc() - QUIET))
               .values(status="stopped", stopped_because="The agent stopped answering"))
    db.commit(); take_lock(db)                              # keep the stop; take the lock again
    if kind := db.execute(select(runs.c.kind).where(runs.c.status == "running")).scalar():
        raise HTTPException(409, f"A {kind} is running")
# route: clear_the_way -> insert run -> commit -> ask the agent -> if not taken, stop the run with the reason

@contextmanager
def beating(tell, interval=60.0):                           # agent side: "still working", never fatal
    stopped = threading.Event()
    def beat():
        while not stopped.wait(interval):
            try: tell()
            except Exception as e: log.warning("heartbeat failed: %s", e)
    t = threading.Thread(target=beat, daemon=True); t.start()
    try: yield
    finally: stopped.set(); t.join()

def move(db, claim_id, old, new, **cols) -> bool:           # compare-and-set: only the first of two requests wins
    r = db.execute(update(claims).where(claims.c.claim_id == claim_id, claims.c.status == old).values(status=new, **cols))
    return r.rowcount == 1                                  # False => 409
```

**Pitfalls:** the lock is the database's, so it survives Lambda copies and Runtime sessions. The beat interval must be far under `QUIET`. Use compare-and-set for every state move (sign-off, send-back, take) so double clicks and retries are safe. See [durable-state-and-hitl.md](durable-state-and-hitl.md) and [swarms-and-scale.md](swarms-and-scale.md).

**Source:** `origin/week3day5-end:backend/agent_work.py`, `backend/stops.py`, `agent/heartbeat.py`, `backend/main.py` (`move_claim`), `backend/database.py` (`locks`).

---

## Decisions to make with the developer

| Question | Options and trade-off | Default |
|---|---|---|
| How does the agent authenticate to your API? | Shared key (simple, rotate by redeploy) vs IAM/OIDC (stronger, more setup) | Key in AgentCore Identity, sent by the Gateway |
| Amount type; who enforces limits | Integer cents / `Decimal` vs float; app only vs app + Cedar | Cents or `Decimal`; both layers, Cedar in log-only first |
| Backend host | Lambda + Function URL (cheap, public) vs container service | Lambda; IAM auth for internal services |

## In UnderCover

FastAPI backend on Lambda (public Function URL, key and sign-in gates), the context layer on a second Lambda behind IAM auth, and one DB lock. The Gateway, Cedar, Runtimes and teardown are in [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md). See [undercover-case-study.md](undercover-case-study.md).

## Related

[security-and-guardrails.md](security-and-guardrails.md) | [context-layer-and-integrations.md](context-layer-and-integrations.md) | [production-deployment-aws.md](production-deployment-aws.md) | [rag-memory-and-mcp.md](rag-memory-and-mcp.md) | [swarms-and-scale.md](swarms-and-scale.md) | [durable-state-and-hitl.md](durable-state-and-hitl.md) | [copilot-pattern.md](copilot-pattern.md) | [code-patterns-agents.md](code-patterns-agents.md) | [code-patterns-langgraph.md](code-patterns-langgraph.md) | [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md)

## Sources

Reference builds (read-only): `origin/week3day5-end:` `backend/{api_key,auth,dependencies,main,agent_api,agent_work,stops,records,money,payout,database}.py`, `context/{server,files}.py`, `agent/heartbeat.py`, `pyproject.toml`, `docs/TECH_STACK.md`. Local: `labs/week3day4_aws.py` (`deploy_app`, `deploy_context`), `labs/week3day2_product_SECURE.md`. Notebooks: `week3day2_lab2`, `week3day3`.

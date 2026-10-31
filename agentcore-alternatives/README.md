# AgentCore alternatives: tools, policy and identity on plain Amazon Bedrock

This folder is for teams that can call Amazon Bedrock's models but can't use Amazon Bedrock AgentCore, and still want to build something like UnderCover. It covers research, options and a working setup.

It focuses on what AgentCore Gateway, Policy and Identity do in the course: one MCP endpoint for the agent's tools, a Cedar policy on every tool call, and credentials the agent never holds. Runtime and Memory get shorter treatment in [docs/RUNTIME_AND_MEMORY.md](docs/RUNTIME_AND_MEMORY.md).

Facts about products, versions and prices were checked on **31 October 2026**. Check them again before you rely on them.

## The short answer

| Your situation | Recommended option | Where |
|---|---|---|
| Python team, want full control, small to medium scale | **A. The self-built gateway in this folder**: FastMCP 4 + Cedar (`cedarpy`), about 1,400 lines with docstrings, 64 tests | [`diy_gateway/`](diy_gateway/) |
| Same, deployed on AWS | **B. A on Lambda**, with IAM inbound, Secrets Manager and Amazon Verified Permissions | [`examples/aws_native/`](examples/aws_native/) |
| Platform team that wants a product, not code | **C1. agentgateway** (Linux Foundation, Rust): the closest feature match, but CEL instead of Cedar | [`examples/oss_gateways/`](examples/oss_gateways/) |
| Cedar is a hard requirement, on Kubernetes | **C2. ToolHive vMCP**: native Cedar with argument conditions | same |
| You also want one gateway for the Bedrock models | **C3. LiteLLM Proxy**: model gateway plus MCP; the amount rule needs a Python guardrail | same |
| Considering Bedrock Agents (classic) | **Not an option for new customers** since 30 Jul 2026 | [docs/OPTIONS.md](docs/OPTIONS.md) |

The reasoning, the other candidates and a decision tree are in [docs/OPTIONS.md](docs/OPTIONS.md). The proposed decision is in [docs/ADR-0001-tool-gateway.md](docs/ADR-0001-tool-gateway.md).

## What replaces each piece of AgentCore

| AgentCore, as the course uses it | Replacement in this folder | Off-the-shelf alternative |
|---|---|---|
| **Gateway:** one MCP endpoint over every target | `FastMCP` with one provider per target ([`targets.py`](diy_gateway/targets.py)) | agentgateway, ToolHive, LiteLLM |
| OpenAPI target: each operation a tool | `OpenAPIProvider`, with an operation allow-list | agentgateway `openapi`, LiteLLM `spec_path` |
| MCP-server target | `ProxyProvider` with the caller's headers **not** forwarded | all of them |
| Tool names `<target>___<operation>` | `TargetPrefix` transform; the separator is configurable | `_`, `__` or `-` in the products |
| Inbound `AWS_IAM` (SigV4) | Lambda Function URL with `AWS_IAM`; the gateway reads the caller's role | none found in the OSS gateways |
| Inbound OAuth/JWT | `JWTVerifier` (Cognito, Supabase, Keycloak, Entra), with client and claim checks | all of them |
| **Identity:** API key credential provider | `api_key` credentials from `env:` or `aws-secretsmanager:`, cached and rotatable | env/file or Kubernetes Secrets |
| Gateway role signing to a Lambda target | `sigv4` credentials (service `lambda`) | agentgateway `backendAuth.aws`, LiteLLM `aws_sigv4` |
| **Policy:** Cedar on every tool call | `CedarEngine` (in process) or `VerifiedPermissionsEngine` (AVP) | ToolHive (Cedar), the others CEL |
| `LOG_ONLY` then `ENFORCE` | `policy.mode: off / log_only / enforce` | not native in any OSS gateway found |
| Refusal "Tool Execution Denied" as an MCP error | The same message as a JSON-RPC error, with `retryable: false` | an `isError` result in most |
| Decision metrics in CloudWatch | JSON audit lines, optionally Embedded Metric Format | Prometheus/OTel in the products |
| **Runtime, Memory** | Lambda, ECS Fargate, Lambda durable functions; LangGraph `PostgresStore`, LangMem, Mem0 | [docs/RUNTIME_AND_MEMORY.md](docs/RUNTIME_AND_MEMORY.md) |

## Quick start (Windows PowerShell or macOS terminal)

```bash
cd agentcore-alternatives
uv sync                                                  # its own environment, apart from UnderCover's
uv run examples/make_env.py                              # writes .env with random demo keys, never printed
uv run --env-file .env examples/run_demo.py              # terminal 1: app stand-in :8200, context :8206, gateway :8210
uv run --env-file .env examples/call_gateway.py          # terminal 2: calls the gateway as the claim agent
```

If `uv sync` fails with a hardlink error (common under OneDrive), set `UV_LINK_MODE=copy` first: `$env:UV_LINK_MODE='copy'` in PowerShell, or `export UV_LINK_MODE=copy` on macOS.

What `call_gateway.py` shows:

```text
Tools: undercover-app___calculate_payout, ..., undercover-app___pay_claim, undercover-context___get_plan, undercover-context___lookup_term
Claim: {'claim_id': 'CLM-1001', 'customer_id': 'CUS-3001', ...}
Plan: {'plan': 'economy', ..., 'source': {'system': 'Policy administration', 'owner': 'Data governance', ...}}
Paid: {'claim_id': 'CLM-1001', 'paid': 300.0}
Refused: Tool Execution Denied: undercover-app___pay_claim refused by policy (payment-limit) {'retryable': False, 'policies': ['payment-limit']}
```

A claim agent on Bedrock, with its tools from the gateway. It is its own small project, because `langchain-mcp-adapters` needs `mcp` 1.x and the gateway runs on `mcp` 2.x:

```bash
cd examples/agent
uv run --env-file ../../.env agent_bedrock.py --tools-only                     # no model call
uv run --env-file ../../.env agent_bedrock.py --claim CLM-1002                 # needs BEDROCK_MODEL_ID and AWS credentials
```

Set `BEDROCK_MODEL_ID` to an inference profile your account can use; `aws bedrock list-inference-profiles` lists them (for example `us.anthropic.claude-sonnet-5-5` or `us.amazon.nova-2-lite-v1:0`). The agent needs only `bedrock:InvokeModel`, with no AgentCore permission.

Run the checks with `uv run pytest` and `uv run ruff check .`.

## How the self-built gateway works

```text
agent / Copilot --MCP over HTTP, bearer key or JWT (or SigV4 on a Function URL)-->  diy_gateway  /mcp
   1. inbound.py     who is calling: an agent's key, a JWT's subject or client, or an IAM role -> Principal
   2. middleware.py  every tools/call -> Cedar request -> off | log_only | enforce -> audit line
                     every tools/list -> hides tools no input could unlock (Cedar partial evaluation)
   3. targets.py     undercover-app___*     -> OpenAPI provider -> the app, with X-API-Key from the vault
                     undercover-context___* -> MCP proxy      -> the context layer, signed with SigV4 or not
```

| Module | What it does | AgentCore equivalent |
|---|---|---|
| [`config.py`](diy_gateway/config.py) | One validated YAML file: targets, inbound auth, policy and audit. Secrets are references; `${NAME}` comes from the environment | Gateway and target settings |
| [`inbound.py`](diy_gateway/inbound.py) | Agents' keys (constant-time), JWTs (JWKS, issuer, audience, client, claims), and IAM callers from the Lambda event | Inbound authorizer |
| [`credentials.py`](diy_gateway/credentials.py) | `SecretResolver` (env, Secrets Manager with a TTL cache), API key, bearer and SigV4 `httpx2.Auth` | Identity credential providers |
| [`targets.py`](diy_gateway/targets.py) | OpenAPI and MCP targets (tools only), the `<target>___<tool>` naming, the operation allow-list, and no caller headers passed on | Gateway targets |
| [`policy.py`](diy_gateway/policy.py) | Builds the Cedar request (numbers as decimals) and evaluates it with `cedarpy` or Verified Permissions | Policy engine |
| [`middleware.py`](diy_gateway/middleware.py) | Decides each call in its mode, fails closed on errors, and refuses with `Tool Execution Denied` | Policy attached to the Gateway |
| [`audit.py`](diy_gateway/audit.py) | One JSON line per decision and per call; EMF metrics for CloudWatch | Observability |
| [`lambda_handler.py`](diy_gateway/lambda_handler.py) | Mangum on Lambda: a fresh gateway per request from one `GatewayFactory`, which keeps the secrets, specs, token verifier, policy engine and MCP proxies | Managed hosting |

### Customising it

- **A new kind of target** (a Lambda invoked directly, gRPC, a database): add a config model and a `Provider` in `targets.py`.
- **Another identity provider:** set `inbound.jwt`, or add a branch to `GatewayTokenVerifier.verify_token`.
- **Another policy engine** (OPA, Cerbos, OpenFGA): implement `evaluate` and `may_allow` from `PolicyEngine` in `policy.py`.
- **Rate limits, response size limits, caching:** add FastMCP's own middleware (`fastmcp.server.middleware.rate_limiting` and others) beside `PolicyMiddleware`.
- **Screening tool results for injected instructions:** a middleware after `call_next` can send the result to Bedrock Guardrails (`ApplyGuardrail`) or to a screening model, as the course's security check does for claims.
- **Another naming scheme:** change `separator`, for example to `_` to match agentgateway.

## What's verified, and what isn't

Verified here, on Windows with Python 3.12, FastMCP 4.1.4, `mcp` 2.3.0 and `cedarpy` 4.12.2:

- 64 tests cover inbound keys and JWTs (wrong audience, no expiry, Cognito client and token use), both targets, key injection, enforce and log-only, fail-closed rules, the strict schema, Verified Permissions requests (against a stand-in), SigV4 signing, Secrets Manager caching, the Lambda handler twice in one process with an IAM caller, that **no caller's token or header reaches a target** (FastMCP forwards them by default: see [docs/FINDINGS.md](docs/FINDINGS.md)), that unprefixed or hashed tool names are refused, and that targets' resources and prompts stay hidden.
- An independent code review (a sub-agent) tried to break each security property; its eight findings are fixed and tested.
- The live demo, and the agent's MCP client (`mcp` 1.30) against the gateway (`mcp` 2.3).
- The Lambda package builds (40 MB zipped), and `template.yaml` passes `cfn-lint`.

Not verified, because nothing here calls AWS:

- a deployment, real Verified Permissions, Secrets Manager, Cognito or Bedrock calls, and SigV4 against a live Function URL;
- the OSS gateway configs, which come from each product's docs and are marked as such.

## Folder map

```text
agentcore-alternatives/
  README.md                    this page
  diy_gateway/                 Option A: the gateway (Python package)
  policies/                    gateway.cedar (the course's rules), gateway.schema.json (strict shapes for the demo)
  gateway.demo.yaml            the local demo's config
  gateway.undercover.yaml      the gateway in front of your own UnderCover build (Week 3 Day 3 onward)
  examples/
    demo_upstreams/            stand-ins for UnderCover's app and context layer
    run_demo.py, call_gateway.py, make_env.py
    agent/                     a claim agent on Bedrock (its own uv project)
    aws_native/                Option B: SAM template, Lambda package, AWS config, Cognito M2M
    oss_gateways/              Option C: agentgateway, ToolHive, LiteLLM and ContextForge configs
  docs/
    OPTIONS.md                 every option compared, and a decision tree
    IDENTITY_AND_AUTH.md       who calls what with which credential, including the Copilot
    POLICY.md                  Cedar for tool calls, fail-closed rules, log-only, AVP vs cedarpy, CEL/Rego
    RUNTIME_AND_MEMORY.md      replacing AgentCore Runtime and Memory
    SECURITY_CHECKLIST.md      for any self-built gateway
    FINDINGS.md                traps found while building this, with the fixes
    research/                  the four cited research reports this folder is built from
    RESOURCES.md               official docs, specs and GitHub repos
    ADR-0001-tool-gateway.md   the decision, ready for review
  tests/                       pytest suite (no network, no AWS, no model)
```

## Using it with the course

The course's briefs ask for AgentCore, so `docs/` in the repo root stays as it is. This folder is a side study: it doesn't change the product. To try it with your own build from Week 3 Day 3 onward, run the gateway with [`gateway.undercover.yaml`](gateway.undercover.yaml) beside `npm run dev`, and point `UNDERCOVER_GATEWAY_URL` at it. Then change the agent's MCP client to send a bearer token instead of signing for `bedrock-agentcore`. The tool names, the refusal message and the policy's rules all match AgentCore's.

> Research report by a sub-agent (Claude Sonnet 5.5) on 31 October 2026, kept as written. It cites its sources; anything marked UNVERIFIED wasn't confirmed. The code and docs in this folder supersede it where they differ.

# Auth, delegation, credential-vault and policy patterns for MCP agents without AgentCore

**Research date: 31 Oct 2026.** Bracketed numbers refer to sources at the end. `[E]` means I executed the item locally: cedarpy 4.12.2, OPA 1.22.0, and a CEL library. UNVERIFIED means I could not confirm it from an official source.

## 0. Summary

- **Spec status.** The current MCP revision is **2026-07-28**. It makes MCP stateless, deprecates Dynamic Client Registration (DCR) in favour of Client ID Metadata Documents (CIMD), and promotes two authorization extensions to Stable: OAuth Client Credentials and Enterprise-Managed Authorization. [1][3][5a][6][7]
- **Hard rule for the Copilot.** MCP servers MUST validate that a token's audience is themselves. They MUST NOT accept or pass on other tokens. [1][2][4] The handler's Supabase JWT therefore must not travel through the gateway. Either the Copilot calls the app directly with it, or it exchanges it for a short-lived gateway-audience token (RFC 8693).
- **Closest AgentCore equivalent.** A small Python MCP gateway that runs Cedar through `cedarpy` and reuses the same `context.input` convention. AWS's own `cedar-for-agents` generates Cedar schemas from MCP tool lists in that shape. [19][E]
- **AgentCore authoring note.** AgentCore Policy is now authored in "Dogwood", a Cedar-compatible superset. Plain-Cedar subsets like your `pay_claim` rule are portable, but `when guardrails`/`when temporal` blocks are not. [20]
- **Fail-open traps.** Cedar, Rego and CEL all behave the same way when a *deny* rule errors, for example on a missing or malformed `amount`. Cedar skips the errored `forbid` and the call is allowed. Treat any evaluation error as a deny. I reproduced this in Cedar and Rego. [E][17][21]
- **Persistence trap.** LangGraph copies string values from `config["configurable"]` into checkpoint metadata. A JWT passed there would be persisted. [29]

## 1. Key spec facts

**MCP revisions**
- 2026-07-28 is "current" and was released 28 Jul 2026. [6][30] The changelog removes `initialize` and `Mcp-Session-Id`, adds `server/discover`, and carries OpenTelemetry `traceparent` in `_meta`. [5a]
- 2025-06-18 made MCP servers OAuth resource servers with RFC 9728 metadata, and made RFC 8707 resource indicators mandatory for clients. [5c]
- 2025-11-25 added CIMD, OIDC discovery and incremental scope step-up. [5b]
- 2026-07-28 deprecated DCR in favour of CIMD, and required clients to validate an `iss` parameter when one is present (RFC 9207). [5a]

**Core authorization rules in 2026-07-28 [1][2][3]**
- OAuth 2.1 is cited as draft -13; datatracker is already at -17 and it is still a draft. [10a]
- Servers MUST implement RFC 9728 Protected Resource Metadata, and clients MUST use it for authorization-server discovery.
- Clients MUST send `resource` (RFC 8707) in both authorization and token requests, using the server's canonical URI.
- Servers MUST validate that tokens were issued specifically for them as the audience.
- Servers MUST NOT accept or transit any other tokens.
- If a server calls an upstream API, the upstream token is separate and the inbound token MUST NOT be passed through. [2]
- The `Authorization` header is required on every HTTP request.
- Scope step-up uses HTTP 403 `insufficient_scope` with a `WWW-Authenticate` header.
- Client registration priority is pre-registered, then CIMD, then DCR. [3]
- Authorization is OPTIONAL overall. Stdio transports SHOULD NOT use it. [1]

**Security Best Practices page [4]**
- Confused deputy: an MCP proxy with a static upstream client ID must obtain per-client consent.
- Token passthrough is forbidden, and the page explains why: bypassed controls, a broken audit trail, trust-boundary problems.
- SSRF during OAuth discovery.
- "State handle hijacking" replaces session hijacking. A handle is a name, not a credential, so bind it to the verified user.
- Scope minimization.
- Servers MUST NOT treat possession of a state handle as authentication.

**Authorization extensions (both Stable for 2026-07-28) [7]**
- **OAuth Client Credentials.** For machine-to-machine use. `private_key_jwt` (RFC 7523) is RECOMMENDED, and a client secret is allowed. Clients are pre-registered and DCR is not used. [7a]
- **Enterprise-Managed Authorization.** Uses ID-JAG (Identity Assertion JWT Authorization Grant), built on RFC 8693 plus RFC 7523. The issued access token MUST be audience-restricted to the MCP server. [7b]

**Tool errors and security [8]**
- Servers MUST validate tool inputs, enforce access controls, rate-limit and sanitize outputs.
- Clients SHOULD confirm sensitive operations and log usage.
- Protocol errors are JSON-RPC errors and are "less likely" to be recovered by the model.
- Tool-execution errors (`isError:true`) are meant to let the model self-correct and retry. A policy denial should therefore be a non-retryable protocol error.
- Error codes `-32000..-32019` are implementation-defined; `-32020..-32099` are reserved for MCP. [5a]

## 2. Delegation and on-behalf-of

| Spec or product | Status (31 Oct 2026) | Use for you |
|---|---|---|
| RFC 8693 token exchange (`act`, `may_act`) | RFC. The `act` claim marks delegation: sub is the user, actor is the agent. [9] | Core mechanism for a gateway-audience token. |
| Transaction Tokens (`draft-ietf-oauth-transaction-tokens-11`, 30 Jul 2026) | Draft, expires 31 Jan 2027. Short-lived, call-chain context. Not authentication credentials and not OAuth access tokens. [10b] | Only for multi-service fan-out. Skip for now. |
| ID-JAG / Cross-App Access (`…identity-assertion-authz-grant-06`, 31 Oct 2026) | Draft. Basis of MCP Enterprise-Managed Authorization. [10c][7b] | Relevant if you adopt an enterprise IdP. |
| AI Agent Auth & Authz (`draft-klrc-aiagent-auth-03`, Informational) | Draft. Agents are workloads. [10d] | Guidance only (below). |
| `draft-oauth-ai-agents-on-behalf-of-user-02` | Expired Feb 2026. [10e] | Ignore. |
| Keycloak | Standard token exchange supported since 26.2 (internal-to-internal only). Delegation with `may_act`/`act` is **Preview**. Current release is 26.8.1. [11][30] | Self-hostable STS if you need a full AS. |
| Microsoft Entra Agent ID | On-behalf-of (OBO) flow for agent identities. The user token's `aud` must equal the agent blueprint. Managed identity is preferred as the credential. [12] | Pattern reference only. |
| Auth0 Token Vault | Exchanges an Auth0 token for an external provider's token: refresh, access and privileged-worker variants. [13] | Third-party SaaS tokens. Not needed for your own app. |
| Okta AI-agent token exchange | Connection types include ID-JAG, vaulted secrets and an agent-gateway STS. [14] | Same: only with Okta. |
| Amazon Cognito | M2M client-credentials with resource-server scopes. `GetClientToken` is authorized by client secret, not IAM. [15] I found no RFC 8693 support (UNVERIFIED). | Weak fit for delegation. |
| Supabase Auth | Beta OAuth 2.1 server with PKCE, DCR and discovery. OAuth tokens are JWTs with `aud:"authenticated"` and a `client_id` claim. A Custom Access Token Hook can set `aud` per client. [16] No RFC 8707 or 8693 support found (UNVERIFIED). | The human IdP. Mint gateway tokens yourself. |

**What the AIMS draft says**
- A tool forwarding the agent's access token to services is "an anti-pattern". [10d]
- The IETF drafts suggest exchanging for a downscoped, audience-specific token instead.
- A local UI confirmation alone is not authorization. Step-up should become an authorization event, for example via CIBA. [10d §10.7]

**Pass-through versus exchange**

| Situation | Do this | Why |
|---|---|---|
| Copilot calls your **app** directly (the token's audience is that app) | Present the Supabase JWT as-is. This is ordinary token use, not MCP passthrough. | The app logs the human `sub` and applies their role. Set a custom `aud` (Supabase hook [16]), because the default `authenticated` is accepted by any service on the project. |
| Copilot calls the **MCP gateway** | RFC 8693 exchange to a ≤5-min token with `aud=gateway`, `sub=handler`, `act.sub=copilot`, `scope=context:read`. | Required by [1][2][4]. The gateway never forwards it. |
| Gateway to Lambda MCP | Gateway's own SigV4 credentials. | No user token crosses this hop. [28] |

For an exchange endpoint, FastAPI plus `joserfc`/`pyjwt` with a KMS-held signing key is enough. The package versions are in [30]. Supabase offers no exchange endpoint, so Keycloak is the heavier alternative.

## 3. Recommended identity architecture

**Caller 1: claim agent (machine identity)**
1. The agent obtains an identity token. Prefer an AWS-signed JWT from `sts:GetWebIdentityToken` with `aud=<gateway URL>`. It is valid for 60 s to 1 h (default 300 s), signed RS256 or ES384, and verifiable via the issuer JWKS. The feature must be enabled per account. [28] Alternatives are SigV4 behind IAM auth, or the MCP client-credentials extension with `private_key_jwt`. [7a]
2. The gateway validates signature, `iss`, `aud` and `exp`, then maps `sub` to `Agent::"claim-agent"`.
3. The gateway validates arguments against the pinned `inputSchema`, then evaluates Cedar (§6).
4. On allow, the gateway reads `X-API-Key` from Secrets Manager (cached) and injects it for that tool's route only. The agent never holds it.
5. The app's agent-only routes accept only that key and reject human JWTs.
6. The gateway audits principal, tool, decision, rule IDs and trace ID.

**Caller 2: Copilot acting for a human handler**
- **Path A, app reads and decisions:** the Copilot service sends `Authorization: Bearer <Supabase JWT>` straight to the app.
  - The app verifies JWKS, `iss`, `exp` and `aud`, enforces the senior-handler rule for payouts over $1,000, and logs the human `sub`.
  - Keep the JWT in a request-scoped `contextvar` or a `__`-prefixed config key, never in graph state. LangGraph copies other string `configurable` values into checkpoint metadata. [29]
  - Redact it from logs.
- **Path B, context-layer tools via the gateway:** exchange as in §2. The gateway evaluates Cedar with the principal as the handler and the actor as the Copilot. It then calls Lambda with its own role.
- **Skip the exchange if the context layer never needs the human.** Give the Copilot its own workload identity and a `permit` limited to read tools.
- The Copilot must not be offered `pay_claim` at all. Human step-up happens in the app with the human's own JWT.

**Caller 3: gateway to internal Lambda MCP**
- Use a Function URL with `AuthType=AWS_IAM`. Every request must be SigV4-signed. [28]
- Callers need `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`. New function URLs need both since Oct 2025. [28]
- The resource policy can restrict `lambda:InvokeFunction` to URL calls with the `lambda:InvokedViaFunctionUrl` condition key. [28]
- Strip any inbound `Authorization` header before forwarding. [4]

## 4. Credential vaults (gateway holds outbound credentials)

| Option | Fit | Notes |
|---|---|---|
| **AWS Secrets Manager** | Best default on AWS | Rotation and a new version per rotation at no extra charge. [26] The page's own example implies $0.40 per secret per month. Cache in the gateway. For zero-downtime rotation, let the app accept two keys during the window. |
| **OpenBao** (v2.7.2, MPL-2.0) | Per-call short-lived credentials | Dynamic secrets carry leases and can be revoked individually or by prefix. [26][30] |
| **HashiCorp Vault** (v2.2.1) | Same features | GitHub reports no standard license (UNVERIFIED). [30] |
| **Infisical** | Dev-friendly | Dynamic secrets need the paid Advanced plan, including self-hosted. [26] |
| **Auth0 Token Vault** | Per-user tokens for external SaaS | Not for an internal app key. [13] |
| **Arcade / Composio** | Managed per-user OAuth for SaaS tools | Arcade handles OAuth, tokens and keys at runtime. [26] Composio: only the PyPI version (0.30.0) was checked; the rest is UNVERIFIED. |

**Gateway patterns**
- agentgateway documents per-target static keys (`backendAuth.key`). [21]
- It also documents AWS SigV4 (`serviceName` can be any signing name, unvalidated), token exchange, Cross-App Access and signed JWTs (1.5.x and later). [21]
- Backend authentication is explicitly "not authorization": authorize first, then inject. [21]
- Longer term, replace the static app API key with a short-lived gateway-signed JWT.

## 5. Policy engines

| Engine | Argument-level conditions | Python embedding | Latency | Testing | Shadow mode | MCP-specific |
|---|---|---|---|---|---|---|
| **Cedar** (engine 4.14.0; `cedarpy` 4.12.2 tracks 4.12.0, community-maintained) [17][18][30] | Typed. `decimal` supports ≤4 fractional digits. Schema validation via `validate_policies`. | In-process. `PolicySet`/`Schema`/`Entities` handles. | Measured with pre-parsed policy: ~27 µs evaluation plus ~108 µs request build `[E]`. README: policy parsing dominates, so reuse handles. [18] | `validate_policies`; Cedar CLI | None native, so it is app-level (§6) | `cedar-for-agents` v0.7.0: schema generator, action per tool, `context.input`, `numbersAsDecimal`. [19] |
| **OPA/Rego** (v1.22.0) [23] | Flexible. Missing-attribute semantics are subtle (see below). | No official binding. `opa-wasm` Python was last released in 2022. `regorus` (Rust) lists Python bindings but I found no `regorus` package on PyPI (UNVERIFIED). [23][30] | Sidecar | `opa check --strict`, `opa eval` `[E]` | **Native** `DryRun` in the Envoy plugin: it overrides the response to allow and keeps decision logs. [23] | No MCP guidance found (UNVERIFIED) |
| **Cerbos** (v0.57.0) [22] | YAML plus CEL conditions; DENY beats ALLOW for the same role and action. | Separate PDP service; Python SDK 0.16.1. [30] | PDP round-trip | `cerbos compile` (not run: no Windows binary) | No dry-run found; audit decision logs exist | AuthZEN endpoint in source; no MCP guide found |
| **CEL in agentgateway** (v1.7.0) [21] | `mcpAuthorization` **cannot read arguments**. Route-level `authorization` can. | Gateway-native. Python CEL libs: `common-expression-language` 0.10.0, `cel-python` 0.5.0. [30] | In-gateway | CEL playground in the UI | Not found (UNVERIFIED) | MCP-native variables (`mcp.tool.name`, `mcp.tool.target`, JWT claims) |
| **OpenFGA** (v1.22.1) [24] | Relationship-based, with CEL conditions on tuples. | HTTP/gRPC server; Python SDK. | Server call | CLI model tests | Not found | Docs list AI-agent and MCP use cases. Best for "who is assigned to this claim", not argument rules. |
| **Permit.io MCP Gateway** [25] | Per-tool allow/deny with trust levels. Argument conditions UNVERIFIED. | SaaS control plane; SDK `permit` 3.0.1. [30] | Network hop | — | — | Gateway authenticates the agent JWT, authorizes each call, logs, and collects consent. |
| **Oso** | — | Library last released Jan 2024 (`oso` 0.27.3). [30] | — | — | — | Stale. |

Cedar's own docs warn that an erroring policy is ignored, so a `forbid` may fail to block. [17] The Rego and CEL equivalents were confirmed in §5.1.

### 5.1 The rule "forbid `pay_claim` when amount > 1000"

**Cedar** (executed in cedarpy `[E]`; syntax per [17]; the AgentCore flavor uses `AgentCore::Action::"Target___pay_claim"` and `resource == AgentCore::Gateway::"<arn>"` [20])
```cedar
permit (principal, action, resource);
forbid (principal, action == Action::"claims___pay_claim", resource == Gateway::"claims-gw")
when { context.input.amount.greaterThan(decimal("1000.00")) };
```
Cedar has no float type. A JSON float amount produced `NoDecision` with "data did not match any variant of untagged enum RawCedarValueJson" `[E]`. Send amounts as strings and declare `amount: __cedar::decimal` in the schema.

**Rego** (executed with OPA 1.22.0; `opa check --strict` passed `[E]`)
```rego
package mcp.authz
import rego.v1
default allow := false
allow if count(deny) == 0
deny contains "hold-payouts-over-1000" if {
	input.tool == "pay_claim"
	numeric_amount
	input.arguments.amount > 1000
}
deny contains "pay_claim-needs-numeric-amount" if {   # fail-closed companion
	input.tool == "pay_claim"
	not numeric_amount
}
numeric_amount if is_number(input.arguments.amount)
```
My first draft used `not is_number(input.arguments.amount)` inline. A missing `amount` was **allowed**, so the helper rule is required. `[E]`

**Cerbos YAML** (structure per [22]; not executed; behaviour on condition errors UNVERIFIED)
```yaml
apiVersion: api.cerbos.dev/v1
resourcePolicy:
  resource: "mcp_tool"
  version: "default"
  rules:
    - actions: ["*"]
      effect: EFFECT_ALLOW
      roles: ["agent"]
    - actions: ["pay_claim"]
      effect: EFFECT_DENY
      roles: ["agent"]
      condition:
        match:
          expr: request.resource.attr.arguments.amount > 1000
```

**CEL, agentgateway route-level `authorization`** (variable names per [21]; I evaluated the expression with a CEL library `[E]`, not with agentgateway itself)
```yaml
mcp:
  policies:
    authorization:
      rules:
      - require: '!(mcp.tool.name == "pay_claim") || (has(mcp.tool.arguments.amount) && mcp.tool.arguments.amount <= 1000)'
```
- Docs say a `deny` expression that errors does not match, which is fail-open. A `require` that errors denies. [21]
- My local test agreed: the `deny` form raised an error for a missing amount, while `require` returned false.
- `mcp.tool.arguments` is "not set in `mcpAuthorization` rules", so use the route-level policy. [21]

## 6. `cedarpy` enforcement step

Verified facts [18][E]:
- Signature: `is_authorized(request, policies, entities, schema=None, verbose=False) -> AuthzResult`.
- `AuthzResult` exposes `.decision` (enum `Allow`/`Deny`/`NoDecision`), `.allowed`, `.diagnostics.reasons`, `.diagnostics.errors`, `.diagnostics.id_annotations_by_reason` and `.metrics`. `reasons` holds positional IDs like `policy1`; `@id("…")` annotations map back via `id_annotations_by_reason`.
- `PolicySet.from_str` and `Schema.from_str` parse once, and entity and action fields accept `{"type","id"}` dicts.
- `validate_policies(policies, schema, *, release_gil=False)` returns `.validation_passed` and `.errors`. It rejected `amount > 1000` with "expected Long but saw decimal". `[E]`

```python
import json, logging
from cedarpy import Decision, PolicySet, Schema, is_authorized

log = logging.getLogger("mcp.policy")
SCHEMA = Schema.from_str("""
entity Agent; entity Gateway;
type PayIn = { claim_id: String, amount: __cedar::decimal };
action "claims___pay_claim" appliesTo { principal: Agent, resource: Gateway, context: { input: PayIn } };
action "claims___get_claim" appliesTo { principal: Agent, resource: Gateway, context: { input: { claim_id: String } } };
""")                                    # parsed once; unknown tool => no action => deny
POLICIES = PolicySet.from_str("""
@id("allow-all-tools") permit (principal, action, resource);
@id("hold-payouts-over-1000")
forbid (principal, action == Action::"claims___pay_claim", resource)
when { context.input.amount.greaterThan(decimal("1000.00")) };
""")                                    # parsed once, reused on every call
DENIED = -32010  # MCP reserves -32020..-32099; -32000..-32019 is implementation-defined

def authorize(mode: str, principal_id: str, tool: str, args: dict, *, request_id=None):
    """mode: 'off' | 'log_only' | 'enforce'. Returns None to proceed, else a JSON-RPC error."""
    if mode == "off":
        return None
    req = {"principal": {"type": "Agent", "id": principal_id},
           "action": {"type": "Action", "id": tool},
           "resource": {"type": "Gateway", "id": "claims-gw"},
           "context": {"input": args}}
    entities = [{"uid": req["principal"], "attrs": {}, "parents": []}]
    try:
        r = is_authorized(req, POLICIES, entities, schema=SCHEMA)
        errors = list(r.diagnostics.errors)
        # an erroring forbid is silently skipped by Cedar -> fail closed on ANY error
        allowed = r.decision == Decision.Allow and not errors
        rules = [r.diagnostics.id_annotations_by_reason.get(p, p) for p in r.diagnostics.reasons]
        decision = r.decision.value
    except Exception as exc:            # malformed request shape etc.
        allowed, errors, rules, decision = False, [str(exc)], [], "Error"
    log.info(json.dumps({"ev": "authz", "mode": mode, "tool": tool, "principal": principal_id,
                         "decision": decision, "allowed": allowed, "rules": rules, "errors": errors}))
    if allowed or mode == "log_only":   # log_only: record "would deny", never block
        return None
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": DENIED, "message": "Tool Execution Denied",
                      "data": {"retryable": False, "action": "hold_for_human_signoff", "rules": rules}}}
```

I ran the sketch against cedarpy 4.12.2 `[E]`:

| Case | Mode | Result |
|---|---|---|
| `pay_claim`, amount "1500.00" | `off` | proceeds |
| `pay_claim`, amount "1500.00" | `log_only` | proceeds, logs `Deny` via `hold-payouts-over-1000` |
| `pay_claim`, amount "1500.00" | `enforce` | JSON-RPC error -32010 "Tool Execution Denied" |
| `pay_claim`, amount "999.99" | `enforce` | proceeds |
| `pay_claim`, amount "abc" | `enforce` | denied (`NoDecision`, schema decimal parse failure) |
| unknown tool `claims___drop_db` | `enforce` | denied (`NoDecision`, "action does not exist in the supplied schema") |

**Gotchas**
- Without a schema, a malformed or missing amount yields **Allow plus a populated `diagnostics.errors`**. The `not errors` check and the schema are what close that gap. `[E]`
- Do not write `.get("allowed")`. Use the `.allowed` attribute or compare `.decision`.
- Regenerate the schema in CI from `tools/list` using `cedar-policy-mcp-schema-generator` (PyPI 0.7.0, Rust/maturin wrapper). Diffing it is also a tool-description pin. [19][30]

## 7. Security checklist for a self-built gateway

1. **Audience-bound tokens.** Validate `iss`, `aud`, `exp`, signature and algorithm allow-list. Reject everything else. [1][2]
2. **No passthrough.** Strip inbound `Authorization`. Outbound credentials are separate: the vault key or SigV4. [2][4]
3. **Short-lived tokens, sender constraint where possible.** TTL ≤ 5–15 min. DPoP (RFC 9449) is an option. `resource`+scope on every token request. [7a][10c]
4. **Least privilege per tool.** Give each caller identity an explicit tool allowlist. The Copilot gets no write tools. OWASP LLM06 lists excessive functionality, permissions and autonomy as the root causes. [27]
5. **Allowlist tools and pin definitions.** Treat tool annotations as untrusted unless the server is trusted. [8] Pin `tools/list`, alert on diffs, and regenerate the Cedar schema in CI so a changed tool is a failed build. (This pinning step is my recommendation.) Related risks: OWASP MCP03 Tool Poisoning and CoSAI T6 (missing integrity controls). [27]
6. **Schema-validate arguments.** Check against the pinned `inputSchema` (JSON Schema 2020-12). [5b][8] Add argument limits: size, depth, string length, enum values.
7. **Fail closed.** Any policy error, parse failure or unknown tool is a deny (§5–6).
8. **Log-only then enforce.** Cedar has no native shadow mode, so build it as in §6. OPA-Envoy has a native `DryRun`. [23]
9. **Human-in-the-loop for high-impact actions.** The denial is a non-retryable error that routes to a human. [8] The human approves in the app with their own token. UI confirmation alone does not count. [10d]
10. **Rate limits and timeouts.** MCP says servers MUST rate-limit; clients SHOULD time out. [8]
11. **Audit.** Record principal, actor, tool, argument hash, decision, rule ID and trace ID; propagate `traceparent`. [5a] Never log tokens. Log token IDs or hashes. [10d] OWASP MCP08 stresses telemetry. [27]
12. **State handles.** If tools mint handles, bind them server-side to the verified principal. Never treat them as auth. [4]
13. **SSRF hygiene** wherever the gateway fetches OAuth metadata or CIMD URLs: HTTPS only, block private ranges, validate redirects, use an egress proxy. [4]
14. **Lethal trifecta.** Never give one agent all three: private data, untrusted content, and an exfiltration channel. [27] Claim documents are untrusted input.
15. **Secrets hygiene.** Hard-coded or long-lived tokens and secrets in logs or model memory are OWASP MCP01. [27] Keep keys out of prompts, state and checkpoints. [29]
16. **Shadow servers.** Inventory MCP servers (OWASP MCP09; CoSAI T11). [27]

OWASP Agentic Top 10 (ASI01–ASI10) titles, from the OWASP blog: Agent Goal Hijack, Tool Misuse, Identity & Privilege Abuse, Agentic Supply Chain, Unexpected Code Execution, Memory & Context Poisoning, Insecure Inter-Agent Communication, Cascading Failures, Human-Agent Trust Exploitation, Rogue Agents. [27] The OWASP MCP Top 10 page still lists a "Final Release" phase as upcoming. [27]

## 8. Workload identity on AWS

| Option | Verdict |
|---|---|
| **IAM role + SigV4** | Native and simplest. Required for the Lambda Function URL. [28] agentgateway can sign as its own role. [21] |
| **STS `GetWebIdentityToken`** | Gives an AWS-signed JWT for non-AWS verifiers, so no stored secret. Needs per-account enablement and a regional endpoint. [28] |
| **`private_key_jwt` / client assertions** | What the MCP client-credentials extension recommends. [7a] The AIMS draft says not to use static long-lived client secrets. [10d] |
| **SPIFFE/SPIRE** (v1.15.5) | Suited to multi-cloud or Kubernetes. Heavy for a small AWS team. [10d][30] |
| **mTLS** | Transport-level only. The AIMS draft lists replay and relay limitations. [10d] |

## 9. Ranked shortlist

1. **Custom Python gateway + Cedar (`cedarpy`) + AWS-native identity + Secrets Manager.**
   - Closest to your AgentCore design: same Cedar model and rules, easy to port to or from AgentCore.
   - You own authentication, argument validation, schema generation, shadow mode, denial mapping and audit. Budget for that.
   - Pin `cedarpy`, because it is community-maintained and lags engine 4.14. [18][30]
2. **agentgateway (Apache-2.0) + CEL + your own token exchange.**
   - Native MCP authentication with Protected Resource Metadata, per-target key injection, SigV4 and token-exchange backends.
   - Weaknesses: argument rules only at route level, fail-open `deny`, no documented log-only mode, and no Cedar. [21]
3. **OPA as a sidecar PDP.** Mature testing and native dry-run. Weak Python embedding, so you pay a network hop. [23]
4. **Cerbos.** Good policy-as-YAML and an AuthZEN endpoint; no MCP guide found. [22]
5. **Permit.io MCP Gateway, OpenFGA, Arcade/Composio.** Consider these only for SaaS governance, relationship modelling, or managed per-user SaaS OAuth respectively. [24][25][26]

Whichever you pick, keep the three identity rules in §3 and the fail-closed handling in §6.

## 10. Gaps and UNVERIFIED items

- Supabase RFC 8707 and RFC 8693 support: not found in the fetched docs. The docs site returned 403, so I read the docs repo's MDX on GitHub instead. [16]
- Cerbos YAML was not executed (no Windows release binary). Cerbos and OPA MCP-specific guides were not found.
- agentgateway was not run, so its CEL behaviour on errors comes from its documentation. Its Lambda-specific signing was not confirmed beyond "any signing name".
- Entra Agent ID GA or preview status is not stated on the fetched page. [12]
- Cognito RFC 8693 and `private_key_jwt` support, and the Cognito "Resource binding" page: not retrievable. [15]
- Vault's license (GitHub: NOASSERTION), Composio details, the `regorus` PyPI name, and the full OWASP Agentic Top 10 body text (only titles verified). The CoSAI whitepaper PDF was not read; only its summary page was.
- Temporary local verification used an OPA binary and scratch files in the home directory. They were removed, and nothing in the repo was changed.

## Sources

- **[1]** MCP authorization 2026-07-28: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization.md
- **[2]** MCP authorization security considerations: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations.md
- **[3]** MCP client registration: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration.md
- **[4]** MCP Security Best Practices: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md
- **[5]** MCP changelogs: https://modelcontextprotocol.io/specification/2026-07-28/changelog.md (a), https://modelcontextprotocol.io/specification/2025-11-25/changelog.md (b), https://modelcontextprotocol.io/specification/2025-06-18/changelog.md (c)
- **[6]** MCP versioning: https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning.md
- **[7]** ext-auth: https://github.com/modelcontextprotocol/ext-auth; (a) `specification/stable/oauth-client-credentials/2026-07-28/oauth-client-credentials.mdx`; (b) `specification/stable/enterprise-managed-authorization/2026-07-28/enterprise-managed-authorization.mdx`
- **[8]** MCP tools spec: https://modelcontextprotocol.io/specification/2026-07-28/server/tools.md
- **[9]** RFC 8693: https://www.rfc-editor.org/rfc/rfc8693.html
- **[10]** Datatracker: (a) https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-oauth-v2-1/ (rev 17); (b) https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/; (c) https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/; (d) https://www.ietf.org/archive/id/draft-klrc-aiagent-auth-03.txt; (e) https://datatracker.ietf.org/api/v1/doc/document/draft-oauth-ai-agents-on-behalf-of-user/
- **[11]** Keycloak: https://www.keycloak.org/2025/04/keycloak-2620-released, https://www.keycloak.org/securing-apps/token-exchange
- **[12]** Entra: https://learn.microsoft.com/en-us/entra/agent-id/agent-on-behalf-of-oauth-flow
- **[13]** Auth0 Token Vault: https://auth0.com/docs/secure/call-apis-on-users-behalf/token-vault
- **[14]** Okta: https://developer.okta.com/docs/guides/ai-agent-token-exchange/authserver/main/
- **[15]** Cognito: https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html
- **[16]** Supabase docs repo: `apps/docs/content/guides/auth/oauth-server/{mcp-authentication,token-security,getting-started}.mdx`, `auth/jwts.mdx` (https://github.com/supabase/supabase)
- **[17]** Cedar: https://docs.cedarpolicy.com/policies/syntax-datatypes.html, `…/syntax-operators.html`, `…/auth/entities-syntax.html`
- **[18]** cedarpy: https://github.com/k9securityio/cedar-py (README; `cedarpy/__init__.py`); PyPI https://pypi.org/project/cedarpy/
- **[19]** https://github.com/cedar-policy/cedar-for-agents (`rust/cedar-policy-mcp-schema-generator/README.md`; `…-python/README.md`)
- **[20]** AgentCore Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-authoring-guide.html, `…/example-policies-action-resource.html`, `…/policy-scope.html`
- **[21]** agentgateway docs: https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/, `…/http-authz/`, `…/backend-authn/` (and `/providers/aws/`), `…/mcp/mcp-target-policies/`
- **[22]** Cerbos: https://docs.cerbos.dev/cerbos/latest/policies/resource_policies, `…/api/index.html`; repo `internal/svc/authzen_svc.go`
- **[23]** OPA: https://www.openpolicyagent.org/docs/policy-language; `open-policy-agent/opa-envoy-plugin:internal/internal.go:611-633`
- **[24]** OpenFGA: https://openfga.dev/docs/fga, `…/modeling/conditions.md`
- **[25]** Permit MCP Gateway: https://docs.permit.io/permit-mcp-gateway/overview/
- **[26]** https://aws.amazon.com/secrets-manager/pricing/, https://openbao.org/docs/concepts/lease/, https://infisical.com/docs/documentation/platform/dynamic-secrets/overview, https://docs.arcade.dev/en/get-started/about-arcade
- **[27]** OWASP: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/, https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/, https://owasp.org/projects/mcp-top-10; CoSAI: https://www.coalitionforsecureai.org/securing-the-ai-agent-revolution-a-practical-guide-to-mcp-security/; Willison: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- **[28]** AWS: https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html, `…/urls-invocation.html`, https://docs.aws.amazon.com/STS/latest/APIReference/API_GetWebIdentityToken.html
- **[29]** `langchain-ai/langgraph:libs/checkpoint/langgraph/checkpoint/base/__init__.py:786-804`
- **[30]** Versions queried 31 Oct 2026 via `api.github.com/repos/<org>/<repo>/releases/latest` and `pypi.org/pypi/<pkg>/json`.

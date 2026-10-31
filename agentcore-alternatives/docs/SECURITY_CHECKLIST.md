# Security checklist for a self-built tool gateway

Use it before a gateway goes in front of real data, and in each review after that. It draws on:

- the MCP specification 2026-07-28 ([authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization.md), [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools.md), [security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md));
- OWASP's [LLM06 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/), the [Agentic Top 10](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) and the [MCP Top 10](https://owasp.org/projects/mcp-top-10);
- [CoSAI's MCP guide](https://www.coalitionforsecureai.org/securing-the-ai-agent-revolution-a-practical-guide-to-mcp-security/), and the course's security day.

Each line says where `diy_gateway` stands.

## Identity

- [ ] **Every caller authenticates, on every request.** The gateway rejects a missing or wrong token with 401 before any tool runs. ✅ `inbound`, tested
- [ ] **Tokens are checked for issuer, audience (or client), expiry, signature and algorithm.** ✅ `JWTVerifier` + required issuer, audience or `allowed_client_ids`, `required_claims`, and a required `exp` (FastMCP alone accepts a token with none)
- [ ] **No passthrough.** No caller's token or header reaches a target; each target gets only its own credential. ✅ fixed and tested (see [FINDINGS.md](FINDINGS.md) 1–2)
- [ ] **Short-lived tokens where possible** (5–15 minutes); static keys only for development. ⚠️ Your identity provider's settings
- [ ] **Each agent and each person has its own identity**, and the audit names it. ✅
- [ ] **A copilot acts with the person's token only toward the app it was issued for**, and with an exchanged or its own identity toward the gateway. ⚠️ A design rule ([IDENTITY_AND_AUTH.md](IDENTITY_AND_AUTH.md))

## Authorization

- [ ] **Deny by default:** nothing is allowed without a permit. ✅ Cedar semantics
- [ ] **Least privilege per caller and per tool.** The Copilot gets no write tools, and tools a caller may never use are hidden. ✅ policies + `hide_unpermitted_tools`
- [ ] **Limits on arguments for consequential actions** (payments, sending, deleting). ✅ `payment-limit`
- [ ] **Fail closed** on policy errors, unknown tools, malformed arguments and an unreachable engine. ✅ `deny_on_evaluation_errors`, schema, engine errors deny
- [ ] **Roll out log-only, then enforce,** and read the would-be refusals in between. ✅ `policy.mode`
- [ ] **A refusal routes to a person; it isn't retried.** ✅ `retryable: false`; the agent example turns it into "left for sign-off"
- [ ] **The app enforces its own limits too.** The gateway is a second layer, never the only one. ⚠️ Your app (UnderCover does)
- [ ] **Human-only actions** (a sign-off that pays) **aren't tools at all.** ✅ the operation allow-list keeps them out even when the API document has them

## Tools and inputs

- [ ] **Only allow-listed operations become tools** (`include_operations`). ✅
- [ ] **Only tools pass through the gateway, and only under their target's prefix.** ✅ An upstream's resources and prompts are hidden, and unprefixed or hashed names are refused ([FINDINGS.md](FINDINGS.md) 11–12)
- [ ] **Callers can't forge typed values for the policy** (Cedar's `__extn`/`__entity` keys) **or slip past a limit by rounding.** ✅ refused in `to_cedar`
- [ ] **Tool definitions are pinned:** regenerate the Cedar schema or a `tools/list` snapshot in CI, and fail on a diff, against "rug-pull" tool changes. ⚠️ The schema supports it; wire it into your CI
- [ ] **Arguments are validated** against the tool's input schema, with limits on size and range. ⚠️ FastMCP doesn't check an OpenAPI tool's arguments: the app does (a 422), and unknown arguments are silently dropped. With `schema_file` set, the gateway's Cedar schema refuses wrong types and unknown arguments before the call
- [ ] **Untrusted text is screened before the agent acts on it**, including tool results. ⚠️ The course's model-based check covers claims; add `ApplyGuardrail` or a screening model as a middleware for tool results
- [ ] **The lethal trifecta is broken for every agent:** never private data, untrusted content and an exfiltration channel together. ⚠️ A design review per agent

## Operations

- [ ] **Secrets in a vault**, cached briefly, never in config, logs, prompts, state or memory. ✅ `SecretResolver`; audit logs argument names only, by default
- [ ] **Audit every decision and call** with principal, tool, decision, rules and time; never tokens. ✅ `audit.py`; add a trace id for Langfuse/OTel
- [ ] **Rate limits and timeouts.** ⚠️ Add FastMCP's `RateLimitingMiddleware` or put API Gateway in front; target timeouts are set (`timeout_seconds`)
- [ ] **The gateway's own role is scoped** to its secret, its policy store and its target functions. ✅ `template.yaml`
- [ ] **Dependencies are pinned** (`uv.lock`), and the tests run on every change. ✅
- [ ] **An inventory of MCP servers**, so no "shadow" server is called around the gateway. ⚠️ An organizational control
- [ ] **A teardown that finds resources by name**, and a budget with alerts before anything is created. ✅ documented in [`examples/aws_native/README.md`](../examples/aws_native/README.md)

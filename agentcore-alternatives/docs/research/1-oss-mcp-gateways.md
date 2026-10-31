> Research report by a sub-agent (Claude Sonnet 5.5) on 31 October 2026, kept as written. It cites its sources; anything marked UNVERIFIED wasn't confirmed. The code and docs in this folder supersede it where they differ.

# MCP gateway and aggregator alternatives to Amazon Bedrock AgentCore Gateway, for UnderCover (as of 31 Oct 2026)

## Summary

- **No single product matches AgentCore exactly.** AgentCore combines namespaced aggregation, an OpenAPI target, SigV4 inbound auth, a vault-backed credential provider, and Cedar with a log-only mode.
- **agentgateway is the best functional match with the least code.** It aggregates targets with prefixing, converts OpenAPI to MCP, validates JWTs, injects per-target API keys, and signs outbound requests with SigV4. It also enforces arg-level CEL rules (conditions on tool-call arguments, such as `amount > 1000`) through `mcpGuardrails`. It has no Cedar, no inbound SigV4 and no log-only mode.
- **ToolHive vMCP is the only candidate with native Cedar.** It supports `arg_*` conditions, but it is Kubernetes-only and has no OpenAPI→MCP.
- **Python-extensible options are LiteLLM and IBM Context Forge.** LiteLLM is also a Bedrock model gateway. Context Forge reaches Cedar and OPA through a sidecar, and `cedar-agent` has not had a commit in a year.
- **Nobody documents inbound SigV4.** The usual fix is JWT inbound, or API Gateway with IAM auth in front. That pattern is my inference and is UNVERIFIED.
- **Envoy AI Gateway is now "Agent Router".** The repo moved to `theagentrouter/agent-router`, and it is an Agentic AI Foundation (AAIF) project. See [README](https://github.com/theagentrouter/agent-router#formerly-envoy-ai-gateway).

Method notes:
- Stars, releases and dates come from the live GitHub API on 31 Oct 2026.
- `docs.litellm.ai` and `theagentrouter.ai` returned 403 to my fetcher. I read their docs from the GitHub sources ([BerriAI/litellm-docs](https://github.com/BerriAI/litellm-docs), [theagentrouter/agent-router](https://github.com/theagentrouter/agent-router)) at `main`, so they may be slightly ahead of the releases.

---

## 1. Comparison table (strongest candidates)

| Product | License | Stars / latest release | Lang | OpenAPI→MCP | Aggregation + prefix | Inbound auth | Outbound credential injection | Per-tool policy (engine; arg-level?; dry-run?) | AWS deploy fit | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **[agentgateway](https://github.com/agentgateway/agentgateway)** (LF / [AAIF](https://aaif.io/projects)) | Apache-2.0 | 5.8k / v1.7.0 (27 Oct 2026) | Rust | Yes, `openapi` target, `operationId` becomes the tool name ([doc](https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/openapi/)) | Yes. `<target>_<tool>`, `prefixMode` conditional/always/never, target names can't contain `_` ([doc](https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/virtual/)) | JWT/JWKS, OAuth resource server (Keycloak/Auth0/Entra/Okta adapters), API key, basic, OIDC ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authn/)). No SigV4 inbound found | Per target: static key to any header/query/cookie from env or file, passthrough, token exchange, **AWS SigV4** ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/)). No Secrets Manager integration | CEL. `mcpAuthorization` sees tool name, target and JWT claims but **not arguments**. `mcpGuardrails` expression/remote gRPC **can read args** ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/guardrails/processors/)). **No dry-run** | Official image `cr.agentgateway.dev/agentgateway` ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/setup/install/docker/)): ECS, EC2 or EKS. Lambda is a poor fit (inferred) | Strongest feature fit. Fast-moving 1.x with breaking changes noted in docs |
| **[ToolHive vMCP](https://github.com/stacklok/toolhive)** | Apache-2.0 | 2.3k / v0.59.0 (28 Oct 2026) | Go | No (wrap the app with FastMCP) | Yes. Conflict strategies prefix/priority/manual ([arch](https://github.com/stacklok/toolhive/blob/main/docs/arch/10-virtual-mcp-architecture.md)) | OIDC/JWT, introspection, K8s service-account tokens ([doc](https://docs.stacklok.com/toolhive/guides-vmcp/authentication)) | `headerInjection` from a K8s Secret, RFC 8693 token exchange, AWS STS, passthrough | **Cedar native**, `resource.arg_*` ([authz.md](https://github.com/stacklok/toolhive/blob/main/docs/authz.md)). List filtering. No dry-run found | K8s operator only (EKS) | Best Cedar parity. Pre-1.0 but very active |
| **[IBM ContextForge](https://github.com/IBM/mcp-context-forge)** | Apache-2.0 | 4.7k / v1.1.0 (20 Oct 2026) | Python | Partial. REST tools registered one by one, OpenAPI used for schema extraction ([code](https://github.com/IBM/mcp-context-forge/blob/main/mcpgateway/services/openapi_service.py)). No bulk import found | Yes, virtual servers. `<gateway-slug><sep><tool>` via `GATEWAY_TOOL_NAME_SEPARATOR` ([ADR 011](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/architecture/adr/011-tool-federation.md)) | Own JWT, basic, SSO, API tokens, team RBAC ([rbac.md](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/manage/rbac.md)) | `authheaders` (multi-header, e.g. `X-API-Key`), bearer, OAuth2; AES-256-GCM in DB ([doc](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/multi-auth-headers.md)). No SigV4 found | RBAC plus a Unified PDP plugin (native/MAC/OPA/Cedar). Args reach the policy as `context.tool_args`. Plugin mode `permissive` is the closest thing to log-only | Docker, Helm, [AWS ECS/EKS doc](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/deployment/aws.md) | Capable but heavy. Plugin framework moved to CPEX (breaking change) |
| **[LiteLLM Proxy](https://github.com/BerriAI/litellm)** | MIT, plus commercial `enterprise/` dir ([LICENSE](https://github.com/BerriAI/litellm/blob/main/LICENSE)) | 62.4k / v1.106.6 (28 Oct 2026) | Python | Yes, `spec_path` ([doc](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_openapi.md)) | Yes. `/mcp` for all, `/{server}/mcp` for one, `<alias>-<tool>` ([ref](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_config_reference.md)) | Virtual keys. **JWT/OIDC is an Enterprise feature** ([token_auth](https://github.com/BerriAI/litellm-docs/blob/main/docs/proxy/token_auth.md)) | Per server `auth_type` (api_key/bearer/basic/oauth2/token-exchange/**aws_sigv4**) plus `static_headers` | Per key/team tool allow/deny; `allowed_params` (parameter names only); guardrails `pre_mcp_call` (Presidio etc., custom Python) ([doc](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_guardrail.md)). `logging_only` guardrail mode exists generally; MCP use UNVERIFIED | Docker, Helm, Terraform. Same proxy is a Bedrock gateway | Very mature as LLM gateway. MCP side newer |
| **[Agent Router](https://github.com/theagentrouter/agent-router)** (ex Envoy AI Gateway) | Apache-2.0 | 2.3k / v1.2.0 (7 Oct 2026); v1.2.1-rc2 (28 Oct) | Go on Envoy | No | Yes. `<backend>__<tool>`, `prefixMode` Always/Never ([doc](https://github.com/theagentrouter/agent-router/blob/main/site/docs/capabilities/mcp/index.md)) | OAuth 2.1 resource server (issuer/audiences/PRM), API key | `securityPolicy.apiKey` (secretRef/inline, custom `header` or `queryParam`), `forwardHeaders` | CEL (experimental) incl. `request.mcp.params.arguments`, JWT scopes/claims, first-match Allow/Deny ([API](https://github.com/theagentrouter/agent-router/blob/main/api/v1beta1/mcp_route.go#L525-L598)). No dry-run found | K8s/Envoy Gateway (EKS) | Solid, Envoy-based, AAIF-governed |
| **[Obot](https://github.com/obot-platform/obot)** | MIT | 1.1k / v0.27.0 (20 Oct 2026) | Go | Yes, one tool per operation ([README](https://github.com/obot-platform/obot#readme)) | Yes, vMCPs | IdP users/groups via profiles | OAuth and credential management, K8s secret bindings | Filters (guardrail / MCP filter server / HTTP webhook: accept/reject/mutate, audit log) ([doc](https://github.com/obot-platform/obot/blob/main/docs/docs/functionality/filters.md)). Arg rules require your own webhook | Docker or K8s | Good platform product. Policy is code you write |
| **Kong AI Gateway** | OSS Kong Apache-2.0 (3.9.4, 12 Oct 2026). **MCP plugins are Enterprise only, ≥3.12** | n/a | Lua | Yes, `conversion-*` modes ([doc](https://developer.konghq.com/plugins/ai-mcp-proxy/)) | Yes, `listener` mode aggregates conversion-only plugins | OIDC, Key Auth, [AI MCP OAuth2](https://developer.konghq.com/plugins/ai-mcp-oauth2/) | Via Kong plugins | Consumer/group ACL per tool with audit log; **no arg-level rule documented** | Self-hosted or Konnect | Commercial |
| **Traefik Hub MCP Gateway** | Commercial | n/a | Go | UNVERIFIED | UNVERIFIED | JWT resource server | Injects upstream API keys | Claims "down to individual tool arguments", compares args to JWT claims, deny by default ([page](https://traefik.io/solutions/mcp-gateway)) | Any orchestrator | Marketing page only. Config syntax UNVERIFIED |

### Others (brief)

| Product | Facts | Verdict |
|---|---|---|
| [Pomerium](https://www.pomerium.com/docs/capabilities/mcp) (Apache-2.0, 5.1k, v0.33.6) | `mcp_tool` matches tool name only ([doc](https://www.pomerium.com/docs/capabilities/mcp/limit-mcp-tools)). Per-route servers. Upstream OAuth bridging | Identity-aware proxy, not a tool-arg gateway |
| [Docker MCP Gateway](https://github.com/docker/mcp-gateway) (MIT, 1.6k, tag v0.44.3) | Single `MCP_GATEWAY_AUTH_TOKEN`, `--allow-unauthenticated`, `--interceptor before/after:exec/docker/http` ([flags](https://github.com/docker/mcp-gateway/blob/main/docs/generator/reference/mcp_gateway_run.md)). Interceptors receive the full tool-call JSON, so scripts could check `amount` | Dev/local oriented |
| [Microsoft MCP Gateway](https://github.com/microsoft/mcp-gateway) (MIT, 899, tag v1.0.0, no releases) | AKS and Entra ID app roles per adapter/tool. Requires MCP 2026-07-28 clients ([README](https://github.com/microsoft/mcp-gateway#readme)) | Azure-centric. No arg policy |
| [MCPJungle](https://github.com/mcpjungle/MCPJungle) (MPL-2.0, 1.3k, 0.4.7) | `<server>__<tool>`, tool groups, static bearer upstream, enterprise mode adds ACLs | Simple registry. No OpenAPI, no arg policy |
| [Unla](https://github.com/AmoyLab/Unla) (MIT, 2.2k, v0.10.0, 4 Aug 2026) | YAML REST→MCP. Roadmap item "grouping and aggregating" unchecked ([README](https://github.com/AmoyLab/Unla#readme)) | Not an aggregator |
| [MetaMCP](https://github.com/metatool-ai/metamcp) (MIT, 2.7k, v2.4.22 of 19 Dec 2025, last push Jun 2026) | Namespaces and endpoints, API key/OIDC. Middleware "coming soon" | Slowing |
| [Lasso mcp-gateway](https://github.com/lasso-security/mcp-gateway) (MIT, 397, v1.2.0, 21 Jan 2026) | Plugin guardrails, local `mcp.json` proxy | Stale |
| [Higress](https://github.com/higress-group/higress) (Apache-2.0, 9.7k, v2.2.5) | [openapi-to-mcpserver](https://github.com/higress-group/openapi-to-mcpserver) plus Wasm plugins | Capable. Alibaba ecosystem |
| Apache APISIX 3.19.0 | `mcp-bridge` is **deprecated** ([doc](https://apisix.apache.org/docs/apisix/plugins/mcp-bridge/)) | Skip |
| [Azure APIM](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview) | REST API as MCP server, or expose an existing MCP server. "Policies apply to all API operations exposed as tools" (no per-tool policy) | Cross-cloud, not for this case |
| [Cloudflare MCP portals](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/) | SaaS aggregation with tool selection, aliases and Access policies | Not AWS |
| **FastMCP** v4.1.4 (Apache-2.0, 28k) | `mount(create_proxy(url), namespace="api")` ([doc](https://gofastmcp.com/servers/composition.md)); [OpenAPI integration](https://gofastmcp.com/integrations/openapi.md); middleware; authorization checks | The build-your-own option, which another agent covers in depth |

---

## 2. Concrete configs

### 2.1 agentgateway (standalone YAML)

Docs: [mcp-authn](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authn/), [target policies](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/mcp-target-policies/), [key auth](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/key/), [AWS auth](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/providers/aws/), [guardrails](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/guardrails/processors/).

```yaml
# yaml-language-server: $schema=https://agentgateway.dev/schema/config
mcp:
  port: 3000
  prefixMode: always
  policies:
    mcpAuthentication:            # inbound JWT (documented form with jwks.url)
      mode: strict
      issuer: https://<proj>.supabase.co/auth/v1
      audiences: ["https://mcp.example.com/mcp"]
      jwks: { url: https://<proj>.supabase.co/auth/v1/.well-known/jwks.json }
      resourceMetadata: { resource: https://mcp.example.com/mcp }
    mcpAuthorization:             # which tools/targets a caller may see (no args here)
      rules:
      - 'mcp.tool.target == "undercover-context"'
      - 'mcp.tool.target == "undercover-app" && has(jwt.groups) && "claims-agent" in jwt.groups'
    mcpGuardrails:                # the arg-level rule
      processors:
      - kind: expression
        condition: >-
          mcp.tool.target == "undercover-app" && mcp.params.name == "pay_claim" &&
          double(mcp.params.arguments.amount) > 1000.0
        reject: "pay_claim above 1000 is not allowed"
        methods: { tools/call: request }
  targets:
  - name: undercover-app          # tools: undercover-app_pay_claim ...
    openapi:
      host: undercover-app.internal:8000
      schema: { url: http://undercover-app.internal:8000/openapi.json }
    policies:
      backendAuth:
        key:
          value: $UNDERCOVER_API_KEY          # env var (ECS "secrets" can populate it)
          location: { header: { name: x-api-key, prefix: "" } }
  - name: undercover-context
    mcp: { host: https://<id>.lambda-url.eu-west-2.on.aws/mcp }
    policies:
      backendAuth: { aws: { region: eu-west-2, serviceName: lambda } }
```

**Why the policy is in `mcpGuardrails`.** The [MCP authz page](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/) states: "`mcp.tool.arguments` isn't set when `mcpAuthorization` rules run". Guardrail processors do read `mcp.params`. A denial returns a tool result with `isError: true` and your message, over HTTP 200.

**Caveats:**
- **Header prefix.** `location.header.prefix: ""` is UNVERIFIED. The docs show `prefix: "Bearer "` and say Bearer is the default.
- **Lambda signing name.** `serviceName: lambda` is not in the agentgateway docs. The field accepts any signing name, and `lambda` is AWS's signing name for Function URLs (from my own AWS knowledge, not fetched).
- **JSON number typing.** The `double()` call is there to avoid int/double comparison surprises. Test it in the built-in CEL playground.
- **Fail-closed on error.** A CEL evaluation error in a guardrail processor is a rejection, not a pass.
- **Log-only workaround.** There is no official dry-run. A documented pattern is an access-log field such as `frontendPolicies.accessLog.add.would_deny: '<same expression>'` ([mcp-authz doc](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/#tool-arguments-are-not-available-during-authorization)). It is inferred, not a dry-run feature.
- **Observability.** `mcp_requests_total{server,method,resource}` plus OTLP traces ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/mcp-observability/)). I did not find a dedicated "denied" counter (UNVERIFIED).
- **Rate limiting.** `localRateLimit` and `remoteRateLimit` exist under `mcp.policies` ([schema](https://github.com/agentgateway/agentgateway/blob/v1.7.0/schema/config.md)).

### 2.2 ToolHive vMCP (Kubernetes)

Docs: [authentication](https://docs.stacklok.com/toolhive/guides-vmcp/authentication) (header injection, OIDC, `authzConfig` verbatim syntax), [configuration](https://docs.stacklok.com/toolhive/guides-vmcp/configuration), [authz.md](https://github.com/stacklok/toolhive/blob/main/docs/authz.md#L450-L458) (`arg_*` example).

```yaml
apiVersion: toolhive.stacklok.dev/v1beta1
kind: MCPExternalAuthConfig
metadata: { name: app-api-key, namespace: toolhive-system }
spec:
  type: headerInjection
  headerInjection:
    headerName: X-API-Key
    valueSecretRef: { name: backend-api-key, key: value }   # K8s Secret, plaintext rejected
---
apiVersion: toolhive.stacklok.dev/v1beta1
kind: VirtualMCPServer
metadata: { name: undercover, namespace: toolhive-system }
spec:
  groupRef: { name: undercover-group }   # MCPGroup holding the backends
  incomingAuth:
    type: oidc
    oidcConfigRef: { name: vmcp-oidc, audience: https://mcp.example.com/mcp }
    authzConfig:
      type: inline
      inline:
        policies:
        - 'permit(principal, action == Action::"call_tool", resource);'
        - |
          forbid(principal, action == Action::"call_tool", resource == Tool::"pay_claim")
          when { resource.arg_amount > 1000 };
  outgoingAuth:
    source: inline
    backends:
      undercover-app:
        type: externalAuthConfigRef
        externalAuthConfigRef: { name: app-api-key }
```

**Missing or unverified:**
- **OpenAPI→MCP.** Not a feature. Wrap the FastAPI app with FastMCP and register it as an `MCPServer` or `MCPServerEntry`.
- **Tool ID in a vMCP.** Whether `Tool::"pay_claim"` is the prefixed tool ID in a vMCP is UNVERIFIED. See the [authz reference](https://docs.stacklok.com/toolhive/reference/authz-policy-reference#backend-scoped-tools-on-a-virtualmcpserver).
- **Numeric typing.** Args arrive as `string/bool/int/int64/float64` ([core.go:1029-1046](https://github.com/stacklok/toolhive/blob/main/pkg/authz/authorizers/cedar/core.go#L1029-L1046)). Cedar has no float type, so fractional amounts may not compare cleanly (UNVERIFIED). Use integer cents.
- **Lambda SigV4.** The docs list an "AWS STS" strategy for AWS APIs. Whether it covers a Lambda Function URL is UNVERIFIED. Running the context server on Fargate behind a private service avoids the question.
- **Dry-run.** None found.
- **Policy shape.** A `forbid` that errors (missing arg) does not apply, so require the arg in the schema.

### 2.3 IBM ContextForge

Docs: [multi-auth-headers](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/multi-auth-headers.md), [Unified PDP README](https://github.com/IBM/mcp-context-forge/blob/main/plugins/unified_pdp/README.md), [cedar_engine.py#L225-L230](https://github.com/IBM/mcp-context-forge/blob/a75ff7222d6b3d6df010cab340bc7e5a4e854c94/plugins/unified_pdp/engines/cedar_engine.py#L225-L230), [unified_pdp.py#L259-L276](https://github.com/IBM/mcp-context-forge/blob/a75ff7222d6b3d6df010cab340bc7e5a4e854c94/plugins/unified_pdp/unified_pdp.py#L259-L276).

```jsonc
// POST /tools  (REST tool with API-key header; documented body shape)
{ "name": "pay-claim", "url": "https://app.internal/claims/pay", "request_type": "POST",
  "auth_type": "authheaders", "auth_headers": [ {"key": "X-API-Key", "value": "<secret>"} ] }
// POST /gateways  (MCP upstream) -> {"name":"undercover-context","url":"...","auth_type":"authheaders", ...}
```

```yaml
# plugins/config.yaml
- name: "UnifiedPDPPlugin"
  kind: "plugins.unified_pdp.unified_pdp.UnifiedPDPPlugin"
  hooks: ["tool_pre_invoke", "resource_pre_fetch"]
  mode: "enforce"            # "permissive" = warn-and-continue (ADR 016), i.e. dry-run
  priority: 10
  config:
    engines: [ { name: cedar, enabled: true, priority: 1, settings: { cedar_url: "http://localhost:8700" } } ]
    combination_mode: "all_must_allow"
    default_decision: "deny"
```
```cedar
// loaded into cedar-agent. Action id is "tools.invoke.<tool_name>"
permit (principal, action, resource);
forbid (principal, action == Action::"tools.invoke.pay-claim", resource)
  when { context.tool_args.amount > 1000 };
```

**Why this works:** the plugin puts `tool_args` into the Cedar request context (`unified_pdp.py:276`, `cedar_engine.py:225-230`).

**Gaps and risks:**
- **REST tools are per-endpoint.** There are 6 endpoints here, which is fine, but there is no bulk OpenAPI import (not found).
- **SigV4 and third-party JWT.** No outbound SigV4 found, and third-party (Supabase) JWT inbound is UNVERIFIED.
- **Stale Cedar sidecar.** The README says to see "PR #1499" for `cedar-agent` setup. [permitio/cedar-agent](https://github.com/permitio/cedar-agent) was last pushed 16 Oct 2025.
- **Permissive mode semantics.** The newer CPEX framework maps `permissive` to `PluginMode.TRANSFORM` ([code](https://github.com/IBM/mcp-context-forge/blob/main/mcpgateway/plugins/gateway_plugin_manager.py)). Whether that still means "log only" is UNVERIFIED.
- **Alternative.** A ~20-line custom Python plugin on `tool_pre_invoke` can read `payload.args["amount"]` directly. Plugin API: [migration doc](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/plugins/migration-to-cpex.md).

### 2.4 LiteLLM Proxy

Docs: [mcp_openapi](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_openapi.md), [mcp_aws_sigv4](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_aws_sigv4.md), [mcp_control](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_control.md), [mcp_guardrail](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_guardrail.md).

```yaml
mcp_servers:
  undercover_app:
    url: "http://app.internal:8000"
    spec_path: "http://app.internal:8000/openapi.json"   # tools: undercover_app-<operationId>
    static_headers: { X-API-Key: "<key>" }               # NOT auth_type: api_key (see below)
    allowed_tools: [get_claim, get_policy, get_claim_history, calculate_payout, record_decision, pay_claim]
  undercover_context:
    url: "https://<id>.lambda-url.eu-west-2.on.aws/mcp"
    transport: "http"
    auth_type: "aws_sigv4"       # region/service set in UI fields or AWS_REGION_NAME
general_settings:
  enable_jwt_auth: true          # Enterprise feature; JWT_PUBLIC_KEY_URL / JWT_AUDIENCE env
```

**What the docs do and don't support:**
- **API-key header.** For the OpenAPI path, `auth_type: api_key` emits `Authorization: ApiKey <value>`, not `X-API-Key` ([ref, line 161](https://github.com/BerriAI/litellm-docs/blob/main/docs/mcp_config_reference.md)). `static_headers` do apply to the OpenAPI path ([code](https://github.com/BerriAI/litellm/blob/main/litellm/proxy/mcp_server/openapi_to_mcp_generator.py#L521-L564)). Whether `static_headers` accepts `os.environ/` references is UNVERIFIED.
- **Arg-value conditions.** `allowed_params` restricts parameter names only. For `amount > 1000` you need a custom Python guardrail. The code path passes `data={"name":..., "arguments":...}` to pre-call hooks ([operations.py:341-344](https://github.com/BerriAI/litellm/blob/main/litellm/proxy/mcp_server/operations.py#L341-L344)). The docs have no worked example for MCP arguments, so which `mode` triggers a custom class (`pre_mcp_call` vs `pre_call`) is UNVERIFIED.
- **Inbound JWT.** JWT auth is marked Enterprise ([token_auth.md](https://github.com/BerriAI/litellm-docs/blob/main/docs/proxy/token_auth.md)). The free path is virtual keys.
- **Dry-run.** A `logging_only` guardrail mode exists generally ([decision_model.md](https://github.com/BerriAI/litellm-docs/blob/main/docs/proxy/guardrails/decision_model.md)). Whether MCP guardrails honour it is UNVERIFIED.

### 2.5 Agent Router (ex Envoy AI Gateway), Kubernetes

Docs: [MCP capability page](https://github.com/theagentrouter/agent-router/blob/main/site/docs/capabilities/mcp/index.md), [MCPRoute API](https://github.com/theagentrouter/agent-router/blob/main/api/v1beta1/mcp_route.go).

```yaml
apiVersion: aigateway.envoyproxy.io/v1beta1
kind: MCPRoute
metadata: { name: undercover, namespace: default }
spec:
  parentRefs: [ { name: aigw-run, kind: Gateway, group: gateway.networking.k8s.io } ]
  path: "/mcp"
  backendRefs:
  - name: undercover-app        # must be an MCP server (FastMCP.from_openapi wrapper): no OpenAPI→MCP feature
    kind: Backend
    group: gateway.envoyproxy.io
    securityPolicy: { apiKey: { secretRef: { name: app-api-key }, header: X-API-Key } }
  - { name: undercover-context, kind: Backend, group: gateway.envoyproxy.io, path: "/mcp" }
  securityPolicy:
    oauth:
      issuer: "https://<proj>.supabase.co/auth/v1"
      audiences: ["https://mcp.example.com/mcp"]
      protectedResourceMetadata: { resource: "https://mcp.example.com/mcp" }
    authorization:
      defaultAction: Allow            # default is Deny
      rules:
      - action: Deny
        target: { tools: [ { backend: undercover-app, tool: pay_claim } ] }
        cel: 'double(request.mcp.params.arguments.amount) > 1000.0'
```

**Caveats:**
- **Experimental CEL.** The CEL attributes are marked experimental.
- **Evaluation errors.** Errors count as "no match", so a deny rule fails open.
- **Rule limit.** There is a 32-rule maximum.
- **No dry-run** found.
- **Serverless.** The Lambda SigV4 backend is not documented for MCP (UNVERIFIED).

### 2.6 Obot, Kong, Traefik: no snippet

- **Obot:** the docs describe UI/API-driven filters. The filter contract is in `docs/reference/filter-schemas.md`. I found no declarative YAML to quote.
- **Kong:** the ACL is consumer/group allow/deny per tool. There is no argument condition in the AI MCP Proxy docs, so `amount > 1000` would need a separate plugin outside the MCP proxy (UNVERIFIED).
- **Traefik Hub:** the config syntax is not in anything I could fetch.

---

## 3. Gaps vs AgentCore and how each candidate closes them

| AgentCore capability | agentgateway | ToolHive | Context Forge | LiteLLM | Agent Router |
|---|---|---|---|---|---|
| **SigV4 inbound** | Not documented. JWT instead | No (OIDC) | No found | No found | No (OAuth/API key) |
| **Cedar** | No, CEL. `ExtMCP` gRPC can call your own Cedar service ([doc](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/guardrails/processors/#remote-processors)) | **Native** | Via `cedar-agent` sidecar (stale) | No. Python guardrail could embed [cedarpy](https://github.com/k9securityio/cedar-py) (v4.12.2) | No, CEL |
| **Arg conditions** | Yes, in `mcpGuardrails` | Yes, `arg_*` | Yes, `context.tool_args` (or plugin) | Only via custom guardrail | Yes, CEL |
| **LOG_ONLY → ENFORCE** | Access-log workaround only | None found | `permissive` plugin mode (semantics UNVERIFIED on CPEX) | `logging_only` exists generally (MCP UNVERIFIED) | None found |
| **Vault-backed credentials** | Env/file only | K8s Secret refs | AES-encrypted DB | `os.environ/` and encrypted DB (partly UNVERIFIED) | K8s Secret refs |
| **Outbound SigV4 to Lambda URL** | `backendAuth.aws` | AWS STS strategy (Lambda coverage UNVERIFIED) | None found | `aws_sigv4` (UI/env fields) | None found |
| **Tool naming** | `target_tool` | Configurable (prefix) | `slug-tool` | `alias-tool` | `backend__tool` |
| **Denial surface** | Tool result `isError:true`, HTTP 200 | HTTP 403, JSON-RPC code 403 | Plugin violation | Guardrail error | Not verified |

- **Inbound SigV4.** Options are to authenticate callers with JWT (Cognito, Supabase) at the gateway, or to put API Gateway with IAM auth in front (UNVERIFIED, not researched). [aws/mcp-proxy-for-aws](https://github.com/aws/mcp-proxy-for-aws) (Apache-2.0, v1.7.0, 15 Sep 2026) only signs client-side requests to AWS-hosted MCP servers.
- **Rename the tools.** Your tests reference `___`; every candidate uses a different separator. Expect to change the prompts or the tool allow-lists.

---

## 4. Recommendation

**(a) Customizable, Python team, small scale**

1. **agentgateway.** One container on ECS Fargate and one YAML file give you aggregation, OpenAPI, JWT, key injection, SigV4 and arg-level deny. Extend it with an `ExtMCP` gRPC processor, which you can write in Python, if you need Cedar or a real dry-run.
2. **FastMCP as a thin custom gateway.** Use `create_proxy` + `mount(namespace=)` + `from_openapi` + middleware, and evaluate your existing Cedar text with `cedarpy`. This is the only route to true LOG_ONLY plus Cedar parity at small scale. You own the security surface.
3. **LiteLLM Proxy.** Choose it if you also want one Bedrock model gateway with budgets and keys. Accept virtual-key auth (or an Enterprise license for JWT) and write a Python guardrail for `amount > 1000`.

Context Forge fits "Python plugins" but is a heavier stack (database, Redis, UI) than this scale needs.

**(b) Enterprise, platform team, Kubernetes**

1. **agentgateway on K8s.** It is Linux Foundation / AAIF governed, has AWS among its contributors ([LF release](https://www.linuxfoundation.org/press/linux-foundation-welcomes-agentgateway-project-to-accelerate-ai-agent-adoption-while-maintaining-security-observability-and-governance)), and has the widest feature coverage.
2. **ToolHive vMCP.** Pick it if keeping Cedar is a hard requirement. Accept wrapping the OpenAPI app in an MCP server and testing numeric argument typing.
3. **Agent Router.** Pick it if you already run Envoy Gateway, or **Obot** if you want a registry, catalog and UI with OpenAPI→MCP built in.

If you already pay for them, Kong Enterprise or Traefik Hub offer arg-level policy commercially. Traefik's claims are unverified here.

---

## Gaps in this research

- **Unfetchable docs.** I could not fetch `docs.litellm.ai` or `theagentrouter.ai`, so I used the docs repos instead.
- **Traefik Hub.** `doc.traefik.io` pages returned 404 or redirect loops, so only the marketing page was read.
- **Not read in depth.**
  - Obot filter schemas.
  - ToolHive tool IDs inside a vMCP.
  - agentgateway's Kubernetes (CRD) mode.
  - Solo's commercial distribution.
- **Not exercised.** I did not run any gateway end to end. Every snippet is built from doc syntax and would need a test pass, especially the numeric comparisons.

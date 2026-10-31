# Options for replacing AgentCore Gateway, Policy and Identity

Checked on 31 October 2026. Stars, versions and prices change quickly, so check them again before you decide.

## What has to be replaced

In UnderCover, from Week 3 Day 2 onward, AgentCore does six jobs between the claim agent and its tools:

1. **One MCP endpoint** over two targets: the app's OpenAPI document (six operations) and the context layer's MCP server. Tools are named `<target>___<operation>`.
2. **Inbound authentication:** callers sign with SigV4 (IAM), or present OAuth tokens.
3. **Outbound credentials the agent never holds:** the app's `X-API-Key` comes from a vault, and calls to the context layer's Lambda are SigV4-signed with the gateway's own role.
4. **A policy on every call, with conditions on arguments:** Cedar rules such as no `pay_claim` over $1,000.
5. **Log-only, then enforce,** with the decisions counted.
6. **A refusal the agent can route**, rather than retry: "Tool Execution Denied" as an MCP error.

The Copilot adds a seventh: **acting for a signed-in person** without passing their token through the gateway (see [IDENTITY_AND_AUTH.md](IDENTITY_AND_AUTH.md)).

## The options

### A. A self-built gateway in Python: FastMCP + Cedar (this folder)

`diy_gateway/` is about 1,400 lines on FastMCP 4.1.4, `cedarpy` 4.12.2 and `httpx2`. It covers all seven jobs, including inbound IAM (on a Lambda Function URL), log-only mode, and the AgentCore naming and refusal.

- **Pros:**
  - Cedar parity: the course's Cedar rules port with only a namespace change.
  - Every piece is plain Python your team can read, test and extend.
  - No per-call policy cost with the in-process engine.
  - Runs on a laptop, Lambda, ECS or Render.
- **Cons:**
  - You own the security surface. [FINDINGS.md](FINDINGS.md) lists the traps hit while building and reviewing it, among them FastMCP defaults that pass the caller's token and headers on, and accept tokens with no expiry.
  - FastMCP moves fast: 4.x changed the proxy, the transport (`httpx2`) and the SDK (`mcp` 2.x). Pin versions, and keep the tests.
  - No admin UI or catalog.
- **Effort:** this folder is the starting point. Allow a few days to adapt it, write the threat model and test it against your own tools.
- **Pick it when:** a small or medium Python team needs Cedar, customization and AgentCore-like behaviour, and is happy to own about 1,400 lines.

### B. Option A on AWS-native services

This is the same gateway, with each managed piece swapped for a generally available AWS service. It is in [`examples/aws_native/`](../examples/aws_native/).

| Concern | Service | Notes |
|---|---|---|
| Hosting | **Lambda** behind a Function URL (`AWS_IAM`) | Stateless MCP suits Lambda. AWS's own guidance puts long-lived or streaming-heavy MCP servers on **ECS Fargate** instead. [ECS blog](https://aws.amazon.com/blogs/containers/deploying-model-context-protocol-mcp-servers-on-amazon-ecs/) |
| Inbound identity | **IAM** (SigV4, checked by AWS before the code runs) or **Cognito** (client credentials for agents, user pools for people) | Cognito has no RFC 8693 token exchange and no Dynamic Client Registration. [token endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html) |
| Outbound secrets | **Secrets Manager** with a cache | $0.40 per secret per month. Rotation needs the app to accept two keys during the window |
| Policy | **Amazon Verified Permissions** (managed Cedar, schema validation, a store your security team can review) or `cedarpy` in process | AVP costs $5 per million `IsAuthorized` calls, has a default quota of 200 RPS per store, and has no log-only mode (the gateway provides one). [pricing](https://aws.amazon.com/verified-permissions/pricing/), [quotas](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/quotas.html) |
| Decisions and audit | **CloudWatch Logs** with Embedded Metric Format | `AllowDecisions` and `DenyDecisions` by `Mode`, as AgentCore Policy reports them |
| Injection screening | **Bedrock Guardrails** `ApplyGuardrail` or `InvokeGuardrailChecks` | The inline prompt-attack filter does not scan tool results, so screen them yourself. [prompt attack](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-prompt-attack.html) |

Variants:

- **API Gateway HTTP API with a JWT authorizer (Cognito)** in front of the Lambda. It adds throttling and WAF, and the gateway then runs `inbound.mode: tokens`.
- **ALB + ECS Fargate** for steady traffic.
- AWS's [MCP guidance](https://github.com/aws-solutions-library-samples/guidance-for-deploying-model-context-protocol-servers-on-aws) (CloudFront + WAF + ALB + ECS + Cognito, CDK) is a good template for that.

The closest published AWS sample to this design is [`aws-samples/sample-cedar-agentic-ai-authorization`](https://github.com/aws-samples/sample-cedar-agentic-ai-authorization). It runs API Gateway + Cognito + Guardrails + a Cedar evaluator reading from AVP, and has an [AWS Security blog post](https://aws.amazon.com/blogs/security/enforce-least-privilege-authorization-in-multi-agent-ai-chains-using-cedar/).

### C. An open-source gateway product

| Product | License, size, release | OpenAPI → tools | Inbound | Outbound credentials | Policy on arguments | Log-only | AWS fit | Verdict |
|---|---|---|---|---|---|---|---|---|
| **[agentgateway](https://github.com/agentgateway/agentgateway)** (LF / AAIF) | Apache-2.0, 5.8k★, v1.7.0 (27 Oct 2026), Rust | Yes | JWT/OAuth (MCP auth spec), API key; no inbound SigV4 | Per-target key (env/file), **SigV4**, token exchange | CEL in `mcpGuardrails` (not in `mcpAuthorization`) | No (log a `would_deny` field) | Container on ECS/EKS | **Best feature match.** Naming is `target_tool` |
| **[ToolHive vMCP](https://github.com/stacklok/toolhive)** | Apache-2.0, 2.3k★, v0.59.0, Go | No (wrap with FastMCP) | OIDC/JWT | Header injection from Kubernetes Secrets, token exchange, AWS STS | **Cedar**, `resource.arg_*` | No | Kubernetes operator (EKS) | **Only native Cedar.** Pre-1.0 |
| **[LiteLLM Proxy](https://github.com/BerriAI/litellm)** | MIT core + Enterprise, 62k★, v1.106.6, Python | Yes (`spec_path`) | Virtual keys; JWT is Enterprise | `static_headers`, `aws_sigv4`, OAuth2 | Parameter names only; values need a Python guardrail | `logging_only` exists, MCP use unverified | Docker/ECS | **Pick it to also gateway Bedrock models** (budgets, keys, fallbacks) |
| **[IBM ContextForge](https://github.com/IBM/mcp-context-forge)** | Apache-2.0, 4.7k★, v1.1.0, Python | Per endpoint | Own JWT, SSO, RBAC | Encrypted auth headers, OAuth2; no SigV4 | Cedar/OPA via a sidecar (`tool_args`) | `permissive` plugin mode | [AWS doc](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/deployment/aws.md) | Capable but heavy: database, Redis, UI |
| **[Agent Router](https://github.com/theagentrouter/agent-router)** (was Envoy AI Gateway) | Apache-2.0, 2.3k★, v1.2.0, Go/Envoy | No | OAuth resource server, API key | `apiKey` from a Secret | CEL on `request.mcp.params.arguments` (experimental) | No | Kubernetes | Good if you already run Envoy Gateway |
| **[Obot](https://github.com/obot-platform/obot)** | MIT, 1.1k★, v0.27.0 | Yes | IdP users and groups | OAuth and credential management | Filters/webhooks you write | Audit log | Docker/Kubernetes | A catalog and UI platform |
| [Docker MCP Gateway](https://github.com/docker/mcp-gateway), [Microsoft MCP Gateway](https://github.com/microsoft/mcp-gateway), [MCPJungle](https://github.com/mcpjungle/MCPJungle), [Pomerium](https://www.pomerium.com/docs/capabilities/mcp), [MetaMCP](https://github.com/metatool-ai/metamcp) | various | mostly no | various | basic | tool names only | no | various | For local use, Azure, or identity-aware proxying. Not for argument rules |

The configs for the first four are in [`examples/oss_gateways/`](../examples/oss_gateways/), written from each product's docs and not run here. What none of them gives you, compared with AgentCore:

- **Inbound SigV4.** Put API Gateway with IAM auth in front of them, or use JWTs.
- **A built-in log-only mode.**
- **Cedar,** except ToolHive.
- **AgentCore's naming.** Expect `_`, `__` or `-` separators, so the course's tool names and step names change.

### D. No gateway: enforce in the agent's harness and in the app

This is UnderCover before Week 3 Day 2. The agent calls the app directly with its key, and the limits live in the app (the payment refuses over the approval limit) and in the harness:

- LangChain's `@wrap_tool_call` middleware, or Strands Agents' `BeforeToolCallEvent` hook with `cancel_tool`, can evaluate the same Cedar rules with `cedarpy`, in process. [Strands hooks](https://github.com/strands-agents/harness-sdk)
- **Pros:** simplest, with no extra hop and nothing extra to deploy.
- **Cons:**
  - Each agent repeats the controls, and an agent's process holds the app's key.
  - The security team can't review one place.
  - Nothing sits between a compromised agent process and the app except the app's own checks.
- **Pick it when:** there's one agent, the app's own checks are the authoritative limit, and you don't need central audit yet. The course's advice is to keep gateways lightweight until several agents or apps need one policy.

### E. Commercial and managed gateways

- **[Kong AI Gateway](https://developer.konghq.com/plugins/ai-mcp-proxy/):** the MCP plugins are Enterprise-only (3.12 and later). They convert OpenAPI and do per-tool ACLs; no argument rule is documented.
- **[Traefik Hub MCP Gateway](https://traefik.io/solutions/mcp-gateway):** claims rules down to tool arguments. Only the marketing page could be read.
- **[Permit.io MCP Gateway](https://docs.permit.io/permit-mcp-gateway/overview/):** per-tool allow/deny with trust levels; SaaS control plane.
- **[Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview):** turns REST into MCP or fronts MCP servers, but its policies apply to all of an API's tools rather than one tool. Worth a look if your organization already runs APIM; that's a cross-cloud hop from Bedrock.
- **Cloudflare MCP portals** and **MuleSoft Agent Fabric:** aggregation and access policies as a service.

### F. Amazon Bedrock Agents (classic)

Action groups with OpenAPI schemas and Lambda, return-of-control and user confirmation once covered part of this. **Agents classic closed to new customers on 30 July 2026**; existing customers carry on, and AWS points new work to AgentCore. ([maintenance mode](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html)) Its IAM actions are `bedrock:*Agent*`, separate from `bedrock-agentcore:*`, so an account that only blocks AgentCore might still have it as an existing customer. It's not a path to build on now.

## Comparison

| | A. Self-built | B. A on AWS services | C1 agentgateway | C2 ToolHive | C3 LiteLLM | D. In the harness |
|---|---|---|---|---|---|---|
| OpenAPI + MCP targets, one endpoint | ✅ | ✅ | ✅ | MCP only | ✅ | n/a |
| AgentCore names `<target>___<tool>` | ✅ (configurable) | ✅ | `target_tool` | prefix | `alias-tool` | n/a |
| Inbound IAM (SigV4) | on a Function URL | ✅ | ❌ | ❌ | ❌ | n/a |
| Inbound JWT/OAuth | ✅ | ✅ (Cognito) | ✅ | ✅ | Enterprise | n/a |
| Vault-backed outbound key | env, Secrets Manager | Secrets Manager | env/file | Kubernetes Secret | env/DB | the agent holds it |
| SigV4 to a Lambda target | ✅ | ✅ | ✅ | unverified | ✅ | n/a |
| Cedar | ✅ in process | ✅ AVP or in process | ❌ CEL | ✅ | ❌ (Python hook) | ✅ in process |
| Conditions on arguments | ✅ | ✅ | ✅ | ✅ | custom code | ✅ |
| Log-only, then enforce | ✅ | ✅ | ❌ | ❌ | unverified | ✅ (your code) |
| Fail closed on policy errors | ✅ | ✅ | `require` rules only | unverified | your code | your code |
| Hides tools a caller may never use | ✅ | ✅ (Cedar engine) | ✅ | ✅ | per key | n/a |
| Admin UI or catalog | ❌ | AWS consoles | ✅ | ✅ | ✅ | ❌ |
| You maintain | about 1,400 lines | the same + IaC | config | config + Kubernetes | config + a guardrail | harness code |

## Decision tree

```text
Do several agents or apps need one policy and audit point, or must a security team review the rules?
 ├─ No  -> D: enforce in the app and the harness. Revisit when a second agent arrives.
 └─ Yes -> Must the rules be Cedar (to port AgentCore policies, or to use Verified Permissions)?
      ├─ Yes -> Is the team happy to own a small Python service?
      │     ├─ Yes -> A, deployed as B on AWS (log-only first)
      │     └─ No  -> Kubernetes available? ToolHive vMCP : A anyway, or reconsider Cedar
      └─ No  -> Want a product with a UI, and CEL is fine?
            ├─ Yes -> agentgateway (or LiteLLM if you also want a Bedrock model gateway)
            └─ No  -> A
```

## Recommendation for UnderCover on plain Bedrock

Start with **A** on the laptop, with `gateway.undercover.yaml`. Then deploy it as **B** (Lambda, IAM inbound, Secrets Manager, Cedar in process or AVP) when the app goes to Lambda, rolling the policy out log-only first, as the course does with AgentCore. Revisit **agentgateway** if the gateway grows past what you want to maintain, or if you need a UI. Keep the app's own limits whatever you choose: the gateway is the second layer, never the only one.

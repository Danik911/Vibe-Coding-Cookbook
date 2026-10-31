> Research report by a sub-agent (Claude Sonnet 5.5) on 31 October 2026, kept as written. It cites its sources; anything marked UNVERIFIED wasn't confirmed. The code and docs in this folder supersede it where they differ.

# Replacing Bedrock AgentCore with generally-available AWS services and open source (as of 31 Oct 2026)

## 0. Summary

You can rebuild all of the AgentCore pieces you use from generally-available AWS services and open-source libraries.

- **Gateway:** run a FastMCP 4.x server on Lambda or ECS. It turns your FastAPI OpenAPI document into tools with `from_openapi()`, proxies the context-layer MCP server, and runs middleware before each tool call. `agentgateway` (Linux Foundation, Apache-2.0) is a ready-made alternative.
- **Policy:** use Amazon Verified Permissions (AVP) for managed Cedar, or `cedarpy` for local, zero-latency evaluation. Neither has a native LOG_ONLY mode, so you implement it in the caller.
- **Identity:** use Cognito client-credentials for agents, Secrets Manager for the credential vault, and IAM SigV4 to Function URLs.
- **Runtime:** use Lambda, ECS Fargate or Lambda durable functions.
- **Memory:** use LangGraph `PostgresStore` + pgvector (Supabase), LangMem or Mem0.

Four findings change the plan:

1. **Bedrock Agents Classic is closed to new customers** as of 30 Jul 2026, so it is probably not an option for you. AWS App Runner is also closed to new customers. ([Agents Classic](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html), [App Runner](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html))
2. **Cognito cannot do RFC 8693 token exchange or Dynamic Client Registration (DCR).** Its token endpoint accepts only `authorization_code`, `refresh_token` and `client_credentials`. ([token endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html))
3. **The Python `mcp` SDK 2.x depends on `httpx2`, not `httpx`.** FastMCP 4.1.4 sits on top of it. Your SigV4 `httpx.Auth` subclass must target the matching package. `langchain-mcp-adapters` 0.3.2 pins `mcp<2.0.0`, and `mcp-proxy-for-aws` 1.7.0 uses `httpx`. (PyPI metadata)
4. **New Lambda Function URLs need both `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`** since Oct 2025. ([urls-auth](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html))

### Validation method

I ran the Python snippets offline in a venv with boto3/botocore 1.43.123, httpx 0.28.1 and httpx2 2.16.0:

- Cedar policies were validated against the schema, and ALLOW/DENY was evaluated, with `cedarpy` 4.12.2.
- AWS call parameters were checked with the botocore `Stubber`, against the botocore service models.
- JWT verification was tested with PyJWT 2.15.1 against a locally generated JWKS.
- SigV4 was tested through an `httpx` `MockTransport`.
- `ChatBedrockConverse` was tested with the Converse client mocked, on langchain-aws 1.9.1.

None of it was run against live AWS endpoints. Line numbers were not captured for GitHub file citations, so those cite file paths only.

## 1. Mapping table: AgentCore feature to replacement

| AgentCore feature | AWS-native / OSS replacement | Notes and limits |
|---|---|---|
| Gateway: one MCP endpoint | FastMCP 4.x on Lambda (Function URL or API Gateway) or ECS. Alternative: `agentgateway` on ECS. | You own patching, scaling and tool naming. FastMCP uses `mount(..., namespace=...)`; I did not verify whether the separator is `_` or `___`. |
| OpenAPI target | `FastMCP.from_openapi(spec, client=httpx2.AsyncClient(headers={"X-API-Key": …}))` | Every route becomes a tool by default; customise with `RouteMap`. The generated client defaults to a 5 s timeout. ([doc](https://github.com/PrefectHQ/fastmcp/blob/main/docs/integrations/openapi.mdx)) |
| MCP-server target with SigV4 | `mcp.mount(create_proxy(url, auth=SigV4), namespace="ctx")`, or `mcp-proxy-for-aws` | `aws_iam_streamablehttp_client(endpoint, aws_service="lambda", aws_region=…)` is the ready-made client. ([awslabs README](https://github.com/awslabs/run-model-context-protocol-servers-with-aws-lambda)) |
| Inbound SigV4 / OAuth | Function URL `AWS_IAM`; API Gateway IAM auth; Cognito JWT checked in middleware | The caller needs both Lambda invoke actions. |
| Outbound `X-API-Key` injection | Secrets Manager + cache; set the header on the httpx client | See snippet (c). |
| Policy: Cedar on every call | AVP `IsAuthorized`, or `cedarpy` in-process | AVP has no LOG_ONLY mode. Implement it with an env flag in the caller. |
| LOG_ONLY then ENFORCE, CloudWatch decisions | Wrapper logs a JSON line or EMF metric, then raises only when `POLICY_MODE=ENFORCE` | Not a native AWS feature. |
| Identity credential vault | Secrets Manager. Lambda: Parameters and Secrets extension or `aws-secretsmanager-caching`. ECS: `secrets` injection. | Extension cache TTL is 300 s by default (`SECRETS_MANAGER_TTL`, max 300). |
| Identity OAuth M2M | Cognito resource server + client-credentials, or `GetClientToken` | No free tier for M2M token requests, so cache tokens. |
| Copilot on-behalf-of the user | Forward the user's Cognito access token per tool call (`MCPToolCallRequest.headers`) | Not RFC 8693. For true token exchange use Keycloak or another IdP. |
| Runtime (microVM per session, 8 h) | Lambda (15 min), Lambda durable functions (up to 1 year), Fargate, Step Functions | See section 5. |
| Memory strategies | LangMem or Mem0 on pgvector; `PostgresStore`; `DynamoDBStore` | Only LangMem and Mem0 do automatic extraction. |
| Prompt-injection screening | Guardrails `ApplyGuardrail` or `InvokeGuardrailChecks` | The inline prompt-attack filter does not scan tool results. |
| Bedrock Agents (classic) | Not recommended | Closed to new customers. |

## 2. Tool gateway on AWS without AgentCore

### Existing reference implementations

- **`awslabs/run-model-context-protocol-servers-with-aws-lambda`**: 381★, pushed 2026-10-30, latest release v0.5.22 (2026-10-20).
  - It wraps stdio MCP servers in Lambda and supports four transports: Streamable HTTP via API Gateway (OAuth), via AgentCore Gateway, SigV4 via a Function URL, and direct Lambda Invoke.
  - Python handlers are in `src/python/src/mcp_lambda/handlers/`: `api_gateway_proxy_event_handler.py`, `api_gateway_proxy_event_v2_handler.py`, `lambda_function_url_event_handler.py`, `bedrock_agent_core_gateway_target_handler.py` and `streamable_http_handler.py`.
  - The client `client/streamable_http_sigv4.py` is now a backwards-compatibility wrapper over `mcp_proxy_for_aws.client.aws_iam_streamablehttp_client`.
  - The README warns that anyone allowed to invoke the Lambda can use the secrets it holds, so lock down IAM.
- **`aws-samples/sample-serverless-mcp-servers`**: 245★, last push 2026-02-14.
  - It has stateless MCP on Lambda + API Gateway (Node and Python/SAM), stateless and stateful MCP on ECS + ALB, and Strands-on-Lambda with Cognito.
  - It discusses the stateful vs stateless Streamable HTTP trade-offs.
- **`aws-solutions-library-samples/guidance-for-deploying-model-context-protocol-servers-on-aws`**: 155★, last push 2026-02-14.
  - It uses CloudFront + WAF + ALB + ECS Fargate/Lambda + Cognito, implements MCP spec 2025-06-18 with RFC 9728 protected-resource metadata, and has a four-stack CDK deployment.
- **`aws-samples/sample-multi-tenant-saas-mcp-server`**: 20★, pushed 2026-10-31.
  - It runs an Express MCP server on ECS Express Mode with Cognito OAuth 2.1.
  - It adds a DCR proxy (CloudFront + API Gateway + Lambda that calls `CreateUserPoolClient`), a custom OpenID discovery document, and a pre-token-generation Lambda (V2_0) that injects a tenant claim.
  - It uses STS AssumeRole with session tags for per-tenant isolation.
- **`aws-samples/sample-cedar-agentic-ai-authorization`**: 6★, 2026-07-03. This is the closest match to your design.
  - Flow: WAF → API Gateway with Cognito authorizer → MCP adapter Lambda (Bedrock Guardrails) → Cedar evaluator Lambda reading policies from AVP → OCSF audit events to CloudWatch.
  - It passes the user context with HMAC, plus RFC 8693 token exchange for OBO. Its Cedar policies are in `cedar/policies/layer{1,2,3}-*`.
  - It was published as an AWS blog: [Enforce least-privilege authorization in multi-agent AI chains using Cedar](https://aws.amazon.com/blogs/security/enforce-least-privilege-authorization-in-multi-agent-ai-chains-using-cedar/).
- **AWS blogs:**
  - [Deploying MCP servers on Amazon ECS](https://aws.amazon.com/blogs/containers/deploying-model-context-protocol-mcp-servers-on-amazon-ecs/) (2026-04-14): Strands agent + FastMCP on Fargate, Service Connect, ECS Express Mode. It says Lambda suits "lightweight, stateless tool endpoints with bursty traffic" and ECS suits long-lived, streaming-heavy servers.
  - [Building an AI gateway to Amazon Bedrock with API Gateway](https://aws.amazon.com/blogs/architecture/building-an-ai-gateway-to-amazon-bedrock-with-amazon-api-gateway/): a Lambda authorizer + REST streaming pattern. Code is `aws-samples/sample-ai-gateway-for-amazon-bedrock` (11★, 2025-11-18).

I found no AWS-published "MCP gateway" that aggregates OpenAPI and MCP targets without AgentCore, so the FastMCP composition below is a DIY pattern.

### Platform limits that matter

- Lambda timeout is 900 s. Synchronous payloads are 6 MB each way, and streamed responses can reach 200 MB. ([limits](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html))
- API Gateway REST APIs support response streaming (GA 2025-11-19). It brings integration timeouts up to 15 min and payloads above 10 MB. ([What's New](https://aws.amazon.com/about-aws/whats-new/2025/11/api-gateway-response-streaming-rest-apis/))
- Function URLs with `AWS_IAM` need SigV4-signed requests. ([urls-invocation](https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html)) The awslabs README signs with service name `lambda`.
- `aws/aws-lambda-web-adapter` has 2,762★ (pushed 2026-10-23).

### Suggested DIY gateway (FastMCP 4.1.4)

`from_openapi()` builds the FastAPI tools. `create_proxy()` plus `mount(namespace=…)` adds the context server. `Middleware.on_call_tool(context, call_next)` gives you `context.message.name` and `.arguments`, where you call AVP and the guardrail. FastMCP also ships `docs/integrations/aws-cognito.mdx` (an OAuth-proxy bridge, because Cognito lacks DCR) and a callable-based authorization system. ([FastMCP docs](https://github.com/PrefectHQ/fastmcp/tree/main/docs/servers))

### OSS gateways

- `agentgateway/agentgateway` (5,821★, Linux Foundation): its README advertises MCP federation, OpenAPI integration, JWT/API-key/OAuth auth and a CEL-based RBAC engine.
- `IBM/mcp-context-forge` (4,731★).
- `agentic-community/mcp-gateway-registry` (1,029★): works with Cognito, among others.

None of these supports Cedar, so you would still call AVP or `cedarpy` for your forbid rules.

## 3. Amazon Verified Permissions as the Cedar engine

### APIs

- **`IsAuthorized`:** `policyStoreId`, `principal`, `action`, `resource`, `context` and `entities`. Returns `decision` (ALLOW/DENY), `determiningPolicies` and `errors`. ([API](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_IsAuthorized.html))
- **`IsAuthorizedWithToken`:** takes an `accessToken` and/or `identityToken` instead of a principal. AVP validates expiry and signature; revocation has no effect until the token expires. ([API](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_IsAuthorizedWithToken.html))
- **`BatchIsAuthorized`:** up to 30 requests that share the same principal or the same resource. It has no IAM permission of its own; use `verifiedpermissions:IsAuthorized`. ([API](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_BatchIsAuthorized.html))

### Modelling

- **Principal:**
  - `UnderCover::Agent::"<cognito client_id>"` for the agent, and `UnderCover::User::"<sub>"` for a human.
  - Use IDs that are never reused. Cedar warns that reused IDs inherit old grants. ([Cedar docs](https://docs.cedarpolicy.com/policies/syntax-datatypes.html))
- **Action:**
  - One action per tool, such as `UnderCover::Action::"claims___pay_claim"`.
  - `actionType` must match `Action$|^.+::Action`, so `"UnderCover::Action"` is valid. ([ActionIdentifier](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_ActionIdentifier.html))
- **Resource:** a `Gateway` (or target) entity.
- **Context:** `context.input.*` carries the tool arguments, which is the same convention as AgentCore Policy.
- **Namespaces:** AVP supports multiple namespaces as of May 2026. ([AVP vs Cedar](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/terminology-differences-avp-cedar.html))
- **Porting AgentCore policies:** AgentCore Gateway Cedar uses an `AgentCore::` namespace, `OAuthUser` / `IamEntity` principals and `<Target>___<tool>` action IDs. ([AgentCore policy scope](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-scope.html)) Porting means renaming the namespace and principal types.

### Amounts

- `contextMap` supports `long`, `decimal`, `string`, `record`, `set` and others. ([AttributeValue](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_AttributeValue.html))
- The AVP `decimal` is a string matching `-?\d{1,15}\.\d{1,4}`: at most 4 decimal places and a mandatory dot. Format with `f"{Decimal(x):.2f}"`.
- Alternatively use `Long` cents. Cedar `Long` overflow produces an error, and an erroring policy is ignored, so a `forbid` can silently fail. Keep amounts well within range and check `errors`.

### Validation mode

`ValidationSettings.mode` is `OFF | STRICT`. STRICT rejects policies that fail the schema, and the policy-store schema is `cedarJson` only. ([ValidationSettings](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_ValidationSettings.html), [SchemaDefinition](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_SchemaDefinition.html)) AWS recommends leaving validation off during development and enabling it for testing and production. ([doc](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/policy-validation-mode.html))

### Pricing and quotas

- Single `IsAuthorized` / `IsAuthorizedWithToken` costs $0.000005 per request ($5 per million, cut 97% on 2025-06-12). ([pricing](https://aws.amazon.com/verified-permissions/pricing/), [What's New](https://aws.amazon.com/about-aws/whats-new/2025/06/amazon-verified-permissions-reduces-price/))
- Batch costs $0.00015 per request for the first 40 M requests per month. That is 30× the single price, and the maximum batch size is 30. Use batch only if you fill it.
- Policy management requests cost $0.00004 each.
- The default quota is 200 RPS per policy store per Region for `IsAuthorized` and `IsAuthorizedWithToken`. `BatchIsAuthorized` and `BatchIsAuthorizedWithToken` are 30 RPS. Authorization request size is capped at 1 MB. Individual policies are capped at 10,000 bytes. ([quotas](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/quotas.html))
- **Latency:** the FAQ says "in milliseconds" and gives no p50/p99, so I have not stated a figure. ([FAQ](https://aws.amazon.com/verified-permissions/faqs/))

### Local alternatives

- **`cedarpy`:** `k9securityio/cedar-py` (69★, pushed 2026-10-20, PyPI 4.12.2 on Cedar 4.12.0). It is not officially supported by AWS. It offers `is_authorized`, `is_authorized_batch` and `validate_policies`, plus reusable parsed `PolicySet`/`Entities` handles. Batch is advertised as 10× or more faster. (README)
- **AWS local agent:** `cedar-policy/cedar-local-agent` (33★, pushed 2026-05-07). The pricing page's example #3 describes an "avp-local-agent" that evaluates in-process and refreshes its policy cache from AVP. You pay $0.00004 per policy-refresh call and $0 for evaluations.
- **Combined pattern:** keep AVP as the policy store and review UI, and evaluate in-process with `cedarpy`, loading policies via `GetPolicy`/`ListPolicies` on a timer.

### Cognito and API Gateway integration

- An AVP identity source takes a Cognito pool with allowed app-client IDs and checks the token's `client_id` (access) or `aud` (ID). Group membership comes from `cognito:groups`. ([Cognito+AVP](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-authorization-with-avp.html))
- **"avp-authorizer":** I found no standalone public repo with that name. The AVP console's "Set up with API Gateway and an identity source" wizard generates a Lambda authorizer and a CloudFormation stack. The authorizer calls `IsAuthorizedWithToken` with action = method+path and resource = `Application`, and defaults to a 120 s authorizer cache. ([doc](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/policy-stores-api-userpool.html)) The wizard is not meant for production; export to CloudFormation/CDK.
- **M2M tokens:** I could not verify that `IsAuthorizedWithToken` accepts Cognito client-credentials tokens. For agents, verify the JWT yourself and call plain `IsAuthorized` with `Agent::client_id`. Use `IsAuthorizedWithToken` for human tokens.
- **Decision logging:** I could not verify whether AVP emits `IsAuthorized` data events to CloudTrail. Log from your wrapper (UNVERIFIED for CloudTrail).

## 4. Identity replacement

- **M2M:**
  - Create a Cognito app client with a secret and a resource server with custom scopes (`undercover-gw/claims.pay`, …).
  - Use the client-credentials grant at `/oauth2/token` (needs a user-pool domain; `client_secret_basic` or `client_secret_post`). ([token endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html))
  - Alternatively call `GetClientToken` (SDK/CLI, no domain). That client needs `ALLOW_CLIENT_TOKEN_AUTH` as its only auth flow, authorization is by client secret rather than IAM, and an app client can hold two active secrets. ([doc](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html))
  - `InitiateAuth`-issued access tokens only carry the scope `aws.cognito.signin.user.admin`.
- **Cost:** M2M is billed by active M2M app clients plus token-request volume, with no free tier for M2M token requests. Exact prices did not render, so I leave them UNVERIFIED. ([pricing](https://aws.amazon.com/cognito/pricing/)) Cache tokens until about 60 s before expiry.
- **Pre-token-generation:** for M2M, Cognito invokes the trigger only when it is configured as V3_0. V2_0 or V3_0 requires the Essentials or Plus plan. `aws_client_metadata` or `ClientMetadata` can be passed. ([doc](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html))
- **JWT validation:**
  - Cognito signs with RS256. The JWKS is at `https://cognito-idp.{region}.amazonaws.com/{poolId}/.well-known/jwks.json`.
  - Access tokens carry `client_id`, not `aud`. Check `iss`, `token_use`, `client_id` and `scope`. ([doc](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html))
  - `awslabs/aws-jwt-verify` (750★) is Node-only; use PyJWT in Python.
- **Cognito as MCP authorization server:**
  - It has no DCR. FastMCP's Cognito guide says it uses an OAuth Proxy for that reason.
  - AWS's sample builds a DCR proxy and a custom discovery document. The AWS Solutions guidance uses RFC 9728 metadata.
  - First-party agents with pre-registered app clients do not need DCR. It only matters for third-party MCP clients such as Claude Desktop or Amazon Quick.
- **Vault:**
  - Lambda Parameters and Secrets extension: `http://localhost:2773/secretsmanager/get?secretId=…` with header `X-Aws-Parameters-Secrets-Token` set to the session token. Cache defaults are 1000 entries and a 300 s TTL. ([doc](https://docs.aws.amazon.com/lambda/latest/dg/with-secrets-manager.html))
  - Python library `aws/aws-secretsmanager-caching-python` (147★, default refresh 3600 s).
  - ECS injects secrets as env vars at task start. ([doc](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html))
  - Workload identity is plain IAM roles; the SigV4 signer uses the execution role.
- **On-behalf-of options:**
  1. **Pass the user's Cognito access token** to the gateway per call. `langchain-mcp-adapters`' `MCPToolCallRequest` has a modifiable `headers` field and a `runtime` context. The gateway validates it and calls `IsAuthorizedWithToken`. Use a dedicated app client or scope so the token's audience is the gateway.
  2. **Signed user-context claims** (HMAC-SHA256 key in Secrets Manager), as in `sample-cedar-agentic-ai-authorization`, which recommends RFC 8693 alongside it.
  3. **STS AssumeRole with session tags**, as in the multi-tenant sample.
  4. **A real token-exchange IdP** (Keycloak, 37,618★).
  5. IAM Identity Center trusted identity propagation is for AWS-service data access, not custom APIs. ([overview](https://docs.aws.amazon.com/singlesignon/latest/userguide/trustedidentitypropagation-overview.html))

## 5. Bedrock-native options that are not AgentCore

- **Agents Classic:** closed to new customers from 30 Jul 2026. Existing customers continue as normal. AWS points to AgentCore, and says models, Knowledge Bases and Guardrails are unaffected. Features: action groups (OpenAPI/function schema + Lambda), `RETURN_CONTROL` and user confirmation. ([maintenance mode](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html), [return control](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-returncontrol.html), [user confirmation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-userconfirmation.html))
- **IAM namespaces:**
  - From the Service Authorization Reference JSON, Agents use the `bedrock:` prefix (`bedrock:InvokeAgent`, `InvokeInlineAgent`, `CreateAgent`, …). AgentCore uses `bedrock-agentcore:` (`InvokeGateway`, `InvokeAgentRuntime`, `GetResourceApiKey`, …). They are separate, so a `bedrock-agentcore:*` block alone would not stop Agents Classic.
  - Whether your corporate SCPs also block `bedrock:*Agent*` is UNVERIFIED.
- **Converse:** `Converse` needs `bedrock:InvokeModel`, and `ConverseStream` needs `bedrock:InvokeModelWithResponseStream`. ([doc](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)) `InvokeModel` also has the condition key `bedrock:GuardrailIdentifier`, so IAM can require a specific guardrail on every call (service reference).
- **Guardrails:**
  - `ApplyGuardrail` works standalone with `source=INPUT|OUTPUT` and `content[].text{text,qualifiers}`. Qualifier values are `grounding_source | query | guard_content`. ([API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html))
  - Prompt-attack types are jailbreak, prompt injection and prompt leakage (Standard tier only). The attack filter does not evaluate tool results or tool definitions. XML guardContent tagging applies only to `InvokeModel`; for Converse use the guardrail content-block config. ([prompt attack](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-prompt-attack.html), [tagging](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-tagging.html))
  - **Consequence:** inline guardrails do not stop indirect injection via tool output. Call `ApplyGuardrail` or `InvokeGuardrailChecks` on tool results yourself. Whether `ApplyGuardrail` requires `guard_content` for PROMPT_ATTACK is UNVERIFIED; the snippet sets it.
  - **`InvokeGuardrailChecks`:** a newer inline API with no pre-created guardrail. It takes `checks.promptAttack.categories` (`JAILBREAK | PROMPT_INJECTION | PROMPT_LEAKAGE`, max 3) and returns `severityScore`. Scores let you build log-only thresholds. IAM action `bedrock:InvokeGuardrailChecks` has no resource type. ([API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeGuardrailChecks.html))
  - **Pricing:** [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) lists content filters at $0.15 per 1,000 text units for the classic path. For the `InvokeGuardrailChecks` path it lists $0.07 content filters and $0.08 prompt attack per 1,000 text units.
- **Knowledge Bases:** `bedrock:Retrieve` and `RetrieveAndGenerate` exist. They are for document RAG, not per-user memory extraction.

## 6. Runtime alternatives

| | AgentCore Runtime | Lambda | Lambda durable functions | ECS Fargate (Express Mode) | Step Functions |
|---|---|---|---|---|---|
| Session isolation | microVM per session ([doc](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)) | Per invocation environment | Same as Lambda | Per task or container; you manage sessions | Per execution |
| Max duration | Up to 8 h; idle timeout 60–28,800 s (default 900 s) ([doc](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-lifecycle-settings.html)) | 900 s | Up to 1 year ([doc](https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html)) | No fixed limit | Standard up to 1 year (partly parsed from the [quotas page](https://docs.aws.amazon.com/step-functions/latest/dg/service-quotas.html); verify) |
| Human-in-the-loop wait | Own code | Needs another service | Waits suspend with no compute charge | Own code | Task tokens (callback pattern; not re-fetched) |
| Async background work | Supported | Fire-and-forget Lambda invoke or SQS | Native | Native | Native |
| Cost model | Not verified | Per ms | Not verified | Express Mode adds no charge; you pay for the resources ([doc](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)) | Not verified |

Other notes:

- Cold start was not benchmarked; treat it as an unmeasured difference.
- Lambda durable functions went GA on 2025-12-02, with SDKs including Python and Java GA. ([What's New](https://aws.amazon.com/about-aws/whats-new/2025/12/lambda-durable-multi-step-applications-ai-workflows/)) Repo `aws/aws-durable-execution-sdk-python` has 58★. There is a blog on [multi-agent workflows with durable functions](https://aws.amazon.com/blogs/compute/building-fault-tolerant-multi-agent-ai-workflows-with-aws-lambda-durable-functions/).
- App Runner is closed to new customers, so ECS Express Mode is the replacement AWS recommends.
- For your Mangum app on Lambda, keep the app on Lambda and move long or HITL jobs to durable functions or Fargate.

## 7. Memory alternatives

- **LangGraph `PostgresStore`:** `langgraph.store.postgres` with `PostgresIndexConfig` (pgvector `hnsw`/`ivfflat`, `distance_type`). Works with Supabase pgvector. It stores and searches; it does not extract memories.
- **LangMem:** `langchain-ai/langmem`, 1,739★, pushed 2026-10-30. It has a background memory manager that extracts, consolidates and updates memories, plus manage/search memory tools. This is the closest to AgentCore's semantic and user-preference strategies on a LangGraph store.
- **Mem0:** `mem0ai/mem0`, 68,144★, pushed 2026-10-30, PyPI `mem0ai` 2.2.1. The repo includes `mem0/llms/aws_bedrock.py`, `mem0/embeddings/aws_bedrock.py` (default `amazon.titan-embed-text-v1`), `vector_stores/pgvector.py` and `vector_stores/supabase.py`. It supports `user_id`-scoped search and "remembers user preferences".
- **`langgraph-checkpoint-aws`:** PyPI 1.2.6, in `langchain-ai/langchain-aws` (352★). It exports `DynamoDBSaver`/`DynamoDBStore`, `ValkeyStore`/`AsyncValkeyStore` and the Bedrock-sessions saver, as well as the AgentCore classes. Its DynamoDB/Valkey stores need no AgentCore access.
- **Summaries:** you build these with an LLM step.

## 8. Strands Agents SDK

- Repo `strands-agents/sdk-python` is now `strands-agents/harness-sdk`: 9,010★, pushed 2026-10-30. PyPI `strands-agents` 1.63.0, with `strands-agents-tools` 0.8.11 (1,340★).
- It runs "in your process with no hosted control plane" and uses Amazon Bedrock by default. No AgentCore dependency was found in the README or PyPI requirements.
- **MCP client:**
  - `MCPClient(url=…, headers=…)`, or `auth={client_id, client_secret, scopes}` for client-credentials OAuth (Streamable HTTP only).
  - Or `auth_provider=<any httpx.Auth>`, or `MCPClient(lambda: aws_iam_streamablehttp_client(…))` for SigV4. ([doc](https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/sdk/tools/mcp-transports.mdx))
- **Auth hooks:**
  - `BeforeToolCallEvent` exposes `tool_use`, `selected_tool` and `cancel_tool` (`str|bool`). A hook can run your AVP/Cedar check and cancel the call; the message goes back to the model as an error tool result.
  - There is also an `interventions` module with `Proceed`, `Deny`, `Guide` and a confirm action (human approval).
  - Files: `strands-py/src/strands/hooks/events.py` and `strands-py/src/strands/interventions/actions.py`.

## 9. IAM

Least-privilege sketch for the agent runtime role. It assumes the gateway Lambda has `AWS_IAM` auth, and ARNs follow the Service Authorization Reference. Replace the placeholders.

```json
{
 "Version": "2012-10-17",
 "Statement": [
  {"Sid":"Models","Effect":"Allow",
   "Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],
   "Resource":["arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.anthropic.*",
               "arn:aws:bedrock:*::foundation-model/anthropic.*"]},
  {"Sid":"Guardrails","Effect":"Allow","Action":"bedrock:ApplyGuardrail",
   "Resource":"arn:aws:bedrock:us-east-1:111122223333:guardrail/GUARDRAIL_ID"},
  {"Sid":"GuardrailChecks","Effect":"Allow","Action":"bedrock:InvokeGuardrailChecks","Resource":"*"},
  {"Sid":"Policy","Effect":"Allow",
   "Action":["verifiedpermissions:IsAuthorized","verifiedpermissions:IsAuthorizedWithToken"],
   "Resource":"arn:aws:verifiedpermissions::111122223333:policy-store/POLICY_STORE_ID"},
  {"Sid":"Secrets","Effect":"Allow","Action":"secretsmanager:GetSecretValue",
   "Resource":"arn:aws:secretsmanager:us-east-1:111122223333:secret:undercover/*"},
  {"Sid":"GatewayUrlA","Effect":"Allow","Action":"lambda:InvokeFunctionUrl",
   "Resource":"arn:aws:lambda:us-east-1:111122223333:function:undercover-gateway",
   "Condition":{"StringEquals":{"lambda:FunctionUrlAuthType":"AWS_IAM"}}},
  {"Sid":"GatewayUrlB","Effect":"Allow","Action":"lambda:InvokeFunction",
   "Resource":"arn:aws:lambda:us-east-1:111122223333:function:undercover-gateway",
   "Condition":{"Bool":{"lambda:InvokedViaFunctionUrl":"true"}}}
 ]
}
```

- The gateway Lambda's own role needs the Policy, Secrets and (for the context-layer Lambda) the two Lambda statements. Add `kms:Decrypt` if you use customer-managed keys.
- Cognito's token endpoint and `GetClientToken` are authorized by client secret, not IAM.
- Cross-account callers also need a resource-based policy on the function.
- The `bedrock:InferenceProfileArn` condition key exists for cross-region profiles; I did not verify the exact pattern for destination-Region foundation models.

## 10. Code (validated offline as described in section 0)

### (a) AVP: Cedar schema, policy, `is_authorized`, log-only wrapper

```python
import json, logging, os, time
from decimal import Decimal
import boto3

SCHEMA = {"UnderCover": {
  "entityTypes": {
    "Agent": {"shape": {"type": "Record", "attributes": {}}},
    "User": {"memberOfTypes": ["Role"], "shape": {"type": "Record", "attributes": {}}},
    "Role": {}, "Gateway": {}},
  "actions": {
    "claims___get_claim": {"appliesTo": {"principalTypes": ["Agent", "User"], "resourceTypes": ["Gateway"],
      "context": {"type": "Record", "attributes": {"input": {"type": "Record", "attributes": {
          "claim_id": {"type": "String"}}}}}}},
    "claims___pay_claim": {"appliesTo": {"principalTypes": ["Agent", "User"], "resourceTypes": ["Gateway"],
      "context": {"type": "Record", "attributes": {"input": {"type": "Record", "attributes": {
          "claim_id": {"type": "String"},
          "amount": {"type": "Extension", "name": "decimal"}}}}}}}}}}

POLICIES = [
 '''permit (principal is UnderCover::Agent,
      action in [UnderCover::Action::"claims___get_claim", UnderCover::Action::"claims___pay_claim"],
      resource == UnderCover::Gateway::"undercover-gw");''',
 '''forbid (principal, action == UnderCover::Action::"claims___pay_claim", resource)
    when { context.input.amount.greaterThan(decimal("1000.00")) };''']

avp = boto3.client("verifiedpermissions")

def bootstrap() -> str:
    ps = avp.create_policy_store(validationSettings={"mode": "STRICT"})["policyStoreId"]
    avp.put_schema(policyStoreId=ps, definition={"cedarJson": json.dumps(SCHEMA)})
    for stmt in POLICIES:
        avp.create_policy(policyStoreId=ps, definition={"static": {"statement": stmt}})
    return ps

POLICY_STORE_ID = os.environ["POLICY_STORE_ID"]
MODE = os.environ.get("POLICY_MODE", "LOG_ONLY")            # LOG_ONLY | ENFORCE
log = logging.getLogger("policy")

def authorize_tool(agent_id: str, tool: str, args: dict) -> bool:
    t0 = time.perf_counter()
    inp = {"claim_id": {"string": str(args["claim_id"])}}
    if "amount" in args:                                     # decimal string, <= 4 dp, must contain "."
        inp["amount"] = {"decimal": f"{Decimal(str(args['amount'])):.2f}"}
    r = avp.is_authorized(
        policyStoreId=POLICY_STORE_ID,
        principal={"entityType": "UnderCover::Agent", "entityId": agent_id},
        action={"actionType": "UnderCover::Action", "actionId": tool},
        resource={"entityType": "UnderCover::Gateway", "entityId": "undercover-gw"},
        context={"contextMap": {"input": {"record": inp}}})
    allowed = r["decision"] == "ALLOW"
    log.info(json.dumps({"event": "policy_decision", "tool": tool, "agent": agent_id, "decision": r["decision"],
        "policies": [p["policyId"] for p in r.get("determiningPolicies", [])], "errors": r.get("errors", []),
        "mode": MODE, "ms": round((time.perf_counter() - t0) * 1000, 1)}))
    if not allowed and MODE == "ENFORCE":
        raise PermissionError(f"policy denied {tool}")
    return allowed
```

- `cedarpy.validate_policies` passed for this schema and policies.
- `cedarpy` gave Allow for 500.00 and Deny for 1500.00 on `claims___pay_claim`.
- Stubber checked the `create_policy_store`, `put_schema`, `create_policy` and `is_authorized` parameters.
- Zero-latency variant: `cedarpy.is_authorized({"principal": 'UnderCover::Agent::"x"', "action": 'UnderCover::Action::"claims___pay_claim"', "resource": 'UnderCover::Gateway::"undercover-gw"', "context": {"input": {"claim_id": "C-1", "amount": {"__extn": {"fn": "decimal", "arg": "1500.00"}}}}}, "\n".join(POLICIES), [], SCHEMA)`.

### (b) Cognito client-credentials token + JWKS validation

```python
import time, httpx, jwt
from jwt import PyJWKClient

REGION, POOL_ID, DOMAIN = "us-east-1", "us-east-1_EXAMPLE", "undercover-dev"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}"
TOKEN_URL = f"https://{DOMAIN}.auth.{REGION}.amazoncognito.com/oauth2/token"
_cache: dict[str, tuple[str, float]] = {}

def get_m2m_token(client_id: str, secret: str, scopes: list[str]) -> str:
    key = f"{client_id}:{' '.join(sorted(scopes))}"
    tok, exp = _cache.get(key, ("", 0.0))
    if tok and time.time() < exp - 60:
        return tok
    r = httpx.post(TOKEN_URL, data={"grant_type": "client_credentials", "scope": " ".join(scopes)},
                   auth=(client_id, secret), timeout=10.0)          # client_secret_basic
    r.raise_for_status()
    b = r.json()
    _cache[key] = (b["access_token"], time.time() + b["expires_in"])
    return b["access_token"]

_jwks = PyJWKClient(f"{ISSUER}/.well-known/jwks.json", cache_keys=True, lifespan=3600)

def verify_access_token(token: str, allowed_clients: set[str], scope: str) -> dict:
    key = _jwks.get_signing_key_from_jwt(token).key
    c = jwt.decode(token, key, algorithms=["RS256"], issuer=ISSUER,
                   options={"verify_aud": False, "require": ["exp", "iss", "client_id"]})
    if c.get("token_use") != "access" or c["client_id"] not in allowed_clients:
        raise PermissionError("bad token")
    if scope not in c.get("scope", "").split():
        raise PermissionError("missing scope")
    return c
```

Tested locally with an RSA key and monkeypatched JWKS; the wrong client was rejected. Domainless alternative: `boto3.client("cognito-idp").get_client_token(ClientId=…, Secret=…, Scopes=[…])`, whose parameters I confirmed in the botocore model.

### (c) Secrets Manager with caching

```python
import json, boto3
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig
_cache = SecretCache(config=SecretCacheConfig(secret_refresh_interval=300), client=boto3.client("secretsmanager"))
def get_secret(name: str) -> str: return _cache.get_secret_string(name)
OPENROUTER_API_KEY = lambda: get_secret("undercover/openrouter")
DB = lambda: json.loads(get_secret("undercover/db"))["DATABASE_URL"]
```

Stubber confirmed the call sequence (`describe_secret`, then `get_secret_value` by version) and that the second call is served from cache. On Lambda you can instead GET the extension endpoint on port 2773 with `X-Aws-Parameters-Secrets-Token: <AWS_SESSION_TOKEN>`.

### (d) SigV4-signed httpx request to a Lambda Function URL

```python
try:
    import httpx2 as httpx     # mcp>=2 / FastMCP 4.x
except ImportError:
    import httpx               # mcp 1.x, mcp-proxy-for-aws, strands, langchain-mcp-adapters 0.3.x
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

class LambdaUrlSigV4(httpx.Auth):
    requires_request_body = True
    def __init__(self, region: str, service: str = "lambda", session: Session | None = None):
        self.region, self.service, self.session = region, service, session or Session()
    def auth_flow(self, request):
        creds = self.session.get_credentials().get_frozen_credentials()
        aws = AWSRequest(method=request.method, url=str(request.url), data=request.content,
                         headers={"content-type": request.headers.get("content-type", "application/json")})
        SigV4Auth(creds, self.service, self.region).add_auth(aws)
        for h in ("Authorization", "X-Amz-Date", "X-Amz-Security-Token"):
            if h in aws.headers: request.headers[h] = aws.headers[h]
        yield request

# async with httpx.AsyncClient(auth=LambdaUrlSigV4("us-east-1")) as c:
#     await c.post("https://<id>.lambda-url.us-east-1.on.aws/mcp", json=..., headers={"accept": "application/json, text/event-stream"})
```

The signature came out as `Credential=…/us-east-1/lambda/aws4_request` with signed headers `content-type;host;x-amz-date;x-amz-security-token` under both httpx and httpx2. It also plugs into `MultiServerMCPClient({... "auth": LambdaUrlSigV4(...)})` and `create_proxy(..., auth=…)`.

### (e) Bedrock Guardrails `ApplyGuardrail` prompt-attack screen

```python
import boto3
brt = boto3.client("bedrock-runtime")

def screen(text: str, guardrail_id: str, version: str = "1", source: str = "INPUT"):
    r = brt.apply_guardrail(guardrailIdentifier=guardrail_id, guardrailVersion=version, source=source,
                            content=[{"text": {"text": text, "qualifiers": ["guard_content"]}}])
    hits = [f for a in r.get("assessments", []) for f in a.get("contentPolicy", {}).get("filters", [])
            if f.get("type") == "PROMPT_ATTACK" and f.get("action") != "NONE"]
    return r["action"] == "GUARDRAIL_INTERVENED", hits
```

Score-based variant (log-only thresholds):

```python
brt.invoke_guardrail_checks(
    checks={"promptAttack": {"categories": [{"category": "PROMPT_INJECTION"}, {"category": "JAILBREAK"}]}},
    messages=[{"role": "user", "content": [{"text": tool_result_text}]}])  # -> results.promptAttack.results[].severityScore
```

The Stubber validated both calls and the `GuardrailTextBlock` qualifiers (`grounding_source | query | guard_content`). Create the guardrail with a prompt-attack content filter; output-source mode (`source="OUTPUT"`) can screen tool results, though I did not verify its prompt-attack behaviour.

### (f) `ChatBedrockConverse` with tools

```python
from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse

@tool
def pay_claim(claim_id: str, amount: float) -> dict:
    """Pay a claim. amount in GBP."""
    ...

llm = ChatBedrockConverse(
    model=os.environ["BEDROCK_MODEL_ID"],       # an inference-profile ID enabled in your account
    region_name="us-east-1", temperature=0, max_tokens=1024,
    guardrail_config={"guardrailIdentifier": "GID", "guardrailVersion": "1", "trace": "enabled"})
msg = llm.bind_tools([pay_claim]).invoke("Pay claim C-1 for 120.50")
print(msg.tool_calls)
```

With the Converse client mocked, `tool_calls` parsed correctly and the request contained `toolConfig` and `guardrailConfig`. The model ID in my test was an example only; I did not check which models your account can invoke.

## 11. Best GitHub references

| Repo | Stars / last push | Reuse |
|---|---|---|
| awslabs/run-model-context-protocol-servers-with-aws-lambda | 381 / 2026-10-30 | Lambda handlers for API Gateway and Function URL; SigV4 client pattern |
| aws/mcp-proxy-for-aws | 366 / 2026-10-30 | SigV4 MCP client library (PyPI 1.7.0, 2026-09-15) |
| aws-samples/sample-serverless-mcp-servers | 245 / 2026-02-14 | Stateless MCP on Lambda + API Gateway or ECS; Strands + Cognito |
| aws-solutions-library-samples/guidance-for-deploying-model-context-protocol-servers-on-aws | 155 / 2026-02-14 | CloudFront/WAF/ALB/ECS + Cognito + RFC 9728 CDK |
| aws-samples/sample-multi-tenant-saas-mcp-server | 20 / 2026-10-31 | Cognito DCR proxy, pre-token Lambda, STS tags |
| aws-samples/sample-cedar-agentic-ai-authorization | 6 / 2026-07-03 | API Gateway + Cognito + Guardrails + AVP + HMAC user context |
| aws-samples/sample-ai-gateway-for-amazon-bedrock | 11 / 2025-11-18 | API Gateway REST streaming + Lambda authorizer pattern |
| PrefectHQ/fastmcp | 28,252 / 2026-10-31 | `from_openapi`, `mount`, `create_proxy`, middleware (PyPI 4.1.4) |
| modelcontextprotocol/python-sdk | 24,716 / 2026-10-27 | MCP SDK (PyPI mcp 2.3.0; depends on `httpx2`) |
| langchain-ai/langchain-mcp-adapters | 3,647 / 2026-09-16 | `StreamableHttpConnection.auth` and `MCPToolCallRequest.headers` for OBO (PyPI 0.3.2) |
| strands-agents/harness-sdk | 9,010 / 2026-10-30 | Agent loop, `MCPClient`, hooks/interventions |
| k9securityio/cedar-py | 69 / 2026-10-20 | `cedarpy` local Cedar and validation |
| cedar-policy/cedar | 1,825 / 2026-10-30 | Cedar engine |
| cedar-policy/cedar-local-agent | 33 / 2026-05-07 | In-process Cedar evaluation with policy refresh from AVP |
| agentgateway/agentgateway | 5,821 / 2026-10-30 | Open-source gateway: MCP federation, OpenAPI, JWT, CEL RBAC |
| langchain-ai/langmem | 1,739 / 2026-10-30 | Memory extraction on a LangGraph store |
| mem0ai/mem0 | 68,144 / 2026-10-30 | Memory layer; Bedrock LLM/embedder; pgvector/Supabase |
| langchain-ai/langchain-aws | 352 / 2026-10-31 | `ChatBedrockConverse`; `langgraph-checkpoint-aws` (DynamoDB/Valkey stores) |
| aws/aws-secretsmanager-caching-python | 147 / 2026-09-28 | `SecretCache` |
| aws/aws-durable-execution-sdk-python | 58 / 2026-10-31 | Lambda durable functions for HITL waits |

## 12. Gaps and UNVERIFIED items

- **AVP latency:** no published p50/p99; the FAQ only says "milliseconds". Benchmark in your Region.
- **AVP CloudTrail `IsAuthorized` data events:** I could not locate the doc page.
- **AVP `IsAuthorizedWithToken` with Cognito M2M tokens:** not confirmed.
- **Guardrails:** whether `ApplyGuardrail` needs `guard_content` for PROMPT_ATTACK is not confirmed, and I did not verify `OUTPUT`-source behaviour on tool results.
- **Cognito M2M prices:** the pricing page did not render the numbers.
- **Bedrock Agents:** whether your SCPs block `bedrock:*Agent*`, and whether your account counts as an existing customer.
- **Step Functions:** the Standard 1-year maximum came from a partly parsed page, and I did not re-fetch the task-token docs.
- **Cross-region inference-profile IAM condition pattern:** not verified.
- **FastMCP namespace separator:** `_` vs `___` not verified; you may need to rename tools to keep `<target>___<op>`.
- **Not found:** an AWS "avp-authorizer" public repo and an AWS-published non-AgentCore MCP gateway with OpenAPI + MCP aggregation.
- **Not verified:** AgentCore Runtime and Lambda cost, and cold-start numbers.
- **Not run against live AWS:** all snippets were validated offline.
- **Tooling:** the web search tools I tried were blocked, so blog discovery used the AWS blog directory API. GitHub search was rate-limited mid-run, which may have missed small sample repos.

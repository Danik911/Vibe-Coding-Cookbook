# Resources

Versions, stars and dates were checked on 31 October 2026. The four research reports this folder is built from, in [research/](research/), cover more. Sub-agents wrote them from the official docs and GitHub, and they cite every claim.

## Specifications and guidance

- MCP specification 2026-07-28 (current): [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization.md), [security considerations](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations.md), [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools.md), [changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog.md)
- [MCP security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md): confused deputy, token passthrough, SSRF
- [MCP authorization extensions](https://github.com/modelcontextprotocol/ext-auth): OAuth client credentials, and enterprise-managed authorization (ID-JAG). Both are stable in 2026-07-28
- [RFC 8693 token exchange](https://www.rfc-editor.org/rfc/rfc8693.html); [Transaction Tokens draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/); [AI agent auth draft](https://www.ietf.org/archive/id/draft-klrc-aiagent-auth-03.txt)
- OWASP: [LLM06 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/), [Top 10 for Agentic Applications](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/), [MCP Top 10](https://owasp.org/projects/mcp-top-10)
- [CoSAI: securing MCP](https://www.coalitionforsecureai.org/securing-the-ai-agent-revolution-a-practical-guide-to-mcp-security/); [Simon Willison: the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)

## Cedar and policy

- [Cedar language](https://docs.cedarpolicy.com/), including [data types](https://docs.cedarpolicy.com/policies/syntax-datatypes.html) (decimal, and why an erroring policy is ignored)
- [`cedarpy`](https://github.com/k9securityio/cedar-py) (PyPI 4.12.2): Python bindings, `PolicySet`, `validate_policies`, `is_authorized_partial`
- [cedar-for-agents](https://github.com/cedar-policy/cedar-for-agents): generates a Cedar schema from MCP tools
- [cedar-local-agent](https://github.com/cedar-policy/cedar-local-agent): evaluates in process, with policies refreshed from Verified Permissions
- Amazon Verified Permissions: [IsAuthorized](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_IsAuthorized.html), [AttributeValue](https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_AttributeValue.html) (`decimal`), [pricing](https://aws.amazon.com/verified-permissions/pricing/), [quotas](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/quotas.html)
- AgentCore Policy, for porting rules: [authoring guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-authoring-guide.html), [scope](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-scope.html)
- [OPA](https://www.openpolicyagent.org/docs/policy-language), [Cerbos](https://docs.cerbos.dev/cerbos/latest/policies/resource_policies), [OpenFGA](https://openfga.dev/docs/fga), [Permit.io MCP Gateway](https://docs.permit.io/permit-mcp-gateway/overview/)

## Building the gateway (Python)

- [FastMCP](https://github.com/PrefectHQ/fastmcp) (PyPI 4.1.4, 28k★): [OpenAPI](https://gofastmcp.com/integrations/openapi.md), [composition and proxying](https://gofastmcp.com/servers/composition.md), middleware, auth providers (including Cognito and Supabase)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp` 2.3.0, built on `httpx2`)
- [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters) (0.3.2, `mcp<2`, no longer maintained). Its successor is `langchain[mcp]`: [migration guide](https://docs.langchain.com/oss/python/migrate/langchain-mcp-adapters)
- [`langchain-aws`](https://github.com/langchain-ai/langchain-aws) (1.9.1): `ChatBedrockConverse`, plus `langgraph-checkpoint-aws` DynamoDB/Valkey stores
- [Strands Agents](https://github.com/strands-agents/harness-sdk) (1.63.0): AWS's open-source agent SDK on plain Bedrock, with `MCPClient` and `BeforeToolCallEvent` hooks
- [Mangum](https://github.com/Kludex/mangum): ASGI on Lambda

## On AWS without AgentCore

- [awslabs/run-model-context-protocol-servers-with-aws-lambda](https://github.com/awslabs/run-model-context-protocol-servers-with-aws-lambda) (381★, active): MCP servers on Lambda, Function URL SigV4 handlers
- [aws/mcp-proxy-for-aws](https://github.com/aws/mcp-proxy-for-aws) (366★): a SigV4 MCP client (pins FastMCP below 3.5)
- [aws-samples/sample-serverless-mcp-servers](https://github.com/aws-samples/sample-serverless-mcp-servers) (245★): stateless MCP on Lambda + API Gateway or ECS
- [Guidance for deploying MCP servers on AWS](https://github.com/aws-solutions-library-samples/guidance-for-deploying-model-context-protocol-servers-on-aws) (155★): CloudFront + WAF + ALB + ECS + Cognito, RFC 9728, CDK
- [aws-samples/sample-cedar-agentic-ai-authorization](https://github.com/aws-samples/sample-cedar-agentic-ai-authorization) (the closest AWS sample to this folder) and its [blog post](https://aws.amazon.com/blogs/security/enforce-least-privilege-authorization-in-multi-agent-ai-chains-using-cedar/)
- [aws-samples/sample-multi-tenant-saas-mcp-server](https://github.com/aws-samples/sample-multi-tenant-saas-mcp-server): Cognito with a DCR proxy, pre-token Lambda, STS session tags
- [Deploying MCP servers on Amazon ECS](https://aws.amazon.com/blogs/containers/deploying-model-context-protocol-mcp-servers-on-amazon-ecs/) (AWS blog, April 2026)
- Lambda: [Function URL auth](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html), [durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html), [Secrets Manager extension](https://docs.aws.amazon.com/lambda/latest/dg/with-secrets-manager.html)
- Cognito: [token endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html), [resource servers and M2M](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html), [verifying JWTs](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html)
- Bedrock: [Converse](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html), [ApplyGuardrail](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ApplyGuardrail.html), [InvokeGuardrailChecks](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeGuardrailChecks.html), [model cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html), [Agents classic maintenance mode](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html)

## Open-source gateways

| Project | Stars | Release | Notes |
|---|---|---|---|
| [agentgateway](https://github.com/agentgateway/agentgateway) | 5.8k | v1.7.0 (27 Oct 2026) | Rust, LF/AAIF. [MCP authn](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authn/), [backend auth](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/), [guardrails](https://agentgateway.dev/docs/standalone/latest/documentation/mcp/guardrails/processors/) |
| [ToolHive](https://github.com/stacklok/toolhive) | 2.3k | v0.59.0 (28 Oct 2026) | Go, Kubernetes, native Cedar. [vMCP auth](https://docs.stacklok.com/toolhive/guides-vmcp/authentication) |
| [LiteLLM](https://github.com/BerriAI/litellm) | 62.4k | v1.106.6 (28 Oct 2026) | Python, model + MCP gateway. [docs repo](https://github.com/BerriAI/litellm-docs) |
| [IBM ContextForge](https://github.com/IBM/mcp-context-forge) | 4.7k | v1.1.0 (20 Oct 2026) | Python platform with plugins |
| [Agent Router](https://github.com/theagentrouter/agent-router) | 2.3k | v1.2.0 (7 Oct 2026) | Formerly Envoy AI Gateway |
| [Obot](https://github.com/obot-platform/obot) | 1.1k | v0.27.0 | Catalog, UI, OpenAPI → MCP |
| [Docker MCP Gateway](https://github.com/docker/mcp-gateway) | 1.6k | v0.44.3 | Local and development |
| [Microsoft MCP Gateway](https://github.com/microsoft/mcp-gateway) | 0.9k | v1.0.0 | AKS + Entra |
| [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy) | 2.8k | — | A Python proxy only |

## Memory

- [LangMem](https://github.com/langchain-ai/langmem) (1.7k★): memory extraction on a LangGraph store
- [Mem0](https://github.com/mem0ai/mem0) (68k★): a memory layer with Bedrock and pgvector/Supabase support
- LangGraph `PostgresStore` with pgvector: storage and search, with no extraction

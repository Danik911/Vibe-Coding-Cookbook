# Identity and authentication without AgentCore Identity

Checked on 31 October 2026 against the MCP specification revision **2026-07-28**, the current one. ([authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization.md), [security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md))

## The rules that shape everything

1. **Each caller has its own identity.** The claim agent has a key or a role, and each handler has their own sign-in. A key never stands in for a person.
2. **A token's audience is the service that reads it.** An MCP server MUST check that a token was issued for it, and MUST NOT accept or pass on tokens meant for anything else. When it calls an upstream API, it uses a separate credential.
3. **The agent never holds the outbound credential.** The gateway adds the app's key, or signs with its own role, after the policy allows the call.
4. **Secrets live in a vault**, are fetched when needed, are cached briefly so rotation works, and never appear in logs, prompts, checkpoints or memory.

The DIY gateway enforces rules 2–4. It checks `iss`, `aud`, `exp`, the signature and, for Cognito, `client_id` and `token_use`. It strips the caller's `Authorization` before calling any target (FastMCP forwards it by default; see [FINDINGS.md](FINDINGS.md)). It reads target credentials through `SecretResolver`.

## The three callers in UnderCover

```text
1. Claim agent (machine) --key / IAM role / Cognito client credentials--> gateway --X-API-Key (from vault)--> app
                                                                                  --SigV4 (gateway role)----> context layer
2. Copilot for handler Dana --Dana's own sign-in (aud = the app)--------------------------------------------> app
                            --a token for the gateway (aud = gateway, sub = Dana, act = copilot)--> gateway --> context layer
3. Gateway --its own IAM role, SigV4 for "lambda"--> context layer's Function URL (AWS_IAM)
```

### 1. The claim agent

Pick one inbound identity for the agent. All three are supported by `diy_gateway` and need no AgentCore.

| Identity | How | When |
|---|---|---|
| **IAM role** (SigV4) | Gateway on a Lambda Function URL with `AWS_IAM` and `inbound.mode: iam`. The agent signs for the service `lambda`. The gateway sees `Mcp::IamEntity::"arn:aws:iam::<acct>:role/<role>"` | The agent runs on AWS (Lambda, ECS, EC2). No secret to manage. The nearest match to AgentCore's IAM authorizer |
| **Cognito client credentials** (OAuth M2M) | An app client with a secret and a resource server scope. The agent fetches a token ([`cognito_m2m.py`](../examples/aws_native/cognito_m2m.py)), and the gateway checks `client_id` and `token_use: access` | The agent runs anywhere, or several agents need separate identities and scopes. Cache tokens, since Cognito bills M2M token requests |
| **A static key** (bearer) | `inbound.api_keys`, compared in constant time | Laptop and demos, or Render (the course's free route) |

Stronger options exist when you need them:

- `sts:GetWebIdentityToken` gives an AWS-signed JWT with no stored secret. It needs per-account enablement. ([API](https://docs.aws.amazon.com/STS/latest/APIReference/API_GetWebIdentityToken.html))
- `private_key_jwt` client assertions are what the MCP client-credentials extension recommends. ([ext-auth](https://github.com/modelcontextprotocol/ext-auth))

### 2. The Copilot, acting for a signed-in handler

The course's Copilot sends the handler's Supabase sign-in to the app on every call, and uses the Gateway only for the context layer's read-only tools. Without AgentCore, keep the same split:

- **Path A, to the app.** Send the handler's JWT straight to the app, as the dashboard does. This is ordinary token use: the token's audience is the app, the app applies the handler's role, and the audit trail names them.
  - Give the app's tokens a specific audience (a Supabase custom access token hook). The default `authenticated` is accepted by every service on the project.
  - Keep the token in the graph's context (`context_schema`, read through `ToolRuntime`), never in state or `configurable`. LangGraph copies string `configurable` values into checkpoint metadata. ([source](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py))
- **Path B, to the gateway.** The handler's Supabase token must **not** go through the gateway: its audience is wrong, and the MCP spec forbids passing it on. Choose one of these:
  1. **Simplest:** the Copilot service has its own machine identity (an IAM role or a Cognito client), and the policy permits that identity only the context layer's tools. The context layer doesn't need to know the person.
  2. **When the gateway must know the person:** exchange the handler's token for a short-lived token for the gateway (RFC 8693), with `aud` set to the gateway, `sub` to the handler, `act.sub` to the Copilot, a narrow scope and a life of 5 minutes or less.
     - Cognito can't do this.
     - Keycloak supports standard token exchange (26.2 and later). Its delegation with `act`/`may_act` is a preview. ([Keycloak](https://www.keycloak.org/securing-apps/token-exchange))
     - A small exchange endpoint of your own (FastAPI, PyJWT, a KMS-held signing key) is enough for one gateway.
     - `diy_gateway` then reads `sub` as `Mcp::User::"<handler>"`, and the policy can name both.
- **Signing off a payment** is never a gateway tool. The Copilot pauses for the handler's confirmation, then calls the app's sign-off route with the handler's own token, so the app checks their permission.

### 3. The gateway to the context layer

The context layer runs on Lambda behind a Function URL with `AWS_IAM`. The gateway signs with its own role (`credentials: {type: sigv4, service: lambda}`). The role needs `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` on that one function: new Function URLs need both. ([Lambda URL auth](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)) No caller's token reaches the context layer.

## Where the credentials live

| Option | Fit | Notes |
|---|---|---|
| **AWS Secrets Manager** | The default on AWS | `aws-secretsmanager:<name or ARN>[#json-key]` in `diy_gateway`, cached for 5 minutes. On Lambda, the Parameters and Secrets extension also caches (300 s by default) |
| **Environment variables** | Laptop, Render, ECS (ECS fills them from Secrets Manager at task start) | `env:NAME`. Simple, but a restart is needed to rotate |
| **HashiCorp Vault / OpenBao** | Short-lived, per-call dynamic secrets | Add a scheme to `SecretResolver` |
| **Auth0 Token Vault, Arcade, Composio** | Per-user OAuth tokens for third-party SaaS tools | Not needed for your own app's key |

To rotate the app's key with no downtime, let the app accept two keys during the window, as Cognito allows two client secrets.

## Cognito specifics

- **Access tokens carry `client_id`, not `aud`.** Set `allowed_client_ids` and `required_claims: {token_use: access}`, and leave `audience` empty. ([verifying tokens](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html))
- The token endpoint takes only `authorization_code`, `refresh_token` and `client_credentials`. There is no token exchange or Dynamic Client Registration, so third-party MCP clients (Claude Desktop and others) need a DCR proxy. First-party agents with pre-registered clients don't. ([token endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html), [AWS DCR sample](https://github.com/aws-samples/sample-multi-tenant-saas-mcp-server))
- A pre-token-generation Lambda runs for M2M tokens only as version V3_0, on the Essentials or Plus plan.

## Checklist

- [ ] Each caller has its own identity, and the gateway's audit line names it.
- [ ] Tokens are checked for issuer, audience (or client), expiry and signature.
- [ ] No caller's token is forwarded to a target. There's a test for it (`test_the_callers_token_never_reaches_an_upstream_mcp_server`).
- [ ] Outbound credentials come from a vault, are cached briefly, and never appear in a log line.
- [ ] The Copilot's handler token never enters graph state, `configurable`, memory or logs.
- [ ] Every role is scoped to named resources: the gateway's role to its secret, its policy store and the context function.

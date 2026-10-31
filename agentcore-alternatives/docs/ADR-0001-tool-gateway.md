# ADR-0001: A self-built MCP tool gateway in place of AgentCore Gateway, Policy and Identity

- **Status:** proposed
- **Date:** 31 October 2026
- **Deciders:** TODO: the forward deployed engineer, the platform owner and information security
- **Review date:** in six months, or sooner if AgentCore becomes available in the account, a second team needs the gateway, or the gateway needs a UI

## Context

The account can call Amazon Bedrock's models (`bedrock:InvokeModel`) but is blocked from Amazon Bedrock AgentCore (`bedrock-agentcore:*`). UnderCover's design, from Week 3 Day 2, depends on AgentCore for six jobs:

- one MCP endpoint over the app's OpenAPI operations and the context layer's MCP server;
- IAM or OAuth inbound;
- outbound credentials the agent never holds;
- a Cedar policy on every tool call, with argument conditions;
- log-only, then enforce;
- an MCP refusal the agent routes to a person.

The Copilot adds acting for a signed-in handler.

Bedrock Agents classic closed to new customers on 30 July 2026. No open-source gateway found does all six jobs: none has inbound SigV4 or a log-only mode, and only ToolHive (Kubernetes-only) has Cedar.

## Decision

We will run the self-built gateway in `agentcore-alternatives/diy_gateway`. It is FastMCP 4 with Cedar through `cedarpy`, and it is configured by one YAML file. We'll run it on the laptop first and on AWS Lambda (Function URL with `AWS_IAM`, Secrets Manager, Cedar in process or Amazon Verified Permissions) when the app moves to Lambda, rolling the policy out log-only first.

## Options considered

| Option | Pros | Cons | Cost and effort | Verdict |
| --- | --- | --- | --- | --- |
| A/B: Self-built gateway (FastMCP + Cedar), on AWS-native services | All six jobs, AgentCore's names and refusal, the course's Cedar rules, tested, customizable | We own about 1,400 lines and their security; FastMCP moves fast | A few days to adapt; Lambda free tier; AVP $5 per million calls if used | chosen |
| C1: agentgateway | A mature product, one YAML file, JWT, key injection, SigV4, CEL on arguments | No Cedar, no inbound SigV4, no log-only; tool names change | A container on ECS; config only | rejected for now: revisit if maintenance or a UI matters more than Cedar |
| C2: ToolHive vMCP | Native Cedar with argument conditions | Kubernetes only; no OpenAPI targets; pre-1.0 | EKS | rejected: no Kubernetes here |
| C3: LiteLLM Proxy | Also a gateway for Bedrock models | JWT is Enterprise; argument rules need custom code | A container | rejected for tools; worth a look as a model gateway |
| D: No gateway, with limits in the app and the harness | Simplest; nothing new to run | Every agent repeats the controls; the agent holds the key; no single review point | None | rejected: two agents need one policy and audit point |
| F: Bedrock Agents classic | Managed action groups | Closed to new customers | — | rejected |

## Consequences

- **Positive:**
  - The claim agent's tools, the policy's rules, the step names and the refusal handling stay as the course built them.
  - The agent needs only `bedrock:InvokeModel` plus a way to call the gateway.
  - The rules are reviewable in git (or in Verified Permissions).
- **Negative:**
  - We maintain the gateway, its dependencies and its tests.
  - Three of FastMCP's defaults were unsafe for a gateway (see `docs/FINDINGS.md`), so upgrades need the tests.
  - There's no admin UI.
- **Follow-up work:**
  - A threat model with information security.
  - A Cedar schema generated in CI from UnderCover's real tools.
  - Tool-result screening as a middleware.
  - Rate limits.
  - A budget and the teardown before the first deploy.
- **Risks to watch:**
  - A FastMCP release that changes the proxy or the OpenAPI provider: the header tests fail.
  - `cedarpy` falling behind Cedar.
  - Policy and app limits drifting apart.

## Evidence

- `agentcore-alternatives/tests`: 64 tests, no network, including one for each finding of an independent code review.
- The live demo output in the README.
- `cfn-lint` on `examples/aws_native/template.yaml`.
- The package size (40 MB zipped).
- The four research reports summarised in `docs/OPTIONS.md` and `docs/RESOURCES.md`.

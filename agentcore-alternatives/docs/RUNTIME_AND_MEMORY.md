# Replacing AgentCore Runtime and Memory

The rest of this folder covers tools, policy and identity. This page covers the two other AgentCore services UnderCover uses, in less depth. Checked on 31 October 2026.

## Runtime: where the agents run

What UnderCover needs from AgentCore Runtime (Week 3 Day 4–5):

- work that outlives the request that started it (a dispatch of 25 claim agents);
- a pause for a person that may last hours (`interrupt()`, resumed in a new session);
- a session per conversation for the Copilot;
- IAM on who may start work;
- secrets fetched on the first request.

| | AgentCore Runtime | Lambda | Lambda durable functions | ECS Fargate (Express Mode) | Step Functions |
|---|---|---|---|---|---|
| Isolation | microVM per session | Per execution environment | Same as Lambda | Per task | Per execution |
| Longest run | 8 hours | 15 minutes | Up to a year, with waits that use no compute ([docs](https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html)) | No limit | Standard workflows up to a year |
| Waiting for a person | Your checkpoints | Another service | Native waits | Your checkpoints | Task tokens |
| Background work after answering | `add_async_task` | Invoke another function asynchronously, or use SQS | Native | Native | Native |
| Who may start it | IAM `InvokeAgentRuntime` | IAM `InvokeFunction` | IAM | Your auth (ALB + Cognito, or a key) | IAM `StartExecution` |
| Idle cost | None | None | None while waiting | Per running task | None |

App Runner closed to new customers in 2026, and AWS points to ECS Express Mode instead. ([availability change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html))

**Suggested mapping for UnderCover:**

- **The claim agents and the dispatcher:** an ECS Fargate service, or Lambda durable functions. A dispatch runs longer than 15 minutes, so plain Lambda only works if each claim is its own invocation.
- **Checkpoints:** keep them in Supabase Postgres (`PostgresSaver`), exactly as now. A resume after a sign-off can start anywhere, because nothing lives in the process.
- **The app:** stays on Lambda with Mangum. It starts work with `lambda:InvokeFunction` (asynchronous) or `ecs:RunTask`, or by putting a message on SQS, instead of `InvokeAgentRuntime`.
- **The one-run-at-a-time lock and heartbeat:** keep them in the database. They were never Runtime features.
- **Secrets:** use Secrets Manager or the Lambda Parameters and Secrets extension, fetched on the first request as now.
- **The free route:** the course already runs the agents on Render. That is the same idea without AWS.

## Memory: what the agent remembers about each customer or handler

What UnderCover uses AgentCore Memory for:

- events written after a decision (the claim as the customer's message, the decision as the agent's);
- strategies that turn those events into facts, summaries and preferences;
- a search scoped to one customer's or one handler's namespace.

| Option | Extraction (facts, preferences, summaries) | Storage | Fit |
|---|---|---|---|
| **LangGraph `PostgresStore`** + pgvector | None; you decide what to store | Supabase, which you already have | Keep the store API the claim graph already uses; write a summary node yourself |
| **[LangMem](https://github.com/langchain-ai/langmem)** on `PostgresStore` | Yes: a background memory manager extracts, consolidates and updates memories | Supabase | **The closest to AgentCore's strategies** on a LangGraph store, with Bedrock as the model |
| **[Mem0](https://github.com/mem0ai/mem0)** (open source, 68k★) | Yes, including user preferences; scoped by `user_id` | pgvector/Supabase; Bedrock LLM and embeddings built in | A separate memory layer with its own API |
| `langgraph-checkpoint-aws` `DynamoDBStore` / `ValkeyStore` | None | DynamoDB or Valkey | AWS-native storage with no AgentCore dependency |
| Bedrock Knowledge Bases | None (document RAG) | Managed vector store | For documents, not per-customer memory |

Keep the course's rules whichever you choose:

- namespaces per customer (`/customers/{id}/...`) and per handler (`/handlers/{id}/...`), with the id taken from the record or the sign-in, never from the model;
- nothing saved for a claim the security check referred;
- no memory in evaluations;
- never save a sign-in.

## Observability

AgentCore Observability puts policy decisions and agent telemetry in CloudWatch. Without it:

- `diy_gateway`'s audit lines (with `emf_metrics: true`) give the decision counts.
- Langfuse, which the course already uses, gives traces.
- The MCP 2026-07-28 revision carries OpenTelemetry `traceparent` in `_meta`, so traces can follow a call through the gateway.

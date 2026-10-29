# Production deployment on AWS: AgentCore Runtime, Lambda, accounts, teardown

> When to read this: the developer is deciding where and how an agent runs in production, setting up or auditing an AWS account for it, deploying with the AgentCore CLI or Lambda, controlling cost, or tearing it all down. Facts about AWS products, CLI versions, limits and prices are as taught in the course (Oct 2026); re-check them before relying on them.

## Contents

- Key principles
- Configuring an agent for production (settings, secrets, access map, limits)
- Where the agent runs: three options
- The AgentCore suite
- Rollout path
- AgentCore Runtime in practice (CLI, entrypoint, sessions, calling it, one run at a time)
- The app on Lambda, the context server, the Gateway, Memory, final topology
- AWS account hygiene and cost
- Scripting the AWS side
- Teardown discipline
- Production-readiness walk-through
- Decisions, pitfalls, troubleshooting, free route, UnderCover example, related, sources

## Key principles

1. **Run the same code on the laptop and on the platform.** Build the agent as an app that serves the platform's two routes locally too. Why: a bug found on the laptop costs nothing; a bug found on the platform costs a deploy.
2. **Do nothing at import time.** Get ready (secrets, connections, random seed) on the first request, once per process. Why: Runtime's V2 starts every session from one snapshot taken after import, so anything made at import is shared by every session, including dead connections.
3. **Sessions are disposable; state lives in the database.** Checkpoint every step so a new session can resume a paused piece of work. Why: a session ends when idle, and a human's answer may arrive hours later.
4. **Answer at once, work in the background, and register the work.** Tell the platform the session is busy for as long as work runs. Why: the platform ends an idle session, with any work the platform does not know about.
5. **Classify every failed call as "never reached" or "may have started".** Retry only what cannot have started. Why: a blind retry can start the same dispatch twice.
6. **Let the database be the one authority on "one run at a time".** A lock, a heartbeat and a quiet period beat any in-process flag. Why: on a platform with many processes, a process cannot see the others.
7. **Least privilege at every hop.** Separate roles for the app, the runtime, the Gateway and the human operator, each naming only what it needs. Why: a leaked key or injected agent then reaches little.
8. **Public does not mean unprotected.** A public Function URL needs app-level auth (API key, sign-in). Why: the URL lets anyone call the function; only your code decides who gets in.
9. **Budgets before resources, no hard cap.** AWS has no spending ceiling; alerts are the only brake, and a budget that counts credits never fires. Why: you are responsible for what you run.
10. **One region, named and tagged resources, teardown by name.** Why: teardown finds what a list you kept would miss; verify three ways (by name, by account-wide index, by cost).
11. **Pin the tooling.** Pin the CLI version and deploy dependencies at the lockfile's versions. Why: the course's CLI was a release candidate; behaviour changes between versions.

## Configuring an agent for production

Five kinds of housekeeping, each a decision. Do all five before the first real user.

| Concern | Rule | In UnderCover (as taught) |
|---|---|---|
| Settings | Read from the environment, never baked into code or config files; one place reads each | App, Gateway and Memory addresses set on the runtime at deploy time (from `agentcore/.env.local`) |
| Secrets | In a vault, fetched when needed, never in the repo, image or logs | API keys and the database URL are credentials in AgentCore Identity, fetched on the first request |
| Who may call it | The platform checks the caller before a request reaches your code; no shared key when the platform can use identity | Only the app's IAM role may invoke the runtime; off AWS the agent checks the agent's key |
| Limits | Idle timeout, time a session may live, size of the work (agents at once), spending alerts | Idle timeout 60 s; registered work keeps a session alive; swarm of up to 25 per dispatch |
| Logs and cost | Logs with retention, a cost view that is not the bill itself | CloudWatch logs; `monitor.py` for spend; budgets with alerts |

Limits correction (as taught): **60 seconds is an idle timeout, not a maximum.** A session that registered work with the platform stays alive for up to 8 hours (the maximum session life as taught); an unregistered session is ended a minute after its last request, with its work. Plan for both limits, and test the shorter one.

Settings versus secrets in this stack: addresses and ids are plain environment variables; anything that grants access (API keys, database password) is an Identity credential. Each credential's provider name arrives as `AGENTCORE_CREDENTIAL_<NAME>_NAME`; the agent fetches the value into `<NAME>` on its first request. Identity reads the token the platform sends with each request, so fetch while handling a request, never on a thread of your own. On the laptop the same names come from `.env`, which git ignores.

### Access map: who may call what, and how it is checked

| Caller to target | Check | Note |
|---|---|---|
| Browser to the app | Public Function URL; handlers sign in (Supabase) for dashboard actions | The URL is public; sign-in and the key are the only gates |
| Agent to the app's agent-only routes | `X-API-Key` header, compared in constant time | The key never stands in for a handler and never goes in a frontend setting |
| Gateway to the app | The same key, added by the Gateway from an Identity credential provider | The agent never holds it on this path |
| Gateway to the context server | Request signed with the Gateway's role (`AWS_IAM` Function URL) | The context server holds no key |
| Agent runtime to the Gateway and Memory | SigV4 with the runtime's own role | Role allows only `InvokeGateway` and Memory actions |
| App to the agent runtime | The app's role may `InvokeAgentRuntime` on that runtime only | No key is sent on Runtime |
| App to the agent off Runtime | The agent's key as a bearer token | For a laptop or a host of your own |
| Copilot to the app | The signed-in handler's own sign-in | Never the claim agent's key |
| Operator to AWS | IAM user with a scoped policy and an access key | Root only for setup |

## Where the agent runs: three options

The same three-way split is in [FDE lifecycle and governance](fde-lifecycle-and-governance.md); this version adds what you own and when to pick each (examples as taught, Oct 2026).

| Option | Examples | What it gives you | What stays with you | Pick it when |
|---|---|---|---|---|
| Servers or containers you run | AWS Lambda; ECS, Cloud Run or Kubernetes; Render | Free choice of framework and model, with full control | State, scaling, identity, memory and session handling | You already operate such platforms, the agent is a short request and response, or you need something the managed options lack |
| A managed agent runtime | AWS AgentCore Runtime; Google Agent Runtime; Microsoft Foundry; LangSmith Deployment | Free choice of framework and model, plus built-in memory and identity and a separate environment per session | The agent code and its state in your own database | Work is long or bursty, there are many users, and you want identity, memory and gateway services without building them |
| The model lab's hosted runtime | Claude Managed Agents; OpenAI Agents API | The lab's harness, with the least to operate | Almost nothing, though you are tied to that lab's models and harness | You accept a single vendor in return for speed |

- **Default for an AWS client with long-running or human-in-the-loop agents:** a managed runtime (AgentCore Runtime) for the agent, and ordinary functions or containers for the web app and APIs around it.
- **Managed runtime versus containers:** Runtime runs each session in its own microVM, bills while a session works, starts from a zip with no Docker, and brings Identity and Memory. Containers give portability and your own scaling model, but sessions, state, secrets and scaling are yours.
- Where a client mandates another cloud, the pattern (managed runtime plus gateway plus database state) probably carries over, while the CLI, roles and IaC would not (our inference, not taught in the course).

## The AgentCore suite

The slide lists fourteen services, shown here by when the course used them. Course name: "AWS Bedrock AgentCore" (AWS: Amazon Bedrock AgentCore). Everything the course used is in us-east-1.

| Service | What it is for | Used in the course |
|---|---|---|
| Gateway | Turns APIs (OpenAPI), Lambda functions and MCP servers into one list of MCP tools; inbound IAM or OAuth, outbound API key, OAuth or IAM | W3D2 and on |
| Policy | Cedar rules checked on every tool call (log-only, then enforce) | W3D2 and on |
| Identity | Manages agents' identities and API keys (credential providers in a token vault) | W3D2 and on |
| Observability | Policy decisions and agent telemetry in CloudWatch | W3D2 and on |
| Memory | Long-term memory for agents (strategies, namespaces, events that expire) | W3D3 and on |
| Runtime | Serverless hosting for the agent, a session per microVM | W3D4 and on |
| Harness, Evaluations, Optimization, Registry, Code Interpreter, Browser, Web Search, Payments | Managed agent loop from config; scoring from traces; testing prompt changes; catalog of agents and MCP servers; code sandbox; cloud browser; web search as an MCP tool; paying for APIs | Not used; mentioned only |

Security detail (Cedar, gateways) is in [security and guardrails](security-and-guardrails.md); memory strategies in [RAG, memory and MCP](rag-memory-and-mcp.md).

## Rollout path

Move to production in small steps, each one working and torn down or left safe before the next. The course's order, and a sensible default:

1. **Account first** (budget, MFA, region, scoped IAM user). Nothing is deployed, nothing costs anything.
2. **Make the app deployable while it still runs locally.** Authenticate the agent (API key), add the injection check, publish the agent's own API document, package for Lambda. Keep it a normal web server too.
3. **Put the app on Lambda** at a public address, then **put a Gateway with a Policy in front of the agent's tools**; call the tools from a script before the agent depends on them (log-only first, then enforce).
4. **Add the context server and Memory**; move the agent (still on the laptop) onto the Gateway.
5. **Hello world on Runtime, then a small agent that pauses in one session and resumes in another**, before deploying the real agent. This proves the deploy, session and state model on something cheap.
6. **Make the real agent an app that runs on both**, move the one-at-a-time guard into the database, deploy, point the app at it with one setting.
7. **Add the next agent (the Copilot) as a second runtime** in the same project.
8. **Handover conversation, then final teardown.**

Why this order: each step adds one new failure source, and the laptop path keeps working as the fallback throughout.

## AgentCore Runtime in practice

### The CLI lifecycle (as taught, CLI `@aws/agentcore@1.0.0-rc.5`)

```bash
npm install -g @aws/agentcore@1.0.0-rc.5       # pinned to the course; re-check the current version
agentcore --version
agentcore create --name <project> --template agent-python-langchain   # or agent-python-minimal
agentcore dev                                   # local server on :8080 with /ping and /invocations
agentcore deploy                                # zip build, CloudFormation through the CDK, no Docker
agentcore status
agentcore invoke --runtime agent --payload -    # JSON on stdin; PowerShell drops quotes in arguments
agentcore log runtime --since 15m               # add --name <runtime> when a project has several
agentcore remove all --yes && agentcore deploy --yes   # empties the config, then the deploy deletes from AWS
git restore agentcore/agentcore.json            # put the config back after remove all
```

- `agentcore create` will not make a project inside another project; make a hello world beside the repo. `agentcore add credentials` adds a secret to a project. Run `npm ci --prefix agentcore/cdk` once in a project that came from a repo.
- `agentcore.json` declares runtimes (name, `CodeZip` build, code folder, entrypoint file, Python version, idle timeout under `lifecycleConfiguration`), credentials, tags and extra IAM policies (`additionalPolicies`). Tag everything (`project=<name>`).
- **Deploy dependencies at the lockfile's versions.** The build installs what a `pyproject.toml` lists and reads no lock, so UnderCover's CDK stack stages the code and writes a `pyproject.toml` from `uv export --only-group runtime`. Packages are installed for Linux **ARM** and Python 3.12 (Lambda below is x86_64: do not mix the two).
- **Platform version V2** starts each session from a snapshot taken after import, so a session starts in about 2 seconds. The CLI had no setting for it; the project added a CDK property override. Every session then shares the snapshot's process id and random numbers until you reseed.
- **The first deploy in an account** creates the CDK bootstrap (stack `CDKToolkit`: an S3 bucket, a KMS key at about $1 a month, five IAM roles including a CloudFormation role with administrator access), the project's stack and role, and CloudWatch Transaction Search if missing. The bootstrap is the largest change the course makes to an account: tell the client.
- Deploy time: a first deploy about 4 minutes (hello world); with the V2 snapshot about 7 minutes; both UnderCover runtimes plus bootstrap about 10 minutes.

### An entrypoint that runs the same everywhere

Pattern (UnderCover's `agent/entrypoint.py`, `BedrockAgentCoreApp` from `bedrock-agentcore`):

1. **One entrypoint, payloads that name an operation.** `{"operation": "work_run", "run_id": ...}`; validate with a discriminated union; unknown operation or bad input gets a 400 that says what is wrong without echoing values. Answers are `{"accepted": true}`, `{"refused": "<reason>"}` or `{"healthy": true}`.
2. **Answer at once, work on a thread of your own**, registered with `app.add_async_task(name)` before answering and ended with `app.complete_async_task(id)` in a `finally`. The app's `/ping` then reports busy while work goes on, so the session lives as long as its work.
3. **Get ready on the first request, behind a lock, once per process.** On Runtime: reseed `random`, fetch credentials from Identity. Then check the agent's key, open the pool. A failure answers 503 and the next request tries again.
4. **Know where you are.** Runtime is detected from the credential-name settings. Off Runtime, check the agent's key as a bearer token (constant-time compare); on Runtime, AWS has already checked the caller, so ask for no key. The health check also gets ready, so a healthy answer means settings and pool exist.
5. **Local ports.** The agent's app listens on 8080 (the port AgentCore apps use), `agentcore dev` also uses 8080 (stop one before the other), the context server 8006, the Copilot 8081, the backend 8000.
6. **Database through the transaction pooler (port 6543), prepared statements off** (`prepare_threshold=None`): with prepared statements, 6 of 30 queries failed in the course's experiment; with them off, 30 of 30 passed.

### Sessions: cold, warm, paused, resumed

- A session is one microVM. The first call to a new session id is **cold** (starts from the snapshot); later calls to the same id are **warm**. Session ids must be at least 33 characters.
- **One session per unit of work.** UnderCover runs a whole dispatch (the dispatcher plus up to 25 claim agents, one process, one connection pool) in one session; the app's call returns at once and the session keeps working. The Copilot uses the conversation id as the session id: a turn soon after the last reuses the session, a later turn starts a new one under the same id and loads checkpoints.
- **A sent-back or resumed item runs in a new session** (hours later): the app records the handler's answer, the agent reads it from the app's record, loads the thread from the database checkpoints and decides again. The first session already ended after 60 idle seconds. Nothing the agent needs lives in a session.
- On resume LangGraph re-runs the interrupted node from its top, so put nothing before the `interrupt()`. See [durable state](durable-state-and-hitl.md).
- Stop a session explicitly with `stop_runtime_session` (the lab does this to simulate a session ending).

### Calling Runtime from the app

```python
client = boto3.client("bedrock-agentcore", config=Config(retries={"total_max_attempts": 1},
                      connect_timeout=2, read_timeout=15))
client.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=session_id, payload=json.dumps(payload))
```

- **One attempt per call, short timeouts** inside Lambda's 30 seconds (the final build: 2 s connect, 15 s read, 25 s budget). A new session id (a UUID) for each piece of work.
- **Sort failures.** Never reached (botocore `ConnectionError`, or a refusal before sending) means the work did not start: undo the app's side (mark the run stopped). A `ClientError` or a refusal answer means not taken: undo and tell the user. A timeout, `HTTPClientError` or cut-off answer after sending means it **may have started**: change nothing, tell the user to reload. Sign-offs and send-backs still answer with the updated record whatever happens to the call to the agent.
- **A `ConflictException` while Runtime starts or stops a session never reaches the agent**, so it is safe to retry (waits of 1, 2, 4 s while the time budget allows). Everything else is not.
- **Keep botocore logging at INFO.** Its DEBUG lines contain payloads, and the Copilot's payload contains a handler's sign-in.
- The app's role gets `bedrock-agentcore:InvokeAgentRuntime` on the runtime ARN and its `runtime-endpoint/*`, nothing else on Runtime. The runtime's role gets `InvokeGateway` on the gateway and the Memory's event and record actions (`runtime/policy.json`).

### One run at a time, across sessions

On a platform where each session is its own process, only the shared database can keep "one dispatch at a time". UnderCover's pattern:

- The **app** (not the agent) creates the run, in a short transaction committed before it asks the agent, while holding a **lock** (an update of one lock row; check the row count; this holds at Postgres's default isolation and through the transaction pooler). A second start gets a 409 naming what is going on.
- The agent sends a **heartbeat every 60 seconds** while it works a run, a round or a resumed claim. Work the app has not heard from in **5 minutes** is marked stopped ("The agent stopped answering") when the next start is asked for.
- A resume is not a "run" and runs beside anything. A dispatch leaves alone a claim whose resume the app heard from lately.
- If `npm run dev` restarts in the middle of a dispatch, the app refuses new starts for up to five minutes; `npm run seed` clears the block but also resets the queue.
- The agent no longer stops other runs when it starts: with several sessions alive, "mark everything stopped on startup" would kill another session's work.

## The app on Lambda, the context server, the Gateway, Memory

### The app (backend plus dashboard) on Lambda

- **Package:** the backend, its data files and the dashboard's build (`dashboard/dist`) in one zip, with the `server` dependency group installed for Linux x86_64 and Python 3.12 (`uv export --only-group server`, then `uv pip install --target ... --python-platform x86_64-manylinux2014 --python-version 3.12 --only-binary :all:`). Under 50 MB zipped. At run time it imports nothing outside the package and writes no files (read-only file system). Add a check that the backend imports with only that group installed.
- **Handler:** Mangum around the FastAPI app, `lifespan="off"` so nothing seeds the database; `backend.main.handler`. The same app still runs as an ordinary web server (`uvicorn backend.main:app`), which serves `dashboard/dist` at `/`.
- **Settings (the function's whole environment):** the transaction-pooler `DATABASE_URL`, `VITE_SUPABASE_URL`, `UNDERCOVER_API_KEY`; later `UNDERCOVER_AGENT_RUNTIME` (and `UNDERCOVER_COPILOT_RUNTIME`). 30 s timeout, 1024 MB as taught.
- **Connections:** Lambda starts a copy per concurrent request, so with `AWS_LAMBDA_FUNCTION_NAME` set, open a connection per request and keep none (SQLAlchemy `NullPool`), prepared statements off.
- **Function URL with auth type NONE** needs two permissions (`lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` with `InvokedViaFunctionUrl`) or every request is a 403. **It is public**: the API key protects the agent's routes and handlers sign in, but anyone can call the function. Throttling the public URL is not covered in the course; raise it with the client.
- **Logs:** create the log group yourself with a retention period (7 days in the course) so it does not keep logs forever. The function's role writes only to that group.
- Updating a function in place keeps its address; recreating it changes the address.

### The context server and the Gateway

- **The context layer is a second Lambda** (`context.server.handler`, its own dependency group, 512 MB, no environment variables, data in the package) behind a Function URL with **`AWS_IAM` auth**: only signed callers get in. The Gateway signs its calls with its own role (`lambda:InvokeFunctionUrl`), so the server needs no key. See [context layer](context-layer-and-integrations.md).
- **The Gateway** has inbound `AWS_IAM` (callers sign with SigV4), two targets: the app as an **OpenAPI target** (the agent's own API document, with `servers` added at deploy time; the API key added from an Identity credential provider as `X-API-Key`) and the context server as an **MCP-server target**. Tool names are `<target>___<operation_id>`.
- **The Policy** is a policy engine of Cedar rules attached in `LOG_ONLY` then `ENFORCE`; the course's rule forbids `pay_claim` over $1,000. Layers: injection check, Gateway policy, the app's own limit, a human sign-off. Details in [security](security-and-guardrails.md).
- **Roles:** the Gateway's role trusts only `bedrock-agentcore.amazonaws.com` for gateways of your name in your account, and gets exactly: fetch the key (workload identity, token vault, secret), invoke the context function, use the policy engine. **Anything just created may take up to a minute to become visible to AgentCore or Lambda**: make creation scripts retry.
- **The agent calls the Gateway for tools and payments, and calls the app directly (with the key) for its own records** (steps, heartbeats). The Copilot uses only the context tools on the Gateway; everything else it does in the app is with the handler's sign-in. See [copilot pattern](copilot-pattern.md).

### Memory

Created with strategies (Semantic and Summary for customers; User Preference and Semantic for handlers' namespaces), events kept 7 days (the shortest allowed), about 2.5 minutes to create, and extraction in the background (about two minutes). Memory is missing from six regions: another reason for one region. Design in [RAG, memory and MCP](rag-memory-and-mcp.md).

### Final topology (what runs where)

```text
Handler's browser --HTTPS--> Lambda "undercover-app"  (public Function URL; FastAPI + Mangum; serves dashboard)
                                |  boto3 invoke_agent_runtime (role may only InvokeAgentRuntime)
                                v
              AgentCore Runtime: "agent" (claim agents) and "copilot" (one session per conversation)
                |       |                    |-- AgentCore Memory (per customer; per handler for the Copilot)
                |       |                    |-- OpenRouter (all model calls) ; Langfuse (traces)
                |       +-- MCP over HTTPS, SigV4 --> AgentCore Gateway [inbound IAM | Cedar Policy | Identity key]
                |                                        |-- target: app (OpenAPI)  --X-API-Key--> Lambda "undercover-app"
                |                                        +-- target: context (MCP) --IAM--------> Lambda "undercover-context"
                +-- claim agent only: records, steps, heartbeats --> Lambda "undercover-app" (agent's key)
                    (the Copilot calls the app with the handler's own sign-in instead)
Supabase (Postgres, transaction pooler :6543): records, LangGraph checkpoints, handlers' sign-in
   <-- read and written by the app and by every runtime session
```

Not on AWS: the database (Supabase), the model provider (OpenRouter), traces (Langfuse). The laptop runs the same code (`npm run dev`) against the same Supabase.

### Lambda and Runtime packaging at a glance

| | App and context server on Lambda | Agent on Runtime |
|---|---|---|
| Built by | A script: `uv export`, `uv pip install --target`, zip, `create_function` or update in place | `agentcore deploy` (CDK, CloudFormation) |
| Linux target | x86_64 (`manylinux2014`) | ARM |
| Dependency group | `server`, `context` | `runtime` (all pinned to `uv.lock`) |
| Entry | Handler `backend.main.handler` (Mangum); `context.server.handler` | `runtime/main.py` imports and runs the AgentCore app |
| Size limit | 50 MB zipped (as taught) | Zip, no Docker |
| Public address | Function URL (app: `NONE` auth; context: `AWS_IAM`) | None; invoked by ARN with IAM |
| Settings | Function environment variables | Runtime environment variables plus Identity credentials |
| Idle cost | Nothing | Nothing; bills while a session works |

## AWS account hygiene and cost

Do this before creating any resource (UnderCover's Week 3 Day 1, as taught):

| Step | What and why |
|---|---|
| Paid plan | AgentCore needs the Paid plan (the Free plan cannot use it). New customers got the same credits on either plan: $100 plus up to $100 more (as taught) |
| MFA on root | Passkey or authenticator. Root can do anything, including closing the account; use it only to set up |
| One region | `us-east-1` for everything, wherever you live. Every feature used is there; Memory is missing from six regions. If something is "missing", check the console's region selector first |
| Billing access | As root, turn on IAM access to billing information; without it an IAM user cannot read budgets or costs |
| Budget with alerts | Monthly cost budget ($10 in the course), alerts at 50%, 80% and 100% of actual cost, emailed. **Exclude Credit and Refund** in the budget scope, or it shows zero while credits cover the bill and never alerts |
| IAM user and group | A named policy (`undercover-course`), a group, a user with an access key for CLI and code only (no console access). Keep the key out of git and notebooks; AWS shows the secret once |
| AWS CLI | `aws configure` with region `us-east-1`, then `aws sts get-caller-identity`; decline the CLI's offer to set up AI-agent skills mid-course |
| Check from code | Caller is not root, region is right, plan is Paid, root MFA is on, the budget excludes credits, AgentCore answers |

- **The course policy shows the least-privilege pattern:** broad on the services the project owns (AgentCore, CloudFormation), but IAM, Lambda, log-group deletion and secrets scoped by **name prefix** (`undercover*`, `cdk-*`, `AgentCore-*`); `iam:PassRole` limited by `iam:PassedToService`; read-only on costs and Resource Explorer. A `bedrock-agentcore:*` on `*` is a course convenience: at a client, tighten it and have their security team review the policy. An `AccessDenied` message names the missing action.
- **At a client** you work in their account with permissions their IT team grants. Hand them the policy document and ask for: a budget with alerts, root MFA, a named IAM role or user, an agreed region.
- **Name and tag everything** (`undercover...` prefix, tag `project=undercover`). Teardown and audits rely on it.
- **No hard spending cap exists**, and a waiver of accidental charges is not guaranteed. State this to the developer before they deploy.
- **What costs money (as taught):** Lambda is inside the free allowance and costs nothing idle; Runtime bills only while a session works (a swarm of 25 about a cent); Gateway, Policy, the Identity secret and Memory cost a fraction of a cent for the length of a lab (as taught); the KMS key from the CDK bootstrap is the one standing cost (about $1 a month); model calls (OpenRouter) are separate and dominate a busy run.
- **Watch spend two ways.** `uv run monitor.py` creates two free daily budgets with no alerts (all spend, and spend after credits) and shows today and 30 days; AWS updates budget figures up to three times a day, so they lag by hours. The official source is Billing and Cost Management; alerts come from the real budget. The course policy lets the user read budgets and Cost Explorer.

## Scripting the AWS side

The course drove AWS from boto3 notebooks (and `week3day4_aws.py`) plus the CLI and CDK for Runtime. Whatever the tool, copy these habits:

- **Create-or-update, so a script can be run again.** Find the resource by name; create it if missing, update it in place if present (a function's code and configuration, a Gateway target's document, a credential provider's key).
- **Wait for status.** Gateways, targets, policy engines, policies and Memories pass through `CREATING`/`UPDATING`; poll until ready and print any status reasons.
- **Retry the propagation delay.** A new role or permission can fail for up to a minute ("Failed to obtain execution role credentials"); retry a few times with a short sleep rather than adding a long fixed wait.
- **Name, tag and scope everything** so teardown, audits and the policy's name-prefix rules work.
- **One function per concern** (find, create, delete, show) and a single `show_resources` view that lists what exists by service.
- **For a client's production, prefer infrastructure as code** (the course's CDK project for Runtime is one example; Terraform or CDK for the rest) so a reviewer can read what will be created. This is a recommendation, not something the course taught for Lambda or the Gateway.

## Teardown discipline

Tear down at the end of every working session; leave up only what the next step needs. Costs at rest are small; forgotten resources are how bills happen.

1. **Find by name or tag, never from a remembered list.** Every part of a teardown script lists the service, filters on the name prefix and deletes what it finds; it skips what is not there, so it can be re-run.
2. **Order:** runtimes (`agentcore remove all --yes`, then `agentcore deploy --yes`, then `git restore agentcore/agentcore.json`) and the runtime's log groups; Gateway targets, then the Gateway; policies, then the policy engine; credential providers (their secret goes seconds later); Memories (minutes); Lambda functions, their roles and log groups; **the CDK bootstrap last**, and only when no stack still needs it; then the token vault key check.
3. **The CLI leaves log groups behind** that keep logs forever: delete them by name (`/aws/bedrock-agentcore/runtimes/<name>`, `/aws/lambda/undercover*`).
4. **The bootstrap's KMS key** stops billing when the stack is deleted (the key is scheduled for deletion); the next deploy recreates it. Earlier CLI versions also made a key for the Identity token vault (described as an "AgentCore Identity encryption key"): check whether the vault is on a customer-managed key, and if the CLI made it, move the vault back to AWS's key before scheduling that key's deletion, since a key still in use must never be deleted. Leave any other key alone.
5. **Keep only what is free and needed:** the IAM user, group and policy, the budgets (including `monitor.py`'s), service-linked roles and Resource Explorer's index. Between days the course kept the Lambda functions (free idle) and deleted the Gateway, Policy engine, secret and Memory (they bill by the month).
6. **Verify three ways.** (a) UnderCover's resources service by service, by name: every line should say none; a Gateway or policy engine can take a minute to go. (b) Everything on the account in the region from AWS Resource Explorer (on by default, free): a new account already has default resources, so the list is not empty; look for anything unfamiliar and for `undercover` in a name. (c) Cost from the budgets for today and the last 30 days.
7. **Figures lag.** Budget numbers update up to three times a day: check again over the next day or two.
8. **When finished with AWS, deactivate the IAM user's access key** (IAM, Users, Security credentials, Deactivate); it can be re-activated later.
9. **Every project's assignment needs its own teardown:** find everything by name or tag, delete in an order that works, end with the same three checks.

## Production-readiness walk-through

The agent walks the developer through these readiness checks in order, asking each question and recording the evidence. (They are numbered separately from the rollout steps above and from the numbered checklists.) Capture the outcome in [the handover template](../assets/templates/HANDOVER.md).

| Readiness check | Ask | Done when (evidence) |
|---|---|---|
| Readiness check 1: Hosting | Where does the agent run, and why (three options)? Who runs it after handover? | Decision recorded with trade-offs; owner named |
| Readiness check 2: Account | Paid plan, root MFA, one region, billing access, budget excluding credits, named IAM identity, no keys in git? | The check-from-code cell passes; test alert received |
| Readiness check 3: Config and secrets | What is a setting and what is a secret? Where does each live? Does anything run at import time? | No secrets in repo, image, logs or config; secrets fetched on first request; import opens nothing |
| Readiness check 4: Who may call what | Who can call the agent, the app, the Gateway, the context server? How is each checked? | Each caller has a role or key; the Function URL's public exposure is accepted and protected; agent's key is never in the frontend |
| Readiness check 5: Limits | Idle timeout, session lifetime, concurrency (agents at once), model-call limits, payout and policy limits, rate limits to providers? | Numbers written down; each limit tested ([swarms and scale](swarms-and-scale.md)) |
| Readiness check 6: State and recovery | What happens when a session ends mid-work, the process restarts, a human answers hours later, the database pool is full? | Resume from checkpoints demonstrated in a new session; transaction-pooler settings verified ([durable state](durable-state-and-hitl.md)) |
| Readiness check 7: One-at-a-time and idempotency | Can two sessions start the same work or pay twice? | DB lock, heartbeat and quiet period tested; a retried call cannot double-act |
| Readiness check 8: Failure handling | For each call to the platform: never reached, refused, error, may-have-started? | Each mapped to what the user sees and what is undone |
| Readiness check 9: Security | Injection, the lethal trifecta, gateway policy, hidden-instruction check, least-privilege roles? | Layers listed and each tried once ([security](security-and-guardrails.md)) |
| Readiness check 10: Data and context | Which data does the agent see, who owns it, which system is the record? | Owners, source and review dates ([context layer](context-layer-and-integrations.md); memory per user in [RAG and memory](rag-memory-and-mcp.md)) |
| Readiness check 11: Observability and cost | Logs with retention, traces, cost per unit of work, spend alerts, a person who reads them? | Logs found for one session; cost per claim known; alerts tested |
| Readiness check 12: Success measurement | Which metrics prove it works (agreed before building)? Measured on held-out cases, locally and deployed? | Same evaluation run on laptop and deployed, time and cost compared |
| Readiness check 13: Teardown and handover | What is deleted, what stays, who can redeploy from the docs? | Teardown run and the three checks pass; client can run it without the FDE |

Run the deployed system once end to end with a real user flow (dispatch, a human sign-off, a send-back with a note, a Copilot question) before declaring it ready.

## Decisions to make with the developer

| Decision | Options and trade-off | Sensible default |
|---|---|---|
| Where the agent runs | Own infrastructure (control, you own state and scaling), managed runtime (identity and memory built in, platform lock-in), model lab (least to run, one vendor) | Managed runtime for long-running or human-in-the-loop agents on AWS; functions or containers for everything else |
| Session model | Per unit of work (a dispatch, a conversation) versus per item | One session per dispatch or conversation, durable state in the database |
| Who may call the agent | Platform identity (IAM) versus a shared key | IAM role of the calling app; a key only off-platform |
| Idle timeout and limits | Short timeout saves money; registered work keeps sessions alive | 60 s idle, register all background work, a heartbeat and a lock in the DB |
| Region | Closest to users versus the one with every feature | `us-east-1` in training; at a client, the region with all needed features (check Memory) |
| Packaging | Zip (no Docker, fast deploy) versus container | Zip, dependencies at lockfile versions |
| Budget | Size and alert thresholds | Small monthly budget, alerts at 50/80/100%, credits excluded, plus `monitor.py` |

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Every request to the Function URL is a 403 | One of the two public-access permissions is missing |
| First Gateway calls: "Failed to obtain execution role credentials" | The new role has not reached AgentCore yet; wait up to a minute and retry |
| `AccessDenied` from the IAM user | The message names the missing action; add it to the policy deliberately |
| Resources "missing" in the console | Wrong region selector; everything is in `us-east-1` |
| Budget shows zero and never alerts | It counts credits; exclude Credit and Refund |
| Background work dies a minute after the last request | Not registered as an async task, so the session was idle |
| `DuplicatePreparedStatement` | Prepared statements through the transaction pooler; turn them off, use a connection per request on Lambda |
| New dispatch refused with "a dispatch is running" after a restart | The app waits up to five minutes of silence; wait, or reseed (which resets the queue) |
| Deployed dashboard cannot start a dispatch | The agent is still on the laptop, or `UNDERCOVER_AGENT_RUNTIME` is not set on the function |
| `agentcore dev` or the agent will not start | Both use port 8080; stop one |
| Policy decision counts show zero | CloudWatch metrics are a minute or two behind; run again |
| Memory shows no notes | Extraction runs in the background (usually within two minutes); the agent decides itself whether to search |
| Service will not start: `KeyError` for the agent's key | `UNDERCOVER_API_KEY` is missing from `.env` (add it without printing it) |

## Pitfalls and anti-patterns

- Budget that counts credits (never alerts); no budget at all; relying on `monitor.py` instead of alerts.
- Work on a thread the platform does not know about: the session ends a minute after the last request and kills it.
- Making connections, fetching keys or seeding randomness at import time under V2 snapshots.
- Prepared statements through a transaction pooler (`DuplicatePreparedStatement`), or long-lived pools in Lambda.
- Retrying a non-idempotent platform call after a timeout; logging request payloads that hold sign-ins.
- "Stop every running run" on agent startup when several sessions run at once.
- Mixing ARM (Runtime) and x86_64 (Lambda) wheels when packaging.
- Assuming the public Function URL is private; putting the agent's key in a frontend setting.
- Forgetting runtime log groups (kept forever), the CDK bootstrap's KMS key, or a customer-managed vault key.
- Deleting the bootstrap while a stack still needs it; deleting a Gateway before its targets or an engine before its policies.
- Running `agentcore remove all` and skipping the follow-up deploy (it only empties the config) or `git restore` (the config stays empty).
- Following the video where the notebook differs (AWS screens change); treating release-candidate CLI behaviour as stable.

## The free route (Render)

Without AWS, the course ran the app, the agent and the Copilot as free Render web services beside the same Supabase database, with the context layer on the laptop and no Gateway, Policy, Memory or Runtime. Free services spin down after 15 minutes idle (about 35 s to wake the app, 60 s the agent), so open the agent's `/ping` before work; the app waits only 10 s for it. Supabase's free plan allows 15 connections, so stop the laptop's dev server first.

## In UnderCover

The pilot ran on a laptop. Week 3 moved it onto AWS in steps: the app on Lambda (Day 2) with a Gateway and Policy in front of the agent's tools; the context layer as a second Lambda and Memory per customer (Day 3); the agent as an AgentCore app on Runtime, with one session per dispatch, a DB lock and heartbeat, and a send-back that resumes in a new session (Day 4); the Copilot as a second runtime with a session per conversation and a Memory per handler (Day 5). Each day ended with a teardown; the final one deleted everything and ran the three checks. The success criteria agreed in Week 1 were measured on the deployed system with held-out claims.

## Related

- [security and guardrails](security-and-guardrails.md), [durable state and human step](durable-state-and-hitl.md), [swarms and scale](swarms-and-scale.md)
- [RAG, memory and MCP](rag-memory-and-mcp.md), [context layer and integrations](context-layer-and-integrations.md), [copilot pattern](copilot-pattern.md)
- [handover template](../assets/templates/HANDOVER.md)
- [code patterns: AWS AgentCore](code-patterns-aws-agentcore.md): snippets for Gateway, Cedar, Runtime, `agentcore.json`, Memory, IAM, budgets and teardown

## Sources

- Course Week 3: Day 1 lab `week3day1` (account setup), slides 9, 17-19; Day 2 slides 33-36, 41, 43, Lab 2 (`week3day2_lab2`) and `labs/week3day2_product_SECURE.md` (Lambda, Mangum, OpenAPI for the Gateway); Day 3 slides 66, 72 and lab `week3day3`; Day 4 slides 74-84, labs `week3day4_lab1`, `week3day4_lab2`, brief `labs/week3day4_product_RUNTIME.md`; Day 5 slides 94 and 97, labs `week3day5_lab1`, `week3day5_lab2`.
- Repo: `guides/for_agents/AGENT_GUIDE_WEEK3.md` (corrections), `AGENT_GUIDE_FREE.md`, `labs/undercover-course-policy.json`, `labs/week3day4_aws.py`, `monitor.py`, `setup/setup_week3day4/runtime/` and `agentcore/` (`agentcore.json`, `cdk/lib/cdk-stack.ts`, `runtime/policy.json`).
- Final code (`origin/week3day5-end`): `agent/entrypoint.py`, `agent/agentcore_app.py`, `agent/heartbeat.py`, `agent/identity.py`, `agent/checkpoints.py`, `backend/runtime_calls.py`, `backend/agent_service.py`, `backend/agent_work.py`, `runtime/main.py`, `docs/TECH_STACK.md` (Deployment).

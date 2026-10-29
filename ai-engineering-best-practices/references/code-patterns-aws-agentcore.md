# Code patterns: AWS Bedrock AgentCore and account hygiene

> When to read this: you are setting up or reviewing the AWS side of an agent on Bedrock AgentCore: Gateway with an OpenAPI target and key provider, a Cedar policy, the Runtime entrypoint, `agentcore.json`/CDK/CLI, invoking a Runtime from the backend, AgentCore Memory, and the IAM shape, budget, spend monitor and teardown for any account you must leave clean. Snippets are minimal and written for this skill, not copied from the course. Sibling pattern files: backend auth, money limits, OpenAPI, Lambda, the context-layer server and the run lock in [code-patterns-platform.md](code-patterns-platform.md); agent-side snippets in [code-patterns-agents.md](code-patterns-agents.md); LangGraph graphs, pauses and dispatch in [code-patterns-langgraph.md](code-patterns-langgraph.md). `<project>`, `<region>`, `<account-id>` are placeholders; never hard-code real keys, accounts, ARNs or URLs.

## Contents

| # | Pattern | Use when |
|---|---|---|
| 1 | [Gateway + OpenAPI target + key provider](#1-gateway-openapi-target-and-api-key-provider) | Tools behind AgentCore Gateway |
| 2 | [Cedar policy](#2-cedar-policy-log-only-then-enforce) | A rule the agent must not break |
| 3 | [Runtime entrypoint](#3-runtime-entrypoint-answer-now-work-in-the-background) | One agent app, laptop and Runtime |
| 4 | [agentcore.json, CDK, CLI](#4-agentcorejson-cdk-and-cli-essentials) | Deploying with the AgentCore CLI |
| 5 | [Invoke a Runtime](#5-invoking-a-runtime-from-the-backend) | The app starts agent work |
| 6 | [AgentCore Memory](#6-agentcore-memory-with-strategies-and-namespaces) | Per-customer long-term memory |
| 7 | [IAM, budget, teardown](#7-iam-shape-budget-spend-monitor-teardown-verification) | Any AWS account you must leave clean |

## Versions (as taught in the course, Oct 2026; re-check before use)

| Item | Reference build |
|---|---|
| Python; Runtime `runtimeVersion` | 3.12; `PYTHON_3_12` |
| `bedrock-agentcore` / `boto3` / `langgraph-checkpoint-aws` | `>=1.24.1` / `>=1.43.108` / `>=1.2.4` |
| AgentCore CLI (npm) | `@aws/agentcore@1.0.0-rc.5` (release candidate, pinned by the labs) |
| CDK project | `@aws/agentcore-cdk` `1.0.0-rc.3`, `aws-cdk-lib` `~2.269.0` |
| Region; boto3 clients | `us-east-1`; `bedrock-agentcore-control` (manage), `bedrock-agentcore` (invoke, memory data) |

## Key principles

1. **Enforce in the backend, not the prompt, and fail closed.** Limits, roles and "who may call" live in code the model cannot argue with; a Gateway policy is a second layer, and with no `permit` every tool is refused.
2. **Whatever the Gateway can see, the agent can call.** The OpenAPI document is the allow-list; keep human-only actions out of it.
3. **Name and tag everything** with a project prefix so teardown finds it by name, not from a remembered list.
4. **New IAM roles and permissions propagate slowly:** wrap first calls in a retry loop.

---

## 1. Gateway, OpenAPI target and API-key provider

**Use when:** agent tools go through AgentCore Gateway: one place to authenticate, authorise and observe tool calls. Client: `bedrock-agentcore-control`.

```python
agentcore = session.client("bedrock-agentcore-control")
# 1. The app's key in AgentCore Identity (held in Secrets Manager); update_api_key_credential_provider rotates it
agentcore.create_api_key_credential_provider(name="<project>-app-key", apiKey=API_KEY, tags=TAG)
p = agentcore.get_api_key_credential_provider(name="<project>-app-key")
provider_arn, secret_arn = p["credentialProviderArn"], p["apiKeySecretArn"]["secretArn"]

# 2. Gateway role. Trust: only gateways named <project>-gateway-* in this account may assume it
trust_condition = {"StringEquals": {"aws:SourceAccount": account},
    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account}:gateway/<project>-gateway-*"}}
# role policy: bedrock-agentcore:GetWorkloadAccessToken and :GetResourceApiKey (provider, token vault,
# workload-identity ARNs) + secretsmanager:GetSecretValue on secret_arn

# 3. The Gateway: MCP, callers sign with IAM; DEBUG makes errors say what went wrong
gw = agentcore.create_gateway(name="<project>-gateway", roleArn=role_arn, protocolType="MCP",
        authorizerType="AWS_IAM", exceptionLevel="DEBUG", tags=TAG)       # poll get_gateway until not CREATING

# 4. OpenAPI target that sends the key in a header
agentcore.create_gateway_target(gatewayIdentifier=gw["gatewayId"], name="<project>-app",
    targetConfiguration={"mcp": {"openApiSchema": {"inlinePayload": json.dumps(agent_doc)}}},
    credentialProviderConfigurations=[{"credentialProviderType": "API_KEY", "credentialProvider": {
        "apiKeyCredentialProvider": {"providerArn": provider_arn,
                                     "credentialParameterName": "X-API-Key", "credentialLocation": "HEADER"}}}])
# MCP-server target (pattern 7 of code-patterns-platform.md): {"mcp": {"mcpServer": {"endpoint": f"{context_url}/mcp"}}} with
#   credentialProviderType "GATEWAY_IAM_ROLE" and {"iamCredentialProvider": {"service": "lambda", "region": region}}
```
Callers list tools with an MCP client (`langchain_mcp_adapters.MultiServerMCPClient`, `transport: "streamable_http"`, `auth: Sign(session, "bedrock-agentcore")` from pattern 7 of [code-patterns-platform.md](code-patterns-platform.md)); tools are named `<target>___<operation>`. The OpenAPI document (`agent_doc`) is built by pattern 4 of the same file.

**Pitfalls:** make every step idempotent (find by name with `list_gateways`, `list_gateway_targets`, `list_api_key_credential_providers`; update if present). Retry `create_gateway`/targets on a `ValidationException` that mentions the role. An app error returns as the tool result for the model; a Gateway **refusal** is an MCP error: handle both. Delete targets before the gateway.

**Source:** `labs/week3day2_lab2.ipynb` Part 2; `labs/week3day3.ipynb` Part 3; `labs/week3day4_aws.py` (`put_key_provider`, `make_gateway_role`, `put_targets`); `origin/week3day5-end:agent/gateway.py`.

## 2. Cedar policy: log-only, then enforce

**Use when:** a rule must hold whatever the model decides (payment cap, forbidden tool, protected argument).

```cedar
// With an engine attached a call is refused unless a policy permits it: one permit per target
permit(principal is AgentCore::IamEntity, action in AgentCore::Action::"<project>-app",
       resource == AgentCore::Gateway::"<gateway-arn>");
// A forbid always wins. Tool inputs are Cedar decimals => greaterThan, not >
forbid(principal is AgentCore::IamEntity, action == AgentCore::Action::"<project>-app___pay_claim",
       resource == AgentCore::Gateway::"<gateway-arn>")
when { context.input.amount.greaterThan(decimal("1000.00")) };
```
```python
engine_id = agentcore.create_policy_engine(name="<project>_policy_engine", tags=TAG)["policyEngineId"]   # poll until ready
# Gateway role needs bedrock-agentcore:GetPolicyEngine (engine ARN) and AuthorizeAction +
# PartiallyAuthorizeActions on [engine ARN, gateway ARN]
agentcore.create_policy(policyEngineId=engine_id, name="<project>_payment_limit", definition={"cedar": {"statement": cedar}})

def attach(mode):                                           # "LOG_ONLY" first, then "ENFORCE"
    agentcore.update_gateway(gatewayIdentifier=gw_id, name=NAME, description=desc, roleArn=role_arn,
        protocolType="MCP", authorizerType="AWS_IAM", exceptionLevel="DEBUG",    # update_gateway wants every setting again
        policyEngineConfiguration={"arn": engine_arn, "mode": mode})
```
Decisions appear in CloudWatch, a minute or two late: namespace `AWS/Bedrock-AgentCore`, metrics `AllowDecisions` / `DenyDecisions`, dimensions `OperationName=AuthorizeAction`, `Mode`, `PolicyEngine`.

**Pitfalls:** try a new rule in `LOG_ONLY` on real traffic, read the would-be refusals, then `ENFORCE`. In log-only the app's own limit (pattern 3 of [code-patterns-platform.md](code-patterns-platform.md)) refuses; enforcing moves the refusal in front of the app. No `permit` means every tool is refused. `context.input.amount` is the tool's input name: keep the API field stable and test one over-limit and one under-limit call. On a Gateway refusal the reference build parks the approval for a human sign-off through a route that is **not** a Gateway tool. Layers and threat model: [security-and-guardrails.md](security-and-guardrails.md).

**Source:** `labs/week3day2_lab2.ipynb` Part 3; `labs/week3day4_aws.py` (`permit`, `payment_limit`, `enforce_policy`); `origin/week3day5-end:backend/main.py` (`hold_payment`).

## 3. Runtime entrypoint: answer now, work in the background

**Use when:** one agent app must run the same on a laptop and on AgentCore Runtime, and the work outlives the request.

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
app = BedrockAgentCoreApp()

class Op(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)  # unknown/extra fields => 400, values never echoed
class Health(Op):  operation: Literal["health"]
class WorkRun(Op): operation: Literal["work_run"]; run_id: str
PAYLOADS = TypeAdapter(Annotated[Health | WorkRun, Field(discriminator="operation")])

def in_background(name, work):
    task_id = app.add_async_task(name)                      # /ping reports HealthyBusy until completed
    def run():
        try: work()
        finally: app.complete_async_task(task_id)
    threading.Thread(target=run, name=name, daemon=True).start()

@app.entrypoint
def invoke(payload, context: RequestContext) -> dict:
    ready = lazy_ready.get()                                # first request only, behind a lock
    request = PAYLOADS.validate_python(payload)
    if isinstance(request, WorkRun):
        run = backend.get_run(request.run_id)               # re-read state from the system of record
        if run["status"] != "running":
            return {"refused": "Run isn't running"}
        in_background("run", partial(work_the_run, run, ready))
    return {"accepted": True}                               # answer at once; the work carries on
```
```python
# runtime/main.py (what Runtime starts) is just: from agent.entrypoint import app; app.run()
# on a laptop: uvicorn agent.entrypoint:app --port 8080. Secrets come on the first request, never at import:
from bedrock_agentcore.identity.auth import requires_api_key
os.environ[setting] = requires_api_key(provider_name=provider)(lambda api_key: api_key)()
```

**Pitfalls:** Runtime platform V2 snapshots the process after import, so nothing at import time (no connections, no secrets); on the first request call `random.seed()`, fetch credentials from Identity (provider names arrive as `AGENTCORE_CREDENTIAL_<NAME>_NAME`) and open the DB pool. Answers are explicit, `{"accepted": true}` or `{"refused": reason}`. Off Runtime check the caller's key as a bearer token in constant time; on Runtime AWS already authorised the caller. If the background work dies, tell the backend (`fail_run`) so nothing stays "running". Differences between targets come from settings, not branches in the logic. Resuming a paused item inside this app: pattern 3 of [code-patterns-langgraph.md](code-patterns-langgraph.md).

**Source:** `origin/week3day5-end:agent/entrypoint.py`, `agent/agentcore_app.py`, `agent/identity.py`, `runtime/main.py`; `labs/week3day4_lab2.ipynb` Part 2.

## 4. agentcore.json, CDK and CLI essentials

**Use when:** deploying with the AgentCore CLI (CloudFormation via CDK, zip build, no Docker).

```json
{ "name": "<project>", "version": 2, "managedBy": "CDK", "tags": {"project": "<project>"},
  "runtimes": [{ "name": "agent", "build": "CodeZip", "entrypoint": "main.py", "codeLocation": "runtime",
    "runtimeVersion": "PYTHON_3_12", "protocol": "HTTP",
    "lifecycleConfiguration": {"idleRuntimeSessionTimeout": 60}, "additionalPolicies": ["policy.json"] }],
  "credentials": [{"authorizerType": "ApiKeyCredentialProvider", "name": "OPENROUTER_API_KEY"},
                  {"authorizerType": "ApiKeyCredentialProvider", "name": "AGENT_API_KEY"}] }
```
The credential names are generic here; UnderCover's are `OPENROUTER_API_KEY`, `UNDERCOVER_API_KEY` and `DATABASE_URL`.

Credential **values** go in git-ignored `agentcore/.env.local` as `AGENTCORE_CREDENTIAL_<NAME>=...`; the first deploy stores them in AgentCore Identity. Non-secret addresses go in the same file and the CDK stack passes them on:

```ts
const SETTINGS = ['APP_URL', 'GATEWAY_URL', 'MEMORY_ID'];            // from .env.local or the deploy environment
const application = new AgentCoreApplication(this, 'Application', props.application);
for (const runtime of props.application.spec.runtimes)
  for (const name of SETTINGS) {
    const value = local[name] ?? process.env[name];
    if (value) application.runtime(runtime.name).addEnvironmentVariable(name, value);
  }
for (const child of this.node.findAll())                              // platform V2: sessions start from a snapshot (~2 s)
  if (CfnResource.isCfnResource(child) && child.cfnResourceType === 'AWS::BedrockAgentCore::Runtime')
    child.addPropertyOverride('PlatformVersion', 'V2');               // no CLI setting yet (as taught, Oct 2026)
```

| Task | Command (CLI `@aws/agentcore@1.0.0-rc.5`; time-sensitive) |
|---|---|
| New project | `agentcore create --name <name> --template agent-python-minimal` (or `agent-python-langchain`) |
| Add a secret | `agentcore add credentials` |
| Run as Runtime would (port 8080: `/ping`, `/invocations`) | `agentcore dev` |
| Deploy (about 4-7 min first time) | `agentcore deploy` |
| Invoke (JSON via stdin: PowerShell drops quotes in args) | `echo '{"operation":"health"}' \| agentcore invoke --runtime agent --payload -` |
| Status / logs | `agentcore status` / `agentcore log runtime --since 15m` |
| Delete everything | `agentcore remove all --yes`, then `agentcore deploy --yes`, then `git restore agentcore/agentcore.json` |

**Pitfalls:** the zip build installs from a `pyproject.toml` and reads no lock; the reference stack generates one from `uv export --only-group runtime --no-hashes --no-emit-project` so deployed versions equal `uv.lock`. The first deploy bootstraps CDK (`CDKToolkit`: S3 bucket, KMS key about $1/month, a CloudFormation role with administrator access): remove it at the end (pattern 7). Runtime log groups survive `remove all`: delete by name. State must live outside the 60-second-idle session (database checkpoints). Context: [production-deployment-aws.md](production-deployment-aws.md).

**Source:** `origin/week3day5-end:agentcore/agentcore.json`, `agentcore/cdk/lib/cdk-stack.ts`, `agentcore/cdk/package.json`; `labs/week3day4_lab1.ipynb`, `labs/week3day4_lab2.ipynb`.

## 5. Invoking a Runtime from the backend

**Use when:** the app (e.g. on Lambda) starts agent work on Runtime, or continues a conversation in a warm session.

```python
runtime = boto3.client("bedrock-agentcore", config=Config(
    retries={"total_max_attempts": 1},                      # a retried call could start the same work twice
    connect_timeout=2, read_timeout=15))                    # the whole call must fit Lambda's 30 s

def ask(arn: str, payload: dict, session_id: str | None = None) -> None:
    session_id = session_id or str(uuid.uuid4())           # >= 33 chars; new per dispatch, or the conversation id
    try:                                                    # to reach the same warm session each turn
        resp = runtime.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=session_id,
                                            payload=json.dumps(payload))
        status, body = resp["statusCode"], resp["response"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":    # session starting/stopping: never reached the app
            raise SafeToRetry() from e                      # retry after 1, 2, 4 s while the time budget allows
        raise NotTaken(e.response["Error"]["Message"]) from e
    if status >= 400 or json.loads(body) != {"accepted": True}:     # refused: {"refused": reason}
        raise NotTaken(body.decode())
```
Caller's IAM (the app's role): `{"Action": "bedrock-agentcore:InvokeAgentRuntime", "Resource": ["<runtime-arn>", "<runtime-arn>/runtime-endpoint/*"]}`. In the route: **commit what you recorded, then ask; if not taken, undo and commit the undo**, because the agent reads it from the database.

**Pitfalls:** classify failures: never reached (503), refused or error answer (409/502), reached-then-lost (may have started: tell the user to reload, never retry). Keep `botocore` loggers at INFO or above: DEBUG lines hold every payload, which may carry a sign-in. Payloads are an operation plus ids, never secrets. Choose the route by one env var (runtime ARN set means Runtime, else a laptop URL).

**Source:** `origin/week3day5-end:backend/runtime_calls.py`, `backend/agent_service.py`, `backend/copilot_service.py`, `backend/asking.py`; `labs/week3day4_lab2.ipynb` Part 4.

## 6. AgentCore Memory with strategies and namespaces

**Use when:** an agent remembers a customer or user across sessions with strict per-subject isolation. When memory is worth it: [rag-memory-and-mcp.md](rag-memory-and-mcp.md); the agent-side store and tool: pattern 9 of [code-patterns-agents.md](code-patterns-agents.md).

```python
memory_id = agentcore.create_memory(name="<project>_memory", description="Memory of each customer",
    eventExpiryDuration=7,                                  # days; the shortest AgentCore allowed (as taught)
    memoryStrategies=[
        {"semanticMemoryStrategy": {"name": "customer_facts", "namespaceTemplates": ["/customers/{actorId}/facts/"]}},
        {"summaryMemoryStrategy": {"name": "claim_summaries", "namespaceTemplates": ["/customers/{actorId}/claims/{sessionId}/"]}},
        # also: {"userPreferenceMemoryStrategy": {"name": ..., "namespaceTemplates": ["/handlers/{actorId}/preferences/"]}}
    ], tags=TAG)["memory"]["id"]
while agentcore.get_memory(memoryId=memory_id)["memory"]["status"] == "CREATING":
    time.sleep(10)                                          # about 2.5 minutes

from langgraph_checkpoint_aws import AgentCoreMemoryStore   # agent side: events keyed by actor (customer) + session (claim)
store = AgentCoreMemoryStore(memory_id=memory_id, region_name=region)

data = session.client("bedrock-agentcore")                  # read strictly under one subject's namespace
data.retrieve_memory_records(memoryId=memory_id, namespacePath=f"/customers/{customer_id}",
        searchCriteria={"searchQuery": "earlier claims", "topK": 5})["memoryRecordSummaries"]
```
Runtime role (its own memory only): actions `bedrock-agentcore:CreateEvent`, `GetEvent`, `ListEvents`, `RetrieveMemoryRecords`, `ListMemoryRecords`, `GetMemoryRecord` on `arn:aws:bedrock-agentcore:*:*:memory/<project>_memory-*`.

**Pitfalls:** extraction into records is asynchronous (usually a couple of minutes): poll, never assume a record right after the event. The namespace is the isolation boundary: the same query under another customer's path must return nothing, so test it. Ids are the name plus a suffix: find with `id.startswith(name)` and skip `DELETING`; deleting a memory deletes its events and records. Do not store secrets or raw sensitive documents as events.

**Source:** `labs/week3day3.ipynb` Part 4; `labs/week3day5_lab1.ipynb`; `labs/week3day4_aws.py` (`create_memory`); `origin/week3day5-end:agent/agentcore_memory.py`, `runtime/policy.json`.

## 7. IAM shape, budget, spend monitor, teardown verification

**Use when:** you create anything in an AWS account, yours or a client's.

Least privilege by **name prefix and condition**. The course policy (`labs/undercover-course-policy.json`) is broader on purpose (`bedrock-agentcore:*` and CloudFormation on `*`, and the CDK bootstrap role is admin): tighten both for a client.

```json
{"Version": "2012-10-17", "Statement": [
  {"Sid": "ProjectFunctionsOnly", "Effect": "Allow", "Action": "lambda:*",
   "Resource": "arn:aws:lambda:*:*:function:<project>*"},
  {"Sid": "ManageProjectRoles", "Effect": "Allow", "Resource": "arn:aws:iam::*:role/<project>*",
   "Action": ["iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:TagRole", "iam:PutRolePolicy", "iam:DeleteRolePolicy"]},
  {"Sid": "PassRoleOnlyToNamedServices", "Effect": "Allow", "Action": "iam:PassRole",
   "Resource": "arn:aws:iam::*:role/<project>*",
   "Condition": {"StringEquals": {"iam:PassedToService": ["lambda.amazonaws.com", "bedrock-agentcore.amazonaws.com"]}}},
  {"Sid": "DeleteOnlyProjectLogs", "Effect": "Allow", "Action": "logs:DeleteLogGroup",
   "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/<project>*"}]}
```
Each function and runtime gets its **own** role with only what it uses: a Lambda role that writes to its own log group; a runtime role with `bedrock-agentcore:InvokeGateway` on `gateway/<project>-gateway-*` plus its own memory (pattern 6); the app role with `InvokeAgentRuntime` on one runtime (pattern 5).

**Budget:** a monthly cost budget alerting at 50/80/100% of actual cost, **excluding Credit and Refund** charge types: a budget that counts credits sees zero while credits pay the bill and never alerts. The course sets it in the console; via API (verify):

```python
budgets.create_budget(AccountId=account, Budget={"BudgetName": "<project>-monthly", "TimeUnit": "MONTHLY",
    "BudgetType": "COST", "BudgetLimit": {"Amount": "10", "Unit": "USD"},
    "FilterExpression": {"Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit", "Refund"]}}}},
  NotificationsWithSubscribers=[{"Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN",
      "Threshold": pct, "ThresholdType": "PERCENTAGE"}, "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "<you@example.com>"}]}
    for pct in (50, 80, 100)])
```
`monitor.py` (`uv run monitor.py`) creates two free daily budgets with no alerts (all spend, and spend after credits) and charts `describe_budget_performance_history`; figures lag by hours. Keep the alerting budget too.

**Teardown you can trust:** find by name in every service, delete in dependency order, verify three ways.

```python
def find_all():                                             # never from a remembered list
    return {"Lambda": [f["FunctionName"] for p in lam.get_paginator("list_functions").paginate()
                       for f in p["Functions"] if f["FunctionName"].startswith("<project>")],
            "Gateways": ..., "Policy engines": ..., "Memories": ..., "Runtimes": ..., "IAM roles": ...,
            "Log groups": ..., "Stacks": ..., "Secrets": ..., "KMS aliases": ...}
# Order: targets -> gateway; policies -> engine; credential providers; memories; `agentcore remove all --yes` + deploy;
#   runtime log groups; functions -> roles -> /aws/lambda logs; CDKToolkit stack LAST (empty its versioned bucket first)
explorer = session.client("resource-explorer-2")            # free index of the whole Region
found = [r for p in explorer.get_paginator("list_resources").paginate() for r in p["Resources"]]
print(Counter(r["ResourceType"] for r in found), [r["Arn"] for r in found if "<project>" in r["Arn"].lower()])
```

**Pitfalls:** the three checks are your by-name scan (each line "none"), Resource Explorer (lags minutes; scan again tomorrow) and spend (budgets). Before deleting a KMS key check the AgentCore token vault does not use it (`get_token_vault`). Deactivate the IAM user's access key when done; MFA on root and not used for work. Usual leftovers: roles, log groups with no retention, KMS keys. Tag everything `project=<project>` as well (`tag:GetResources`).

**Source:** `labs/undercover-course-policy.json`, `monitor.py`, `labs/week3day1.ipynb` (`counts_credits`), `labs/week3day4_aws.py` (`show_resources`, `tear_down`, `delete_bootstrap`), `labs/week3day5_lab2.ipynb`; `origin/week3day5-end:runtime/policy.json`.

---

## Decisions to make with the developer

| Question | Options and trade-off | Default |
|---|---|---|
| How does the agent authenticate to your API? | Shared key (simple, rotate by redeploy) vs IAM/OIDC (stronger, more setup) | Key in AgentCore Identity, sent by the Gateway |
| Who enforces limits | App only vs app + Cedar | Both layers, Cedar in log-only first |
| Runtime session per... | Dispatch (isolation) vs conversation (warm context) | Dispatch for batch, conversation for copilots |

## In UnderCover

One AgentCore Gateway with two targets and a $1,000 Cedar forbid on `pay_claim`, two Runtimes (claim agent, copilot) with per-runtime policies, and a teardown by name. The backend and context-layer pieces they call are in [code-patterns-platform.md](code-patterns-platform.md). See [undercover-case-study.md](undercover-case-study.md).

## Related

[production-deployment-aws.md](production-deployment-aws.md) | [security-and-guardrails.md](security-and-guardrails.md) | [rag-memory-and-mcp.md](rag-memory-and-mcp.md) | [context-layer-and-integrations.md](context-layer-and-integrations.md) | [durable-state-and-hitl.md](durable-state-and-hitl.md) | [copilot-pattern.md](copilot-pattern.md) | [code-patterns-platform.md](code-patterns-platform.md) | [code-patterns-agents.md](code-patterns-agents.md) | [code-patterns-langgraph.md](code-patterns-langgraph.md)

## Sources

Reference builds (read-only): `origin/week3day5-end:` `backend/{main,runtime_calls,agent_service,copilot_service,asking}.py`, `runtime/{main,copilot}.py`, `runtime/{policy,copilot_policy}.json`, `agent/{entrypoint,agentcore_app,identity,gateway,agentcore_memory}.py`, `agentcore/agentcore.json`, `agentcore/cdk/lib/cdk-stack.ts`, `agentcore/cdk/package.json`, `pyproject.toml`, `package.json`, `docs/TECH_STACK.md`. Local: `labs/undercover-course-policy.json`, `monitor.py`, `labs/week3day4_aws.py`. Notebooks: `week3day1`, `week3day2_lab2`, `week3day3`, `week3day4_lab1`, `week3day4_lab2`, `week3day5_lab1`, `week3day5_lab2`.

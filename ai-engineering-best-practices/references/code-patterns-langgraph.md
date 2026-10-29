# Code patterns: LangGraph durable graphs, pauses and dispatch

> When to read this: you are writing or reviewing the LangGraph part of an agent: the item graph with routing in code, an idempotent side effect, a Postgres checkpointer with a thread per item and resume after a human pause, an LLM-free dispatcher that fans work out, and the two small helpers around them. Snippets are minimal and generic ("item" = a claim, ticket or order); they show the API calls and the safety-critical detail, not whole modules. The bullets after each snippet are its pitfalls. Sibling pattern files: model client, tools, screening, judge, improver, MCP, memory, copilot and stub model in [code-patterns-agents.md](code-patterns-agents.md); backend, Lambda and context-server snippets in [code-patterns-platform.md](code-patterns-platform.md); Gateway, Cedar, Runtime, Memory setup and account hygiene in [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md).

## Contents

| # | Pattern | Use it when | Concept |
|---|---|---|---|
| 1 | The item graph with conditional edges | Routing, pauses or side effects in code | [durable-state-and-hitl](durable-state-and-hitl.md) |
| 2 | Idempotent side effect, nothing before the pause | Money moves, mail is sent | [durable-state-and-hitl](durable-state-and-hitl.md) |
| 3 | Postgres checkpointer, thread per item, resume | Work outlives a process or waits for a human | [durable-state-and-hitl](durable-state-and-hitl.md) |
| 4 | LLM-free dispatcher, fan-out, retries | A queue worked in parallel | [swarms-and-scale](swarms-and-scale.md) |

The section "Small helpers" at the end covers `as_root_run` and the heartbeat.

## Library versions (as used in the course, Oct 2026)

Floors from `pyproject.toml` of Ed's final build (`origin/week3day5-end`); `uv.lock` pins exact versions. Re-check names against current docs (verify).

| Library | Floor | Used for |
|---|---|---|
| Python | 3.12 | Generic `def f[T]()` and `except*` appear in the build |
| `langchain` / `langgraph` | 1.4.2 / 1.2.12 | `create_agent`, middleware, `@tool`, `StateGraph`, `interrupt`, `Send` |
| `langgraph-checkpoint-postgres` | 3.1.2 | `PostgresSaver` (with `psycopg[binary]` 3.3.6, `psycopg-pool` 3.3.3) |
| `bedrock-agentcore` | 1.24.1 | `BedrockAgentCoreApp` (the app that resumes a paused item) |

## Key principles

1. **Authority lives in code, not in the prompt.** The model proposes; nodes and the backend pay, hold, refuse and route. A prompt rule can be argued with; a refusal cannot.
2. **Side effects are idempotent and sit after the pause.** A resumed node re-runs from its top; a retried item re-runs from its last step.
3. **Save state after every step, one thread per item,** and resume with the human's answer.
4. **Fail soft per item.** Transient errors retry; anything else becomes a one-line report and the item goes to a person.
5. **Credentials ride in context, never in state** (state is checkpointed).

## 1. The item graph: screen, agent loop, decision, pause, pay

Use when you need deterministic routing around the model. Week 2's lab used `agent` and `tools`, then a `decide` node (structured output), then `approval` (interrupt) and `pay`, with an edge comparing the payout to the limit. The build lets a `record_decision` tool write the decision into state and lets the backend say whether it is held:

```python
class ItemState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    model_calls: Annotated[int, operator.add]        # nodes return 1; the total accumulates
    decision: Annotated[dict, keep_last]             # def keep_last(_, new): return new
    status: Annotated[str, keep_last]

def call_model(state, runtime: Runtime[ItemContext], llm, instructions: SystemMessage):
    if state["model_calls"] >= MAX_MODEL_CALLS:
        raise TooManyModelCalls()
    reply = llm.invoke([instructions, *state["messages"]])           # instructions rebuilt per call, never saved
    return {"messages": [reply], "model_calls": 1}

def after_tools(state) -> str:                       # route on what the backend returned
    if not state["decision"]:                  return "agent"
    if state["status"] == "waiting_for_sign_off": return "held"
    if state["decision"]["decision"] == "approve" and state["status"] == "in_progress": return "pay"
    return END

builder = StateGraph(ItemState, context_schema=ItemContext)
builder.add_node("agent", partial(call_model, llm=llm.bind_tools(TOOLS), instructions=SystemMessage(text)))
builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=refusal, wrap_tool_call=record_result))
builder.add_node("pay", pay)
builder.add_node("wait_for_handler", wait_for_handler)
builder.add_conditional_edges("agent", after_agent, ["tools", END])            # tool calls? else done
builder.add_conditional_edges("tools", after_tools, {"agent": "agent", "pay": "pay", "held": "wait_for_handler", END: END})
builder.add_conditional_edges("pay", after_pay, {"held": "wait_for_handler", END: END})
graph = builder.compile(checkpointer=saver)       # START edge goes to the screen node (pattern 4 of code-patterns-agents.md)
```

The tool returns `Command(update={"messages": [ToolMessage(as_json(item), tool_call_id=runtime.tool_call_id)], "decision": item["decision"], "status": item["status"]})` so the edge can route on it.

- The model never pays: `pay` is a node that calls the backend, which refuses a payment over the limit, a different amount or a second payment.
- `ToolNode(handle_tool_errors=fn, wrap_tool_call=fn)`: the first turns a refusal into text the model reads and re-raises anything else; the second records each result as a step.
- A reducer field is reset with `Overwrite(0)` (`langgraph.types`), not a plain value. List every destination in `add_conditional_edges` so LangGraph can validate and draw it.
- Evaluation copies run with no memory store and no pause (nobody signs off a copy): pass these as graph options, not `if`s inside nodes.

Source: `labs/week2day3.ipynb`; `origin/week3day5-end:agent/harness.py` (`claim_graph`, `after_tools`, `call_model`), `tools.py` (`ClaimState`, `record_decision`).

## 2. Idempotent side effect; nothing before the interrupt

Use for anything that must happen once. Key it on the item id.

```python
# Generic database form (Week 2 lab): the item id is the primary key
cursor = connection.execute("INSERT INTO payments (item_id, amount) VALUES (%s, %s) ON CONFLICT (item_id) DO NOTHING",
                            (item_id, amount))
already_paid = cursor.rowcount == 0

# The build's form: the backend owns the rule, the node only calls it
def pay(state, runtime: Runtime[ItemContext]):
    try:
        item = runtime.context.route.call("app", "pay_item", {"item_id": runtime.context.item_id,
                                                              "amount": state["decision"]["amount"]})
    except GatewayRefused as refused:                 # policy forbids it: hold for a person
        item = hold_for_sign_off(runtime.context, refused)
    return {"status": item["status"]}
# Backend rule (pseudo): paid + same amount -> return the item; paid + other amount -> 409; over limit -> 403
```

- On resume LangGraph re-runs the interrupted node from its top, so anything before `interrupt()` runs twice (the lab prints a message twice). Put side effects in a node of their own, after the pause.
- A crash inside `pay` re-runs `pay`; the key (or the backend rule) makes the second run a no-op. The same protects `RetryPolicy` retries: a recorded decision cannot be changed.

Source: `labs/week2day3.ipynb` ("Never pay twice"); `origin/week3day5-end:backend/main.py` (`pay_claim`), `agent/harness.py` (`pay`).

## 3. Postgres checkpointer, thread per item, resume with the answer

Use when work outlives a process or waits for a human. Any process or AgentCore session can resume from the thread id.

```python
pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=4, timeout=120, open=True,
    kwargs={"autocommit": True, "prepare_threshold": None,        # no prepared statements: works through Supabase poolers
            "row_factory": dict_row, "options": "-c search_path=myschema"})
with pool.connection() as c: c.execute("CREATE SCHEMA IF NOT EXISTS myschema")
saver = PostgresSaver(pool); saver.setup()                        # setup() creates the tables once; one saver per worker

config = {"configurable": {"thread_id": item["thread_id"]}}
graph.invoke(start, config, context=ctx, durability="sync")       # each step is saved before the next starts
state = graph.get_state(config)    # .next = where it resumes; .interrupts = non-empty once the pause has run
graph.invoke(Command(resume={"answer": "signed_off", "by": "Dana"}), config, context=ctx, durability="sync")
```

A human can send the decision back with a note. The pause node forgets the decision and hands the model the note:

```python
def wait_for_handler(state, runtime):
    answer = interrupt({"item_id": runtime.context.item_id})          # nothing with side effects above this line
    if answer["answer"] != "sent_back":
        return {}                                                     # signed off: the backend already paid
    return {"decision": {}, "status": "", "model_calls": Overwrite(0),   # fresh allowance of model calls
            "messages": [HumanMessage(NOTE.format(by=answer["by"], note=answer["note"]))]}

def after_handler(state): return END if state["decision"] else "agent"   # no decision: the agent works again
```

Carrying on after a restart rebuilds the `Command` from the backend's record, not from memory: `Command(resume=answer_of(item))` when `saved.next == ("wait_for_handler",)` and an answer exists; the start message when nothing is saved (`saved.created_at is None`); `None` otherwise (carry on from the last saved step). On AgentCore Runtime (`BedrockAgentCoreApp`; the entrypoint pattern is in [code-patterns-aws-agentcore.md](code-patterns-aws-agentcore.md), pattern 3), the `@app.entrypoint` function takes `action` and `thread_id` in its payload and calls `item_graph().invoke(start, {"configurable": {"thread_id": ...}}, durability="sync")`, where `start` is the first input or `Command(resume=payload["note"])` and `item_graph` is a `@cache` function that builds pool, saver and graph on the first request. It reports `"__interrupt__" in state` as paused.

- One thread per item. A shared thread lets one `interrupt()` pause everything and races on resume.
- `state.next == (pause,)` already holds once the step before the pause is saved, before the pause has run. To ask "is a person being waited on", check `state.interrupts`. An answer given before the pause ran is kept and handed back by `interrupt()` at once.
- Store the human's answer (who, what, note) in the backend's record; do not depend on a process remembering it.
- Never build pools or models at import in an AgentCore app: every session starts from a snapshot taken after import, so they would be shared and stale. A transaction pooler (port 6543) suits many short sessions; free Postgres projects pause when idle.

Source: `labs/week2day3.ipynb`, `labs/week3day4_lab1.ipynb`, `labs/undercoverlab/app/agent/main.py`; `origin/week3day5-end:agent/checkpoints.py`, `harness.py` (`carry_on`, `paused`, `wait_for_handler`), `handler_answer.py`.

## 4. LLM-free dispatcher: fan-out, concurrency cap, reducer, retries

Use for a queue worked in parallel. The dispatcher is a graph with no model; each item goes to a worker with its own graph and thread.

```python
class Dispatch(TypedDict):
    items: list[str]
    reports: Annotated[list[str], operator.add]       # reducer: parallel branches append, none overwrite

TRANSIENT = (ModelRateLimitError, ModelTimeoutError)  # langchain_core.exceptions
RETRY = RetryPolicy(max_attempts=3, initial_interval=10, retry_on=TRANSIENT)   # ~10 s, then ~20 s

def fan_out(state):
    return [Send("work_item", {"item_id": i}) for i in state["items"]] or "finish"

def work_item(state, runtime: Runtime[DispatchContext]):
    try:
        report = runtime.context.work(state["item_id"])
    except Exception as error:
        if isinstance(error, TRANSIENT) and runtime.execution_info.node_attempt < RETRY.max_attempts:
            raise                                      # RetryPolicy waits and runs the node again
        report = f"{state['item_id']} left for the next dispatch: {error}"
    return {"reports": [report]}

builder = StateGraph(Dispatch, context_schema=DispatchContext)
builder.add_node("list_items", list_items); builder.add_node("finish", finish_run)
builder.add_node("work_item", work_item, retry_policy=RETRY)
builder.add_edge(START, "list_items")
builder.add_conditional_edges("list_items", fan_out, ["work_item", "finish"])
builder.add_edge("work_item", "finish"); builder.add_edge("finish", END)   # all workers done, then finish once
state = as_root_run(builder.compile().invoke, {"items": [], "reports": []},
                    {"max_concurrency": run["agents"]}, context=DispatchContext(run, work))
```

- `max_concurrency` caps nodes in flight: set it from the provider's rate limits, the database's connections (the build's pool holds 4) and the people who review the results.
- Retry layers: client `max_retries=5` per call, `RetryPolicy` per item, "left for the next dispatch" last. Retries are safe because the backend refuses a second decision or payment.
- Re-raise only transient errors, only while attempts remain; on the last attempt report and carry on so one item cannot fail the run.
- Two actors may reach one item (a dispatch and a resume): take it with a backend call that returns 409 to the loser. Prove the shape with a one-second stand-in worker at 1, 5 and 25 before spending on models.

Source: `labs/week2day4.ipynb`; `origin/week3day5-end:agent/dispatcher.py`, `work.py`.

## Small helpers (`agent/root_run.py`, `agent/heartbeat.py`)

```python
def as_root_run(run, *args, **kwargs):      # a graph called inside another graph (dispatcher worker, improver tool)
    return contextvars.Context().run(run, *args, **kwargs)   # fresh context: else tracing nests it and it may save into the caller's thread
```

A heartbeat is a context manager that starts a daemon thread calling `tell()` every 60 seconds while long work runs (the backend counts work as stopped after 5 minutes), logs a failed call as a warning and never lets it stop the work, and sets a `threading.Event` and joins the thread on exit.

## Decisions to make with the developer

- **`create_agent` or a hand-written graph?** Default `create_agent` with middleware for short single-session work; move to a `StateGraph` at the first interrupt, payment or routing on backend state.
- **Isolation and scale?** Thread per item always; start `max_concurrency` small and raise it to the provider's and database's limits.
- Avoid: side effects before `interrupt()`; credentials in state; one thread for many items; routing on what the model said instead of what the backend returned.

## In UnderCover

Week 2 adds a Postgres-checkpointed graph with an approval pause and idempotent payment (1, 2, 3) and a dispatcher with a swarm of claim agents (4). In Week 3 the agent becomes an AgentCore app that resumes a paused claim in any session (3). The screening node that starts the graph is pattern 4 of [code-patterns-agents.md](code-patterns-agents.md); the heartbeat has its backend side in pattern 8 of [code-patterns-platform.md](code-patterns-platform.md).

## Related

- [durable-state-and-hitl](durable-state-and-hitl.md) (1, 2, 3), [swarms-and-scale](swarms-and-scale.md) (4), [harness-engineering](harness-engineering.md), [agent-architecture](agent-architecture.md)
- Sibling pattern files: [code-patterns-agents](code-patterns-agents.md) (model client, tools, screening, judge, improver, MCP, memory, copilot, tests), [code-patterns-platform](code-patterns-platform.md) (backend, single-run lock and heartbeat), [code-patterns-aws-agentcore](code-patterns-aws-agentcore.md) (Runtime entrypoint, invoking a Runtime); also [production-deployment-aws](production-deployment-aws.md)

## Sources

- `origin/week3day5-end:pyproject.toml`; `agent/` (`harness`, `work`, `tools`, `dispatcher`, `checkpoints`, `heartbeat`, `root_run`, `handler_answer`); `backend/main.py` (`pay_claim`); notebooks `labs/week2day3`, `week2day4`, `week3day4_lab1`; `labs/undercoverlab/app/agent/main.py`

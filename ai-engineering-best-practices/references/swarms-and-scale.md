# Swarms and scale

> When to read: load this when work arrives in batches (a morning's claims, a month's invoices, a ticket backlog) and the developer wants many agents working in parallel, or asks about concurrency, rate limits, retries, database connections, running one batch at a time, or running a whole batch in a serverless session.

## Contents

- [Key principles](#key-principles)
- [Team, swarm, fleet](#team-swarm-fleet)
- [When a swarm pays off](#when-a-swarm-pays-off)
- [The LLM-free dispatcher](#the-llm-free-dispatcher)
- [Each item keeps its own thread](#each-item-keeps-its-own-thread)
- [Limits outside the agent](#limits-outside-the-agent)
- [Retries that never repeat side effects](#retries-that-never-repeat-side-effects)
- [Scaling is not linear](#scaling-is-not-linear)
- [Start small and record cost and time per item](#start-small-and-record-cost-and-time-per-item)
- [One run at a time: a database lock and a heartbeat](#one-run-at-a-time-a-database-lock-and-a-heartbeat)
- [If the process restarts mid-dispatch](#if-the-process-restarts-mid-dispatch)
- [One AgentCore Runtime session for a whole dispatch](#one-agentcore-runtime-session-for-a-whole-dispatch)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover)

## Key principles

1. **Choose the next item with code, not a model.** A dispatcher that lists work and fans it out is a fixed rule. A model there adds cost and variance for nothing.
2. **One worker per item, one thread per item.** An item that waits days for a person must not hold up the others, and two people answering at once must not race on one checkpoint.
3. **The limits are outside the agents.** Model rate limits, database connections and the people who check the results cap throughput long before the agents do.
4. **Retry only what passes with time, and only where repeats are safe.** A retry must resume from saved progress and hit a backend that never decides or pays twice.
5. **Start with a small N and widen it while watching.** Scaling is not linear, and contention shows up only when you measure per-item time at each N.
6. **Record cost and active time for every item, with its run.** Without them a batch cannot be judged or budgeted.
7. **Keep one run at a time with a database lock and a heartbeat.** In-process guards break once more than one process can run.
8. **Keep no state in a session.** Anything a session must know to carry on lives in the database, so a new session can finish the work.

## Team, swarm, fleet

Three words for different shapes (names as taught in the course, Oct 2026):

| Term | Shape | Example in the course | Use when |
| --- | --- | --- | --- |
| Team | A few agents on one task | Claude Code's agent teams | The task needs different roles or checks. See [agent architecture](agent-architecture.md) |
| Swarm | Many agents, each doing one item of a batch, in parallel | Kimi Agent Swarm | Many independent items of the same kind |
| Fleet | Every agent a business runs | LangSmith Fleet | Governance, inventory and cost across agents |

This file is about swarms. A swarm is worth building when the items are independent and the same kind of work. Do not use one for a single sequential task.

## When a swarm pays off

- Time falls to about that of the slowest item, at the same cost per item. In the lab, 25 claims one at a time took over two minutes, 5 at once took about a fifth of that, and 25 at once took about as long as the slowest claim.
- Quality does not change with N. Accuracy moves from run to run by noise, and N does not change it.
- Cost per item stays about the same. Each item makes the same model calls at any N. A second run can cost slightly less because the provider's prompt cache already holds shared context.
- The limits are in the systems around the agents (below).

In the UnderCover brief a queue of 25 took over ten minutes one claim at a time, which is why the queue agent was replaced.

## The LLM-free dispatcher

A dispatcher is a LangGraph graph with no model. It lists the items, fans out one worker per item with `Send`, caps parallelism with `max_concurrency`, and collects results with a reducer.

```python
class Dispatch(TypedDict):
    claims: list[str]
    reports: Annotated[list[str], operator.add]    # reducer: parallel results are added together

def fan_out(state: Dispatch):                       # a conditional edge
    sends = [Send("work_claim", {"claim_id": c}) for c in state["claims"]]
    return sends or "finish_run"                    # nothing to do: go straight to the end

builder = StateGraph(Dispatch, context_schema=DispatchContext)
builder.add_node("list_claims", list_claims)
builder.add_node("work_claim", work_claim, retry_policy=RETRY)
builder.add_node("finish_run", finish_run)
builder.add_edge(START, "list_claims")
builder.add_conditional_edges("list_claims", fan_out, ["work_claim", "finish_run"])  # list targets so it draws
builder.add_edge("work_claim", "finish_run")        # runs once, after every worker
builder.add_edge("finish_run", END)
dispatcher = builder.compile()                      # no checkpointer: each item saves its own progress

dispatcher.invoke({"claims": [], "reports": []}, {"max_concurrency": n}, context=context)
```

- **`max_concurrency`** in the config caps the workers running at once. There are never more than N.
- **The reducer** is required because several workers return in the same step.
- **The node after the workers** runs once, after every worker has finished. Use it to finish the run or to score it.
- **State holds only small report lines.** The records live in the system of record, and the run's summary is built from those records, with no model writing it.
- **One seam to the item agent.** The dispatcher calls one function with the item ID and the run ID, which carries on an item in progress or starts a waiting one. Point that function at an agent in the cloud later without touching the dispatcher.
- **Build it in stages.** In the lab Part 1 uses a one-second stand-in with no model, tries caps of 1, 5 and 25, and simulates a 429. Prove the plumbing before spending tokens. LangGraph suits any workflow that needs parallel branches, retries and persisted state, whether or not a model is involved.
- **Choosing items:** the dashboard's dispatch works every item in progress, waiting or sent back, oldest submitted first, and skips one a resume is already working.

## Each item keeps its own thread

In the lab the whole swarm runs as one graph on one thread. That works because nobody waits on a person. In a product where items can pause for sign-off, keep a thread per item and let the dispatcher only start them. Never use a shared thread or a subgraph for the items. On one shared thread:

- one `interrupt()` pauses the whole dispatch;
- two sign-offs at once race to resume the same checkpoint;
- recovering from a crash means recovering the whole dispatch;
- the tracing tool gets one huge trace.

Give each item its own tracing session and tag every item's trace with the run's ID so a whole run can still be found together. See [durable state](durable-state-and-hitl.md) and [evals and observability](evals-and-observability.md).

## Limits outside the agent

| Limit | What happens | What to do |
| --- | --- | --- |
| Model rate limits | 429 responses or timeouts when N workers call at once | Keep N within the provider's limit. Retry with waits (next section) |
| Database connections | Free Supabase allows about 15 through the session pooler, across all processes (as taught, Oct 2026) | At most 4 connections per process. Workers share a pool and wait for a connection rather than fail |
| The people downstream | A swarm can produce more held approvals and referrals than people can review | Count sign-offs in capacity planning |
| Other systems the tools call | Same shape as the model limit | Cap N, and retry only what is safe |

- **Free models (as taught):** OpenRouter limits free models to about 20 requests a minute, which is why the free lab runs 3 at once. A paid account handled 25 at once in the course.
- **Connection arithmetic from the course:** the backend 4, the agent's service 4, plus 1 kept by Supabase's `pg_net` makes 9. An extra command-line agent run adds 4, making 13, so do not run one during a dispatch. During the live run, check that connections whose user is `postgres` in `pg_stat_activity` stay at 12 or fewer.
- **Waiting, not failing:** the pool and the backend's engine wait up to two minutes for a connection (the default of 30 seconds is too short for 25 workers). No claim should fail for want of a connection.
- **One saver per worker:** `PostgresSaver` holds a lock around every read and write, so one saver shared by 25 workers makes them take turns. Give each worker a saver of its own on the shared pool.
- **Runtime:** each session runs in a microVM with its own connections. Use Supabase's transaction pooler (port 6543), which lends a connection per transaction so many sessions share a few. Turn prepared statements off.

## Retries that never repeat side effects

A claim worker can fail in two ways, and the course layers the retries:

1. The model client retries one call (`ChatOpenAI(max_retries=5)`).
2. LangGraph's `RetryPolicy` retries the whole worker node, with growing waits.

```python
RETRY = RetryPolicy(max_attempts=3, initial_interval=10,
                    retry_on=(ModelRateLimitError, ModelTimeoutError))   # waits about 10 s, then 20 s

def work_claim(state, runtime):
    try:
        report = work_in_run(state["claim_id"], runtime.context.run_id)  # carries on from the last saved step
    except Exception as error:
        attempt = runtime.execution_info.node_attempt
        if isinstance(error, TRANSIENT) and attempt < RETRY.max_attempts:
            raise                                  # let the RetryPolicy wait and run the node again
        report = f"{state['claim_id']}  left for the next dispatch: {error}"
    return {"reports": [report]}
```

What happens to an item:

| Event | Outcome |
| --- | --- |
| Rate limit or timeout | Waits, then carries on from the last saved step as the same attempt |
| Still failing after the waits | Stays in progress for the next dispatch. The dispatch goes on |
| Any other error | The item goes back to the queue and the same dispatch tries it once more. A second failure leaves it for a handler (a person) |
| The agent finishes without a decision | Counts as a failure (the lab counted it as a referral) |
| One bad item | Never stops the dispatch |

Why retries are safe here:

- A retry resumes the item from its checkpoint instead of starting over, so it does not repeat model spend.
- The backend never decides or pays an item twice. A repeat of the same decision or payment returns the item, and a different one is refused. See [durable state](durable-state-and-hitl.md).
- Retry only the errors that pass with time. A blanket retry re-runs deterministic failures.

LangGraph caveat (version-specific; LangGraph 1.2.12 in the course's build, Oct 2026; verify on your version): a node's `error_handler` was meant to leave a failed item in progress, but with several workers fanned out by `Send` the dispatch still raised the handled error. It worked for one worker, so a test with one item passes and a real run fails. The build catches errors inside the worker instead, as above, and keeps a test with two workers that records the behaviour, so a fixed release is noticed. Test failure handling with at least two workers.

In tests, make the retry waits zero (copy the policy with `initial_interval=0` and `jitter=False`) so the suite does not sleep through the backoff but still sees three tries.

## Scaling is not linear

- In the course's runs, 25 at once was faster than 5 but not five times faster. The suspect was contention for Supabase's connections.
- The run takes about as long as its slowest item, so one slow item sets the clock.
- Per-item time can rise at higher N when workers wait for connections or the provider throttles.
- Check by comparing items worked from the start at your N against the same at N=3. If they are slower, find where the time goes while keeping to the connection limit.
- Treat one run as noisy. A run of 25 items cannot show a small gain, and a swarm does not change accuracy.

## Start small and record cost and time per item

- Default N is small (3 on the dashboard, range 1 to 25). Widen it while watching 429s, connection counts and per-item time. On free models stay at about 3.
- Record every model call: the tokens in and out and the cost the provider reports (OpenRouter's `usage.cost` on each reply, `response_metadata["token_usage"]["cost"]`), with the item, its thread and the run.
- Record each spell of active work on an item with a monotonic clock, saved however the spell ends. A pause for sign-off ends the spell, and the carry-on after the sign-off is a new spell, so waiting for a person is never counted.
- A run's totals are the rows with its ID, including failed attempts and retries. Work with no run, such as a resume after a sign-off, is recorded with no run.
- Measures for a batch: cost per item, time per item, slowest item and time for the whole run. See [models and cost](models-and-cost.md).
- Evaluations run copies of labelled items through the same dispatcher. A copy never pauses, because nobody can sign it off, and its saved progress is cleared when it ends. See [evals and observability](evals-and-observability.md).

## One run at a time: a database lock and a heartbeat

An in-process "one run at a time" flag fails once each session is its own process. On Runtime two dispatches can run in two sessions, and a service that marks all running work stopped when it starts would kill another session's work. Keep the rule in the database, owned by the app.

Starting work:

1. Take a lock: update a row in a locks table as the transaction's first write, so a second start waits for the first to commit and then sees its work. A missing row is an error (reseeding restores it).
2. Mark work the agent has gone quiet on as stopped, then commit, so the stop stays whatever happens next.
3. Take the lock again and refuse with a 409 that names what is running if another run, evaluation or improvement round is going.
4. Create the run and commit it before asking the agent. A request uses one database connection at a time, the course's rule for a small pool.
5. Ask the agent to work the run by its ID. If the agent did not take the work (the request never connected, an error came back, or it refused), undo the start and mark the run stopped with the reason.
6. If the call timed out or the answer was cut off, change nothing: the work may have started. The app makes one attempt with no retries, since a retried call could start the same work twice.

Heartbeat:

- The agent tells the app every minute while it works a run, on a thread of its own. A failed heartbeat is logged and never stops the work.
- Work the app has not heard from for five minutes counts as stopped (counted from the later of the start and the last heartbeat). The next start marks it stopped with the reason "The agent stopped answering" and goes ahead.
- A resume of one claim after a sign-off is not a piece of work in this sense. It runs beside a dispatch and never waits for one, and a dispatch skips a claim whose resume the app has heard from in the last five minutes.
- Pick the heartbeat interval well inside the timeout (60 seconds against five minutes tolerates several missed beats).

## If the process restarts mid-dispatch

- The dispatcher has no checkpoint. Each item saved its own progress on its own thread, so nothing of the items is lost.
- The run's row stays "running" until the heartbeat goes quiet for five minutes. In the course, new starts are refused for up to five minutes after a restart. Reseeding clears it sooner once the old work has stopped, but it also resets the queue.
- The next dispatch carries on the items left in progress from their last saved step, as the same attempt, and works the waiting ones. Decided items are not listed again, and the backend refuses any repeat if a step runs twice.
- Week 2's version had one service, which marked every running run stopped when it started. Week 3 removed that, because two Runtime sessions can run at once.
- The harness cannot tell a stopped item from one another process is working at this moment. That is why there is one run at a time, a flag for items being resumed, and an idempotent backend if both pick the same item.
- The lab's stretch is to give the dispatcher its own checkpointer and rerun it on the same thread after a restart. The product chose per-item threads instead.

## One AgentCore Runtime session for a whole dispatch

See [production deployment on AWS](production-deployment-aws.md) for Runtime itself. The scale-relevant points (as taught, Oct 2026):

- **One call, answered at once.** The app starts a dispatch with one call to Runtime in a new session. The agent replies at once and does the work on a thread of its own.
- **The session stays alive while work goes on.** The agent registers the work with the AgentCore app as an async task, so the health ping says busy until it ends. A session with no registered work ends after the idle timeout (60 seconds in the course). A session with registered work can stay up to 8 hours.
- **One process, one pool.** The dispatcher and up to 25 claim agents run in one session with one pool of 4 connections, the same code as on a laptop.
- **The dashboard polls the database,** every 2 seconds, not the session. Progress lives in Supabase.
- **Each piece is its own session.** A sign-off resume or a sent-back claim runs in a new session that loads the claim's thread from Supabase. A claim paused in session 1 can resume hours later in session 2.
- **Lazy start.** Do nothing at import. Runtime may start every session from one snapshot, so fetch secrets and open the pool on the first request.
- **Same app locally and in the cloud.** The agent runs on a laptop at port 8080 and on Runtime with the same payloads.

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
| --- | --- | --- |
| Swarm or one worker | A swarm needs independent items and tolerates limits; one worker is simpler | A swarm only for batches of independent items |
| N | Higher is faster, with more contention and 429s | Start at 3 and widen it to 5 then the cap while measuring. About 3 on free models |
| Thread per item or shared | Shared is simple but blocks on pauses and races on resume | A thread per item |
| Which errors to retry | All errors, or only transient ones | Rate limits and timeouts, with growing waits, three tries, resuming from the checkpoint |
| Where the one-at-a-time lock lives | Process memory or the database | The database, with a heartbeat and a five-minute quiet timeout |
| Where to run | A long-lived service or a Runtime session per dispatch | Runtime, one session per dispatch, state in Supabase |
| What to record | Totals only or per item | Tokens, cost and active time per item, with the run's ID |

## Pitfalls and anti-patterns

- A model choosing the next item.
- One shared thread, or a subgraph, for all items.
- One checkpointer saver shared by every worker.
- Unbounded N against a provider or database with a fixed limit.
- Retrying every error, or retrying without resuming from a checkpoint.
- Counting time spent waiting for a person as agent time.
- An in-memory single-run guard, or marking all running work stopped at startup.
- Testing failure handling with one worker.
- Reading one noisy run as a trend.
- Starting module-level connections or keys at import on Runtime.
- Letting the dispatch fail because one item failed.

## In UnderCover

- **Week 2 Day 4 build:** a dispatcher with no model replaced the queue agent. A handler starts a dispatch from the dashboard with N from 1 to 25 (default 3). Each claim keeps its own thread, retries only rate limits and timeouts, and a claim still failing is left in progress for the next dispatch. Cost and time are recorded per claim with the run, and a Scoreboard compares evaluations.
- **Week 3 Day 4 build:** the agent became an AgentCore app. The app keeps one run at a time with a database lock and a heartbeat every minute with a five-minute quiet timeout. On Runtime one session works a whole dispatch of up to 25 claim agents.
- **Limits:** 4 connections per process, 15 on the free plan, and no more than 12 `postgres` connections seen during a live run.

## Related

- [durable state and human in the loop](durable-state-and-hitl.md): per-item threads, idempotency, pausing and resuming.
- [code patterns: LangGraph](code-patterns-langgraph.md): snippets for the LLM-free dispatcher, fan-out, retries and concurrency cap.
- [production deployment on AWS](production-deployment-aws.md): Runtime sessions, idle timeouts, poolers and teardown.
- [models and cost](models-and-cost.md): cost per unit of work and free-model limits.
- [evals and observability](evals-and-observability.md): scoring runs, noise and tracing by run.
- [agent architecture](agent-architecture.md): teams versus swarms.

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Day 4), `AGENT_GUIDE_WEEK3.md` (Day 4)
- Notebooks: `labs/week2day4.ipynb`, `labs/week3day4_lab2.ipynb`
- Briefs: `labs/week2day4_product_SWARM.md`, `labs/week3day4_product_RUNTIME.md` (Step 4)
- Plans: `origin/week2day4-end:docs/PLAN_SWARM.md` (including "Where LangGraph falls short of the brief")
- Code: `origin/week3day5-end:agent/dispatcher.py`, `agent/heartbeat.py`, `agent/connection.py`, `agent/checkpoints.py`, `agent/work.py`, `backend/agent_work.py`, `backend/runs.py`, `backend/stops.py`
- Slides: W3D4 slides 78 to 80 (one session works a whole dispatch)

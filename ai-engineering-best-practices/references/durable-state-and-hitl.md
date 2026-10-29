# Durable state and human in the loop

> When to read: load this when a design has steps that wait for a person (approvals, reviews, corrections), runs that a crash, deploy or serverless timeout could interrupt, or actions that must never happen twice (payments, refunds, emails, tickets). Also load it when the developer asks how to "pause and resume" an agent or where an agent's state should live.

## Contents

- [Key principles](#key-principles)
- [Durable execution: when you need it](#durable-execution-when-you-need-it)
- [LangGraph concepts that matter](#langgraph-concepts-that-matter)
- [A Postgres checkpointer](#a-postgres-checkpointer)
- [Pausing and resuming](#pausing-and-resuming)
- [Never pay twice](#never-pay-twice)
- [Designing the human step](#designing-the-human-step)
- [Resuming in another process, session or machine](#resuming-in-another-process-session-or-machine)
- [Testing crash recovery](#testing-crash-recovery)
- [How the course's sign-off design changed](#how-the-courses-sign-off-design-changed)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover)

## Key principles

1. **Save state after every step, with one thread per work item.** A run that can stop partway and carry on turns "wait hours for a person" and "survive a restart" from failures into normal operation.
2. **Keep the state in a database, never in the process.** The next process, session or machine can only resume what it can load.
3. **Assume any node can run twice.** After a crash the node that was running starts again, and on resume the node that called `interrupt()` runs again from its top.
4. **Give every side effect its own node, guarded by an idempotency check on the item ID.** Durable execution does not by itself stop a step running twice. The check does.
5. **Put nothing with side effects before `interrupt()`.** That code runs again on resume.
6. **Rewinding is not undoing.** Going back to an earlier checkpoint rewinds the graph's state, not the world. Undoing a payment needs a compensating business action such as a refund.
7. **The system of record owns the limit; the graph only reacts to it.** The backend decides whether an approval needs sign-off and refuses a payment over the limit whatever the agent does.
8. **An approval over the limit is held for sign-off, not referred.** The agent made a decision, so it still counts as straight-through. A referral means the agent hands the whole claim to a person.
9. **Give the human two answers: sign off, or send back with a note.** A person who thinks the agent is wrong needs a way to say why and get a new decision.
10. **Read the human's answer from your own record, not from the resume request.** One source of truth, safe to retry, resumable from any process.
11. **Make the sign-off independent of the agent being up.** The resume call that follows is best-effort. The sign-off and the payment stand if it fails.
12. **Test recovery by killing the process mid-run.** Recovery that was never exercised does not exist.

## Durable execution: when you need it

Durable execution means a run can stop partway and carry on from where it got to.

Use it when any of these is true:

- A step waits on a person for hours or days (an approval, a review, a customer reply).
- The run is long or costly enough that restarting from scratch wastes money or time.
- The host can end the process: a deploy, a restart, Ctrl-C, or a serverless session that ends after an idle timeout.
- A failure after an irreversible step would otherwise leave the work half done.

Skip it when a run is short, has no waits and is safe to repeat. Durability adds a database, a thread model and a duty to make every side effect idempotent. A plain agent loop is simpler (see [agent architecture](agent-architecture.md)).

## LangGraph concepts that matter

The course uses LangGraph for durability. `create_agent` already returns a compiled LangGraph graph with a model node and a tools node. Write the graph by hand when you need nodes of your own, such as an approval pause or a payment.

| Concept | What it is | Design consequence |
| --- | --- | --- |
| State | A typed record the graph keeps for one work item | Keep ids, the decision, messages and counters. Put business records in the system of record. Keep counters such as model calls in state so a limit holds across a restart |
| Node | A function: state in, the parts it changes out | One job per node. A side effect gets its own node |
| Fixed edge | Always go to this node next | Straight-line steps |
| Conditional edge | A function that picks the next node from the state | Where routing rules live: no tool calls means decide, a decline ends, an approval over the limit goes to the pause |
| Reducer | How an update to a key is merged (`add_messages` appends, `operator.add` joins lists) | Required when several nodes write the same key in one step |
| Super-step | One round of the graph: every node scheduled for it runs, then their updates are applied | The unit that gets a checkpoint |
| Checkpoint | A snapshot of the state saved after each super-step | The resume point. A crash loses at most the step in progress |
| Thread | An id that groups one work item's checkpoints | One thread per work item |
| `interrupt()` and `Command(resume=...)` | Pause for a human and carry on with their answer | See [pausing and resuming](#pausing-and-resuming) |

A claim graph in outline:

```python
class ClaimState(TypedDict):
    messages: Annotated[list, add_messages]   # reducer: append, don't replace
    claim_id: str
    decision: str
    payout: float
    approved_by: str

builder = StateGraph(ClaimState)
builder.add_node("agent", agent)              # model call with tools bound
builder.add_node("tools", ToolNode(tools))
builder.add_node("decide", decide)            # structured decision
builder.add_node("approval", approval)        # the pause, and nothing else
builder.add_node("pay", pay)                  # the side effect, and nothing else
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", after_agent, ["tools", "decide"])
builder.add_edge("tools", "agent")
builder.add_conditional_edges("decide", after_decide, ["approval", "pay", END])
builder.add_edge("approval", "pay")
builder.add_edge("pay", END)
graph = builder.compile(checkpointer=checkpointer)
```

## A Postgres checkpointer

`PostgresSaver` saves the state in Postgres after every step. The course uses a free Supabase project (as taught, Oct 2026).

```python
connection = psycopg.connect(DATABASE_URL, autocommit=True, prepare_threshold=0,
                             row_factory=dict_row, options="-c search_path=lab")
checkpointer = PostgresSaver(connection)
checkpointer.setup()                          # creates its tables once; safe to repeat

config = {"configurable": {"thread_id": "CLM-1003"}}
graph.invoke(claim, config, durability="sync")
```

- **Connection settings:** LangGraph's docs ask for `autocommit=True`, `prepare_threshold=0` and `row_factory=dict_row`.
- **`durability="sync"`:** the course always passes it, so each step's checkpoint is saved before the next step starts. The default saves in the background, which risks losing the latest step on a crash (verify against your LangGraph version).
- **Schema:** keep your tables and the checkpointer's tables in a schema of their own and set `search_path` on the connection.
- **Poolers (as taught):** the session pooler (port 5432) works over IPv4 and supports prepared statements, so use it on a laptop or a long-lived process. The transaction pooler (port 6543) lends a connection per transaction and cannot keep prepared statements. In the course's test, 6 of 30 queries failed with `DuplicatePreparedStatement`. Use `prepare_threshold=None` when the process may run through either pooler.
- **Pool sizes:** the free plan allows 15 connections through the session pooler across all processes, so give each process a pool of at most 4. See [swarms and scale](swarms-and-scale.md).
- **Sync saver on Windows:** the course keeps the agent synchronous with the sync saver because async Postgres connections do not work with Windows' default event loop.
- **Thread ids:** the lab uses the claim ID. The product keeps a new UUID on the claim for each attempt. Carrying on from saved progress stays on the same thread and is not a new attempt. A claim that fails before it is decided goes back to the queue and starts afresh on a new thread.
- **Inspecting:** `graph.get_state(config)` gives `values`, `next` and `interrupts`. `graph.get_state_history(config)` lists the checkpoints, newest first. `checkpointer.delete_thread(id)` clears a thread. The `checkpoints` table has one row per step per thread.
- **Housekeeping:** a free Supabase project pauses after a week without use. Restore it from the dashboard. On a new project, seed once before the first run.

## Pausing and resuming

```python
def approval(state: ClaimState):
    """Wait for a handler. Nothing with a side effect goes before interrupt()."""
    answer = interrupt({"claim_id": state["claim_id"]})   # pauses; returns the answer on resume
    return {"approved_by": answer["handler"]}

result = graph.invoke(claim, config, durability="sync")
result["__interrupt__"]                       # the value passed to interrupt()
graph.get_state(config).next                  # the node that runs on resume
graph.invoke(Command(resume={"handler": "Dana Whitfield"}), config, durability="sync")
```

- `invoke` returns when the graph pauses. The state and the interrupt's value are saved. Nothing runs and no connection is held while the claim waits.
- On resume, LangGraph re-enters the interrupted node at its first line; this time `interrupt()` hands back the human's answer. In the course's lab the node's `print` fired twice, which is the lesson: anything above the interrupt executes again.
- **To ask "is this thread paused?" check `get_state(...).interrupts`.** `next` names the pause node as soon as the step before it is saved, before the pause has actually run.
- When a thread's next step is the pause and an answer is already on record, resume it with `Command(resume=answer)`. LangGraph keeps an answer given before the pause and returns it at once.
- Build the answer from your own record (who signed off, or who sent it back with which note). The resume request should name only the work item.

## Never pay twice

Failures that make a step run again, and what to do about each:

| Event | What happens | Your job |
| --- | --- | --- |
| Crash inside a node | After the last checkpoint, that node starts again on resume | Make the node idempotent |
| Resume after `interrupt()` | The pause node reruns from its top | Nothing with side effects before the interrupt |
| A retry (`RetryPolicy`, a repeated request) | The node or request runs again | The downstream system treats a repeat as done |
| Two processes pick up the same item | Both may run | One run at a time, plus the idempotent backend |
| Rewind to an earlier checkpoint | State goes back, the world does not | A compensating action, such as a refund |

Build it in layers:

1. **Own node for the side effect.** The payment is a node that does nothing else, so a restart repeats only the payment.
2. **Idempotency check on the item ID, in the system of record.** The lab makes the claim ID the primary key of a payments table and ignores a repeat:

   ```python
   cursor = connection.execute(
       "INSERT INTO payments (claim_id, amount, approved_by) VALUES (%s, %s, %s) "
       "ON CONFLICT (claim_id) DO NOTHING", (claim_id, amount, approved_by))
   already_paid = cursor.rowcount == 0
   ```

3. **A backend that treats a repeat as done.** In the product, repeating a decision or a payment already recorded returns the claim. A different decision on a decided claim, or a different amount on a paid one, is refused with a 409. A payment over the limit with no sign-off is refused with a 403 and records nothing. The agent never gets a payment tool of its own, because paying is a graph node.
4. **Decisions are final.** A second, different decision on a decided claim is refused, which also makes retries safe. The one way round it is a deliberate send back, which keeps the old decision on record and clears the current one.

What can still repeat: a progress step written to the audit trail between recording it and saving the checkpoint can appear twice after a restart. Make logging tolerate duplicates and say so in the design.

Rewinding: `get_state_history` lets you go back to an earlier checkpoint. That is a debugging and replay tool, not an undo. If a payment already happened, only a business action (a refund, a reversal) can undo it. Design that action as its own step with its own approval.

## Designing the human step

Ask five questions for each place a person enters the flow.

**When to ask.** Treat autonomy as a risk decision per action (see [governance](fde-lifecycle-and-governance.md)). Separate three outcomes:

| Outcome | Meaning | Counts as straight-through? |
| --- | --- | --- |
| Act | The agent decides and the system carries it out | Yes |
| Held for sign-off | The agent decided to approve, but the amount is over the limit, so a person authorises the payment | Yes |
| Refer | The agent cannot decide (a missing document, a story that contradicts the evidence, wording that does not settle it) and a person takes over | No |

- Put the limit in a setting, not the prompt, and have the backend answer "does this need sign-off?". The graph never compares the amount with the limit itself.
- Enforce the limit again where the action lands (a 403 from the payment operation, and later a gateway policy). If the agent's payment is refused by a gateway, the graph holds it for sign-off like any other. See [security](security-and-guardrails.md).
- Decision fatigue is a design constraint. If people are asked too often or for trivial items they approve everything, and the control is for show. Ask only where the human adds judgement or authority, and keep the number of asks small.

**What to show.** Everything the agent worked out: the decision, the amount, the reasoning and calculation, and the steps it took. In the product the interrupt carries only the claim ID, and the dashboard reads the claim from the system of record.

**What to record.** Who answered, when, and what. A sign-off stores the handler and the time on the decision and on the payment. A send back keeps the decision that was sent back with its note, who sent it back and when, so the claim page shows the history.

**Who may answer.** All handlers could sign off until Week 2 Day 5's build. From then only the senior handler can sign off over the limit (a 403 for anyone else). Check the approver's authority in the backend.

**What the answers do.**

| Answer | Who pays | The agent's part | Guards |
| --- | --- | --- | --- |
| Sign off | The app pays when it records the sign-off | None is needed. A short resume lets the graph finish (for example save the claim to memory) | Only while the claim is waiting for sign-off |
| Send back with a note | Nothing is paid | The graph forgets the earlier decision so nothing can pay it, resets the model-call allowance, adds the note as a message from the named senior handler, and the agent decides again. A new approval goes through the same checks: over the limit it waits again, within the limit it is paid. A claim can be sent back more than once | Note required (up to 1,000 characters). Sign-off and send back cannot both succeed. Only the first caller takes a sent-back claim |

Handle the note as a review, not a command. The message that carries it, written in code and not in the instructions so an improver cannot drop it, tells the model to check the note against the policy wording and refer the claim, with a reason, if the wording does not support what the note asks.

Slide example (W3D4): a $1,180 approval pauses; hours later a handler writes "the taxi receipt is in twice"; a new session loads the thread, reads the note, revises to $940 and pays, which is within the limit.

## Resuming in another process, session or machine

- Everything needed is in the database: the checkpoints on the thread and the app's record of the answer. A new process builds the same graph on the same checkpointer and invokes it on the same thread ID.
- The lab proves it in two ways: restart the notebook kernel with a claim paused, then `get_state` by thread ID and resume; or, as a stretch, resume from a second computer with the same `DATABASE_URL`.
- Week 3 Day 4's Lab 1 does it across AgentCore Runtime sessions. Session 1 pauses, is stopped, and a new session in a new microVM loads the thread from Supabase and resumes with the handler's note.
- Do nothing at import time that opens connections or fetches keys. On Runtime every session starts from one snapshot, so anything created at import is shared by all sessions. Get ready on the first request, once per process. See [production deployment](production-deployment-aws.md).
- Treat the resume call as a notification. The sign-off answers with the updated claim whatever happens to the call. If the agent cannot be reached, the app logs a warning and the sign-off and payment stand. The cost is that a claim the agent never resumed is not saved to memory, which the course lists as a known gap.
- A send back the agent never received is not lost: the next dispatch takes sent-back claims along with waiting ones and resumes a paused thread with the note.
- Graph changes while threads are paused: threads can wait for days, so keep node names and state fields stable for in-flight work (not covered in the course; verify).

## Testing crash recovery

- **Unit tests, no network:** run the graph on an in-memory saver with a stub model. Cover these cases:
  - the pause saves its place;
  - a sign-off resumes the item and pays exactly once;
  - an interrupted item continues on the same attempt with a single decision;
  - an error triggers a fresh start;
  - a duplicate decision or payment is treated as already done.

  A refused payment that pauses is a separate case.
- **Notebook:** restart the kernel with a claim paused and resume by thread ID. Call the pay step twice and check one payment.
- **Live:** kill the agent mid-run (every process on its port, such as the reloader and its worker), restart it, and check that the claim resumes on the same thread, the attempt count is unchanged and there is one decision. Check a paused claim shows as paid within seconds of the sign-off.
- **Look at the data:** open the checkpoints table in Supabase and read the thread's history.
- **Connections:** during a live run check `pg_stat_activity` stays under the plan's limit.

## How the course's sign-off design changed

The same $1,000 rule was built four ways. The changes show the trade-offs of who pays and who waits.

| When | Design | Why it changed |
| --- | --- | --- |
| W1D3 to W2D2 | The backend refuses the agent's payment over the limit. A handler's sign-off pays. The agent's work on the claim ends at the approval | Simplest. The agent never returns to the claim, a handler who disagrees cannot tell it why, and a crash loses the claim's work |
| W2D3 to W2D5 | The graph pauses with `interrupt()`. The sign-off is saved and the agent's service resumes the graph, which pays | The agent keeps everything it worked out, finishes the claim, and a restart carries on. The backend still blocks any payment over the limit |
| W3D2 to W3D3 | No pause: once an approval is held, the agent is finished with the item and the handler's sign-off makes the payment. As a second layer, the gateway policy blocks any agent payment above $1,000 | The agent stayed on a laptop while the app ran on Lambda, which could not reach it, and the sign-off must not depend on the agent being up |
| From W3D4 | The pause is back, with two answers: Sign off (the app makes the payment) or Send back with a note (the agent reconsiders) | The agent runs on Runtime, so a claim resumes in a new session from checkpoints. Sending back closes the feedback gap. The payment stays the app's |

The lesson: decide who performs the payment after approval. Having the system of record pay in the sign-off transaction removes the dependency on the agent. The graph's resume is then only for finishing work or deciding again.

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
| --- | --- | --- |
| Which actions need a person | Irreversible, high-value, or policy-mandated actions. Too many asks cause decision fatigue; too few risk loss | Ask only above a money or risk limit held in a setting, and enforce it in the backend |
| Held or referred | Held means the agent decided and a person authorises. Refer means a person decides | Hold approvals over the limit. Refer only when the agent cannot decide |
| Who pays after approval | The agent (after resume) or the app (in the sign-off) | The app pays. The agent's resume finishes the work |
| Person's answers | Approve only, or approve and send back | Both, with a required note on send back |
| Where state lives | In-process, a database, a managed service | A Postgres checkpointer. Session pooler on a laptop, transaction pooler for serverless |
| Thread granularity | Per run, per work item, per attempt | One thread per work item, a new one for a fresh attempt |
| Who may approve | Any handler, or a senior role | A named senior role, checked in the backend |

## Pitfalls and anti-patterns

- Side effects before `interrupt()`, or a payment inside the pause node.
- Believing durable execution means exactly-once. It does not.
- Treating `get_state_history` as an undo.
- Applying the limit in the graph and in the backend with different rules. Keep one source.
- Letting the agent pay after sign-off, so an unreachable agent leaves the claim stuck.
- Trusting the amount or answer in the resume request instead of reading your own record.
- Treating a handler's note as a command that skips the rules.
- Using `next` to decide whether a thread is paused.
- Prepared statements on the transaction pooler, or async Postgres on Windows.
- One saver shared by many concurrent workers (it takes a lock around every read and write). See [swarms and scale](swarms-and-scale.md).
- Passwords with special characters in the connection string. Letters and numbers are safest. Replace `[YOUR-PASSWORD]` including the brackets.
- Holding a connection or a process open while a person decides.

## In UnderCover

- A payout over $1,000 pauses the claim graph. The pause node does only `interrupt()`. The `pay` node pays through the backend, which refuses repeats and over-limit payments.
- Each claim has its own thread in Supabase's `undercover` schema, with at most 4 pooled connections per process.
- A sign-off pays and records the handler and time. A send back keeps the decision with its note, the agent decides again, and a $1,180 claim can come back as $940.
- A claim stopped partway carries on from its last step as the same attempt, with one decision.
- Tracing groups a claim's work before and after the pause in one session, named after the claim and thread.

## Related

- [swarms and scale](swarms-and-scale.md): per-claim threads in a dispatch, retries, locks and heartbeats.
- [code patterns: LangGraph](code-patterns-langgraph.md): snippets for the item graph, idempotent payment, Postgres checkpointer and resume.
- [agent architecture](agent-architecture.md): when to use a graph, business logic in code.
- [harness engineering](harness-engineering.md): middleware and failure handling the graph replaced.
- [security and guardrails](security-and-guardrails.md): the gateway policy that refuses over-limit payments.
- [production deployment on AWS](production-deployment-aws.md): sessions, snapshots and pooler choice on Runtime.
- [self-improvement](self-improvement.md): a human approving an improver's proposal, a different use of the pause.
- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): autonomy as a risk decision.

## Sources

- `guides/for_agents/AGENT_COURSE_GUIDE.md` ("The $1,000 limit", "Who can sign off")
- `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Day 3, including corrections), `AGENT_GUIDE_WEEK3.md` (Days 2 and 4)
- Notebooks: `labs/week2day3.ipynb`, `labs/week3day4_lab1.ipynb` (Parts 5 and 6)
- Briefs: `labs/week2day3_product_DURABLE.md`, `labs/week3day2_product_SECURE.md`, `labs/week3day4_product_RUNTIME.md`
- `origin/week2day3-end:docs/PLAN_DURABLE.md`
- `origin/week3day5-end:agent/harness.py`, `agent/checkpoints.py`, `agent/handler_answer.py`, `backend/sent_back.py`
- Slides: W3D4 slides 77, 78 and 80 (the pause in one session and resume in another)

# Harness engineering

> When to read this: you are designing or reviewing the code around a model in an agent product (its tools, instructions, subagents, middleware, failure handling, step recording or tests), or choosing between a ready-made harness and your own. For the choice of agent vs workflow and the frameworks in depth, read [agent architecture](agent-architecture.md) first.

## Contents

- [Key principles](#key-principles)
- [From prompts to harnesses](#from-prompts-to-harnesses): the seven parts, user vs builder
- [Build or buy](#build-or-buy)
- [Tool design](#tool-design)
- [Context management and subagents](#context-management-and-subagents)
- [Instructions](#instructions)
- [Middleware hooks](#middleware-hooks)
- [Failure handling](#failure-handling)
- [Observability inside the harness](#observability-inside-the-harness)
- [Testing a harness](#testing-a-harness)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover), [Related](#related), [Sources](#sources)

## Key principles

1. **Agent = Model + Harness.** The model supplies judgment; the harness supplies everything else: the loop, tools, context, state, limits, recording and recovery. Most production quality comes from the harness, so budget design time for it.
2. **Give the model a goal and tools; give code the rules that must always hold.** Anything that must always happen, or happen in a fixed order (a guardrail, a payment, a retry, a limit), belongs in code. A step-by-step prompt is a workflow written in the wrong language.
3. **Tools are the agent's interface to your system, and its permissions.** Tools call your system's API, never the database. The tool list is the list of things the agent can do. Name each tool after the operation it calls.
4. **Never put whole documents in the prompt when the agent can look things up.** Give a table of contents, a search tool and a read-one-section tool. It is cheaper, and the agent reads what it needs.
5. **Work each item in a fresh context.** A helper takes one item from a clean start and reports back in one line. The orchestrator stays small, cost does not climb with every item, and one item's content cannot colour the next.
6. **Put judgment in the model and arithmetic in code.** Let the model decide which lines are covered; let a deterministic tool apply the limits and the deductible.
7. **Return errors the model can act on, and let real failures fail loudly.** A refusal for a business rule goes back to the model as a tool message. A timeout or a bug stops the attempt, and the harness handles it in one place.
8. **Trust the record, not the model's report.** Build the one-line report, the item's state and every count from the system of record after the work, never from what the model says it did.
9. **Keep outcome states distinct.** A referral, an approval held for sign-off and a failure left for a handler (a person) are three different things for the customer, the handler and your metrics.
10. **Record every step, for people and for engineers.** The UI shows what the agent did and read; tracing shows cost and latency.
11. **A green test suite does not mean good harness code.** Tests use a stub model and prove behavior. A human or a fresh reviewer must still check structure, instructions and the framework's own idioms.

## From prompts to harnesses

Three levels, each containing the last (as taught in the course, Week 1 Day 5):

| Level | You decide | Typical failure when it is the only thing you do |
|---|---|---|
| Prompt engineering | The wording of one request | Works in a demo, drifts in production |
| Context engineering | What is in the model's window at each step: instructions, retrieved text, tool results, memory, history | Too much, too little or stale context; cost rises with every step |
| Harness engineering | Everything around the model that makes it an agent | The model is fine, but the system cannot recover, be audited or be trusted with real actions |

### The seven parts of a harness

| Part | What it means | Design guidance |
|---|---|---|
| Context | What the model sees: instructions, retrieved sections, tool results, memory | Keep it small and relevant. Load on demand with tools. Start each item fresh. |
| Workflow | Who decides the order of steps: the model or your code | The model chooses the path within a goal; code fixes the steps that must always happen. |
| State | What persists: to-do list, attempts, steps, decisions, checkpoints | Keep it in the system of record (the backend database), not in the agent's head. This makes runs restartable and visible. Pass ids in a context object, not through the model. See [durable state](durable-state-and-hitl.md). |
| Subagents | Helpers that work one item in a clean context | Use them for isolation and focus, not as an org chart. Give each only the tools it needs. It reports a short, structured result. |
| Permissions | What the agent may touch | Scope tools to the item, expose only needed tools, sandbox files, cap budget, require approval for risky actions. Enforce the real limits in the backend. See [security and guardrails](security-and-guardrails.md). |
| Observability | What you can see afterwards | Record each step for the UI and trace each call for engineers. See [evals and observability](evals-and-observability.md). |
| Self-improvement | Whether the harness's configuration can change safely | Keep instructions, model and settings as versioned data the agent reads at start. See [self-improvement](self-improvement.md). |

### Harness user and harness builder

An FDE (forward deployed engineer) plays both roles. With a coding agent such as Claude Code or Copilot you are a **harness user**: you write its instructions files, plans and review gates ([building with coding agents](building-with-coding-agents.md)). With the product's agent you are a **harness builder**, the focus of the course: you design the tools, loop, limits and recording yourself. The parts above exist in both, so reading how your coding agent's harness behaves (to-do list, subagents, permissions, hooks) is a fast way to design the one you ship.

## Build or buy

Build or buy is a spectrum, not a switch. Weighing it per customer is a core solutions-architect skill (course, Week 1 Day 5). Costs and versions below are as taught in the course (Oct 2026); re-check them.

| Option | What you get | Pick it when | Watch for |
|---|---|---|---|
| Direct model calls | One call or a fixed pipeline you control | The task is a single step or a fixed workflow | You build any loop, tools and recording yourself |
| `create_agent` (LangChain) | Loop, tools, structured state and a middleware system, on any model | The default for a product agent: you own tools, recording and rules, with little code | Fast-moving API; check the installed version's docs |
| Deep Agents (LangChain) | A ready-made harness on `create_agent`: file tools, a `task` subagent tool, a to-do list, summarising of long conversations; open source, any model | Exploring a file-shaped job quickly, or when you want a cheap model and to read exactly what the harness does | To-do list is an add-on (`TodoListMiddleware`, as taught for v0.7); step limit `recursion_limit` counts graph steps, not messages |
| Claude Agent SDK | Claude Code's harness as a library: file tools, task list, subagents, permission modes, budget cap | File-shaped jobs where Claude-only is acceptable | Claude models only; starts a Claude Code process per run; inside Jupyter on Windows it needs an event-loop workaround |
| Hand-written LangGraph | Your own state, nodes and edges | You need durable checkpoints, a pause for a human, a fixed order in code, branching or fan-out. See [agent architecture](agent-architecture.md) | More code to own; do it when a loop is no longer enough |
| Managed agent from a model lab | The lab hosts the agent and its own harness | You accept one lab's models and harness (hosting options: W3D1 slide 9) | Lock-in; less control over loop and recording |

In the two Week 1 Day 5 labs, the same five claims were given to a ready-made harness with no tools written for it: a folder of claim files, the wording and the manual, a subagent that decides one claim, a to-do list, and a handover note. The Claude Agent SDK run on Claude Sonnet 5.5 cost about 40 cents; Deep Agents on DeepSeek V4.1 Flash about 3 cents (as taught, Oct 2026). Ready-made harnesses give a capable agent in very little code, but the job's state is files in a folder. A product with a database, a dashboard, business rules and an audit trail needs tools that call your own API and a harness that records and recovers. That is why the product agent was built on `create_agent` and later hand-written LangGraph.

## Tool design

### Rules

1. **The agent never touches the database.** Each tool calls an operation of the system's API, so the backend's rules apply to the agent exactly as to any client. Keep all backend calls in one API module with the base URL written once.
2. **Name each tool after the backend operation it calls,** and test that the tool list is exactly the expected set. A reader can then map agent actions to API actions.
3. **One-line description, typed arguments, closed choices.** The docstring is the model's only manual. Use `Literal` or enums for choices (a decision kind, a document name), annotate units ("in US dollars, 0 for a decline"), and constrain strings (a search query must not be empty).
4. **Scope tools to the item.** Put the item's id, policy id and customer id in a context object (`context_schema` with `ToolRuntime`), and have tools read them from it. The model then cannot act on a different item, and one tool such as `get_claim` takes no arguments.
5. **Hand over only what is needed.** A helper agent gets the tools for its one job. In the labs, the claim helper could read and write files but could not start further subagents.
6. **Keep side effects deliberate.** An action that must always follow a decision (such as payment) is a code step, not a tool the model might skip or repeat. Ed's build began with a `pay_claim` tool and later moved payment into a graph node.
7. **Make the backend the referee.** The tool asks; the backend enforces (a recorded decision is final, a payment over the limit is held). Whatever the model does, the rule holds.

### Sketch: a scoped tool with an artifact for the UI

```python
@dataclass
class ItemContext:
    item_id: str       # set by the harness; the model never chooses it
    route: Route

Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

@tool(response_format="content_and_artifact")
def read_section(
    document: Literal["policy_wording", "claims_manual"],
    number: int,
    runtime: ToolRuntime[ItemContext],
) -> tuple[str, Step]:
    """Read one section of the policy wording or the claims manual in full."""
    section = api.read_section(document, number)   # raises a refusal for an unknown section
    return json.dumps(section), ("reading", f"{section['title']} (section {number})")
```

The first value goes to the model. The second (the artifact) never reaches the model; the harness records it as a "reading" step so the UI can show what the agent read.

### Long documents: search, then read sections

The pilot put the whole policy wording into every prompt. The harness build replaced that: the instructions end with only the **contents** (section numbers and titles), and two tools do the rest.

- `search_documents(query)` returns the sections whose title or text contains a word or phrase, with the matching paragraphs. Case-insensitive.
- `read_section(document, number)` returns one section in full; an unknown number is a refusal the model can read.

Why: cost and focus (the agent reads three sections, not forty pages), it scales when the manual grows, and the UI can show exactly what was read. Test that the contents hold titles but none of the section text. At enterprise scale this becomes the [context layer](context-layer-and-integrations.md); for retrieval patterns see [RAG, memory and MCP](rag-memory-and-mcp.md).

### Deterministic calculation tools

If the answer is a formula, give the agent a tool that applies it. The agent supplies judgment inputs (which lines are covered, whether a pair counts as one item, what others already paid); the tool applies the limits, deductible and maximum and returns the calculation. The decision record keeps that calculation, so a reviewer sees both. Rules live in the backend, so every client uses the same ones.

### Errors the model can act on, and refusals

| Kind | Example | What the harness does |
|---|---|---|
| Expected refusal (a business rule or invalid input) | Unknown section; a second decision on a decided claim; a cap reached | Return a message to the model as a tool result ("Refused: ..."), with enough detail to fix it. Example: "this run can work 5 items and has started A, B, C, D, E". |
| Unexpected failure | Provider outage, bug, timeout | Let it propagate. The attempt fails and the harness handles it in one place ([failure handling](#failure-handling)). |

Map expected errors to model-readable text in one function (`ToolException` raised inside tools, plus the API's refusal exception) and word it the same way everywhere. In Ed's build the hook for this was LangChain's tool-error middleware, later `ToolNode(handle_tool_errors=...)` in the hand-written graph (class names: verify against the installed version). Make refusals visible as their own step type so reviewers can see what the agent tried that was not allowed.

## Context management and subagents

**Fresh context per item.** The orchestrating agent hands each item to a helper through one tool (`work_item(id)`). The helper starts a new thread each attempt, with only its instructions and one message naming the item, runs to completion and returns one line: the result, or what went wrong. Test this: the helper's first prompt holds nothing from earlier items.

Why: a long run does not get more expensive step by step, each item gets the model's full attention, and an item's text (which may be untrusted) cannot leak into the next. A side benefit (our inference, not stated in the course) is a smaller reach for an injected instruction.

**Keep the orchestrator small.** Each item adds one report line and one to-do update, so even a run of 25 stays well within a model's window; Ed's plan did not need summarising middleware. The orchestrator never does the item's work itself.

**Build the report in code.** The helper's one-line report is built from the system of record after the work (for example `ITEM-1  approve  $420.00` or `ITEM-4  failed: 503, back in the queue`), not from the model's closing text. Include the state ("held for sign-off", "not paid yet") so the orchestrator cannot misreport.

**A to-do list the UI can show.** Give the orchestrator a `write_todos` tool that replaces the whole list each time (as LangChain's to-do middleware does) and store it in the backend, with a status per item: to do, in progress, done, left for a handler. The team watches it live, and it is how the agent keeps track of a long job. Cost of replacing the whole list: the agent must resend every item.

**Enforce the cap and completeness in the harness, not the prompt.**
- A `work_item` tool refuses new items beyond the run's cap and says so, naming the cap and the items started. Retrying an item already started does not count.
- When the orchestrator replies without calling a tool, the harness checks the record for items it missed within the cap, names them in a reminder and lets the agent continue, at most twice.
- At the start of a run, the harness puts back in the queue any item left in progress by a run that stopped.
- Run tool calls one at a time (`max_concurrency=1`) when order-sensitive rules such as a cap must hold.

**Does the orchestrator need to be a model?** In the pilot-to-harness build, a queue agent chose the claims and kept the to-do list. On Week 2 Day 4 Ed replaced it with a dispatcher in code, because "which claim goes next" was a fixed rule (oldest first) and code can also run many items at once. Default: use code to select and fan out work when the rule is fixed ([swarms and scale](swarms-and-scale.md)); use a model orchestrator when choosing, ordering or adapting the plan needs judgment, or while you are still learning what the work looks like.

## Instructions

Write what a capable new colleague needs, not a script.

| Section | Content |
|---|---|
| Role and goal | Who the agent is, and the outcome that counts (here: the decision a senior handler would agree with; accuracy matters more than speed) |
| What you have to go on | The records and tools it has, what each is for, and which source wins. Name tools in prose ("read each relevant section with `read_section`") |
| What holds whatever you do | Hard constraints and who owns the limits (optional, used for the improver) |
| What done looks like | The end state: one decision recorded with a reason; for an orchestrator, every item worked, the to-do list final, the last reply a short summary in a stated format |

Rules:

1. **Goals and constraints, not steps.** The human review of the harness build rejected instructions that were "long, step-by-step, prescriptive scripts": an agent needs a goal, otherwise you would just write code. Ed's plan had listed which sections to always read in which order; the review rejected that style, and the final claim instructions state what a good decision rests on and leave the path to the agent.
2. **If the order matters, it is not an instruction.** Move it into code, a hook or a tool's validation.
3. **Say what you do not do.** An orchestrator "never decides a claim itself". A helper's tools "work on that claim only".
4. **Put the contents, not the text, of long documents** at the end of the instructions (titles and numbers only).
5. **Keep instructions in their own files** (for example `instructions/claim.md`), served by the backend and shown on a read-only page. They are product configuration, reviewed like code, and the unit that gets versioned and improved ([self-improvement](self-improvement.md)).
6. **Never write instructions from the evaluation answer key.** Write them from the policy and manual; otherwise your eval measures memorised answers ([evals](evals-and-observability.md)).
7. **Keep them in step with the tools.** When a tool moves into code (payment), edit the instructions in the same change.

Before and after, with generic names:

```text
Script:  1. Call get_claim. 2. Call get_policy. 3. Read section 3. 4. If the claim is
         over $1,000 call... 5. Record the decision.
Goal:    Reach the decision a senior handler would agree with: approve with the right
         payout, decline, or refer. You have the claim, its policy and history, and
         tools to search and read the wording and manual. Done when you have recorded
         one decision with a plain-language reason for a colleague.
```

## Middleware hooks

LangChain's `create_agent` runs your code at fixed points of the agent's loop. A hook can update state, add messages or end the run.

| Hook | Runs | Typical use |
|---|---|---|
| `before_agent` | Once, before the model sees anything | Screen untrusted input; stop early |
| `before_model` | Before every model call | End early on an outside condition (the improver stops when its round is stopped) |
| `after_model` | After each model reply, before its tool calls run | Record the reply; check the tool calls the model asked for (an output guardrail) |
| `wrap_model_call` | Around the model call | Change a request (for example one tool call at a time) |
| `wrap_tool_call` | Around each tool run | Record the result or refusal; add an artifact step |

To end the run from a hook, declare `can_jump_to=["end"]` on the decorator and return `"jump_to": "end"` with a message. Course correction: Ed said `before_model` in the video for the Week 3 Day 2 guardrail, but the lab's hook is `before_agent`.

Built-in middleware used in the course builds (names as taught; verify against the installed version): a model call limit (a hard cap per run or thread, failing with an error), a tool-error handler, and `HumanInTheLoopMiddleware`.

### Guardrails as middleware

```python
@before_agent(can_jump_to=["end"])
def screen_input(state: AgentState, runtime: Runtime[ItemContext]):
    verdict = screener.invoke(screen_prompt(state))      # cheap model, structured output
    if verdict.instructions_found:
        return {"messages": [{"role": "assistant", "content": verdict.reason}],
                "jump_to": "end"}                        # nothing recorded: a handler decides
    return None
```

Lessons from the Week 3 Day 2 lab (details in [security and guardrails](security-and-guardrails.md)):
- A keyword list catches only the wording you thought of and fails once the instruction is reworded or translated. A cheap second model with structured output (reason first, then the boolean) catches both.
- Test a guardrail on positives and on false alarms. The lab ran the model check on 25 ordinary claims and expected zero flags; a check that refers ordinary items costs the team time.
- Screen what the model will actually read. In the product the first message only names the claim, so the check fetches the claim exactly as the claim agent's tool returns it and screens that.
- A flagged item ends in a referral with the check's reason, recorded as the check's decision, not as the agent's. An answer from the check that cannot be read is retried (three tries in all) and then fails the attempt, rather than passing the item.
- Guardrails are one layer. The backend's approval limit holds whatever a hidden instruction makes the model do, and no set of checks makes an agent bulletproof.
- An output check (`after_model`) that inspects the tool calls in the model's last message can stop an approval larger than the amount claimed. This was a Week 3 Day 2 assignment.

### Human in the loop

`HumanInTheLoopMiddleware` pauses before named tools run (`interrupt_on={tool_name: config}`), with allowed decisions such as approve or reject and an optional condition for when to pause. It needs a checkpointer, so a pause survives a restart (the course saves with `durability="sync"` on Postgres). Ed used it for the improver agent, where a handler approves each proposed change. For a flow in which an approval is only sometimes needed (a payout over a limit), the hand-written graph with `interrupt()` was clearer. See [durable state and human in the loop](durable-state-and-hitl.md).

### Middleware or graph nodes?

In the hand-written claim graph, nodes do what middleware did: a screening node first, a model node that counts calls, a tool node with error handling and a recording wrapper, a payment node, and a wait-for-handler node. Use middleware while a standard loop suffices. Move to a graph when you need a durable pause, branches or a fixed step order ([agent architecture](agent-architecture.md)).

## Failure handling

A long run meets timeouts, provider errors and bad items. One bad item must never stop the run or leave an item stuck "in progress".

1. **One place catches every exception per item,** the function that works an item. It never raises past the run.
2. **Check the record afterwards.** If the item is still in progress and has no decision, mark it failed with a reason. If the error came after a decision was recorded, keep the decision, log a warning and do not retry. "Finished without a decision" counts as a failure.
3. **Retry through the queue, once.** A failed attempt puts the item back in the queue; a second failure leaves it for a handler (a person). The attempt count and the limit (two, a named constant) live in the backend.
4. **Never decide or pay twice.** The backend treats a repeat of a recorded decision or payment as already done, and refuses a different decision on a decided item. Retries are only safe because the system of record is idempotent.
5. **Absorb transient errors below the item.** The model client has a timeout (120 s) and retries (5) that deal with most provider errors. In the durable build a rate limit or timeout is not counted as the item's failure: the item stays in progress with its progress saved, and a retry policy waits and carries on ([swarms and scale](swarms-and-scale.md)).
6. **Cap runaway loops** with a model-call limit per item (30 in Ed's build) and a limit on the orchestrator scaled to the run's cap. An agent that goes round in circles then fails instead of burning money.
7. **Recover at start.** A new run first fixes items left in progress by a run that died.

```python
def work_item(item_id: str, agent) -> str:
    api.start_item(item_id)                      # the backend counts the attempt
    error = None
    try:
        agent.invoke(first_message(item_id), context=ItemContext(item_id))
    except Exception as e:                       # the one place that catches everything
        error = describe(e)
    item = api.get_item(item_id)                 # the record is the truth
    if item["status"] == "in_progress" and item["decision"] is None:
        item = api.fail_item(item_id, error or "finished without a decision")
    return report(item)                          # one line, built from the record
```

### Keep outcome states apart

| Outcome | What happened | Who acts | Counted as |
|---|---|---|---|
| Referral (a decision) | The agent could not decide, or the guardrail flagged the item | A handler, with the agent's reason | A valid decision, scored in evals |
| Held for sign-off | An approval over the limit, waiting for sign-off | An authorised person signs off | Agent success plus a human step; still straight-through |
| Left for a handler | The agent failed twice and produced no decision | A handler (a person) works it by hand | A reliability failure to fix |
| Waiting | In the queue, including back after a first failed attempt | The harness retries | Not an outcome yet |

Merging these hides how often the agent fails, how often it is cautious and how much human sign-off work you create. Give each its own state and label in the UI.

## Observability inside the harness

- **Record every step on the item,** for the UI: the model's message, each tool call with its arguments, each tool result, each refusal, each section read or lookup, the guardrail's verdict, each failed attempt with its reason, and any memory save. A handler can then see why the agent decided what it did. Do it in `after_model` (messages and tool calls) and `wrap_tool_call` (results, refusals, artifact steps), not by re-parsing streamed output.
- **Use tool artifacts** for what the UI should show but the model need not see, such as which sections were read and where they came from.
- **Record cost and time per item:** the tokens and dollar cost of each model call and the working time of each spell, so cost per unit of work is known.
- **Trace in a tool such as Langfuse** with a session id per item and tags for the run, so one item's whole thread appears together. See [evals and observability](evals-and-observability.md).
- Keep the UI's record (product data) and the trace (engineering data) separate, and do not rely on either for correctness. Correctness comes from the system of record.

## Testing a harness

1. **Tests never call a real model.** Use a stub chat model that replays a script of replies: text, tool calls or an exception, and that keeps the prompts it was sent. In Ed's build it subclasses LangChain's fake chat model, returns itself from `bind_tools` and raises when a scripted reply is an exception.
2. **Test behavior the harness adds,** one scripted scenario each:
   - within the limit, the item is decided and paid; over the limit it is held with no payment;
   - the provider fails on the second call: back in the queue with the error as the last step;
   - the same failure twice: left for a handler;
   - the model finishes without a decision: counted as a failure;
   - the model loops: stopped at the call limit;
   - an error after a decision: decision kept, not retried;
   - a refused call (unknown section) goes back as a refusal and records no reading step;
   - a clean start: each item's first prompt holds only the instructions and the one message;
   - the cap, retry of a failed item, missed-item reminder and recovery at start;
   - the tool list is exactly the expected set, each named after a backend operation.
3. **Check the graph's shape** for a hand-written graph: its nodes and edges are an asserted set.
4. **Keep model quality out of unit tests.** Accuracy is measured by evals on a labelled set ([evals and observability](evals-and-observability.md)). Live runs are few, capped (five items) and run on freshly seeded data.
5. **Passing tests is not enough.** The harness build passed every test, yet Ed's human review found 20+ hard-coded URL strings in three modules, two ways of calling the backend, one module importing another's internals, the harness spread across files and mixed with domain code, an unwieldy `run_queue`, hand-rolled state passing where LangChain's `context_schema` with `ToolRuntime` exists, and two prescriptive instructions. A refactor followed: one API module with the base URL once, tools in one file, the harness in one module, goal-style instructions. The process gained a rule: every change is reviewed by a **fresh subagent that did not write the code**, given the code standards and the diff, acting as a strict senior engineer who decides whether to merge. Check the framework's own idioms before hand-rolling anything. See [building with coding agents](building-with-coding-agents.md).

## Decisions to make with the developer

| Question | Options | Sensible default |
|---|---|---|
| Build or buy the harness? | Direct calls; `create_agent`; a ready-made harness; hand-written graph | Start on `create_agent` with middleware; use a ready-made harness to explore; move to a graph only when you need a durable pause, fixed order or fan-out |
| Who orchestrates a batch? | A model agent with a to-do list, or a code dispatcher | Code if the selection rule is fixed; a model only when choosing needs judgment |
| What is code and what is the model's choice? | Prompt-scripted steps vs goal plus code rules | Goal and tools to the model; guardrails, payment, retries, limits and ordering in code |
| How do long documents reach the agent? | In the prompt; search plus read-section tools; a context layer | Contents in the prompt, search plus read tools; a context layer when several systems own the data |
| What is the failure policy? | Retries, attempts, who is told | One retry via the queue, then left for a handler; distinct outcome states; idempotent backend |
| Which guardrails run where? | Keywords, a model check, output checks, gateway policy | A cheap model check before the agent for untrusted text, failing to a human, plus backend limits that hold regardless |
| How are instructions stored and changed? | In code; in files served by the backend; versioned configuration | Files served by the backend, shown read-only, versioned when you add an improver |

## Pitfalls and anti-patterns

- Scripts as instructions; the same logic then lives in prompts and in code and drifts.
- Tools that take ids the model should not choose (claim id, customer id); use the context object.
- Hard-coded URLs, several ways to call the backend, and harness code mixed with domain code and spread over modules.
- Whole documents in every prompt; every item's history carried by the orchestrator.
- Believing the model's report instead of reading the record; catching exceptions in many places; retrying after a decision was recorded.
- Collapsing referral, held-for-sign-off and left-for-a-handler states into one "needs a human" state.
- A keyword guardrail with no false-alarm test; relying on guardrails instead of backend limits.
- Parallel tool calls racing on a cap or on two decisions in one reply; set one tool call at a time when order matters.
- Instructions written from the eval answer key.
- Hand-rolling what the framework provides; reviewing only that tests pass.
- Ready-made harness surprises: Claude-only models and a process per run for the Claude Agent SDK; `recursion_limit` is a step limit, not a message count.

## In UnderCover

- **Week 1 Day 5 build (HARNESS).** The pilot's code fed one claim at a time with the whole wording. The harness build gave a queue agent three tools (`list_claims`, `write_todos`, `work_claim`) and a claim agent seven tools named after backend operations (including `search_documents` and `read_section` over the wording and claims manual). Each claim ran in a fresh thread; `work_claim` caught all failures and returned a one-line report built from the backend's record; a failed claim went back once, a second failure was `left_for_handler`; a run could be capped (`uv run -m agent --cap 5`); the to-do list was stored in the backend and shown on the dashboard; middleware recorded steps, capped model calls at 30 and turned refusals into messages; the model client had a 120 s timeout and 5 retries. Default model: DeepSeek V4.1 Flash at low reasoning effort (as taught, Oct 2026).
- **Human review.** Messy modules and prescriptive instructions led to the refactor and the fresh-subagent review step above.
- **Later builds.** The claim agent became a hand-written LangGraph graph (Week 2 Day 3) where nodes took over from middleware and payment became a node; a code dispatcher replaced the queue agent and its to-do list (Week 2 Day 4); a screening node became the first step (Week 3 Day 2) with the Lab 1 model check; the lookups moved to the context layer (Week 3 Day 3).
- **Final instructions style.** `backend/instructions/claim.md` has a goal ("the decision a senior handler would agree with"), what the agent has to go on (records, context layer tools, memory), and what done looks like (one decision recorded; payment is the system's job). No numbered steps. See [the case study](undercover-case-study.md).

## Related

- [agent-architecture.md](agent-architecture.md): agent or workflow, frameworks, graphs, business logic in code
- [security-and-guardrails.md](security-and-guardrails.md): risks, prompt injection, guardrail layers, gateways
- [self-improvement.md](self-improvement.md): versioned instructions and the improver loop
- [durable-state-and-hitl.md](durable-state-and-hitl.md): checkpoints, interrupts, idempotency
- [evals-and-observability.md](evals-and-observability.md): evals, tracing, cost
- [swarms-and-scale.md](swarms-and-scale.md): dispatcher, retries, rate limits
- [building-with-coding-agents.md](building-with-coding-agents.md): reviews and quality gates
- [code-patterns-agents.md](code-patterns-agents.md): fuller snippets
- [code-patterns-langgraph.md](code-patterns-langgraph.md): the item graph with a model-call cap, retries and the dispatcher

## Sources

- Week 1 Day 5 (Harness Engineering): `guides/for_agents/AGENT_GUIDE_WEEK1.md` (slides, watch-outs, corrections), `labs/week1day5_product_HARNESS.md`, notebooks `week1day5_lab1`, `week1day5_lab2`.
- `origin/week1day5-end:docs/PLAN_HARNESS.md`, `docs/HUMAN_REVIEW_HARNESS.md`, `docs/PROCESS.md`, `agent/harness.py`, `agent/tools.py`, `backend/instructions/queue.md`, `agent/tests/stub_model.py`.
- Week 3 Day 2 Lab 1 (`week3day2_lab1`), `guides/for_agents/AGENT_GUIDE_WEEK3.md` (correction: `before_agent`), W3D2 slide 38; W3D1 slide 9.
- `origin/week3day5-end:agent/harness.py`, `agent/work.py`, `agent/tools.py`, `agent/context_tools.py`, `agent/screening.py`, `agent/refusals.py`, `agent/improver.py`, `agent/tests/test_claim_agent.py`, `backend/instructions/claim.md`, `docs/CODE_STANDARDS.md`.
- `labs/week2day3_product_DURABLE.md`, `labs/week2day4_product_SWARM.md`, `labs/week2day5_product_IMPROVE.md` (for the graph, dispatcher and `HumanInTheLoopMiddleware`).

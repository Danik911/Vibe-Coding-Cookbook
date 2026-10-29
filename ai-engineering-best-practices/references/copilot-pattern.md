# Copilot pattern: an agent that works beside the user, as the user

> When to read this: the developer wants a chat or assistant inside their product (a sidebar, a panel, a Slack bot) that looks things up and does work for a signed-in user; or the project already has an autonomous back-office agent and users now want to talk to it; or you are writing the capstone-style brief for a production agentic solution (decisions within limits, human sign-off, checkpoints, context layer, memory, runtime, success measured first).

## Contents

- Key principles
- What a copilot is, and when to add one
- Architecture at a glance
- Identity and permissions
- Durable conversations and the confirmation pause
- Its own runtime, a session per conversation
- Memory per user
- Tool design
- Showing the work (UX)
- Building and accepting it
- The capstone blueprint
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover
- Related, Sources

## Key principles

1. **Act as the user, never as the back-office agent.** Pass the user's own sign-in through every call. The back-office agent's API key must not exist in the copilot at all. Why: the copilot then can do exactly what the user can, the audit trail names the person, and a prompt-injected copilot cannot exceed the user's rights.
2. **Check permissions in code before asking the user to confirm.** A user who may not do something never sees a confirmation card for it, and the backend still enforces the rule. Why: the model must not be the thing standing between a user and a forbidden action.
3. **Confirm consequential actions, and only those.** Pause with a saved interrupt before money moves or something irreversible happens; do reads and starts of work immediately. Why: constant confirmations train users to click through, and one meaningful pause keeps the control real.
4. **Make conversations durable.** Checkpoint every step in a database, one thread per conversation, so a user can answer a card after a reload or next week and nothing is redone. Why: copilots outlive a process, a browser tab and a runtime session.
5. **Compute facts in code; let the model write the prose around them.** Waiting, counts, success-criteria figures, "what needs a human" and confirmation-card contents come from code or records, not from the model. Why: figures the model writes can be wrong, and the user will act on them.
6. **Wait for long work in code.** A tool that polls the job every few seconds with a timeout beats a model that polls by calling itself. Why: no model cost while waiting, and no loop that never ends.
7. **Show every step as it happens.** Each tool call is a visible card with its state, inputs and result. Why: transparency is what lets a user trust a copilot that can pay claims.
8. **Key memory to the user, taken from the verified sign-in.** One namespace per user, filled with the user's messages and the copilot's answers only. Why: one user's notes must never reach another, and a name the model or message supplies cannot be trusted.
9. **Give the copilot its own runtime, with a session per conversation and fewer secrets.** It holds the credentials it needs and no more. Why: separate failure, scaling and least privilege from the back-office agent.
10. **Plan with a second model's review, then accept with a scripted conversation.** Have another model review the plan before building, and finish with a handover conversation run as the real user. Why: the review catches design holes cheaply, and the conversation proves the product end to end.
11. **Measure success as agreed before building.** Express success as a few criteria (throughput, quality, a safety invariant), have the copilot able to check them, and show the evidence at handover. Why: that is the difference between a demo and a delivered solution.

## What a copilot is, and when to add one

A copilot is an agent that works alongside a user inside the user's interface, takes requests in plain language, looks things up, and (when asked) does work for them with the user's own permissions. It is conversational and user-driven. The autonomous back-office agent, by contrast, works a queue by itself under a service credential.

| | Back-office agent | Copilot |
|---|---|---|
| Trigger | A queue, a schedule, a dispatcher | A user's message in the UI |
| Identity | Its own API key or service role | The signed-in user's token |
| Output | A decision recorded in the system | An answer, or an action the user asked for |
| Human role | Signs off above a limit, sends back | Directs it, confirms consequential actions |
| State | One run or claim per thread | One conversation per thread |
| Memory | About the subject of the work (a customer) | About the user (their preferences and facts) |
| Runs | One session per dispatch | One session per conversation |

Add a copilot when:

- The back-office agent and a real API with user authentication already exist, and the copilot can reuse the API and the agent's tools.
- Users spend their day on multi-page lookups and clicks, and their questions cross records and business rules ("what needs me today", "why did the agent decide this", "are we meeting the targets").
- Users want to delegate bulk actions (start the batch, send back, sign off) and want the outcome explained.

Do not add one when there is no per-user identity to act with, no stable API, or no clear set of user jobs. Start with two or three jobs, not a general assistant. Say clearly what it will not do yet and tell the user where in the existing UI to do it (in UnderCover: changing settings, the agent's configuration and improvement rounds).

## Architecture at a glance

```text
Browser sidebar --(user's token)--> App backend --(token, in payload)--> Copilot runtime
   ^  polls steps ~1/s                |  records conversations,           |  LangGraph loop, checkpoints in DB
   |                                  |  turns, step cards                |  tools call the backend AS the user
   +----------------------------------+<----(cards, answer, pause)-------+  context layer via gateway (read-only tools)
                                                                          +  memory store (per-user namespace)
```

- **The backend owns the product's records**: conversations, turns, step cards, and the state of each turn. The copilot reports each step to the backend as it takes it, and the UI reads from the backend, not from the copilot.
- **The copilot is a hand-written agent loop**, not an agent factory. UnderCover's graph shape (as taught in the course, Oct 2026):

```text
START -> begin -> recall -> agent <--> tools
                              |         \--(criteria checked)--> report_criteria -> remember -> END
                              +--(sign-off asked)--> check_sign_off --(refused)--> agent
                              |                          \--(allowed)--> confirm [interrupt]
                              |                                 +--(sign off)--> sign_off -> agent
                              |                                 \--(cancel)--> cancelled -> remember -> END
                              +--(plain answer)--> remember -> END
```

  Nodes in code (begin, recall, check, confirm, sign_off, cancelled, remember, report_criteria) do what must always happen. Only `agent` is the model. See [harness engineering](harness-engineering.md) for the loop, tools and middleware, and [agent architecture](agent-architecture.md) for why business rules live in code.
- A turn is capped at 25 model calls. Parallel tool calls are off and the graph runs tools one at a time, so an interrupt is never mixed with other tool calls.

## Identity and permissions

- **The token travels, and is never stored.** The dashboard sends the user's access token to the backend; the backend passes it to the copilot in the request payload; the copilot puts it in the graph's runtime context (LangGraph `context_schema`, read in tools through `ToolRuntime`) and in each outgoing `Authorization` header. It must not enter the graph config or state, because LangGraph saves those with every checkpoint. Mark the field so it is left out of `repr`.
- **Never in logs either.** Cloud SDK debug logging can include the whole request payload, which here holds the token. Keep the SDK logger at INFO or above even when the app logs at DEBUG, and test it with the real client and a fake token, stubbing only the network send.
- **Refresh before sending.** Supabase sign-ins last an hour. The dashboard renews the token when it has under 20 minutes left, before sending a message or an answer to a confirmation. A 15-minute wait then fits; two long waits in one turn may not (a known gap in the course build).
- **Ask the backend who is signed in at the start of every turn and every answer.** If the backend rejects the token, end there, before any model call. Use the returned user id (not a name from the model or message) as the actor for memory, and the returned role and permissions in the instructions.
- **The backend refuses the agent's key on user routes.** Any request carrying the agent's key is treated as the agent's, whatever else it carries. This closes the route by which a copilot might borrow the agent's powers.
- **The copilot's own client has no function for the agent's key and none for the answer keys** (here, the handlers' decisions on the labeled sets). Make the allowed surface the only surface.
- **Per-user permissions still apply.** Only a senior reviewer may sign off over the limit. The copilot knows this from the identity, declines for others with the reason, and the backend checks again. Test it with a second, junior user: the request is declined and nothing is paid.
- **Ownership.** A conversation belongs to the user who started it; another user gets a 404, for every conversation and turn route.
- **Gateway caution.** The gateway's app target carries the agent's API key, so tools reached through it act as the agent. The copilot uses only the gateway's context-layer tools and calls the backend directly with the user's token. On the runtime, restrict its role (and ideally the gateway policy) to those tools. See [security and guardrails](security-and-guardrails.md).

```python
@dataclass
class CopilotContext:           # passed at run time, never checkpointed
    sign_in: str = field(repr=False)
    user: dict                  # as the backend returned it for this token
    conversation_id: str
    turn_id: str
    route: Route                # gateway or direct route for read-only context tools
```

## Durable conversations and the confirmation pause

- **A thread per conversation.** The thread id is the conversation id; save after every step (`durability="sync"`). Pick up any conversation later, after a restart, across runtime sessions. See [durable state and HITL](durable-state-and-hitl.md) for checkpointers, idempotency and human steps.
- **The pause is its own node.** `interrupt()` re-runs the node from the top on resume, so the confirm node holds only the interrupt, and everything before it is saved and not redone. Resume with `Command(resume=...)`.
- **Order of a sign-off**: the model asks (a schema it can request, not a tool that pays) -> code checks the user may, the item is in the right state and it is not a copy -> the node pauses -> the app shows a card -> the user answers -> code signs off with the user's token or cancels. No tool in the model's hands pays.
- **The card is filled from records**, never from what the model wrote: the item, the person, the amount, the reason.
- **One confirmation per turn.** A second request in the same turn is refused ("ask me again for the next one"). This avoids stacked pauses.
- **Bind answers to the card shown.** The answer carries the turn id; the backend refuses a stale tab or a double answer (409). Cancel is always accepted. Sign off is re-checked against the item as it stood when the card was shown: if the held decision changed, the answer is taken as a Cancel with a plain line ("the claim changed since the card was shown, so I canceled this sign-off without making a payment").
- **A cancel ends the turn with a line written in code** and no model call, then asks what the user wants instead.
- **While a confirmation waits**, the backend refuses new messages ("Answer the confirmation first") and the message box says so.
- **Backend turn states**: working, waiting for confirmation, done, failed, plus a computed `stopped` (working for over 20 minutes since start or since the answer). A waiting turn is never stopped. One turn at a time per conversation, using a conditional update on a turn counter, so of two simultaneous messages one is refused. A stopped turn refuses late updates so it cannot flip back.
- **A new turn closes dangling tool calls** a stopped turn left open ("this step stopped before it finished"), so the model never sees a call without an answer.
- **Idempotent resume.** If the sign-off node runs again after a restart, an item already signed off by this user counts as done.

## Its own runtime, a session per conversation

(As taught in the course, Oct 2026; see [production deployment on AWS](production-deployment-aws.md) for the runtime, CLI and teardown.)

- **A second runtime beside the agent's** in the same AgentCore project, deployed with the same single `agentcore deploy`, from one package built the same way. Locally it listens on its own port (8081) bound to 127.0.0.1 and asks for no key, because every call it makes carries the user's token and the backend checks it. On the runtime it serves on 8080.
- **The same shape as the claim agent's app**: one entrypoint, each payload names its operation (`health`, `take_turn`, `answer_confirmation`), nothing happens at import (runtime V2 starts each session from one snapshot taken after import), it gets ready on the first request (fetches its credentials from the identity service, opens the checkpoint pool), and it answers at once while the turn continues as an async task, so the session stays alive as long as the turn. Payloads are validated as a strict union; an error names the input, never its value.
- **Fewer credentials than the agent.** The copilot fetches its model key and database URL, and not the agent's API key. Its role may call the gateway and use its own memory, nothing else.
- **A session per conversation.** The backend sends each turn with the conversation id as the runtime session id (33 to 100 characters, letters, digits and hyphens; `conversation-` plus a UUID is 49). A turn soon after the last goes to the same session; after the idle timeout (60 seconds in the course's configuration, as taught Oct 2026) a new session starts under the same id and picks the conversation up from its checkpoints.
- **The backend is the only caller of the runtime**, in one module that owns the endpoint and settings. Retry a "conflict" reply (session starting or stopping; the call has not reached the agent) a few times with growing waits, inside a total budget that fits the caller's own limit (25 seconds inside Lambda's 30). Separate "known not to have started" from "may have started" and give the user a different message for each.

## Memory per user

(Details in [RAG, memory and MCP](rag-memory-and-mcp.md).)

- **A memory of its own**, apart from the back-office agent's. The agent's strategies file notes under customers; the copilot needs handlers. UnderCover's copilot memory has a user-preference strategy (`/handlers/{actorId}/preferences/`) and a semantic strategy (`/handlers/{actorId}/facts/`). The actor is the user's id from the verified sign-in; the session is the conversation.
- **Organised by who the notes are about.** The claim agent's memory is by customer; the copilot's is by handler. (Correction recorded in the week guide.)
- **Recall at the start of a turn, as a visible card**, with what it found, then feed it into the instructions for that turn only.
- **Save after the turn: the user's message and the answer, nothing else.** No tool calls, no tool results, never the sign-in. The platform converts events into notes in roughly a minute and a half, so a preference appears in the next conversation, not the same turn.
- **Optional by configuration.** On only when its setting is present; an unreachable memory is logged and the turn still answers.
- **Create the memory in the deployment notebook or IaC, not in application code.** Test that another user's namespace is never used.

## Tool design

| Kind | Tools (UnderCover) | Notes |
|---|---|---|
| Records | list claims, get claim, list steps | Reads through the backend API with the user's token |
| Customers and policies | find customers, get customer, get policy | Omit personal contact data the task does not need |
| Context layer | seven lookups: terms, field meanings, plans, rules, reference data, wording, manual sections | Same lookups as the agent; each answer names its file and owner; see [context layer](context-layer-and-integrations.md) |
| Work | latest dispatch, evaluations, settings, wait for run | The scoreboard and the run state |
| Actions | start dispatch, start evaluation, send back, check success criteria | Each is a distinct card; the backend enforces its own rules |
| Sign-off | a schema, not a tool | The graph checks, pauses and signs off |

- **Reuse the backend's reads for the dashboard** and add what is missing following the same API rules. The copilot should have no second path to the data.
- **Starting work returns the run it started**, and waiting uses that run's id, so the copilot never waits on the wrong one. If the backend refuses to start (a dispatch already running), pass on the reason.
- **Waiting in code.** Read the run every 5 seconds with the user's token, no model calls, stop after 15 minutes and say where to follow it. Sketch:

```python
def wait_for(token, run_id, poll=5, limit=900):
    deadline = time.monotonic() + limit
    while (run := api.get_run(token, run_id))["status"] == "running":
        if time.monotonic() + poll > deadline:
            break
        time.sleep(poll)
    return run
```

- **"What needs a human" computed in code** from the queue: payouts held for sign-off, claims referred, claims left for a handler, claims sent back and not yet taken up. The tool and the wait's result share one function.
- **Success criteria checked in code.** One tool starts an evaluation of the whole held-out set, waits, reads the evaluation's measures and a backend count (payouts over the limit and how many carry a human sign-off), builds a table and a verdict line, and puts it in the graph state. The graph then ends the turn with exactly that text and no further model call. A review of the plan found that appending a code-built table to model-written text left room for wrong figures above it. Details:
  - Straight through: at least 70% of claims handled with no handler; this counts every claim not referred, including approvals waiting for sign-off (correction in the week guide).
  - Accuracy: at least as accurate as agreed, meaning the evaluation's accuracy on the whole held-out set at or above the objective in Settings.
  - Over the limit: every payout above the approval limit has a person's sign-off, measured against the limit recorded on the decision; "none paid yet" counts as met, and the answer says why.
  - If the evaluation cannot start, fails or is still going after 15 minutes, give no figures for the first two and still report the third.
- **Explaining why an item needs a human.** Write instructions that define when an explanation is complete: it rests on the record and the agent's steps, every rule section it relies on was read from the context layer, and it names the rule or setting (the approval limit) that brought the item to the human. Then verify it live. In the course build, a small model at low reasoning effort did not read the context layer unless asked; the fix would be code (a record read that also brings the sections the decision cites). If something must always happen, code it.
- **Refusals go back to the model as text** with a short reason; the card keeps the bare reason. Other errors mark the card failed and fail the turn. A rejected sign-in stops the turn at once, since nothing more can be recorded with it.
- **Show the tool's own name on cards.** The gateway prefixes tool names with the target (for example `undercover-context___lookup_term`); strip that for display.
- **Instructions give goals, not scripts**: the goal, who it works for, its access and powers, the success criteria, and how to answer (brief, plain business English, currency format, every figure from a tool, claim ids named). Behaviour that must always occur belongs in code.

## Showing the work (UX)

- **A sidebar on every signed-in page**, open the first time, collapsible to a slim tab with its own icon, choice remembered per browser. The page beside it stays usable and shows the changes the copilot makes like any other change (the dashboard behind the sidebar shows claims moving while the copilot waits). On a narrow window the sidebar opens over the page.
- **Each tool call is a compact card as it happens**: an icon for its kind (records, customers, context layer, the agent's work, memory, action), tool name and main input, and state (working with seconds so far, done with time, refused or failed with the reason). Clicking opens what was asked and what came back, trimmed, with the file and owner of a context-layer answer. Actions that change something stand out from lookups.
- **The answer appears in full when the turn ends**, with a small line giving model calls, cost and time. The platform here (a function behind the app) cannot stream, and the cards already show progress, so skip word-by-word streaming.
- **Poll the conversation about once a second while a turn works, and not when idle or waiting for a confirmation.** The backend computes each working card's seconds at read time.
- **Chat basics**: user on the right, copilot on the left, markdown answers (small tables, lists), claim ids as links, a greeting with suggested questions on an empty conversation, new conversation and earlier conversations (titled with the first question), message box disabled while working or while a confirmation waits, "Signed in as" the user's name.
- **The confirmation card** shows the item, the person, the amount and the agent's reason with two clear buttons. After the answer it shows what actually happened, read from the sign-off's real result: pending, signed off and paid, cancelled with a reason, refused or failed. It must not claim success from the click alone.

## Building and accepting it

1. **Write the brief as the customer would** and let the coding agent plan in phases (six in UnderCover: the backend's records, the graph with its lookups and the pause, waiting and criteria and memory, the runtime app, the sidebar, the docs and live checks), committing each phase. See [building with coding agents](building-with-coding-agents.md).
2. **Have a second model review the plan before any code.** In the course build, the plan was reviewed by Codex before Claude Code built it. (When the course says "Copilot for a second opinion on the plan", it means Codex.) The review kept the six-phase plan and amended seven things, for example:
   - Write the whole success-criteria answer in code.
   - Bind confirmation answers to the displayed turn and re-check the held decision.
   - Run tools one at a time.
   - Keep the SDK logger above DEBUG and test with the real client path.
   - Add a negative case for the safety criterion and bound the retries.
   - Refuse late updates to a stopped turn, and document the crash gaps.
   Review plans for security and state-machine holes, not style.
3. **Test without models, AWS, Supabase Auth or the gateway.** Use a stub model that plays scripted replies with usage and cost, an in-memory saver, and stand-ins for the runtime and the memory. "A freshly built copilot on the same saved state" answers a pause, to prove resume works in a new process. Search every table, checkpoint, memory event and log for the token and assert it is nowhere. Cover: refusal passed on, wait for a run, criteria answered from an evaluation (none paid yet, evaluation failed), one turn at a time, a failed turn then a new message, a stopped turn, Cancel, the agent's key never sent, another user refused a conversation.
4. **Drive the UI end to end against a stand-in copilot** that plays one scripted turn through the backend with the user's token, covering a lookup, an action, a refusal, a confirmation and a formatted reply.
5. **Run the live checks once, last, after one reseed**, then record what they cost and what did not meet the brief. In UnderCover, one check did not pass as written (the context-layer explanation above) and was recorded as a known gap rather than hidden.
6. **Accept with the handover conversation**, run on the deployed product as the real user, in one conversation. The course's version (slide 95) has five prompts; they are paraphrased here, with what each one shows:

| # | Prompt (paraphrased) | What it demonstrates |
|---|---|---|
| 1 | Run the queue with ten agents, then say which claims still need me | A dispatch started on the runtime, with the copilot waiting in code while the dashboard updates |
| 2 | Explain why CLM-1011 is waiting for me | The copilot reads the claim's steps, the policy wording and the limit, and explains them |
| 3 | Return that claim to the agent with a note | An action taken as the user; the claim agent resumes it in a new session |
| 4 | Approve payment on another claim | The copilot stops to ask before paying and resumes from its checkpoint |
| 5 | Tell me whether we are meeting the agreed success criteria | A held-out evaluation, with every figure computed in code |

   Afterwards: tell it how you like answers, start a new conversation a few minutes later and see it remember; sign in as a junior user and see a sign-off declined. Generalise this: write five questions that together touch bulk work, explanation, correction, a consequential action and evidence against success criteria, and run them on the deployed system.

## The capstone blueprint

The course's assignment is a reusable blueprint for any production agentic solution: a business problem where agents make decisions within limits, built on LangGraph and deployed on a managed runtime. Use it as a checklist when scoping a new project. The solution can be a variation of UnderCover or something completely different.

| Element | Design question | UnderCover answer | Evidence to produce |
|---|---|---|---|
| Decisions within limits | What may the agent decide alone, and what is the limit? Who sets it? | The agent decides claims up to the approval limit; payments over it are held | A rule enforced in code and in the gateway policy, with tests at the boundary |
| Human sign-off above the limit | Who may approve, and how is the pause saved and resumed? | A senior handler signs off; the pause is a saved interrupt; a confirmation card in the copilot | A test that no payout over the limit lacks a person's sign-off |
| Durable state | Where do checkpoints live, and what is the thread? | LangGraph checkpoints in a database; a thread per claim and per conversation | Resume in a fresh process and a new runtime session |
| Enterprise context layer | What definitions, rules and reference data do agents need, who owns them? | Business-owned files exposed as tools, each naming its source and owner | Every decision cites what it relied on |
| Long-term memory | Whom is it about, and what is stored? | A namespace per user: customers for the claim agent, handlers for the copilot | Notes recalled in a later session; another namespace never used |
| Runtime deployment | Where does it run, with which identity and secrets? | Agent and copilot runtimes, gateway, identity service, app on Lambda | A deployed run and a teardown that leaves nothing behind |
| Success measured first | What does "working" mean, with baseline and target? | Three criteria agreed at the start: straight-through share, accuracy vs handlers, every over-limit payout approved by a person | An evaluation at the end, computed in code, shown at handover |

Be the forward deployed engineer: define the evals first and end by measuring them. Pick criteria of three types: a throughput measure, a quality measure and a safety invariant. See [FDE lifecycle and governance](fde-lifecycle-and-governance.md) for discovery and handover and [evals and observability](evals-and-observability.md) for building the measurement. The assignment is shared as a pull request with a short write-up and a link to the repository (optional, in `community_contributions/`).

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
|---|---|---|
| Is a copilot warranted, and for which jobs? | General assistant vs two or three named jobs | Name the user jobs (lookup, explain, start work, one consequential action) before designing |
| Which actions can it take? | Read-only; reads plus starting work; reads plus consequential actions | Reads plus starting work and one confirmed consequential action; refuse the rest and point to the UI |
| What needs confirmation? | Everything; nothing; only consequential actions | Only the action that moves money or cannot be undone |
| Identity | Pass the user's token; a service identity with on-behalf-of claims | Pass the user's token; never hold the agent's key; check who is signed in each turn |
| Runtime | Shared with the agent; its own | Its own runtime, a session per conversation, fewest credentials |
| Memory | None; per-user notes; also read the agent's memory | Per-user preferences and facts, on only when configured; save only message and answer; do not read the agent's memory |
| Progress UX | Stream tokens; poll step cards | Poll about once a second and show cards; stream only if the platform can |
| Success criteria | Vague quality goal; three measurable criteria | Throughput, quality and safety criteria agreed in discovery, checked by a code-built answer |
| Model and effort | Larger model, higher effort vs cheaper | The course used GPT-6 Luna at low effort (as taught, Oct 2026), with a configurable override; verify tool use live |

Ask these in this order: jobs, identity, actions and confirmations, success criteria, runtime, memory, UX.

## Pitfalls and anti-patterns

- **The user's token in config or state.** Checkpoints save them. Keep it in the run context only.
- **Reusing the back-office key**, or using the gateway's app target from the copilot. The call then acts as the agent.
- **The model polling a job** by repeated calls, or writing figures. Wait in code and compute figures in code.
- **Appending a code table to model text**, leaving the model's own figures above it. End the turn with the code's text.
- **Card contents from the model.** Fill them from records.
- **Work before `interrupt()` in the same node**, which repeats on resume.
- **A stale tab answering a newer card**, or a held decision that changed. Bind to turn id and re-check.
- **Two messages at once** both accepted. Use a conditional update.
- **Stuck "working" turns** after a crash. Compute `stopped` and refuse late updates. Know the crash gaps: the app and the saved graph can disagree if the copilot dies between saving a pause or result and telling the app; a sign-off may have paid while the sidebar shows no outcome.
- **A token expiring mid-turn** (one-hour sign-ins). Renew before sending; long chains of waits may still fail.
- **Debug logs that leak payloads** (SDK request logging).
- **Import-time work on the runtime**, which the platform snapshots. Do it on the first request.
- **Instructions as the only control** for behaviour that must always happen (lookups, checks). Put it in code.
- **Step-recording routes that take the user's token.** In the course build a user could write to their own conversation's records through the API; nothing there pays or decides. Keep any such route free of side effects, and know where your equivalent is.
- **Letting the model name the user or the amount.** Identity, role and every figure come from the backend, not from the message.

## In UnderCover

The Copilot (Week 3 Day 5, brief `labs/week3day5_product_COPILOT.md`) is a sidebar on every dashboard page for claims handlers. It looks up claims, customers, policies, the latest dispatch, evaluations, settings and the seven context-layer lookups; starts dispatches and evaluations; sends decisions back with a note; and signs off held payouts after a confirmation card.

- **Identity.** Dana Whitfield can sign off over the $1,000 limit; Marcus Oyelaran cannot, so the Copilot declines for him with the reason. The Copilot calls the app only through one module that sends `Authorization` and never `X-API-Key`; the app answers 403 to a handler route carrying the agent's key.
- **State.** Three app tables (conversations, turns, step cards) beside the graph's checkpoints in Supabase; `conversation-<uuid>` ids double as the runtime session id and the memory session.
- **Runtime.** `agentcore/agentcore.json` gets a second runtime `copilot` beside `agent`; `runtime/copilot.py` starts it; a small policy file lets its role call the gateway and use only `undercover_copilot_memory`. The app invokes it with the conversation id as the session id.
- **Memory.** `undercover_copilot_memory` has preferences and facts by handler; the claim agent's memory is by customer. Deployment is on Lab 1's two runtimes and two memories.
- **Success criteria.** The three criteria agreed at the start of the pilot are checked by one tool; Dana's fifth handover question answers with a code-built table.
- **Process.** Ed built it with Claude Code after Codex reviewed the plan; the review is in `docs/REVIEW_PLAN_COPILOT.md` on the end branch. The live run (Oct 2026) passed all checks except the context-layer explanation, recorded as a known gap. Eleven Copilot turns cost about $0.014 in model calls, and the whole live session about $0.10 including the dispatch and evaluation (as recorded, Oct 2026).
- **Lab 1** (`week3day5_lab1`) deploys everything and runs the handover; **Lab 2** tears it all down, and `uv run monitor.py` shows spend. Never create or delete AWS resources unless the student asks.

## Related

- [Durable state and HITL](durable-state-and-hitl.md): checkpointers, interrupts, resume semantics, idempotent human steps
- [Security and guardrails](security-and-guardrails.md): API keys, gateways, policies, why user identity matters
- [RAG, memory and MCP](rag-memory-and-mcp.md): memory namespaces, strategies, context tools over MCP
- [Production deployment on AWS](production-deployment-aws.md): runtimes, sessions, identity, memory creation, teardown
- [Harness engineering](harness-engineering.md): the loop, tools, middleware and instructions as goals
- [Context layer and integrations](context-layer-and-integrations.md): what the lookups read and who owns it
- [Evals and observability](evals-and-observability.md): the evaluation behind the success-criteria check
- [Building with coding agents](building-with-coding-agents.md): plans, phases and reviews
- [UnderCover case study](undercover-case-study.md), [agent code patterns](code-patterns-agents.md) (the copilot graph, cards and criteria in code), [platform code patterns](code-patterns-platform.md) (sign-in and role check), [AWS AgentCore code patterns](code-patterns-aws-agentcore.md) (invoking a Runtime for a chat turn)

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK3.md` (Week 3 Day 5, with its corrections)
- Week 3 slides 87–97 (W3D5: the Copilot, its sidebar, Lab 1, the handover conversation, the assignment and the teardown)
- `labs/week3day5_product_COPILOT.md` and notebook `labs/week3day5_lab1.ipynb`
- `origin/week3day5-end:docs/PLAN_COPILOT.md` and `docs/REVIEW_PLAN_COPILOT.md`; `docs/STATUS.md` (known gaps, last live run)
- `origin/week3day5-end:agent/copilot/` (`graph.py`, `tools.py`, `cards.py`, `waiting.py`, `criteria.py`, `memory.py`, `entrypoint.py`, `needs_a_handler.py`, `instructions.md`, `app_api.py`)
- `origin/week3day5-end:backend/` (`copilot.py`, `copilot_service.py`, `conversations.py`) and `runtime/copilot.py`, `runtime/copilot_policy.json`

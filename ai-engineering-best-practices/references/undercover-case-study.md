# UnderCover case study: the reference architecture

> When to read this: you need to see how the practices in the other references fit together in one real system, you want the order in which the system was built and why, or you must map the blueprint onto a new domain (expense approvals, access requests, loan checks). Read the topic files for the "how"; read this for the "how it all fits".

Facts about products, models, prices, limits and CLI versions are as taught in the course (Oct 2026); re-check them before relying on them. UnderCover is fictional, and the figures come from Ed Donner's runs and builds, so treat them as illustrations of the shape of the results, not as benchmarks.

## Contents

- [Key principles](#key-principles)
- [The business problem, users and success criteria](#the-business-problem-users-and-success-criteria)
- [How the system evolved](#how-the-system-evolved)
- [The final topology](#the-final-topology)
- [Components and responsibilities](#components-and-responsibilities)
- [One claim, end to end](#one-claim-end-to-end)
- [One Copilot conversation](#one-copilot-conversation)
- [Key numbers as taught](#key-numbers-as-taught)
- [What went wrong, and what it taught](#what-went-wrong-and-what-it-taught)
- [Applying the blueprint to a new domain](#applying-the-blueprint-to-a-new-domain)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [Related](#related) and [Sources](#sources)

## Key principles

1. **Fix the business problem and the success criteria before the architecture.** They are the only way to tell whether a build helped; UnderCover agreed three criteria in week 1 and the final Copilot checks them in week 3.
2. **Start simple and add machinery only against a measured problem.** A single structured call beat an agent on a fixed workflow; a code dispatcher replaced a model that only chose "next claim". Each build answered one named pain.
3. **Rules that must hold live in code at the system of record, not in the prompt.** The approval limit, the payout calculation, the completeness of a decision record and "never pay twice" are enforced by the backend, with the Gateway's Policy as a second layer. Why: prompts are followed most of the time; money needs always.
4. **The agent is one worker inside a system.** Code chooses the work, fans it out, retries, builds summaries and enforces limits; a clean-context agent does one unit of judgment. Why: it keeps cost, failure and audit predictable.
5. **Keep state outside the agent process.** Checkpoints in a database make every session disposable, so a crash, restart or a new Runtime session carries on instead of starting again.
6. **Design the human step, not just a pause.** Threshold, who may release, what the person sees, and the options (sign off, send back with a note) changed three times because each design met a real constraint.
7. **Separate identities.** The agent has its own API key; handlers have their own sign-in; the key never stands in for a person, and the user-facing Copilot acts only as the signed-in user.
8. **Name each data source's owner.** Governed business data (read-only context layer), the agent's own notes (memory) and the system of record (database, reached only through the app) have different owners, rules and failure modes.
9. **Measure, then let the agent improve itself inside code-enforced guardrails.** Held-out scores, noise thresholds, a budget and a human approval decide; the improver cannot change its own yardsticks.
10. **Passing checks is not the same as being fit to ship.** Review by someone who did not write the code, a status document with honest known gaps, and live runs recorded in the docs were part of every build.

## The business problem, users and success criteria

UnderCover Travel Insurance is a fictional US insurer (plans: Economy, Premium, First). Claims handlers work a queue by hand: read the customer's story and documents, check the policy and the policy wording (later also the claims manual), then **approve with a payout, decline, or refer** (when it needs judgment or more information). The pilot's goal: handle claims **straight through, as accurately as the handlers do**, with a person approving any payout over $1,000.

| User | What they do with the system |
|---|---|
| Claims handlers (Marcus Oyelaran, Priya Raman) | Watch the queue and the agent's steps, start dispatches, read claims and decisions, ask the Copilot. Cannot sign off over the limit. |
| Senior handler (Dana Whitfield) | Everything above, plus: sign off payouts over the limit, send held decisions back with a note, start/stop improvement rounds, approve the improver's proposals, change settings. |
| Head of claims operations | Wrote the brief for each build; owns the success criteria. |
| Data governance, information security, platform team | Own the context files, the security rules, and the deployment files, respectively. The agent team builds to fit what they own. |
| The agents (claim agent, improver, Copilot) | Not users but actors, each with its own identity and limits. |

**Success criteria** as finally agreed (checked by the Copilot in code from the records):

| Criterion | Measure |
|---|---|
| Straight through | At least 70% of held-out claims not referred (approvals held for sign-off count as straight through). |
| Accuracy | Accuracy on the held-out set at or above the objective in Settings (right decision and payout within $1). |
| Over the limit | Every payout above the limit has a handler's sign-off on its payment. |

**Cost of mistakes** is a business cost, separate from API cost, set at $1,500 for a wrongful decline, the payout itself for a wrongful approval, $50 for a needless referral and the gap for a wrong amount. It lets a reviewer compare "wrong but cheap" with "wrong and dear" and set the objectives sensibly; see [evals and observability](evals-and-observability.md).

## How the system evolved

Nine builds, each from a brief written by the customer's people, each planned in `docs/PLAN_<NAME>.md` and then implemented phase by phase. Sizes are the insertions/deletions of Ed's `-start` to `-end` diff (docs, tests and generated files included), a rough guide to effort only.

| Build (day; size) | What was added | Why | Architecture lesson | Covered in |
|---|---|---|---|---|
| **Pilot** (W1D3; ~3.5k lines added) | FastAPI + SQLite backend, React dashboard (queue, claim page, agent steps), LangChain `create_agent` that reaches claims only through the backend API; backend blocks any payment over $1,000 | A measurable pilot: queue, decisions with reasons, visible steps | Agent behind an API; the rule is enforced by the system, not the prompt; a coding agent builds from a plan with checks | [agent architecture](agent-architecture.md), [building with coding agents](building-with-coding-agents.md) |
| **HARNESS** (W1D5; 52 files, +2.7k/-0.7k) | One queue agent with a to-do list shown on the dashboard, a fresh subagent per claim reporting in one line, section-level search of wording and manual, retry once then leave for a handler, goal-style instructions | Harder claims, longer jobs, failures that stalled the queue | Harness parts (context, planning, subagents, failure handling); review caught what tests missed | [harness engineering](harness-engineering.md) |
| **DURABLE** (W2D3; 51 files, +3.0k/-0.7k) | Records on Supabase; claim agent as a hand-written LangGraph graph with `PostgresSaver`; `interrupt()` for sign-off; payout tool in the backend; Langfuse traces; idempotent decide/pay | Wait days for a person, survive a crash, stop payout errors | Durable state, a node per side effect, idempotency, deterministic work in code | [durable state and HITL](durable-state-and-hitl.md), [evals and observability](evals-and-observability.md) |
| **SWARM** (W2D4; 87 files, +5.4k/-1.5k) | LangGraph dispatcher with no model (`Send`, `max_concurrency`), N claim agents (1-25), cost and time per claim, evaluations on two labeled sets, Scoreboard | Whole queues arrived at once; nobody could say how accurate or costly the agent was | Do not use a model for fixed routing; measure continuously; limits and retries are architecture | [swarms and scale](swarms-and-scale.md), [evals and observability](evals-and-observability.md) |
| **IMPROVE** (W2D5; 191 files, +14.7k/-1.2k) | Versioned configuration (prompt, model, reasoning), judge grading explanations, improver agent in rounds with human approval and code-enforced keep/rollback, handler sign-in, senior-handler role | Hand-tuning loop was slow; dashboard going to the whole team | Self-improvement needs fixed yardsticks, a held-out set, a budget and a human gate; identity arrives with real users | [self-improvement](self-improvement.md), [security and guardrails](security-and-guardrails.md) |
| **SECURE** (W3D2; 77 files, +2.3k/-0.7k) | Agent API key (`X-API-Key`), injection check as the graph's first node on its own model, OpenAPI of the agent's 8 operations for the Gateway, app packaged for Lambda, sign-off pays directly | Public address; CLM-1901 hides an instruction in the story | Defence in depth; least tool surface; identity separation; guardrail as its own node | [security and guardrails](security-and-guardrails.md), [production deployment on AWS](production-deployment-aws.md) |
| **CONTEXT** (W3D3; 88 files, +4.5k/-0.8k) | Agent tools through the AgentCore Gateway (SigV4 MCP client); context layer as a FastMCP server on Lambda over 7 governed files; section-14 decision record; AgentCore Memory per customer; "Context used" panel | Policy never saw direct calls; knowledge was scattered; records incomplete; no recall between claims | Three data sources with three owners; provenance on every answer; memory is best-effort, the database is truth | [context layer](context-layer-and-integrations.md), [RAG, memory and MCP](rag-memory-and-mcp.md) |
| **RUNTIME** (W3D4; 121 files, +6.1k/-1.7k) | Agent as an AgentCore app (same code on laptop and Runtime), pause returns with Sign off / Send back with a note, one-run-at-a-time lock with heartbeat, credentials in AgentCore Identity | Agent still on a laptop; a handler could not steer the agent | Sessions are short-lived and idle-timed; state in the database lets another session resume; local/cloud parity | [production deployment on AWS](production-deployment-aws.md), [durable state and HITL](durable-state-and-hitl.md) |
| **COPILOT** (W3D5; 132 files, +12.5k/-0.9k) | Chat sidebar agent on its own Runtime (session per conversation), acts with the handler's own sign-in, confirmation card before any payment, waits and success-criteria answers in code, handler memory | Handlers spend the day on the dashboard; questions need several pages | A user-facing agent inherits the user's identity and limits; what must always happen is code | [copilot pattern](copilot-pattern.md) |

**How each build was run** (the process is part of the architecture; see [building with coding agents](building-with-coding-agents.md)):

1. Customer brief in `labs/` copied to `docs/`; a planning request wrote `docs/PLAN_<NAME>.md` (design first, then 5-7 phases, each with checkbox success criteria), and the developer reviewed it. For the Copilot a second model also reviewed the plan and amendments were folded in.
2. Implementation phase by phase: build with tests on a stub model, verify criteria, run `npm run check` (lint, types, tests with 80% coverage, e2e), review by a fresh subagent, update `docs/STATUS.md`, commit.
3. Live runs with the real model recorded in the status document, with the known gaps listed honestly.

### The sign-off design changed with the constraints

The same rule ("a payout over $1,000 needs a senior handler") was implemented four ways. Reuse the pattern of asking what the current deployment forces, not any single design.

| Period | Who pays | Does the agent pause? | What forced the change |
|---|---|---|---|
| W1D3 to W2D2 | Handler's sign-off pays; backend refuses the agent's payment | No: approval ends the agent's work | Simplest thing that enforces the rule |
| W2D3 to W2D5 | Agent pays after sign-off | Yes: `interrupt()` resumes the graph | The agent should keep its work and finish the claim; payment is its own node that checks the claim id |
| W3D2 to W3D3 | Sign-off pays at once; the Gateway's Policy also refuses agent payments over the limit | No | The app on Lambda cannot reach a laptop-based agent service; payments must pass the Policy |
| W3D4 on | Sign-off: the app pays; Send back with a note: the agent decides again | Yes: pause returns, resumable in a new Runtime session | A handler who disagreed had no way to tell the agent; checkpoints in Supabase make cross-session resume possible |

## The final topology

As it stands at the end of week 3 (matches the course's final deployment slides, W3 slides 84 and 94, plus the build's TECH_STACK). Everything also runs on a laptop with `npm run dev`; the Gateway and Memory are then optional (the "direct route").

```text
 Handler (browser) --- sign in ---> Supabase Auth
        |
        v  HTTPS
+------------------------------- AWS (us-east-1) ----------------------------+
|                                                                            |
|  [1] UnderCover app  (Lambda, Function URL)                                |
|      dashboard files + FastAPI API (Mangum); enforces every business rule  |
|        |  InvokeAgentRuntime: start runs, resume claims, Copilot turns      |
|        v                                                                   |
|  [2] AgentCore Runtime                                                     |
|      agent runtime   : dispatcher -> claim agents (+ improver)             |
|                        a session per dispatch / evaluation / resumed claim |
|      copilot runtime : a session per conversation                          |
|        |                                        |                          |
|        | MCP tools (SigV4)                      | direct, runtime's role   |
|        v                                        v                          |
|  [3] AgentCore Gateway                     [5] AgentCore Memory x2         |
|      Policy (Cedar) + Identity                 customers  | handlers       |
|        |  adds API key        |  IAM                                       |
|        v                      v                                            |
|      [1] the app        [4] Context layer (Lambda, AWS_IAM)                |
|                             FastMCP server, 7 read-only lookups            |
+----------------------------------------------------------------------------+
  Supabase Postgres: records, checkpoints (schema `undercover`), auth  <- [1], [2]
  OpenRouter: every model call  <- [2] and the judge     Langfuse: traces  <- [2]
```

Reading the diagram:

- **Gateway as choke point.** Every tool call of the claim agent passes the Gateway: the Policy refuses `pay_claim` over $1,000 (and a refusal goes back to the model as a refusal; a refused payment waits for sign-off), Identity adds the app's API key, and the context layer is reached with IAM. The backend refuses over-limit payments too.
- **Memory is outside the Gateway.** The agent reads and writes AgentCore Memory directly with its Runtime role; one Memory for customers (claim agent), one for handlers (Copilot).
- **The Copilot bypasses the Gateway for records.** It calls the app directly with the handler's own sign-in; only its context-layer tools use the Gateway. A known gap: nothing but its tool list stops its route reaching the app's agent-only tools, so the Gateway's Policy should confine the Copilot's role to the context tools.
- **The app starts the agents; the agents call back.** Long work runs on Runtime and answers at once; the agent reports heartbeats every minute, and the app treats five silent minutes as stopped.
- **One database for laptop and cloud.** Lambda and Runtime use Supabase's transaction pooler (port 6543), so no prepared statements and no connection reuse on Lambda.
- **Local ports** (`npm run dev`): backend 8000, claim agent app 8080, Copilot 8081, context layer 8006, dashboard 5173.

## Components and responsibilities

| Component | Runs on | Responsibility | Must not |
|---|---|---|---|
| Dashboard | Browser; static files served by the app | Queue, claim pages with every step, Scoreboard, Configuration, Improvement, Settings, Copilot sidebar; handler sign-in | Call the agent or hold the agent key |
| App (backend) | Lambda | System-of-record API; rules (approval limit, record completeness, idempotent decide/pay, who may call what); starts and tracks runs; one-run lock; Copilot conversations | Trust the agent's output without checks |
| Dispatcher | Agent runtime (no model) | Pick claims (in progress, waiting, sent back; oldest first), fan out N at a time, retry, finish with a summary built from records | Judge claims |
| Claim agent | Agent runtime | Work one claim from a clean start: lookups, memory search, payout tool, record a decision, report a line | Pay over the limit, see answer keys, act on another customer |
| Injection check | First node of the claim graph | A second model reads the customer's text; a flagged claim is referred and the claim model never sees it | Be changed by the improver |
| Context layer | Lambda behind IAM | Seven governed files (data dictionary, glossary, plans, claim rules, reference data, wording, manual), each answer naming source, owner, review date | Be edited by the agent |
| Gateway | AgentCore | Turn API/MCP into tools, enforce Cedar Policy, add credentials | Hold business logic |
| Memory | AgentCore Memory | Per-customer facts and claim summaries (claim agent); per-handler preferences and facts (Copilot) | Be the record of truth or store stories/documents |
| Improver | Agent runtime | Propose configuration and recipe changes in rounds, with reasons | Change objectives, noise, budget, models allowed, eval sets, judge |
| Judge | Called by the backend | Grade each explanation against the handler's reason | Decide claims |
| Copilot | Own runtime | Answer and act for the signed-in handler; confirmation card before payment | Use the agent key or see the answer key |
| Supabase | Hosted Postgres | Records, graph checkpoints, handler sign-in | Be exposed to the agent except through the app |
| OpenRouter / Langfuse | External | Models for everything / traces | |

## One claim, end to end

1. A handler starts a dispatch on the queue page (N = 1 to 25). The app checks nobody else's run is going (one at a time), records the dispatch and asks the agent runtime to work it; the call answers at once.
2. The dispatcher (code, no model) lists the claims and sends each to a claim agent, at most N at once. Each claim gets its own thread in Supabase.
3. **Screening:** a separate model reads everything the customer wrote and checks for instructions aimed at the handler. A flagged claim is referred with the reason, nothing is saved to memory, and the claim model never sees it.
4. The claim agent works from a clean start. Its tools come through the Gateway: it fetches the claim, policy and history from the app, searches wording and manual sections, and looks up definitions, claim rules and outside facts in the context layer (each answer naming its file, owner and review date). It decides itself whether to search the customer's memory.
5. The payout is calculated by UnderCover's payout rules in the backend (a tool), never by the model.
6. It records the decision with the full section-14 record: decision, payout, calculation, section relied on, reason, who decided (agent version), when, and the manual's version. The backend refuses an incomplete record and an approval whose payout is not the calculation for that attempt.
7. **Within the limit:** a `pay` node pays idempotently (a repeat of a recorded payment is treated as done). **Over the limit:** the Policy or the backend holds the payment, the graph pauses with `interrupt()` and its place is saved in Supabase; the claim shows "waiting for sign-off".
8. A senior handler either **signs off** (the app pays at once, recording who and when; a short session resumes the graph so it finishes and saves to memory) or **sends back with a note** (up to 1,000 characters; the decision is cleared, the note, author and time are recorded; the graph resumes, possibly in a new session, reading the note as a senior handler's review, and decides again or refers if the wording does not support it).
9. When the claim ends decided, the `remember` node saves the claim and the decision (not the story or documents) to that customer's memory; AgentCore extracts memories in the background, usually within about two minutes.
10. Failure handling is in code: a rate limit or timeout waits and carries on as the same attempt; another error puts the claim back in the queue for one more try in the same dispatch; a second failure leaves it for a handler. After a crash the next dispatch resumes from the checkpoint without counting a new attempt.
11. When the dispatch ends, a summary is built from the records (approved, declined, referred, payouts waiting for sign-off, claims left for a handler), with cost and time per claim recorded.

## One Copilot conversation

1. The handler types in the sidebar. The dashboard renews the handler's sign-in if less than 20 minutes remain, then sends it with the message to the app; the app passes it to the Copilot's Runtime session for that conversation. The sign-in is never saved in state, steps, memory or logs.
2. The Copilot first asks the app who is signed in; if the app rejects it, the turn ends before any model call.
3. It recalls the handler's memory, then loops (hand-written LangGraph graph, one tool at a time, at most 25 model calls a turn): read records as the handler (queue, claim, steps, customers, policies, latest dispatch, evaluations, settings; never the answer key), look things up in the context layer through the Gateway, start a dispatch or evaluation, send a decision back with a note.
4. Each tool call appears as a card in the sidebar as it happens. Waiting for a dispatch is done in code (poll every 5 seconds, up to 15 minutes), then it reports what needs a handler: held payouts, referrals, left-for-handler claims, unclaimed sent-back claims.
5. **Sign-off:** code first checks that this handler may sign off over the limit (a handler who cannot is told so). A node of its own holds the `interrupt()`; the card shows the claim, customer, amount and the agent's reason from the records. Nothing is paid until the handler presses Sign off and pay; then the graph resumes with the answer, the app pays as that handler, and the card says "paid" only from the sign-off's real result.
6. **Success criteria:** it runs a held-out evaluation and answers with a table of the three criteria written entirely in code from the records, so the model cannot misstate a figure.
7. The turn ends with a memory save (preferences and facts per handler, apart from customers' memory). The conversation is durable: the handler can close the browser, restart, and later answer a waiting confirmation.

## Key numbers as taught

Figures are from Ed's runs in the course (Oct 2026). Small runs are noisy: a run of 25 claims cannot show a small gain, and a run is not a ranking of models.

| Where | Number | What it teaches |
|---|---|---|
| W1D2 | On the fixed 25-claim task the LangChain agent took longer, cost more and did no better than one structured-output call. Queue totals: $0.0042 (GPT-6 Luna), $0.0318 (Gemini 3.5 Flash Lite), $0.0033 (Jev) | A fixed workflow does not need an agent; model choice moved cost by nearly 10x on the same job |
| W1D2 | Assignment target: the cheapest model that gets at least 15 of 25 right with the agent | Choose a model by task results and cost, not by reputation |
| W1D4 | Approving every claim gets 60% of decisions right (20 claims not needing the manual) | A trivial baseline sets the bar; compare with the decision score, not the stricter accuracy |
| W2D1 | Approve-all gets 56% of decisions right, kappa 0; refer-all costs $950 (average $38 a claim) on the 25 harder claims | Baselines and the cost of mistakes show what "good" must beat |
| W2D1 | A Python payout tool cut wrong decisions or amounts from 36 to 8 of 75 over three runs; baseline wrongly declined 4 times, tool version once; neither wrongly approved | Put calculation in code |
| W2D2 | Facts held in long-term memory: 14 of 25 fully right without, 25 of 25 with | Missing knowledge is a retrieval problem, not a prompt problem |
| W2D4 | A queue of 25 handled one at a time took over ten minutes; a swarm of 25 takes about as long as its slowest claim, but was faster than 5 agents without being 5x faster | Parallelism is bounded by shared resources (connections, rate limits) |
| W2D4 build | At 25 agents each non-model step took about 2.6x longer than at 3 (0.37 s vs 0.14 s); Supabase's free pooler allows 15 connections, so each process uses at most 4 | Contention shows up in plumbing, not the model |
| W2D5 | Judge grades run 0-3 (F=0, C=1, B=2, A=3); same version run twice to measure noise; round spending limit starts at $0.50 | Keep/rollback needs noise thresholds and a budget |
| W3D2 | In CLM-1901 a hidden instruction asks for a $4,800 watch to be approved: GPT-6 Luna declines and GPT-4o mini approves; a keyword check misses a reworded version, while a model check with Structured Outputs catches both and flags none of the 25 ordinary claims | Layer guardrails and test them for false alarms |
| W3D4 | Runtime idle timeout 60 s (a session with registered work lives up to 8 hours); 6 of 30 queries failed with `DuplicatePreparedStatement` on the transaction pooler | Platform limits shape code; read them early |
| Final build, one live run (Oct 2026) (laptop, `npm run dev`, direct route with no Gateway or Memory; Copilot on GPT-6 Luna at `low`) | Dispatch of 26 claims at N=10 in 1 min 45 s: 20 approved (3 held for sign-off), 3 declined, 3 referred. Held-out evaluation at 25 agents in 1 min 24 s: 88% straight through (target 70%), 88% accuracy (objective 60%), $255 of mistake cost. Whole session about $0.10, of which the Copilot's 11 turns about $0.014 | Order of magnitude of cost and speed; one run, so noisy |
| Course | About $10 of API spend typical; AWS $10 monthly budget; the first Runtime deploy's CDK bootstrap KMS key costs about $1 a month until Lab 2's teardown deletes it | Always plan the teardown |

## What went wrong, and what it taught

| Episode | What happened | Lesson |
|---|---|---|
| Human review of the harness (W1D5) | The build passed every test, yet the head of engineering found 20+ hard-coded URLs, two ways of calling the backend, modules reaching into each other, state passed by closures, and step-by-step scripts as instructions. A rebuild followed | Checks prove it works, not that it is fit to merge. Add a fresh-reviewer step before every commit, a design in every plan, and written code standards |
| Prompts that spelled out steps | Scripts as prompts; later the Copilot, told to draw on the context layer, did not read it when explaining a claim unless asked to check a section | Give goals, inputs and "done"; anything that must always happen belongs in code (even then, only code guarantees it) |
| Contention in swarms (W2D4, W3D4) | 25 agents were faster than 5 but not 5x; plumbing steps slowed 2.6x; prepared statements failed through the transaction pooler | Size pools and limits as part of the design; start N small; test the deployment path |
| Sign-off design (see table above) | Four implementations of one rule | Revisit the human step whenever the deployment changes; keep the rule in the backend so the UI can change |
| Durable is not exactly-once (W2D3) | Durable execution can rerun a node after a crash; rewinding a checkpoint does not undo a payment | Put each side effect in its own node and make it idempotent on a business key; undoing needs a business action such as a refund |
| Noise in small eval sets (W2D1-W2D5) | A run of 25 moves between runs; the improver never sees held-out claims, yet their scores pick versions | Measure noise first; use a held-out set for keep/rollback and a separate set for the final check |
| Model-written verdicts | A plan review found that appending a correct table to free model text would let wrong figures through | Write answers that must be right (criteria table) entirely in code |
| Stale confirmation (Copilot review) | An old browser tab could answer a newer card, or a held decision could change after the card was shown | Bind a confirmation to the turn, re-check the held decision at execution, allow one sign-off request per turn |
| Memory is best-effort | The agent decides whether to search memory; extraction lags about 90 s; a crash between decision and `remember` loses that note | Use memory for helpful recall; keep the database as the source of truth (claim history still counts for repeat claims) |
| Deployment surprises | A public Function URL: the key protects routes, not the function; a Runtime session ends at the idle timeout even if a thread is still working | Register long work with the platform; protect the endpoint as well as the routes; no set of checks makes an agent bulletproof |

## Applying the blueprint to a new domain

Fill one column per project before designing anything. Values for the examples are illustrative; set the real ones with the client.

| Blueprint slot | UnderCover | Expense approvals | IT access requests |
|---|---|---|---|
| Work item | Claim | Expense report | Access request ticket |
| Reviewer roles | Handlers; senior handler (Dana) signs off | Finance approvers; controller signs off | Service desk; security approver signs off |
| Agent's decisions | Approve with payout / decline / refer | Approve with reimbursable amount / reject / refer to manager | Grant (role, duration) / deny / refer |
| Autonomy threshold | $1,000, a setting | Amount above `<limit>` or a policy exception | Privileged or production role, or sensitive data |
| Consequential action (enforced by the system) | `pay_claim` | `reimburse_expense` | `grant_access` (identity change) |
| Untrusted input | Customer's story and documents | Employee notes, receipts and invoice text | Requester's justification, ticket comments |
| Business rules in code | Payout rules (plans, deductible, caps) | Per-diem and category caps, currency conversion | Role-to-permission mapping, maximum duration, separation of duties |
| Context sources (name owner and review date) | Wording, manual, data dictionary, glossary, plans, claim rules, outside facts | Expense policy, per-diem tables, approved vendors (finance, procurement) | Access policy, role catalogue, data classification (security, system owners) |
| System of record | Claims, policies, customers, decisions, payments in Postgres via the app | Ledger or ERP via the app's API | Identity governance system via the app's API |
| Memory subject | Customer (claim agent); handler (Copilot) | Employee (prior exceptions, recurring items) | Requester or target system |
| Eval sets and answer key | 25 queue claims, 25 held-out, harder sets; handlers' decisions kept away from the agent | Past reports with approvers' decisions, a held-out slice | Past tickets with the security approver's decisions |
| Cost of mistakes | $1,500 wrongful decline, payout if wrongly approved, $50 needless referral | Wrongful approval = amount plus audit risk; wrongful rejection = rework and friction; referral = approver time | Wrongful grant = incident exposure (highest); wrongful deny = lost productivity; referral = reviewer time |
| Success criteria | 70% straight through, accuracy objective, every over-limit payout signed off | Same shape: straight-through share, accuracy vs approvers, every over-limit reimbursement approved by the controller | Same shape, with "no privileged grant without security sign-off" as the hard one |
| Identities | Agent API key; handler sign-in; Copilot uses the handler's | Same | Same |
| Copilot questions | What needs me? Why this decision? Are we meeting the criteria? | What needs my approval? Why was this flagged? | Which grants are waiting? Why was this denied? |

Build order to reuse (stop where the project's needs stop): measurable pilot with a system-enforced limit; evals and baselines; harness; durable state with the human step; dispatcher and scoreboard; improver; security and identity; context layer and memory; deployment on the platform; Copilot. Do not build a later stage "because it is coming".

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
|---|---|---|
| How much of the blueprint does this project need? | Pilot only; plus durable human step; plus swarm; plus improver; plus gateway/context/memory; plus Copilot. Each stage adds operating cost and attack surface | Pilot, evals, harness, durable human step first; add the rest only against a measured need |
| Autonomy threshold and who releases | One limit per consequential action in settings, a named senior role, enforced in the backend (and the Gateway) | One setting, one senior role, enforced at the system of record |
| Where do agents run | AgentCore Runtime as in the course (AWS-specific), your own infrastructure, or the model lab's | Course's AWS stack, run the same code on a laptop first |
| Memory: yes or no, and for whom | Per subject (customer, handler, employee), summaries only, off in evaluations | Start without; add per-subject memory once the eval set shows missing history matters |
| Which source is the record of truth | App database vs context files vs memory | Database through the app's API; context for governed read-only data; memory for notes |

## Pitfalls and anti-patterns

- Building ahead of the brief or the evals "because it will be needed".
- Treating green tests as "done" without a reviewer who did not write the code.
- Letting the agent hold the credential to do the consequential action, or letting its key stand in for a person.
- Giving a user-facing agent the agent's key rather than the user's sign-in.
- Using a model for fixed routing or arithmetic that code does exactly.
- One long scripted prompt instead of a goal, plus code for what must always happen.
- Treating memory or the context layer as the system of record.
- Reading a single noisy run as a result, or selecting versions on the same set you report.
- Copying UnderCover's names and limits instead of the slots in the mapping table.

## Related

- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): discovery, success criteria, autonomy and handover.
- [Models and cost](models-and-cost.md): model choice, tokens, cost per claim.
- [Agent architecture](agent-architecture.md): agent or not, single vs multi-agent, business logic in code.
- [Harness engineering](harness-engineering.md): tools, subagents, instructions, failure handling.
- [Building with coding agents](building-with-coding-agents.md): docs set, plans, quality gates, reviews.
- [Evals and observability](evals-and-observability.md): eval sets, cost of mistakes, noise, tracing.
- [Self-improvement](self-improvement.md): judge, improver loop, keep/rollback.
- [RAG, memory and MCP](rag-memory-and-mcp.md): retrieval, MCP, AgentCore Memory.
- [Durable state and HITL](durable-state-and-hitl.md): checkpoints, interrupts, idempotency, human step.
- [Swarms and scale](swarms-and-scale.md): dispatcher, concurrency, limits, retries.
- [Security and guardrails](security-and-guardrails.md): risks, injection check, gateways, Cedar policy.
- [Context layer and integrations](context-layer-and-integrations.md): data owners, system of record, enterprise MCP.
- [Production deployment on AWS](production-deployment-aws.md): Runtime, Gateway, Identity, Memory, Lambda, teardown.
- [Copilot pattern](copilot-pattern.md): user-facing agent acting with the user's identity.
- [Code patterns: agents](code-patterns-agents.md), [code patterns: LangGraph](code-patterns-langgraph.md), [code patterns: platform](code-patterns-platform.md) and [code patterns: AWS AgentCore](code-patterns-aws-agentcore.md): snippets for the pieces above.
- [Decision guide](decision-guide.md), [checklists](checklists.md) and [glossary](glossary.md): question bank, reviews, terms.
- Template: [architecture document](../assets/templates/ARCHITECTURE.md).

## Sources

- Course map and corrections: `guides/for_agents/AGENT_COURSE_GUIDE.md`, `AGENT_GUIDE_WEEK1.md`, `AGENT_GUIDE_WEEK2.md`, `AGENT_GUIDE_WEEK3.md`.
- Requirements: `docs/SPEC.md` (pilot) and `origin/week3day5-end:docs/SPEC.md` (final); `origin/week3day5-end:docs/TECH_STACK.md`, `docs/STATUS.md` (built, known gaps, live runs, review of the harness), `docs/CODE_STANDARDS.md`, `docs/PROCESS.md`, `docs/REVIEW_PLAN_COPILOT.md`; `origin/week1day5-end:docs/HUMAN_REVIEW_HARNESS.md`.
- Briefs: `labs/week1day5_product_HARNESS.md`, `week2day3_product_DURABLE.md`, `week2day4_product_SWARM.md`, `week2day5_product_IMPROVE.md`, `week3day2_product_SECURE.md`, `week3day3_product_CONTEXT.md`, `week3day4_product_RUNTIME.md`, `week3day5_product_COPILOT.md`.
- Slides: W3D2 slides 34 and 43; W3D3 slides 59, 62 and 66; W3D4 slides 73, 78, 81 and 84; W3D5 slides 90 and 94 (final topology: slides 84 and 94).
- Build sizes: `git diff --stat origin/<day>-start origin/<day>-end` for each day.

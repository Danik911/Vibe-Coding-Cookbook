# Review checklists

> When to read this: at a tollgate (end of discovery, R&D, development, implementation), before shipping or switching on a risky capability (public address, improver loop, user-facing copilot), at the end of each build phase with a coding agent, and before handover. Run the list that matches the moment with the developer. Each item is distilled from a topic reference; follow its link when the developer asks "why".

Names, products, limits and numbers inside items are as taught in the course (Oct 2026). Where an item names a figure (an approval limit, a pool size, a timeout), treat it as the course default and replace it with the project's own.

## Contents and when to run each

Session stages (in [SKILL.md](../SKILL.md)) to checklist numbers: A->1, B->2, C->4, D->3, E->9, F->6, G->5, H->8, I->7, J->10, K->11, L->12, M->13, N->14.

| # | Checklist | Run it when |
|---|---|---|
| 1 | [Discovery tollgate](#1-discovery-tollgate) | End of discovery, before R&D or any build is funded |
| 2 | [Architecture review](#2-architecture-review) | End of R&D (approve the build); whenever someone proposes a new agent, framework or platform piece |
| 3 | [Harness and tools review](#3-harness-and-tools-review) | During development and before go/no-go; after any change to tools, instructions or failure handling |
| 4 | [Model and cost review](#4-model-and-cost-review) | When choosing a model; before go/no-go; after any model, price, prompt or provider change |
| 5 | [Evals readiness](#5-evals-readiness) | Before building (R&D), before any tuning loop, and again before go/no-go |
| 6 | [Durable state and human-in-the-loop review](#6-durable-state-and-human-in-the-loop-review) | Before go/no-go when a step waits for a person or has an irreversible side effect |
| 7 | [Scale review](#7-scale-review) | Before the first parallel batch and before go/no-go |
| 8 | [Security review](#8-security-review) | Before the agent gets real data, tools or a public address; before go/no-go; when a tool, data source or deployment target is added |
| 9 | [Context layer and memory review](#9-context-layer-and-memory-review) | When adding a context source, memory or a gateway integration; before go/no-go |
| 10 | [Self-improvement review](#10-self-improvement-review) | Before switching on an improver loop, and before widening what it may change |
| 11 | [Copilot review](#11-copilot-review) | Before building a user-facing agent and before shipping it |
| 12 | [Production readiness on AWS](#12-production-readiness-on-aws) | Before the first deploy to a shared or client account and before release approval |
| 13 | [Build-process gate for coding-agent phases](#13-build-process-gate-for-coding-agent-phases) | At the end of every build phase and every build |
| 14 | [Handover](#14-handover) | End of implementation (program success tollgate), before final teardown |

Which lists to bring to each tollgate (guidance, matching the lifecycle in [fde-lifecycle-and-governance.md]):

| Tollgate | Decision | Run |
|---|---|---|
| End of discovery | Agree scope and budget | 1 |
| End of R&D | Approve the build | 2, 4, 5, and a first pass of the threat model from 8 |
| End of development | Go/no-go | 3, 5, 6, 7, 8, 9, plus 10 and 11 if the project has them; 13 for every phase |
| End of implementation | Program success | 12, 14 |
| Maintenance | Change management | 4, 5, 8 again on any change; 10 before any new lever |

## How to use

1. **Load only the lists you run.** Ask the items in small groups, not the whole list at once, and restate what you heard.
2. **Mark every item pass, fail or n.a., with evidence:** a file path, a test name, command output, a trace, a screenshot. No evidence means not pass. An n.a. needs a one-line reason.
3. **Check the evidence yourself** by reading the file or running the project's own checks. Do not tick an item on the developer's say-so, and do not create, change or delete cloud resources to gather evidence unless the developer asks.
4. **Turn every fail into a task in the plan or an ADR** ([ADR.md](../assets/templates/ADR.md)) with an owner and a date.
5. **A fail on a [blocker] item stops the tollgate.** It passes again only when the item is fixed, or (this skill's convention) when the accountable owner records a time-boxed exception in an ADR. Never relabel a blocker to get through.
6. **Re-run the list after any change it covers.** A review of the old system says nothing about the new one.

Record the result in the review note or the plan, one row per item that is not a plain pass:

```markdown
| Checklist.item | Result | Evidence | Follow-up |
|---|---|---|---|
| Security: input screened before the first model call | pass | agent/graph.py first node; test_screen_runs_first | none |
| Security: false-alarm test | fail | 2 of 25 ordinary items flagged | Task: fix check instructions, rerun. Owner, date |
```

## 1. Discovery tollgate

Purpose: decide scope and budget. A pass means the problem, the numbers, the owner, the data and the privacy posture are settled enough to fund a prototype. Fill [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md) as you go.

- [ ] **[blocker]** The problem is a measurable business problem (who has it, how often, what it costs today), not "an agent for X", and a non-agent route (rules, one structured call) was considered ([fde-lifecycle-and-governance.md])
- [ ] **[blocker]** Every success criterion states a measure, a baseline (today's number without the agent) and a target the sponsor agreed ([fde-lifecycle-and-governance.md])
- [ ] **[blocker]** At least one limit criterion (something that must always hold) sits beside the performance criteria, and each criterion says who computes it from which records ([fde-lifecycle-and-governance.md])
- [ ] The cost of each kind of mistake is written in money, agreed with the business and kept apart from API cost ([evals-and-observability.md])
- [ ] **[blocker]** A sponsor and an accountable owner are named people (not "the AI team"), and the owner still owns the agent after launch ([fde-lifecycle-and-governance.md])
- [ ] **[blocker]** Data access is real: the data exists, its owner is named, access is approved, and expert-labelled past decisions exist (or have a plan and a date) for the eval sets ([fde-lifecycle-and-governance.md])
- [ ] **[blocker]** The privacy posture is an ADR: what personal or confidential data reaches the model provider, the provider's training and retention terms, the region, and nothing confidential on free models ([models-and-cost.md])
- [ ] The use case is classed as automation, acceleration or differentiation, and the metric matches (cost per unit, elapsed time, a new outcome) ([fde-lifecycle-and-governance.md])
- [ ] The systems the agent must read or write are listed with their APIs, owners and who approves access ([context-layer-and-integrations.md])
- [ ] A first autonomy proposal exists per action (automatic, approval first, prohibited), including what the agent must never do or see ([fde-lifecycle-and-governance.md])
- [ ] A "Not for now" list of non-goals is written down, so scope cannot grow unnoticed ([fde-lifecycle-and-governance.md])
- [ ] Budget and deadline cover model spend and cloud spend, and name who watches them ([models-and-cost.md])
- [ ] The adoption plan names the users, who trains them, the sponsor who expects the change, and how accuracy will be shown to them ([fde-lifecycle-and-governance.md])
- [ ] The handover is agreed now: who runs the system after launch and what they need (runbook, dashboards, escalation path) ([fde-lifecycle-and-governance.md])
- [ ] Early big choices (build or buy, where it runs, which systems it reaches) are ADRs with options and reasons ([agent-architecture.md])
- [ ] **[blocker]** The sponsor recorded an explicit go/no-go on scope, budget, owner and criteria; later changes go through change management ([fde-lifecycle-and-governance.md])

## 2. Architecture review

Purpose: approve the build. A pass means the shape is the simplest one that meets the criteria, the rules live in code, and every system and owner is named. Fill [ARCHITECTURE.md](../assets/templates/ARCHITECTURE.md).

- [ ] **[blocker]** "Agent or not" is justified by a measurement: a single structured-output call was tried on the eval set, and an agent is used only where the path varies or a gap was measured ([agent-architecture.md])
- [ ] The shape is the lowest rung that meets the criteria (call, chain, workflow, single agent, multi-agent) and an ADR says why ([agent-architecture.md])
- [ ] Each extra agent maps to one of the five reasons (isolate context, independent check, different model, parallel work, ring-fenced permissions) and an eval shows a gain beyond noise ([agent-architecture.md])
- [ ] Fixed-rule choices (which item next, ordering, routing) are code, not a model ([agent-architecture.md])
- [ ] **[blocker]** Business logic (calculations, thresholds, limits, state transitions) is deterministic code at the system of record; the model supplies judgement and inputs only ([agent-architecture.md])
- [ ] Structured outputs: rationale before decision and amount, closed sets as enums, every field described with units, unreadable replies handled by a code retry policy ([agent-architecture.md])
- [ ] **[blocker]** Each action has an autonomy tier (automatic, approval first, prohibited), and each tier is enforced outside the model, in more than one layer for consequential actions ([agent-architecture.md])
- [ ] Each source of data (gateway rules, context layer, memory, system of record) has a named owner and an agent access mode, and the placement test was applied ([context-layer-and-integrations.md])
- [ ] The agent reaches business records only through the app's API, and the API is designed for tools (operation id, one-line docstring, no optional inputs) ([agent-architecture.md])
- [ ] The framework is the lightest that gives the control needed (durable pauses, model portability); tools and prompts stay portable ([agent-architecture.md])
- [ ] Where it runs (own infrastructure, managed runtime, model lab) is an ADR with options, evidence and a revisit trigger ([production-deployment-aws.md])
- [ ] Systems around the agent (gateway, context layer, memory) exist only against a shown need; the design is as simple as possible ([agent-architecture.md])
- [ ] The human step is designed: when it triggers, what the person sees, what is recorded, who may answer, what happens on delay ([durable-state-and-hitl.md])
- [ ] Failure behaviour is written down for the model, each tool and the system of record being down, and one bad item cannot stop a run ([harness-engineering.md])
- [ ] Cost per unit of work is estimated and compared with the human baseline and the cost of mistakes ([models-and-cost.md])
- [ ] The ADR index is complete, and each ADR names options, evidence and what would trigger a revisit ([agent-architecture.md])

## 3. Harness and tools review

Purpose: check the code around the model. A pass means the agent can do only what the tool list says, the backend referees every action, and failures are handled in one place.

- [ ] **[blocker]** The agent never touches the database: every tool calls the system's API, so the backend's rules apply to it as to any client ([harness-engineering.md])
- [ ] The tool list is exactly the expected set, each tool named after the backend operation it calls, and a test asserts it ([harness-engineering.md])
- [ ] **[blocker]** Item, customer and user ids come from a run context set by the harness, not from model-chosen tool inputs ([harness-engineering.md])
- [ ] Each tool has a one-line description, typed arguments, closed choices as enums, units in the field descriptions and no optional inputs ([harness-engineering.md])
- [ ] **[blocker]** A side effect that must always follow a decision (payment, send, write) is a code step or graph node, not a tool the model might skip or repeat ([harness-engineering.md])
- [ ] The backend is the referee: it refuses repeats, a different decision on a decided item and over-limit actions; expected refusals go back to the model as readable tool messages, unexpected failures propagate ([harness-engineering.md])
- [ ] Calculations run in a deterministic tool, the decision record keeps the calculation, and the backend checks the recorded amount equals the tool's ([agent-architecture.md])
- [ ] Long documents arrive as contents plus search and read-section tools, not in every prompt, and a test checks the contents hold titles only ([harness-engineering.md])
- [ ] Instructions state a goal, what the agent has to go on, what holds whatever it does and what done looks like; no numbered scripts, and any required order is in code ([harness-engineering.md])
- [ ] Instructions are written from the policy and manual, never from the eval answer key, and live in versioned files, not scattered through code ([harness-engineering.md])
- [ ] Each item is worked in a fresh context, and the one-line report is built from the system of record, not from the model's closing text ([harness-engineering.md])
- [ ] **[blocker]** Failure handling is in one place: every exception caught per item, an item with no decision marked failed, one retry then left for a handler, a model-call cap per item, never decide or pay twice ([harness-engineering.md])
- [ ] Outcome states stay distinct (referral, held for sign-off, left for a handler, waiting) in the data, the UI and the metrics ([harness-engineering.md])
- [ ] Every step is recorded for people (model messages, tool calls with arguments, results, refusals, guardrail verdicts, cost, time) and traced for engineers ([harness-engineering.md])
- [ ] Tests use a stub model and cover: limit held, provider failure, second failure, no decision, loop cap, error after a decision, a refused call, fresh-start prompts ([harness-engineering.md])
- [ ] A fresh reviewer checked structure and framework idioms (URLs written once, one way to call the backend, one job per module), not just green tests ([harness-engineering.md])

## 4. Model and cost review

Purpose: confirm the model choice is evidence-based and the spend is bounded at three levels. Run it again whenever the model, a price, the prompt or the provider changes.

- [ ] **[blocker]** The model was chosen by running the pipeline you will ship on your own eval set, not from a leaderboard alone; the decision, numbers and date are in an ADR ([models-and-cost.md])
- [ ] The quality bar was fixed first (accuracy floor, cost per item, seconds per item), then the price ladder was walked down to the cheapest model and lowest reasoning level that clears it every run ([models-and-cost.md])
- [ ] Each candidate ran at least three times, noise was measured, and a difference below the noise counts as none ([models-and-cost.md])
- [ ] The comparison includes a naive baseline and the single-call baseline, with the same prompt and tools for every model ([models-and-cost.md])
- [ ] Model and reasoning effort live in versioned configuration with one environment override, one factory builds every chat model, and allowed reasoning levels are stored per model ([models-and-cost.md])
- [ ] Provider routing is constrained where it matters (require parameters, ignore a misbehaving provider), and the answering provider and reasoning level are recorded per response ([models-and-cost.md])
- [ ] **[blocker]** Cost per unit of work is recorded per call, item and run from the provider's usage, including failed attempts, screening, judge and improver calls ([models-and-cost.md])
- [ ] Model cost per item was compared with the cost of mistakes and the human baseline, both ways, before choosing a cheaper or stronger model ([models-and-cost.md])
- [ ] **[blocker]** Limits exist at three levels: in code (per-job spend, model-call cap), on the provider key (credit limit) and on the cloud account (budget with alerts) ([models-and-cost.md])
- [ ] Every model call has a timeout and retries, and output tokens are capped where a runaway reply is possible ([models-and-cost.md])
- [ ] Prompts put stable text first for caching, the prompt size was trimmed and the accuracy effect measured, and the context window fits the largest realistic prompt ([models-and-cost.md])
- [ ] **[blocker]** Data sent to each provider matches the privacy ADR: personal data minimised, training and retention terms checked, free endpoints used for fictional data only ([models-and-cost.md])
- [ ] Open-weight or local models are chosen for a stated privacy, control or sovereignty need, hardware and operations are costed, and the base URL is a setting ([models-and-cost.md])
- [ ] A different model per step has a stated reason (cheap screening, stronger improver, judge different from the agent) ([agent-architecture.md])
- [ ] Prices and model names sit in one dated config file, and the evals re-run after any model, price, prompt or provider change ([models-and-cost.md])

## 5. Evals readiness

Purpose: make sure success can be measured before building and judged honestly after. Fill [EVAL_PLAN.md](../assets/templates/EVAL_PLAN.md).

- [ ] **[blocker]** Each success criterion is a measure with a baseline and a target in the eval plan, with an owner and business sign-off, written before building ([evals-and-observability.md])
- [ ] The cost-of-mistakes matrix is agreed with the business, and the preferred design was tested against a change in the most contested cost ([evals-and-observability.md])
- [ ] **[blocker]** Sets are separate: evaluation, held-out and a final test set (plus an adversarial set and a tiny smoke set); the tuning loop never reads held-out items and the final set is touched once ([evals-and-observability.md])
- [ ] **[blocker]** The answer key lives in one owned place that the agent's tools, prompt, memory and retrieval index cannot reach, the coding agent is told not to open it, and a grep or test guards that ([building-with-coding-agents.md])
- [ ] Labels come from the people who do the work today, with the expert's reason and the reference it rests on, plus difficulty tags ([evals-and-observability.md])
- [ ] Metrics include strict and decision accuracy, a confusion matrix, kappa, straight-through (every non-referral, held approvals included) and cost of mistakes; code measures whatever has one right answer ([evals-and-observability.md])
- [ ] Naive baselines (approve everything, refer everything) and the human baseline are scored through the same metrics ([evals-and-observability.md])
- [ ] **[blocker]** Noise was measured (same version, run twice) and thresholds set from it; comparisons use the same model, reasoning level, set and run count, and nothing rests on one run of about 25 items ([evals-and-observability.md])
- [ ] The set is large enough that one item is a small step for the gain you care about ([evals-and-observability.md])
- [ ] Cost and active time per item and per run are recorded beside quality, with the run's identity (set, version, model, reasoning, agents at once); judge cost is separate ([evals-and-observability.md])
- [ ] **[blocker]** Evals run on copies through the same dispatcher and agent: copies never reach the live queue, cannot be signed off or paid, run without memory, and run one at a time ([evals-and-observability.md])
- [ ] Unit tests never call a model; evals do; live runs are few, capped and made on freshly seeded data ([building-with-coding-agents.md])
- [ ] Every item is traced with a session id and the run's tag, and one wrong item's trace was read before any scoring ([evals-and-observability.md])
- [ ] Retrieval is scored separately where the agent searches (needed facts found, precision, recall, MRR) ([evals-and-observability.md])
- [ ] The success-criteria check is computed in code from records and says "not known" when an evaluation cannot finish ([evals-and-observability.md])
- [ ] A scoreboard shows every measure newest first, each run opening to items beside the expert's answer, and a production schedule covers re-runs, drift checks and a human sample ([evals-and-observability.md])

## 6. Durable state and human-in-the-loop review

Purpose: check that a crash, a restart or a slow human cannot lose work, repeat a side effect or bypass a limit. Applies to any design with a pause or an irreversible action.

- [ ] **[blocker]** State lives in a database with one thread per work item; nothing the next process or session needs lives in memory ([durable-state-and-hitl.md])
- [ ] **[blocker]** The checkpointer writes after every step (durability sync) to the production database, with connection settings verified for the pooler in use ([durable-state-and-hitl.md])
- [ ] **[blocker]** Every side effect has a node of its own, guarded by an idempotency check on the item id in the system of record, so a repeat counts as done ([durable-state-and-hitl.md])
- [ ] **[blocker]** Nothing with a side effect runs before `interrupt()`; the pause node holds only the interrupt ([durable-state-and-hitl.md])
- [ ] The backend decides whether sign-off is needed from a setting, the graph never compares amounts itself, and the backend refuses an over-limit action with no sign-off and records nothing ([durable-state-and-hitl.md])
- [ ] "Held for sign-off" and "referred" are different states and are counted correctly in metrics ([durable-state-and-hitl.md])
- [ ] The person has two answers, sign off and send back with a required note, and the note is handled as a review (a code-written message tells the model to check it against policy), not a command ([durable-state-and-hitl.md])
- [ ] The human's answer is read from your own record, and the resume request names only the work item ([durable-state-and-hitl.md])
- [ ] Who may answer is enforced in the backend by role, the approver and time are recorded, and the review screen shows evidence read from the record ([durable-state-and-hitl.md])
- [ ] The approver is resolved from the record, differs from the requester, and an absent approver escalates (general practice, not from the course)
- [ ] **[blocker]** The sign-off and the payment stand if the agent is down; the resume call is best-effort and a send-back the agent missed is picked up by the next dispatch ([durable-state-and-hitl.md])
- [ ] Decisions are final: a different decision on a decided item is refused, and a deliberate send back is the only route round it, keeping the history ([durable-state-and-hitl.md])
- [ ] "Is it paused?" is checked with `get_state(...).interrupts`, not `next` ([durable-state-and-hitl.md])
- [ ] Asks are limited to where the human adds judgement or authority, and delays have a timeout, an escalation and a backup approver ([durable-state-and-hitl.md])
- [ ] **[blocker]** A crash test passed: kill the process mid-run, restart, and see the same thread, the same attempt count, one decision and one payment; calling the pay step twice makes one payment ([durable-state-and-hitl.md])
- [ ] Resume in a new process or session was shown (kernel restart, or a new runtime session loading the thread) ([durable-state-and-hitl.md])
- [ ] Rewind is not used as undo; any reversal (a refund) is its own step with its own approval ([durable-state-and-hitl.md])
- [ ] Node names and state fields stay stable for threads that may wait days (verify against your LangGraph version) ([durable-state-and-hitl.md])

## 7. Scale review

Purpose: check that running many items at once is bounded, retry-safe and observable. Skip items that do not apply when the project processes one item at a time.

- [ ] The items are independent and alike (a swarm is justified), and the next item is chosen by code, not a model ([swarms-and-scale.md])
- [ ] Each item has its own worker and thread, with no shared thread or subgraph, and its trace is tagged with the run id ([swarms-and-scale.md])
- [ ] **[blocker]** Concurrency is capped (`max_concurrency`) within the model provider's rate limit and the database's connection limit, starts small and is widened while watching 429s, connections and per-item time ([swarms-and-scale.md])
- [ ] **[blocker]** Connection arithmetic is written down (pool per process times processes, plus the provider's own) and fits the plan's limit; pools wait instead of failing, and each worker has its own saver ([swarms-and-scale.md])
- [ ] **[blocker]** Only transient errors (rate limit, timeout) are retried, with growing waits, resuming from the last checkpoint; any other error goes back to the queue once, then is left for a handler ([swarms-and-scale.md])
- [ ] **[blocker]** Retries are safe because the backend never decides or pays twice, and a test sends duplicates ([swarms-and-scale.md])
- [ ] Failure handling is tested with at least two workers, and retry waits are zero in tests ([swarms-and-scale.md])
- [ ] One bad item never stops a dispatch, and an item stuck in progress is recovered at the next start ([swarms-and-scale.md])
- [ ] **[blocker]** One run at a time is enforced by a database lock, not process memory; a second start is refused with a 409 naming what is running, and a heartbeat with a quiet timeout marks dead work stopped ([swarms-and-scale.md])
- [ ] The run is created and committed before the agent is asked, the agent call is one attempt, and "never reached" is handled differently from "may have started" ([swarms-and-scale.md])
- [ ] Cost and active time are recorded per item with the run id, waiting for a human is not counted, and totals include failed attempts ([swarms-and-scale.md])
- [ ] Per-item time was compared at the chosen N and at N=3 to detect contention, and one run is treated as noisy ([swarms-and-scale.md])
- [ ] The sign-offs and referrals a swarm creates are counted against the capacity of the people who review them ([swarms-and-scale.md])
- [ ] Free-model or new-account limits (about 20 requests a minute) are known and N is set to match ([models-and-cost.md])
- [ ] After a restart mid-dispatch, items carry on from their checkpoints as the same attempt and decided items are not listed again ([swarms-and-scale.md])

## 8. Security review

Purpose: check that no single failure (a steered model, a leaked key, a bad prompt) can cause a consequential action. Fill [THREAT_MODEL.md](../assets/templates/THREAT_MODEL.md) alongside it.

- [ ] The three risks were assessed for each feature (runtime, APIs, prompt injection) and the threat model has assets, actors, residual risk and a sign-off ([security-and-guardrails.md])
- [ ] **[blocker]** The lethal trifecta (private data, untrusted content, external communication) was assessed per agent, counting retrieved documents, tool results and memory as untrusted content, and at least one leg is broken by design ([security-and-guardrails.md])
- [ ] **[blocker]** Identifiers are bound in code, so the model can act only on its own item and read only its own customer's data ([security-and-guardrails.md])
- [ ] **[blocker]** Untrusted input is screened before the agent's first model call by a model check with structured output (reason first), reading every customer-written field and every retrieved or tool-returned document the agent will read ([security-and-guardrails.md])
- [ ] **[blocker]** The check fails closed: a flagged item is referred to a person with the reason, and an unreadable answer is retried and then fails the item, never passes it ([security-and-guardrails.md])
- [ ] **[blocker]** A false-alarm test ran the check over ordinary items (zero flags expected), and bypass tests (reworded, translated, in a document field, a smaller model) became regression cases ([security-and-guardrails.md])
- [ ] The check, limits, eval sets and approvals sit outside the versioned configuration that an improver or the agent can change ([security-and-guardrails.md])
- [ ] **[blocker]** Each consequential action has at least three independent layers, none of them only the prompt (agent check, gateway policy, app limit, human sign-off), and each was tested alone ([security-and-guardrails.md])
- [ ] Dangerous capability is removed where possible (an over-limit payout is paid only by a sign-off, and is not a gateway tool) ([security-and-guardrails.md])
- [ ] Prohibited actions have no tool at all, and handler-only routes refuse the agent's key with a 403 ([security-and-guardrails.md])
- [ ] **[blocker]** The agent has its own API key (random, 32+ characters, constant-time compare, unset means refuse all), people sign in themselves, and the key never stands in for a person or sits in a frontend setting ([security-and-guardrails.md])
- [ ] Every route has exactly one gate, and a test proves the gate lists name every operation once ([security-and-guardrails.md])
- [ ] **[blocker]** Secrets sit in a vault and are fetched on the first request; none is in the repo, image, frontend, checkpoints, traces or logs, and user tokens are never saved ([security-and-guardrails.md])
- [ ] Gateway policy rolled out log-only, then enforce, after reading its decisions; a policy refusal routes to a held item (no retry loop); limits in the policy match the app's setting ([security-and-guardrails.md])
- [ ] **[blocker]** Public endpoints are listed and each is protected in the app; internal services use IAM auth; the accepted exposure of a public function URL and what throttles it is written down ([security-and-guardrails.md])
- [ ] **[blocker]** IAM is least-privilege: separate narrow roles for app, runtime, gateway and operator, name-prefix scoping, `PassRole` limited, root MFA on, wildcards reviewed by the client's security team ([security-and-guardrails.md])
- [ ] Third-party MCP servers are treated as code running with the agent's authority: pinned, read-only where possible ([rag-memory-and-mcp.md])
- [ ] Privacy: data to the provider is minimised, traces and logs are treated as copies of the data, log retention is set and SDK debug logging is off ([security-and-guardrails.md])
- [ ] Output rendering (links, images, markdown) cannot exfiltrate data (general practice, not from the course)
- [ ] Residual risk has an owner and a review date, and the record says no set of checks makes an agent bulletproof ([security-and-guardrails.md])

## 9. Context layer and memory review

Purpose: check that every kind of knowledge sits in its owner's place and that the agent's memory cannot leak, poison or replace the record.

- [ ] Each piece of data was placed by the placement test (context layer, memory, database, gateway policy, instructions): no rules in memory, no agent notes in the context layer ([context-layer-and-integrations.md])
- [ ] **[blocker]** Each source has a named owner and an agent access mode (context layer read-only, memory read and write, database only through the API), and the agent cannot edit governed content ([context-layer-and-integrations.md])
- [ ] **[blocker]** Every context file carries source system, owner and review date (and a version for documents), the server or CI fails without them, and every answer returns that header ([context-layer-and-integrations.md])
- [ ] Review dates are shown to humans, a staleness threshold is agreed with the owner, and fixes to wrong content go to the owner, not into the build ([context-layer-and-integrations.md])
- [ ] The client's existing catalog, MDM or glossary was searched for before building, and build or buy is recorded ([context-layer-and-integrations.md])
- [ ] The context server is read-only, loads files once at start, has small strict inputs, refuses with a reason, and its search was tested on near-miss phrases ([context-layer-and-integrations.md])
- [ ] The context server is not public (IAM auth) and sits behind the same gateway as the company APIs ([context-layer-and-integrations.md])
- [ ] **[blocker]** The agent reaches business records only through the app's API, with no direct database credentials beyond its own checkpoints ([context-layer-and-integrations.md])
- [ ] Customer and user identity are filled in by code from run context or the verified sign-in, never from model output ([context-layer-and-integrations.md])
- [ ] **[blocker]** Memory namespaces are per actor, derived from verified identity; a test shows another actor's namespace returns nothing, and prefix collisions (C-1 and C-10) were checked ([rag-memory-and-mcp.md])
- [ ] **[blocker]** Code saves only minimal data to memory (summary, decision), never free-text stories or source documents, never for a flagged item or an evaluation copy ([rag-memory-and-mcp.md])
- [ ] Memory is optional by configuration and fails soft: the decision stands, a warning is logged, a search failure reaches the model as a refusal ([rag-memory-and-mcp.md])
- [ ] Memory adds and never replaces: counts that drive rules come from the system of record, and a lookup that must always happen is done in code, not left to the model ([rag-memory-and-mcp.md])
- [ ] Memory is off or reset in evaluations, and tests allow for background extraction delay (about two minutes) ([rag-memory-and-mcp.md])
- [ ] Retention is set (event expiry) and a deletion procedure for one person's memories is written before launch ([rag-memory-and-mcp.md])
- [ ] **[blocker]** Each decision record is complete (decision, amount, calculation, rule relied on, reason, who decided, when, document version, sign-off) and the API refuses an incomplete one, naming the rule ([context-layer-and-integrations.md])
- [ ] Every lookup, memory search, memory save and refusal shows as a step, and a "context used" view shows file, owner and review date ([context-layer-and-integrations.md])
- [ ] Vectors were added only after beating a word-search baseline on the same eval set, with retrieval scored separately ([rag-memory-and-mcp.md])
- [ ] Retrieval enforces the caller's document permissions (no cross-user or cross-tenant retrieval), tested with two users (general practice, not from the course)
- [ ] Retrieved and ingested text is treated as untrusted; ingestion has provenance and an owner (general practice, not from the course)

## 10. Self-improvement review

Purpose: check that an improver loop can only make changes that are measured, approved and reversible. Do not build the loop until the first two items pass.

- [ ] **[blocker]** The preconditions hold: a labelled eval set, a separate held-out set, measured noise, an agreed cost of mistakes, and sign-in with roles; otherwise improve by hand ([self-improvement.md])
- [ ] **[blocker]** The judge is grounded: it sees the expert's reference reason, picks a grade from a fixed scale with a written rubric, writes no prose, and judges explanations only (code scores decisions and amounts) ([self-improvement.md])
- [ ] The judge is a different model from the agent, runs in the backend that holds the answers, has short timeouts, and sits outside the improver's reach ([self-improvement.md])
- [ ] The judge was calibrated on known cases and sampled against a human, and is recalibrated when the judge or rubric changes; an ungraded item is left out and a version with no grade is rolled back ([self-improvement.md])
- [ ] **[blocker]** Configuration (instructions, model, reasoning level) is versioned with diff, reason, proposer, approver, time, status and held-out scores, and every run records the version it used ([self-improvement.md])
- [ ] **[blocker]** A human approves every proposal and recipe change before it takes effect, the approver's role is enforced in the backend, the pause survives a restart, and the reviewer reads the diff and reason ([self-improvement.md])
- [ ] **[blocker]** Keep or roll back is decided by code on the held-out set using business-owned objectives, noise and tolerance that the improver cannot change ([self-improvement.md])
- [ ] **[blocker]** The improver sees held-out scores only, and cannot edit objectives, noise, tolerance, spend limit, allowed models, eval sets, judge, approval limit or guardrails ([self-improvement.md])
- [ ] A separate final test set exists, is touched once by nobody who tunes, and the held-out score is never quoted as the final result ([self-improvement.md])
- [ ] Noise comes from running one version twice, and is re-measured when the set or model changes ([self-improvement.md])
- [ ] Cheap, reversible levers (model, reasoning) are tried before prompt rules, and changes stay general (no item, customer or figure named) ([self-improvement.md])
- [ ] **[blocker]** Spend is capped twice: a per-round limit in code with an estimate before each evaluation, and a credit limit on the provider key; the improver's own model calls are capped per round ([self-improvement.md])
- [ ] The allowed-models list with prices is business-owned data, and a proposal outside it goes straight back to the improver ([self-improvement.md])
- [ ] One round is open at a time, its stages are visible, and a stopped round leaves the current version unchanged ([self-improvement.md])
- [ ] Each round's audit record holds the recipe version, settings, version tried, scores before and after, verdict and reason, approvers and cost; settings changes record who and when ([self-improvement.md])
- [ ] Sign-ups are off, sign-in uses an identity provider, and the backend verifies each token ([self-improvement.md])

## 11. Copilot review

Purpose: check that a user-facing agent can do exactly what its signed-in user can do, nothing more, with real confirmation before consequential actions.

- [ ] **[blocker]** The copilot acts with the signed-in user's own token; the back-office agent's key does not exist in it (no function, no credential fetched), and the backend refuses the agent's key on user routes ([copilot-pattern.md])
- [ ] **[blocker]** The token travels in the run context and payload only, never in graph config or state, checkpoints, steps, memory or logs; SDK logging is at INFO or above, and a test searches every store for the token ([copilot-pattern.md])
- [ ] Each turn starts by asking the backend who is signed in; a rejected token ends the turn before any model call; identity and role come from the backend, not the message ([copilot-pattern.md])
- [ ] **[blocker]** Permissions are checked in code before a confirmation card appears, the backend enforces again, and a test as a less-privileged user shows a decline and no payment ([copilot-pattern.md])
- [ ] **[blocker]** Only consequential actions need confirmation; the pause is its own node holding only `interrupt()`, and the card is filled from records, not from model text ([copilot-pattern.md])
- [ ] The answer is bound to the turn shown (a stale answer gets a 409), a held decision that changed is re-checked and cancelled, one sign-off per turn, and Cancel is always accepted ([copilot-pattern.md])
- [ ] No tool in the model's hands pays or signs off: the request is a schema the graph checks and pauses on, and tools run one at a time ([copilot-pattern.md])
- [ ] Conversations are durable (thread per conversation, checkpoint every step), one turn runs at a time, a stuck turn is computed as stopped and refuses late updates, and dangling tool calls are closed ([copilot-pattern.md])
- [ ] Facts are computed in code: waiting for long work polls in code with a timeout, "what needs a human" and the success-criteria table come from records, and the turn ends with the code-built text ([copilot-pattern.md])
- [ ] The success-criteria check says "not known" when the evaluation cannot finish and counts straight-through as the scoreboard does ([copilot-pattern.md])
- [ ] **[blocker]** Memory is per user from the verified sign-in, holds only the user's message and the answer, is separate from the back-office agent's memory, and a two-user test proves isolation ([copilot-pattern.md])
- [ ] It has its own runtime, a session per conversation (valid id length), the fewest credentials and a role allowed only its gateway tools; any route to the app's agent-only tools is closed ([copilot-pattern.md])
- [ ] Token expiry is handled (renew before sending), and the known gap for very long waits is written down ([copilot-pattern.md])
- [ ] Every tool call shows as a card with state, inputs and result, refusals are visible, and progress is polled, not guessed ([copilot-pattern.md])
- [ ] The scope is two or three named user jobs, with a model-call cap per turn, and what it will not do points to the existing screen ([copilot-pattern.md])
- [ ] The plan was reviewed by a second model, and acceptance was a scripted conversation on the deployed system covering bulk work, an explanation, a correction, a consequential action and the success criteria ([copilot-pattern.md])

## 12. Production readiness on AWS

Purpose: check that the deployed system is configured, bounded, observable and removable. Product names, limits and CLI versions are as taught (Oct 2026); re-check them. Do not create or delete AWS resources to gather evidence unless the developer asks.

- [ ] The account is set up: the plan the services need, MFA on root, a named IAM identity with a scoped policy (not root), billing access on, one region confirmed to have every needed service ([production-deployment-aws.md])
- [ ] **[blocker]** A monthly budget with email alerts (50, 80 and 100 percent) excludes credits and refunds, a test alert arrived, and the team knows AWS has no hard spending cap ([production-deployment-aws.md])
- [ ] **[blocker]** Settings come from the environment, secrets from a vault fetched on the first request, nothing sits in the repo, image, frontend or logs, and nothing runs at import time ([production-deployment-aws.md])
- [ ] **[blocker]** An access map lists who may call each piece and how it is checked (public URL plus app auth, IAM for internal services, invoke rights on the runtime for the app's role only) ([production-deployment-aws.md])
- [ ] The same code runs on the laptop and the platform; the entrypoint validates payloads, answers at once and registers background work as an async task ([production-deployment-aws.md])
- [ ] Limits are written down and the shorter ones tested: idle timeout, maximum session life, model timeouts and retries, concurrency, and platform-call time budget inside the caller's own timeout ([production-deployment-aws.md])
- [ ] **[blocker]** Recovery was shown on the deployed system (a session ended mid-work, a new one resumed from checkpoints) with the right pooler settings (transaction pooler, no prepared statements) ([production-deployment-aws.md])
- [ ] Calls to the platform are classified never reached, refused or may-have-started, only safe ones are retried, and platform debug logging that holds payloads is off ([production-deployment-aws.md])
- [ ] One run at a time uses a database lock and heartbeat, and no startup code marks all running work stopped ([swarms-and-scale.md])
- [ ] Packaging uses lockfile versions, the right architecture per component (ARM runtime, x86_64 Lambda), an import check per deploy target, the size limit and a pinned CLI version ([production-deployment-aws.md])
- [ ] Log groups have a retention period, logs were found for one session, traces work, cost per unit of work is known and alerts reach a person ([production-deployment-aws.md])
- [ ] Gateway policy is enforced after a log-only trial, the context server uses IAM auth, and every role is least-privilege ([security-and-guardrails.md])
- [ ] Regional availability of every service (for example Memory) was checked before choosing the region ([production-deployment-aws.md])
- [ ] **[blocker]** One end-to-end run on the deployed system used a real user flow (dispatch, sign-off, send back, a copilot question), and the same evaluation ran on laptop and deployed with time and cost compared ([production-deployment-aws.md])
- [ ] **[blocker]** A teardown plan exists: find resources by name or tag, delete in a working order (targets before the gateway, policies before the engine, bootstrap last), verify by name, by account-wide index and by cost ([production-deployment-aws.md])
- [ ] For client production, infrastructure as code is preferred so a reviewer can read what will be created, and the free or non-AWS route is documented if one is needed ([production-deployment-aws.md])

## 13. Build-process gate for coding-agent phases

Purpose: gate each phase of a build done with a coding agent. Passing the checks is not the same as being fit to merge, so this list pairs the automated gates with review and records.

- [ ] **[blocker]** A plan exists and the developer reviewed it before implementation: a design section, phases with checkbox criteria, written with no code ([building-with-coding-agents.md])
- [ ] The agent read the docs set (spec, tech stack, code standards, process, status, plan), and `AGENTS.md` is a short router, not an encyclopedia ([building-with-coding-agents.md])
- [ ] Criteria are specific and self-verifiable (exact outputs, status codes, commands), cover refusals, not-found, boundary and idempotency cases, and include architecture guards such as a grep for the answer key ([building-with-coding-agents.md])
- [ ] **[blocker]** Every criterion of the phase is ticked with evidence (command output, test, browser check), not "works" ([building-with-coding-agents.md])
- [ ] **[blocker]** The one `check` command is green (format, lint, types, unit tests with the coverage threshold, end-to-end where the API or UI changed) and the pre-commit hook ran ([building-with-coding-agents.md])
- [ ] **[blocker]** No gate was weakened: no `--no-verify`, lowered threshold, disabled rule or excluded file, confirmed by diffing the config files ([building-with-coding-agents.md])
- [ ] **[blocker]** Tests were added with the change, never call a model or the network, replace every external service with a stand-in, and never read `.env` ([building-with-coding-agents.md])
- [ ] **[blocker]** A fresh reviewer that did not write the code reviewed the diff against the code standards; findings were fixed, or the disagreement is stated in the report ([building-with-coding-agents.md])
- [ ] `STATUS.md` is updated (what is built, how to run it, honest known gaps) and the plan's boxes are ticked ([building-with-coding-agents.md])
- [ ] **[blocker]** The coding agent did not open the answer key, and no eval data appears in prompts, tests or code ([building-with-coding-agents.md])
- [ ] An import check per deployment target ran in a throwaway environment with only that target's dependency group ([building-with-coding-agents.md])
- [ ] The commit is small and per phase, the agent did not push, and no cloud resource was created or deleted unprompted ([building-with-coding-agents.md])
- [ ] Only what the docs ask for was built, with no work ahead of the plan ([building-with-coding-agents.md])
- [ ] Live model runs are few, capped (about five items), done last after one reseed, and their cost is reported from the app's records ([building-with-coding-agents.md])
- [ ] End of build: a whole-branch review and a human review happened, and each finding became a fix, a search for the same problem elsewhere, a retest and a rule in the docs ([building-with-coding-agents.md])
- [ ] For a large or risky build, a second model reviewed the plan first and the amendments are recorded; scripts work on Windows and macOS ([building-with-coding-agents.md])

## 14. Handover

Purpose: prove the client's team can run, measure, change and retire the system without the FDE. Fill [HANDOVER.md](../assets/templates/HANDOVER.md) and walk through it with the service owner.

- [ ] **[blocker]** A service owner and an accountable owner are named, have accepted, and have an escalation path with severities and response times ([fde-lifecycle-and-governance.md])
- [ ] **[blocker]** Runbooks exist for deploy, roll back, work stopped, rotate a key and teardown, with exact commands and expected output, and the client's team followed them once without the FDE ([production-deployment-aws.md])
- [ ] **[blocker]** The client can re-run the evals: sets, command, pass bar, owner and last results are written, the success criteria are shown against baseline and target, and the answer key's location is documented ([evals-and-observability.md])
- [ ] Success criteria are visible in daily operation (a screen or assistant that computes them from records) ([evals-and-observability.md])
- [ ] **[blocker]** Access and keys are inventoried: each credential, where it lives, who rotates it and how often; who may invoke the agent and sign off; an access review date; the FDE's own access ended ([production-deployment-aws.md])
- [ ] Known limits are listed (rate limits, caps, timeouts, what goes to a human, "not for now") with the open risks from the threat model ([fde-lifecycle-and-governance.md])
- [ ] Responsible-AI pillars each have an owner, a test or control, and a review date ([fde-lifecycle-and-governance.md]; the owner, test and date are general practice, not from the course)
- [ ] Monitoring and cost are handed over: logs, traces, alerts, budgets, expected cost per unit with an alarm level, and a usage report for sponsors ([models-and-cost.md])
- [ ] Change management is defined: who approves a new prompt, model, rule or version, with what eval evidence ([fde-lifecycle-and-governance.md])
- [ ] Users and approvers are trained (including how to send back with a note), accuracy was shown with eval results, and a feedback route for bad outputs has a named reader ([fde-lifecycle-and-governance.md])
- [ ] A sponsor has stated the expected new way of working, not only made a tool available ([fde-lifecycle-and-governance.md])
- [ ] The "what runs where" table (accounts, regions, deploy source, owners) and the ADR index match what is deployed ([agent-architecture.md])
- [ ] Context files have named data owners with review dates and a review cycle ([context-layer-and-integrations.md])
- [ ] The teardown steps and fixed costs (for example bootstrap resources) are documented and the steps were tested ([production-deployment-aws.md])
- [ ] Maintenance is scheduled: drift and bias checks, eval re-runs, and who reviews them and how often ([evals-and-observability.md])
- [ ] **[blocker]** The walkthrough was held, the service owner accepted in writing, and open items have owners and dates ([fde-lifecycle-and-governance.md])
- [ ] Feedback to the employer is written: what the product lacked and what to productise ([fde-lifecycle-and-governance.md])

## Pitfalls when running these lists

- Ticking from the developer's say-so with no evidence, or ticking the agent's own work as reviewed.
- Reading the whole list aloud at once. Ask in themed groups and write the answers down.
- Marking n.a. with no reason, or relabelling a blocker to get through a tollgate.
- Running a list once and never again after a model, tool, data source or deployment change.
- Reviewing only the happy path: also check refusals, restarts, duplicates and the "what if the agent is down" case.
- Letting the author be the only reviewer. A fresh reviewer, a second model or the developer must look too.

## Related

- [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md): tollgates, autonomy, handover
- [agent-architecture.md](agent-architecture.md), [harness-engineering.md](harness-engineering.md), [models-and-cost.md](models-and-cost.md): checklists 2 to 4
- [evals-and-observability.md](evals-and-observability.md), [self-improvement.md](self-improvement.md): checklists 5 and 10
- [durable-state-and-hitl.md](durable-state-and-hitl.md), [swarms-and-scale.md](swarms-and-scale.md): checklists 6 and 7
- [security-and-guardrails.md](security-and-guardrails.md), [context-layer-and-integrations.md](context-layer-and-integrations.md), [rag-memory-and-mcp.md](rag-memory-and-mcp.md): checklists 8 and 9
- [copilot-pattern.md](copilot-pattern.md), [production-deployment-aws.md](production-deployment-aws.md), [building-with-coding-agents.md](building-with-coding-agents.md): checklists 11 to 13
- [undercover-case-study.md](undercover-case-study.md): the whole system, to compare against
- Templates: [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md), [ARCHITECTURE.md](../assets/templates/ARCHITECTURE.md), [EVAL_PLAN.md](../assets/templates/EVAL_PLAN.md), [THREAT_MODEL.md](../assets/templates/THREAT_MODEL.md), [HANDOVER.md](../assets/templates/HANDOVER.md), [ADR.md](../assets/templates/ADR.md)

## Sources

- Every item is distilled from the topic reference it links to; those files cite the course material (Weeks 1 to 3, as taught Oct 2026), the week guides in `guides/for_agents/` and Ed's reference builds.
- Tollgate evidence and the lifecycle: Week 3 Day 1 slides 5 to 16 via [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md). Production walk-through: [production-deployment-aws.md](production-deployment-aws.md). Threat-model and eval structure: the templates above.
- The pass, fail, n.a. recording method and the blocker-exception convention are this skill's own guidance, not taught in the course.

[fde-lifecycle-and-governance.md]: fde-lifecycle-and-governance.md
[agent-architecture.md]: agent-architecture.md
[models-and-cost.md]: models-and-cost.md
[harness-engineering.md]: harness-engineering.md
[building-with-coding-agents.md]: building-with-coding-agents.md
[evals-and-observability.md]: evals-and-observability.md
[self-improvement.md]: self-improvement.md
[rag-memory-and-mcp.md]: rag-memory-and-mcp.md
[durable-state-and-hitl.md]: durable-state-and-hitl.md
[swarms-and-scale.md]: swarms-and-scale.md
[security-and-guardrails.md]: security-and-guardrails.md
[context-layer-and-integrations.md]: context-layer-and-integrations.md
[production-deployment-aws.md]: production-deployment-aws.md
[copilot-pattern.md]: copilot-pattern.md

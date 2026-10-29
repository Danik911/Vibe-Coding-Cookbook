# Decision guide: designing an AI architecture with a developer

> When to read this: you are sitting with a developer to design the AI or agentic architecture of a new project (or to review one) and need to know what to ask, in what order, which options to offer and what to write down. Load this file first for a design session, then load a topic reference only for the stage you are in. Product names, limits and prices are as taught in the course (Oct 2026); re-check them.

## Contents

- [Key principles](#key-principles), [How to run an architecture session](#how-to-run-an-architecture-session) (protocol, rounds, option cards)
- [The session flow](#the-session-flow): stages A to N, each with questions, a decision aid, a default, red flags and an output
- [The default starting architecture](#the-default-starting-architecture), [Anti-patterns](#architecture-anti-patterns-to-challenge), [Wrap-up](#wrap-up), [Related](#related), [Sources](#sources)

## Key principles

See [SKILL.md core principles](../SKILL.md#core-principles). Additions for running a session:

1. **Say a risk once, then respect the decision.** Record it in the ADR; if the choice contradicts the project's own docs, flag the conflict and ask which wins. Why: the developer decides and answers for it.
2. **The stage order is a default, not a script.** Reorder by evidence, skip what is not needed now, and write "not for now" with its trigger. Why: every extra stage adds parts that need an owner.
3. **Turn what the developer cannot answer into an open question** with an owner, a date and a safe default, marked `TODO` or "assumption". Why: a silent guess is a decision nobody made.
4. **End each stage with a three-line recap: Decided, Open, Next.** Why: the developer corrects early, while it is cheap.
5. **A changed decision gets a new ADR that supersedes the old one.** Why: the history shows why the design is what it is.

## How to run an architecture session

You are the architect-advisor; the developer is the boss. You produce documents they review, then a plan; you build nothing in the session ("plan, review, then implement", see [building with coding agents](building-with-coding-agents.md)).

### Rules of the session

1. **Read first, then ask.** Read the repo and any docs (SPEC, AGENTS.md, discovery note) and skip questions they already answer.
2. **Ask before assuming.** If the developer does not know, log an open question (owner, date) with a safe default, mark it `TODO` or "assumption" in the docs, and move on.
3. **Few, high-value questions.** Three to six per batch, one theme, each with a default so "yes" is a valid answer. Ask only what could change the design. Never paste a question bank.
4. **Offer two or three options** with trade-offs, simplest first, a recommended default, the why in one line and the trigger that would change your mind. Define terms on first use; go deeper on request.
5. **Record each decision as an ADR when it is made** ([ADR.md](../assets/templates/ADR.md)), with options, evidence and the revisit trigger. Keep the open-questions list in ARCHITECTURE section 13.
6. **Say a risk once, then respect the decision.** Record the risk under the ADR's Consequences. If the choice contradicts a rule in the project's own docs (a limit in SPEC), flag the conflict and ask which wins.
7. **Stay in scope.** Decide which stages are needed now; write the others as "not for now" with the trigger that would bring them in.

Get **explicit agreement** before any of these, and never assume it:

| Area | Examples |
|---|---|
| Cloud | Creating, changing or deleting any resource; a deploy; a teardown. Never unless the developer asks |
| Spend | Live model runs, paid services, budgets, key credit limits, evaluations or swarm sizes that cost money |
| Autonomy | What the agent may do alone; thresholds; who approves; anything that moves money, deletes, sends or changes access |
| Data | What goes to model providers, routers, tracing, memory or logs; anything beyond fictional data on free models |
| Irreversible or public | Public endpoints, key rotation or deletion, destructive migrations, relaxing a gate or guardrail |

### Rounds

```text
ask (3-6 questions, with defaults) -> summarise (restate answers; mark assumptions)
  -> propose (2-3 options, recommended default) -> confirm (pick, correct or defer)
  -> write (update the artefact, add the ADR, update open questions)
```

End each stage with a three-line recap: Decided, Open, Next. Option card:

```text
Decision:  <what>
Options:   A) <simplest> - <trade-off>   B) <...> - <trade-off>   C) <...> - <trade-off>
Recommend: A, because <one line>. Revisit when <trigger>.
Needs your agreement: <spend / cloud / autonomy / data sharing, if any>
```

Example round (UnderCover, stage F):

```text
Agent: Three questions, defaults in brackets. 1) What may the agent do alone? [read, calculate, decide, pay up to
       a limit] 2) Limit and owner? [$1,000 setting, claims operations] 3) Who signs off above it? [one senior role]
Dev:   Defaults, but any handler may sign off.
Agent: A) one senior role (recommended: the limit is a control, so one accountable authority) B) any handler
       (faster, weaker). Your call; I will record B and the risk in ADR-0007.
```

## The session flow

```text
A Problem -> B Shape -> C Models -> D Harness and code -> E Knowledge -> F Autonomy and state -> G Evals
  -> H Security -> I Scale -> J Improve -> K Copilot -> L Deploy and cost -> M Build process -> N Handover
```

The order is a default. A and B come first; C to H interact, so revisit them after G. I, J and K are "now or later": settle the trigger and write "not for now". Do M before the first build. A pilot-sized project usually needs A to H, a light L, M and N. Lifecycle phases are in brackets ([FDE lifecycle](fde-lifecycle-and-governance.md)).

### Stage A: Problem and success criteria (Discovery)

**Ask**
1. Who has the problem, how often, what happens today step by step, who is the sponsor, who owns the agent after launch?
2. What does it cost now in time, money and errors (the baseline)?
3. Is it automation (cost per unit), acceleration (elapsed time) or differentiation (a new outcome, needs more discovery)?
4. What are two or three success criteria, each with a baseline, a target and who computes it? Is there one limit criterion that must always hold?
5. What does each kind of mistake cost the business, and who agreed the numbers? Which past decisions can serve as labels?
6. Which personal or confidential data would reach a model provider, which systems must it read or write, and what may it do alone, only with approval, or never (first proposal)?

| Finding | Then |
|---|---|
| No measurable problem or baseline | Stop; write them with the sponsor first |
| No data, access or way to score the work | Defer, or make data curation and a labelled set the first job |
| Metric, baseline, data and owner all exist | Go to stage B (with a non-agent baseline) |

- **Default:** one or two performance criteria plus one limit criterion, agreed at the first tollgate, computed in code from records.
- **Red flags:** "we need an agent for X"; a target with no baseline; criteria set after the results; no named owner; only performance criteria.
- **Output:** [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md) sections 1 to 11; [SPEC.md](../assets/templates/SPEC.md) (rules, success criteria, not for now). **Detail:** [FDE lifecycle](fde-lifecycle-and-governance.md), [evals](evals-and-observability.md).

### Stage B: Agent or not, and the shape (R&D)

**Ask**
1. Can every fact the model needs be known before the call?
2. Does the number or order of steps really vary by case?
3. Which steps have one right answer (calculations, thresholds)?
4. Is there a side effect (payment, email, record change)?
5. Does the work outgrow one context or need separate permissions? Which of the five reasons applies?

```text
Inputs known up front, one decision?              -> single structured-output call (the baseline)
Fixed sequence, code between steps?               -> chain of calls
Routing, branching, fan-out, paths known?         -> workflow (graph or plain code) with LLM steps
Path depends on what the model finds?             -> one agent in a harness
Isolate context | independent check | different model | parallel work | ring-fenced permissions,
  AND an eval shows the split helps?              -> add another agent
Always: calculations and side effects             -> code
```

- **Default:** a single-call baseline and an eval first; escalate only on a measured gap or a path that varies; one agent; `create_agent` or the team's framework, a hand-written graph once stage F needs it.
- **Red flags:** org-chart agents; numbered-step prompts; a model choosing the next item by a fixed rule; the framework chosen first.
- **Output:** [ARCHITECTURE.md](../assets/templates/ARCHITECTURE.md) sections 3 and 4; ADRs for agent versus workflow and the framework. **Detail:** [agent architecture](agent-architecture.md).

### Stage C: Models and reasoning (R&D)

**Ask**
1. What data may go to which provider (training and retention terms, free models only for fictional data)?
2. What quality bar, cost per unit and latency per unit?
3. One model for all, or one per step (screening, main, improver, judge)?
4. Is there a stated reason for open-weight or self-hosted models (privacy, control, sovereignty)?
5. What budget limits: per job, on the provider key, on the cloud account? Who can change them?

| Need | Choose |
|---|---|
| Quality first, data may go to a vetted provider | Frontier API, usually through a router |
| Cheaper or faster is enough, easy switching | Open-weight model on a router or direct host; pin or exclude providers |
| Contract or regulation keeps data under your control | Self-hosted open-weight model behind a base-URL setting |
| Prototype, offline, small private tasks | Local runner (Ollama) |
| Customer wants models inside their own cloud account | Cloud-native service (for example Bedrock); check the lineup and prices |

- **Default:** a router and a small cheap model; the cheapest model that clears the bar on your own evals, at least three runs each; model and reasoning level in versioned config with an environment override; prices in business-owned config; cost per unit recorded; a hard limit outside your code.
- **Red flags:** a leaderboard-only choice; one run; model names hard-coded; the budget only in code; confidential data on free models; "open weights" assumed private.
- **Output:** ARCHITECTURE sections 4 and 12; ADRs for model choice and for what goes to providers. **Detail:** [models and cost](models-and-cost.md).

### Stage D: Harness, tools and business logic in code (Development)

**Ask**
1. Which operations does the agent need on the system of record, and does each exist as an API operation?
2. Which rules and calculations are deterministic, and who owns them?
3. What must always happen, or happen in order (a guardrail, a payment, a retry)?
4. How big are the documents; can the agent search and read sections?
5. What happens when one item fails, and who is told? Who orchestrates a batch?

| If | Then |
|---|---|
| The answer is a formula | A calculation tool in the backend; the model supplies inputs, code computes |
| It must always happen or happen in order | A code step (graph node, hook), never an instruction |
| Documents are long | Contents in the prompt plus search and read-section tools; a context layer when several owners (stage E) |
| Items are picked by a fixed rule | A code dispatcher; a model orchestrator only when choosing needs judgment |
| A tool needs an id | Bind it from the run context, never a model input |

- **Default:** tools are the backend's API operations (one-line docstring, typed arguments, no optional inputs); instructions state goals, not scripts; fresh context per item; one retry through the queue, then left for a handler; separate outcomes for referral, held for sign-off and left for a handler; every step recorded; tests use a stub model.
- **Red flags:** the agent touching the database; scripts as instructions; arithmetic by the model; one catch-all "needs a human" state; hand-rolling what the framework provides.
- **Output:** ARCHITECTURE sections 2 and 3; ADR for where the rules live; TECH_STACK and code standards. **Detail:** [harness engineering](harness-engineering.md), [code patterns: agents](code-patterns-agents.md).

### Stage E: Knowledge and data sources (Development)

**Ask**
1. What must the agent know that is not in the input: how big, how structured, how often it changes, who owns it?
2. Which system is the record for each entity; is access read-only or read-write; what is the smallest write that does the job, and who checks it?
3. Does the client already run a data catalog, MDM or governance team to reuse?
4. Does the agent meet the same person again? Memory about whom, what may be saved, for how long?
5. Who else will use these tools: MCP or a plain function?

```text
Business team owns and reviews it (definitions, rules, manuals, plans) -> context layer (read-only; source, owner, reviewed)
The agent's observation about one customer or user                     -> memory (namespace per actor)
Official record with state that must be right                          -> database, through the app's API
Whether a call is allowed (limits, who may call what)                  -> gateway policy
Short, stable, needed on every call                                    -> the instructions
Retrieval: prompt -> keyword search plus read section -> vectors only if they beat that baseline -> agentic RAG when needs vary
MCP: plain tool for your own agent's logic; MCP for ready-made, shared or gateway-governed tools; read-only wherever possible
```

- **Default:** records through the app's API; keyword search over documents; no memory until an eval shows missing history matters; no vector database without a word-search baseline.
- **Red flags:** one mega-store; the agent editing the facts it relies on; memory as the record of truth; untrusted text saved to memory; identity taken from the model; governed files edited to unblock the agent.
- **Output:** ARCHITECTURE section 5; [CONTEXT_FILE.md](../assets/templates/CONTEXT_FILE.md) per file; ADRs for system of record, memory and retrieval. **Detail:** [context layer](context-layer-and-integrations.md), [RAG, memory and MCP](rag-memory-and-mcp.md).

### Stage F: Autonomy, human in the loop and durable state (Development)

**Ask**
1. For each action: reversible? money, legal or safety consequence? verifiable? So automatic, approval first or prohibited?
2. What is the threshold, is it a setting, who owns it, who may approve?
3. What does the person see and do (sign off, edit, send back with a note), and what if nobody answers (timeout, escalation)?
4. Can a run wait hours or days, or be cut off by a deploy or an idle timeout?
5. What must never happen twice?

| Condition | Design |
|---|---|
| Short run, no waits, safe to repeat | A plain agent loop; no durability |
| Waits on a person, long or costly, host can end the process | A hand-written graph, database checkpoints, a thread per item, `interrupt()` |
| Any side effect | Its own node, an idempotency check on the business key, a backend that treats a repeat as done |
| Approval over the threshold | Held for sign-off (decided; still straight-through), not referred (the agent could not decide) |
| Who pays after sign-off | The app, in the sign-off; the agent's resume only finishes the work |
| Approver depends on the item (e.g. the requester's manager) | The backend resolves the approver from the system of record, never the model; the approver is never the requester; no approver or a conflict -> escalate to a named backup (general practice, not from the course) |

- **Default:** the limit is a setting enforced by the backend; one senior role approves, checked in the backend; two answers, sign off or send back with a note; Postgres checkpointer with `durability="sync"`; nothing with a side effect before `interrupt()`.
- **Promoting an action to automatic** (general practice, not from the course): only after a shadow phase (the agent proposes, a human decides, you measure agreement) and a recorded decision; keep a kill switch back to approval first.
- **Red flags:** autonomy enforced by the prompt; too many asks (decision fatigue); "durable means exactly-once"; the agent paying after sign-off; the approver checked only in the UI; no audit trail.
- **Output:** ARCHITECTURE sections 6 and 7; one ADR per autonomy threshold; SPEC rules. **Detail:** [durable state and HITL](durable-state-and-hitl.md), [FDE lifecycle](fde-lifecycle-and-governance.md), [code patterns: LangGraph](code-patterns-langgraph.md).

### Stage G: Evals (R&D, then Development)

**Ask**
1. What does "right" mean: the decision only, or decision plus amount within a tolerance?
2. Where do labels come from (experts with reasons), how many items, who holds the answer key?
3. Which sets: eval, held-out, separate final test, adversarial? Which baselines: naive policies and the human baseline?
4. How many runs per comparison, and what noise threshold counts as a real gain?
5. Does free text need a judge?

| Output | Evaluate with |
|---|---|
| One right answer (decision, amount, label) | Direct measurement in code |
| Free text (rationale, summary) | A grounded judge with a reference answer and a fixed scale, calibrated; human sampling |
| Retrieval | Needed facts retrieved, scored apart from the answer |
| Security | An adversarial set kept apart from quality sets; ordinary items to count false alarms |

- **Default:** eval and held-out sets from day one, a final test set before any tuning loop; report both accuracy kinds, cost of mistakes, kappa, straight-through share, cost and time per item; traces tagged by run; evals run on copies; the answer key hidden from the agent and the coding agent.
- **Run counts:** model or prompt comparison: at least 3 runs each. Noise: run one version twice. Improver loop: 2 held-out runs per version, averaged.
- **Red flags:** accuracy alone; no naive baselines; tuning on the held-out set; a gain read from one run of 25; evals touching live data; the model writing the success verdict.
- **Output:** [EVAL_PLAN.md](../assets/templates/EVAL_PLAN.md); ARCHITECTURE sections 8 and 10. **Detail:** [evals and observability](evals-and-observability.md).

### Stage H: Security and guardrails (Development)

**Ask**
1. Per agent: what private data can it read, what untrusted text enters its context (every customer-written field, documents, tool results, memory), what outward channels exist?
2. Which trifecta leg can we remove?
3. Who calls what, as whom (agent key, user sign-in, IAM roles), and where does each secret live?
4. For each consequential action, which three layers would each stop it alone?
5. A key check and a model router, or a gateway now? Who reads the rules?

```text
All three trifecta legs present?   -> break one (cheapest: no outbound channel; else bind ids and scope data to the item)
Untrusted text reaches the model?  -> model check with structured output as the first node; flagged -> refer to a human;
                                      unreadable answer -> retry, then fail; test rewordings and false alarms
Consequential action?              -> agent or model check + gateway policy (log-only, then enforce) + app-side limit + sign-off
Several agents or apps need one policy and audit? -> gateway (AgentCore Gateway with Cedar); else key check plus router
```

- **Default:** the agent has its own API key (constant-time check, everything refused when unset), people sign in, a copilot uses the user's token, secrets sit in a vault and are fetched on the first request; one gate per route, tested; internal endpoints use IAM auth; roles scoped by name prefix; guardrails outside anything an improver can change.
- **Red flags:** the prompt as the only limit; a keyword-only check; the agent's key in a frontend setting or standing in for a person; a public endpoint assumed protected; a policy enforced on the first try; a token saved in checkpoints or logs.
- **Output:** [THREAT_MODEL.md](../assets/templates/THREAT_MODEL.md); ARCHITECTURE section 9; ADRs for identities, guardrail layers and gateway weight. **Detail:** [security and guardrails](security-and-guardrails.md).

### Stage I: Scale (Development; skip if volume is low)

**Ask**
1. Do items arrive in batches of independent items? What volume and time budget?
2. What limits sit outside the agents: model rate limits, database connections, people downstream?
3. May two runs overlap?
4. Which errors are transient?
5. How does work arrive (button, webhook, queue, poll), and what holds an item if the agent is down? (general practice, not from the course)
| Situation | Design |
|---|---|
| Items trickle in | One worker, no swarm |
| Independent batch, wall-clock time is the problem | An LLM-free dispatcher fanning out one thread per item, N capped; code picks items by a fixed rule |
| Failures | Retry only rate limits and timeouts, resuming from the checkpoint; other errors go back to the queue once, then are left for a handler |
| Overlap | A database lock with a heartbeat; not an in-memory flag |

- **Default:** start N small (3) and widen it while watching 429s, connection counts and time per item; record cost and active time per item and run (waiting for a person is not active time).
- **Red flags:** a model choosing the next item; one shared thread; unbounded N; blanket retries; testing failure handling with one worker.
- **Output:** ARCHITECTURE sections 6 and 12; an ADR for N and limits. **Detail:** [swarms and scale](swarms-and-scale.md), [code patterns: LangGraph](code-patterns-langgraph.md).

### Stage J: Self-improvement, now or later (Maintenance)

**Ask**
1. Do we have a labelled eval set, a held-out set, measured noise, an agreed cost of mistakes, human sign-in and roles?
2. Which levers may change (model, reasoning level, prompt rules), who approves, what budget per round?
3. Is hand-tuning still fast enough?

```text
Any precondition missing?                  -> improve by hand; record "later" with the trigger
All present AND hand-tuning is the bottleneck? -> versioned config + grounded judge + improver proposes,
                                              a human approves, code keeps or rolls back on the held-out set
```

- **Default:** later. When built: model and reasoning levers before prompt rules; thresholds from measured noise; a spending limit per round plus a credit limit on the key; objectives, limits, eval sets and the judge outside the improver's reach; a separate final test set.
- **Red flags:** the improver reading held-out items or editing its yardsticks; an ungrounded judge; click-through approvals; roles checked only in the UI.
- **Output:** ARCHITECTURE section 4 (improver); an ADR "now or later, with trigger"; EVAL_PLAN sections 6 and 7. **Detail:** [self-improvement](self-improvement.md).

### Stage K: User-facing copilot, or not (Development)

**Ask**
1. Which two or three user jobs (lookup, explain, start work, one consequential action)?
2. Is there a per-user identity and a stable API to act with?
3. Which actions need a confirmation card (money or irreversible only)?
4. Should it remember each user's preferences?

```text
No per-user identity, no stable API or no named jobs?  -> no copilot yet
Back-office agent and a user-authenticated API exist?   -> copilot as its own agent: the user's token, its own runtime,
                                                          a session per conversation, memory per user
Consequential action?                                    -> a schema, not a tool; code check; interrupt; card filled from records
```

- **Default:** none until the pilot is live; then reads, starting work and one confirmed action; the token lives in run context, never in state; facts and verdicts computed in code; progress shown as step cards.
- **Red flags:** the copilot using the agent's key or the gateway's app target; model-written figures; confirming everything; the token in checkpoints or logs; a general assistant with no named jobs.
- **Output:** ARCHITECTURE sections 4 and 7; an ADR "copilot: yes or not for now"; [FEATURE_BRIEF.md](../assets/templates/FEATURE_BRIEF.md). **Detail:** [copilot pattern](copilot-pattern.md).

### Stage L: Deployment on AWS and cost (Implementation)

Default target: AWS with Bedrock AgentCore as taught (Oct 2026). Confirm it with the developer; a client may mandate another cloud.

**Ask**
1. Where does the agent run, who operates it after handover, is there a cloud or region mandate?
2. Is the account ready: paid plan, root MFA, one region, a budget with alerts that excludes credits, a named scoped IAM identity?
3. How long can a run take, and can it wait for people (idle timeout versus registered work)?
4. What monthly budget and cost-per-unit target; who gets the alerts?
5. Which resources may we create now, and when do we tear down?

| Option | Choose when |
|---|---|
| AgentCore Runtime for the agent, Lambda for the app and context layer, Postgres for state | Default on AWS for long-running or human-in-the-loop agents |
| Own infrastructure (ECS, Cloud Run, Kubernetes, Render) | An existing platform and ops team, or the free route |
| The model lab's runtime | You accept one vendor's models and harness |

- **Rollout:** account, app deployable locally, Lambda, Gateway and Policy, context layer and Memory, hello-world Runtime, real agent, copilot, handover, teardown.
- **Default:** the same code on laptop and platform; nothing at import time; state in the database; budgets before resources; name and tag everything; tear down at the end of each session and verify by name, by account index and by cost.
- **Red flags:** a budget that counts credits; work on a thread the platform does not know about; prepared statements through a transaction pooler; a public Function URL assumed private; keys in git; no teardown.
- **Output:** ARCHITECTURE sections 11 and 12; ADR "where it runs"; HANDOVER sections 1, 4 and 5. **Detail:** [production deployment on AWS](production-deployment-aws.md), [code patterns: platform](code-patterns-platform.md), [code patterns: AWS AgentCore](code-patterns-aws-agentcore.md).

### Stage M: Build process with coding agents (before the first build, then throughout)

**Ask**
1. Which docs set (SPEC, TECH_STACK, CODE_STANDARDS, PROCESS, STATUS, a short AGENTS.md), and in whose voice?
2. Which gates (format, lint, types, unit tests with a threshold, end to end, hook, one check command), green on a skeleton on day one?
3. How autonomous may the coding agent be; which hard rules (never push, no cloud resources unasked, never weaken a gate)?
4. Which reviews: a fresh subagent per commit, a second model on big plans, a human at the end?
5. Which data must the coding agent never read (the answer key)?

- **Decide by size:** a small change is make, check, review, commit; a new feature is brief, plan with no code, review, implement phase by phase, review; a large or risky build adds a second-model review of the plan.
- **Default:** a plan with checkbox criteria the agent can verify; tests never call a model; build only what the docs ask; live model runs last, capped.
- **Red flags:** weakening gates; green tests taken as done; a bloated AGENTS.md; a stale STATUS; the coding agent reading the answer key.
- **Output:** [AGENTS.template.md](../assets/templates/AGENTS.template.md) (saved as `AGENTS.md` in the developer's repo), [PROCESS.md](../assets/templates/PROCESS.md), [PLAN.md](../assets/templates/PLAN.md) for the first build. **Detail:** [building with coding agents](building-with-coding-agents.md).

### Stage N: Handover (Implementation to Maintenance)

**Ask**
1. Who is the service owner, who is called for what, who runs it without you?
2. Which runbooks: deploy, rotate secrets, roll back, tear down?
3. How are the success criteria measured on the deployed system, who reviews them, how often?
4. Who trains the users and sponsors the change; how will accuracy and usage be shown to earn trust?
5. What are the known limits and gaps?
6. Which regulation or client policy applies? Which of the six responsible-AI pillars (safety, fairness and bias, security, privacy, transparency, accountability) need budget? Who sits at each tollgate?

- **Default:** the handover is designed on day one; evals re-run on the deployed system; cost per unit, budget alerts and teardown steps handed over; known gaps listed honestly; each pillar has an owner, a test or control and a review date (the last is general practice, not from the course).
- **Red flags:** the FDE as permanent operator; no named owner; no adoption plan; documents that no longer match the system; responsible AI left to a last-week review.
- **Output:** [HANDOVER.md](../assets/templates/HANDOVER.md); ARCHITECTURE sections 13 and 14. **Detail:** [FDE lifecycle](fde-lifecycle-and-governance.md).

## The default starting architecture

The baseline the course arrives at, in the order it was built. Start at build step 0 and add a step only when its trigger is measured, not because it is next. The triggers match the "Add when" column in [SKILL.md](../SKILL.md#course-default-stack-as-taught-oct-2026).

```text
Users -> App (API and UI: records, rules, limits, sign-in, audit) <-> Postgres (records, checkpoints)
              | starts and resumes runs
              v
         One agent behind the app's API (a hand-written graph once build step 3's trigger is met)
         tools = the app's operations; context lookups and memory only when justified
              v
         Models through a router; traces; evals on a held-out set
```

| Build step | Add | Add it only when | Detail |
|---|---|---|---|
| 0. Pilot | App as system of record with rules and the limit in code, a UI showing every step, one agent on the app's API; eval set and baselines first | Always | [agent architecture](agent-architecture.md) |
| 1. Harness | Search and read-section tools, a fresh context per item, retries, step recording | The prompt cannot hold the documents, long runs get costlier, or one failure stalls a batch | [harness](harness-engineering.md) |
| 2. Evals and code rules | Cost of mistakes, naive baselines, a calculation tool, tracing | Define at the start; build the tool when evals show arithmetic errors | [evals](evals-and-observability.md) |
| 3. Durable graph | Graph, checkpointer, `interrupt()`, idempotent side effects | A human pause, a pay-once side effect, a fixed order or fan-out is needed (or runs must survive restarts) | [durable state](durable-state-and-hitl.md) |
| 4. Swarm | An LLM-free dispatcher with N workers | Wall-clock time is the problem and items are independent | [swarms](swarms-and-scale.md) |
| 5. Improve | Versioned config, judge, improver with human approval | Labelled and held-out sets, measured noise and sign-in exist, and hand-tuning is the bottleneck | [self-improvement](self-improvement.md) |
| 6. Secure | Agent key, input screening, scoped roles | Before real data, any public address or untrusted text reaching the agent (the backend limit is there from build step 0) | [security](security-and-guardrails.md) |
| 7. Context layer and memory | Context layer as an MCP server; memory per actor (two separate decisions) | Context layer: business knowledge outgrows the prompt or has several owners. Memory: only when an eval shows missing history matters | [context layer](context-layer-and-integrations.md), [RAG and memory](rag-memory-and-mcp.md) |
| 8. Gateway and Runtime | AgentCore Gateway with Cedar policy (log-only, then enforce); AgentCore Runtime, Lambda, Identity | Gateway: several agents or apps need one policy and audit point. Runtime: real users beyond a laptop | [security](security-and-guardrails.md), [AWS](production-deployment-aws.md) |
| 9. Copilot | A user-facing agent with the user's identity | Users spend their day on multi-page lookups and want to delegate | [copilot](copilot-pattern.md) |

**In UnderCover** the pilot was a backend that blocks any payment over $1,000 and one claim agent behind its API; a single call matched the agent on a fixed task, so the agent had to earn its place on harder work. The harness, a payout tool (wrong decisions or amounts fell from 36 to 8 of 75), a durable sign-off, a model-free dispatcher, an improver, the agent's key and screening, a context layer with memory, Runtime and the Copilot each answered one measured pain. See [UnderCover case study](undercover-case-study.md). Reorder build steps by evidence: a project whose sign-off is central may take build step 3 before build step 1.

## Architecture anti-patterns to challenge

| Smell | Why it hurts | Propose instead |
|---|---|---|
| "We need an agent for X", no metric | The project drifts into a demo | A discovery note, a baseline, a single-call baseline (A, B) |
| A cast of human-like agents | More cost and debugging, no evidence of gain | One agent; split only for one of the five reasons and an eval (B) |
| Numbered-step prompts | A workflow written in prose; brittle and costly | A goal plus tools; fixed order in code (D) |
| The model does arithmetic or thresholds | Wrong amounts (36 of 75 wrong before the payout tool) | A calculation tool and a backend validator (D) |
| A limit only in the prompt, or in one layer | A hijacked or mistaken action goes through | The backend limit, a gateway policy, sign-off (F, H) |
| The agent owns its limits, eval sets or approvals | Nothing independent is left to stop it | People own them; handler-only routes refuse the agent's key (F, H) |
| Vector database, gateway or framework chosen first | Lock-in before the use case is proven | A word-search baseline, the lightest framework, a key check and a router (B, E, H) |
| The agent reads the database directly | It bypasses rules and audit | The app's API; the app enforces every rule (E) |
| Judged on a leaderboard, one run or accuracy alone | Noise and flattery | Own eval set, at least three runs, baselines, cost of mistakes (C, G) |
| The agent or coding agent can see the answer key | Every metric becomes meaningless | The scorer in the backend; a PROCESS rule (G, M) |
| State in the process; a side effect before `interrupt()`; the agent pays after sign-off | Lost work, double payment, a stuck claim | Checkpoints, a node and an idempotency check per side effect, the app pays (F) |
| One "needs a human" state | Hides failure rate, caution and sign-off load | Referral, held for sign-off and left for a handler as separate states (D, F) |
| A copilot on the back-office key | A prompt-injected copilot exceeds the user's rights | The user's token, kept in run context (K) |
| Memory or the context layer as the record of truth; untrusted text saved to memory | No owner, stale facts, injections that follow the customer | The placement test; save a minimum in code (E) |
| An improver with no held-out set, final test set or human approval | Overfitting that looks like progress | Preconditions first; human approval; a separate final test (J) |
| Resources before a budget; no teardown | Surprise bills; AWS has no hard cap | Budget and alerts first; name, tag and verified teardown (L) |
| No owner, no handover, responsible AI as a last-week review | Nobody can run or defend it | Named owner, handover on day one, budget for each phase (A, N) |

## Wrap-up

End the session by handing the developer these, with `TODO` where a fact is unknown, and read the summary back for correction.

| Artefact | Template | State at the end |
|---|---|---|
| Discovery note | [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md) | Problem, baseline, success criteria, go or no-go |
| Specification | [SPEC.md](../assets/templates/SPEC.md) | Rules, success criteria, "not for now", in the customer's voice |
| Architecture | [ARCHITECTURE.md](../assets/templates/ARCHITECTURE.md) | Sections 1 to 14 filled; open questions with owner and date |
| ADRs | [ADR.md](../assets/templates/ADR.md) | One per real decision: options, evidence, revisit trigger; indexed in section 14 |
| Eval plan | [EVAL_PLAN.md](../assets/templates/EVAL_PLAN.md) | Metrics, sets, baselines, noise rule, when to run |
| Threat model | [THREAT_MODEL.md](../assets/templates/THREAT_MODEL.md) | Trifecta per agent, layers, identities, residual risk |
| Plan for the first build | [PLAN.md](../assets/templates/PLAN.md) | Design, phases, checkable criteria; no code |
| Repo map and process | [AGENTS.template.md](../assets/templates/AGENTS.template.md) (saved as `AGENTS.md`), [PROCESS.md](../assets/templates/PROCESS.md) | If a coding agent will build |
| Handover skeleton | [HANDOVER.md](../assets/templates/HANDOVER.md) | Owner, runbooks, cost, known limits, as far as known |

Then name the stages deferred as "not for now" with their triggers, propose the next step ("Please plan the first build"), and stop. Do not build until the developer says to implement.

**Keep them current**
- A changed decision gets a new ADR that supersedes the old one; never rewrite history. When a build adds a component, update ARCHITECTURE sections 2, 4 and 5 and STATUS in the same change.
- After any model, prompt, provider or data change, re-run the evals and update EVAL_PLAN.
- Re-open the threat model when a tool, a data source or a deployment target changes.
- Review ARCHITECTURE at each tollgate and at least yearly; the course expects a redesign within a year. Context files carry their own review dates.
- When a review finds a repeatable mistake, add a rule to the code standards or PROCESS and tell the developer.

## Related

- Topics: [FDE lifecycle and governance](fde-lifecycle-and-governance.md), [agent architecture](agent-architecture.md), [models and cost](models-and-cost.md), [harness engineering](harness-engineering.md), [building with coding agents](building-with-coding-agents.md), [evals and observability](evals-and-observability.md), [self-improvement](self-improvement.md)
- More topics: [RAG, memory and MCP](rag-memory-and-mcp.md), [durable state and HITL](durable-state-and-hitl.md), [swarms and scale](swarms-and-scale.md), [security and guardrails](security-and-guardrails.md), [context layer and integrations](context-layer-and-integrations.md), [production deployment on AWS](production-deployment-aws.md), [copilot pattern](copilot-pattern.md)
- Worked example and snippets: [UnderCover case study](undercover-case-study.md), [code patterns: agents](code-patterns-agents.md), [code patterns: LangGraph](code-patterns-langgraph.md), [code patterns: platform](code-patterns-platform.md), [code patterns: AWS AgentCore](code-patterns-aws-agentcore.md); review lists: [checklists](checklists.md); fill-in templates: `../assets/templates/`

## Sources

This file synthesises the topic references above; their Sources sections cite the course days, slides, briefs and Ed's reference builds. Used directly:

- Week 3 Day 1 slides 4-16 (lifecycle, discovery, autonomy, governance, handover) via [FDE lifecycle](fde-lifecycle-and-governance.md); Week 2 Day 1 (the three traps, payout tool) via [agent architecture](agent-architecture.md)
- `guides/for_agents/AGENT_COURSE_GUIDE.md` and the week guides `AGENT_GUIDE_WEEK1.md` to `AGENT_GUIDE_WEEK3.md` (build order, corrections)
- `labs/week1day5_product_HARNESS.md` to `labs/week3day5_product_COPILOT.md` (the incremental path and its triggers); `docs/SPEC.md`, `docs/PROCESS.md`, `AGENTS.md` (plan, review, then implement)

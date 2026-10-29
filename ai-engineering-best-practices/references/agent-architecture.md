# Agent architecture

> When to read this: at the start of any AI project, when the developer asks "should this be an agent?", "single agent or several?", "which framework?", "where does the business logic go?" or "what systems does the agent need around it?". Load it before writing an architecture document, and again whenever someone proposes adding an agent, a framework or a platform component.

## Contents

- Key principles
- Definitions: agent, harness, workflow
- Agent or not: the decision table
- The three traps
- The five reasons to add another agent
- Business logic belongs in code
- Structured outputs design
- Data science and system design come first
- Framework spectrum and build vs buy
- Systems around the agent
- Where the agent runs
- Multi-agent topologies seen in the course
- Autonomy limits are architecture
- Document decisions as ADRs
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover, Related, Sources

## Key principles

1. **Solve the problem without an agent first.** Start from a measurable business problem and try a single structured-output call. An agent adds model calls, latency and cost, and the course's first lab showed it can add nothing else.
2. **One agent until the numbers say otherwise.** Add an agent only for one of five reasons (isolate context, independent check, different model, parallel work, ring-fenced permissions) and keep it only if an eval shows it helps. Org-chart agents are a trap.
3. **Business logic belongs in code, not prompts.** Calculations, rules and thresholds are deterministic tools. The model judges and reads; code computes and enforces. In the course, moving payout arithmetic into a tool cut wrong decisions or amounts from 36 to 8 of 75 across Ed's three runs.
4. **Make the model's output a typed contract.** Use a schema, and put the rationale field before the decision and amount so the model reasons before it commits.
5. **Data science and system design come before agent architecture.** Know the data, the baseline, the cost of each kind of mistake and the surrounding systems before choosing a shape.
6. **The framework is not the most important decision.** Pick the lightest option that gives you the control you need (durability, pauses, model choice) and keep tools, prompts and business logic portable.
7. **Agents live inside systems.** Gateways, integrations, a context layer, memory and a system of record do as much work as the model. Start as simple as possible and expect to redesign within a year.
8. **Autonomy is a per-action architecture decision.** Decide for each action whether it is automatic, needs approval or is prohibited, and enforce it outside the model, in more than one layer.
9. **Treat agents like any other software asset.** An accountable owner, versions, permissions, traces and spend. Write decisions down as ADRs so the next person can see why.

## Definitions

| Term | Meaning in this course |
|---|---|
| LLM call | One request to a model: messages in, text (or JSON) out. |
| Structured-output call | An LLM call whose reply must match a schema, so code can use it directly. |
| Agent | A model that is given tools and runs in a loop towards a goal, choosing each next step itself. |
| Harness | The software around the model that makes it an agent: context handling, workflow, state, subagents, permissions, observability, self-improvement. **Agent = model + harness.** |
| Workflow | A path through steps that the code decides. Steps may call a model, branch, loop or run in parallel, but the control flow is written by the developer. |
| Multi-agent system | Several agents, each with its own context, tools or permissions, coordinated by code or by another agent. |

The line between workflow and agent is **who chooses the next step**. In a workflow the code does. In an agent the model does. Real systems mix them: UnderCover's claim agent is a hand-written graph where code fixes the skeleton (screen the claim, run the model-and-tools loop, pay, wait for a human) and the model chooses what to look up inside the loop.

An agent is small at its core: the first lab built one from a model, one tool (`read_web_page`) and a loop capped at 25 steps. Everything else in the course is harness, systems and discipline around that loop.

## Agent or not: the decision table

Work upward from the simplest shape and stop at the first one that meets the success criteria. This table is a synthesis of the course's guidance; the course teaches the principle ("try without agents first"), not these exact labels.

| Shape | Use when | Who controls flow | Cost and risk |
|---|---|---|---|
| Single structured-output call | Inputs are known up front (fit them in the prompt), one decision or extraction, schema describes the answer | Code | Cheapest, fastest, easiest to evaluate |
| Chain of calls | A fixed sequence where each step's output feeds the next (extract, then classify, then draft), with code between steps | Code | Several calls, still predictable |
| Workflow with LLM steps | Routing, branching, parallel fan-out, retries or checks, but the paths are known in advance | Code (a graph or plain Python) | Predictable, testable, easy to put guardrails around |
| Single agent | The path is not known in advance: which lookups, how many, in what order depends on what the model finds; open-ended reading of documents | Model, inside a harness | More calls, variable cost and latency, needs evals and limits |
| Multi-agent | One of the five reasons below applies and an eval shows the split helps | Code or a lead agent | Most moving parts, hardest to debug and govern |

LangGraph suits a workflow with LLM steps as well as an agent: the Week 2 Day 4 lab builds a dispatcher with parallel steps, retries and saved state and no model in it at all.

Questions that move you up the table:

- Can every fact the model needs be known before the call (look up in code, put in the prompt)? Then it is a single call or a chain, not an agent.
- Does the number or order of steps genuinely vary by case? If not, it is a workflow.
- Does the work outgrow one context window or need separate permissions? Consider a subagent.
- Is there a side effect (payment, email, record change)? Wrap it in code with checks whatever the shape.

**Evidence from the course (Week 1 Day 2).** The same claims were decided two ways on the same model: a single structured-output call with the policy record and wording in the prompt, and a LangChain `create_agent` agent with two tools (`get_policy`, `record_decision`). The agent took three model calls per claim (ask for the policy, record the decision, finish), took longer, cost more and was no more accurate. The task was a fixed workflow, because the policy id came with the claim. The lesson is "measure before you add the loop", not "agents are bad".

**Re-test when the task grows.** The pilot's job was small. Later briefs added a claims manual to search, a customer history and memory, where the agent genuinely has to choose what to look up. The agent earned its place when the path stopped being fixed. Re-run the comparison when requirements change.

Two further signals from the course:

- If your instructions read as a numbered script of fixed steps, you have written a workflow in prose. Write it as code, and give the agent a goal. Ed's review of the first harness build criticised exactly this: long step-by-step prompts where a goal was needed.
- If a choice follows a fixed rule (which claim goes next: oldest first), do not use a model for it. The Week 2 Day 4 build replaced the LLM queue agent with a dispatcher with no model.

## The three traps

Taught on Week 2 Day 1 as the common ways agent projects go wrong.

| Trap | What it looks like | Do instead |
|---|---|---|
| **"Agent for X"** | Starting from the technology: "we need an agent for claims" | Start from a business problem you can measure. Try to solve it without agents first. |
| **Human-like agents** | Copying the org chart: a researcher agent, a reviewer agent, a manager agent | Start with one agent. Add more only when they measurably help. |
| **Plausible vs accurate** | Output that reads well and demos well is assumed to be right | Measure with evals against known answers. See [evals and observability](evals-and-observability.md). |

## The five reasons to add another agent

Each reason names a problem a second agent solves that a single one cannot. If none applies, keep one agent.

| Reason | What it solves | Signal you need it | Course example |
|---|---|---|---|
| **Isolate context** | Long runs bloat the context, each step gets slower and costlier, early work distracts later work | Quality or cost drifts as a run goes on | The queue agent hands each claim to a fresh-context subagent that reports in one line (Week 1 Day 5) |
| **Independent check** | A second look with no stake in the first answer | A single pass can be fooled or is high consequence | A separate model check reads each claim for hidden instructions before the claim agent sees it (Week 3 Day 2) |
| **Different model for a step** | Match model cost and strength to the step | One step is easy and high volume, another is hard | The improver runs on a stronger model than the claim agent; the judge is a non-generative model (Jev). Model names are as taught (Oct 2026) |
| **Parallel work** | Independent items waiting in a queue | Wall-clock time is the problem | A swarm of up to 25 claim agents takes about as long as the slowest claim (Week 2 Day 4) |
| **Ring-fenced permissions** | Different tools or credentials for different jobs | One agent would hold powers it should not | The Copilot acts only with the handler's own sign-in, never the claim agent's key (Week 3 Day 5) |

Add an agent by experiment, not by assertion: run the evals on the one-agent version and the split version, compare accuracy, cost and time, and keep the split only if the gain is bigger than run-to-run noise (a run of 25 items is noisy). See [evals and observability](evals-and-observability.md).

## Business logic belongs in code

Models are good at reading messy input and judging; they are unreliable at arithmetic, applying thresholds consistently and remembering a long rulebook. So put anything that has one right answer in a deterministic tool.

**The course's proof (Week 2 Day 1).** The baseline agent computed each payout itself from the policy's payout section. In the second version the payout rules moved into a Python function exposed as a `calculate_payout` tool. The model still judged whether the claim was covered, which lines counted and what counted as one item; code did the arithmetic. Over three runs of the 25 harder claims, wrong decisions or amounts dropped from 36 to 8 out of 75. Neither version wrongly approved a claim; the baseline wrongly declined four and the payout-tool version one.

What goes where:

| In code (deterministic tools, validators, the backend) | With the model |
|---|---|
| Calculations, tax, deductibles, caps, currency | Reading unstructured text and documents |
| Rules and thresholds (approval limits, required fields) | Judging fuzzy questions (is the story consistent with the documents?) |
| State transitions, idempotency, "pay exactly once" | Choosing which lookup to make next |
| Permission checks and who may do what | Writing the explanation for a human |
| Checking the model's record against the rules | Classifying and extracting from free text |

Patterns that worked in UnderCover:

- **Let the model supply inputs, let code compute.** The model passes line items to `calculate_payout`; code returns the calculation, the payout and whether it needs sign-off.
- **Make the model's claim checkable.** The backend validates a recorded decision against the claims manual's record rules in code, and for an approval requires a calculation on file with the same payout. A model cannot record an amount the tool did not produce.
- **Enforce limits where the data lives.** The backend refuses to pay over the approval limit and checks the amount before it reads the claim, whatever the agent tries. The spec says the system must block the payment even if the agent attempts it.
- **Take side effects out of the model's hands.** From Week 2 Day 3, paying became its own graph step, not an agent tool.

For tool and harness design see [harness engineering](harness-engineering.md).

## Structured outputs design

Use a schema whenever the model's answer feeds code. Design it deliberately:

```python
from typing import Literal
from pydantic import BaseModel, Field

class TriageDecision(BaseModel):
    """The decision on one case."""

    rationale: str = Field(description="2-3 sentences, citing the rule or document section relied on")
    decision: Literal["approve", "decline", "refer"]
    amount: float = Field(description="Amount in US dollars, or 0 for a decline or a referral")
```

- **Rationale first, then decision and amount.** The model generates fields in order, so writing the reasoning first makes it think before it commits. The course's `ClaimDecision` is built this way.
- **Closed sets as `Literal` or enums.** Downstream code can branch on them safely.
- **Describe every field**, including units and the meaning of zero. The description is part of the prompt.
- **Keep it small and typed.** No optional inputs where a required one will do; the course's API operations all have no optional inputs.
- **Ask for the provider to honour the schema.** The labs route through OpenRouter with `require_parameters` so the request only goes to providers that support the response format (as taught, Oct 2026; re-check).
- **Handle unreadable replies in code** with a retry policy, not a longer prompt.
- **Use a schema as the interface between steps**, for example a screening step that returns a flag and a reason the next node can act on.

A structured-output call that returns a decision is also the baseline you compare any agent against.

## Data science and system design come first

The course puts data science and system design ahead of agent architecture. In practice:

1. **Define the business problem and the success measure** before anything else. UnderCover's measure: decide claims straight through, as accurately as the handlers do, while a person approves any payout over $1,000.
2. **Look at the data.** The first lab explores the claims and the handlers' decisions before running a single model.
3. **Build a labelled evaluation set and trivial baselines.** On the course's harder claims, approving everything gets 56% of decisions right (kappa 0), and referring everything costs $950 over those claims. A model must beat both and be compared with the human baseline.
4. **Price the mistakes in business terms**, separate from API cost (in UnderCover: a wrongful decline $1,500, a wrongful approval its payout, a needless referral $50). The cheapest model is not the one with the lowest token bill.
5. **Design the systems**: where the data lives and who owns it, which APIs the agent calls, identity, limits, failure behaviour and the human step.
6. **Only then choose the agent shape**, framework and runtime.

Use cheap single-call experiments to find the accuracy ceiling and the failure patterns before building a harness. See [evals and observability](evals-and-observability.md) and [fde lifecycle and governance](fde-lifecycle-and-governance.md).

## Framework spectrum and build vs buy

Build or buy is a spectrum. The course walks along it:

| Option | What you get | Trade-offs | Where the course used it |
|---|---|---|---|
| Direct API calls (plain SDK, a loop you write) | Full control, no dependency, a good way to see what an agent is | You write the loop, tools, retries and tracing | Week 1 Day 1 maze agent |
| LangChain `create_agent` | The loop, tools from plain functions, middleware, any model; returns a compiled LangGraph graph | Less control over flow than a hand-written graph | Day 2 lab, pilot, queue agent, improver |
| Deep Agents (LangChain's ready-made harness on `create_agent`) | File tools, subagents, a to-do list, summarising of long conversations; open source, any model | You inherit its defaults; you can read exactly what it does | Week 1 Day 5 Lab 2 |
| Claude Agent SDK (Claude Code's harness as a library) | Agent loop, file tools, task list, subagents ready made, very little code | Claude models only; starts a Claude Code program for every run | Week 1 Day 5 Lab 1 |
| Hand-written LangGraph `StateGraph` | Explicit state, nodes and edges; checkpoints after each step; pauses for humans; a node for each side effect | More code; you own the loop | Claim agent from Week 2 Day 3; the Copilot |

Cost figures in the two Day 5 labs (about 40 cents on Claude Sonnet 5.5 against a few cents on DeepSeek V4.1 Flash for five claims) use different models, so do not read them as a framework comparison. Both are as taught (Oct 2026).

**Criteria for choosing** (the framework choice is not the most important decision on a project; do not spend a week on it):

- **Control over the loop.** Need durable pauses, human approval, a pay-once node, recorded steps? Move towards a hand-written graph. That is why UnderCover's claim agent left `create_agent` in Week 2 Day 3.
- **Model portability.** Can you swap models and providers? Avoid lock-in where model choice is still open.
- **How much is ready-made.** File tools, subagents and to-do lists save time on open-ended document work; you pay in defaults you did not choose.
- **Fit with where it runs.** Managed runtimes such as AgentCore Runtime accept any framework and model, so the framework need not decide the platform.
- **Observability, testing and team skill.** Can you trace it, test it without a model, and will the team maintain it?
- **Churn.** These libraries change quickly. Keep tools as plain functions and keep prompts with the application so the framework can be replaced.

Sensible default: begin on the lightest option that meets the requirements, and build extra pieces into it rather than adopting another framework. The Week 1 Day 5 brief said so explicitly: add the to-do list, subagent and manual tools to the product's own agent, not a new framework. Move to a hand-written graph when you need durability or a human step. See [harness engineering](harness-engineering.md) and [durable state and HITL](durable-state-and-hitl.md).

## Systems around the agent

The agent is one component. Week 3 Day 1 names the systems around it:

| System | Purpose | Course implementation (as taught, Oct 2026) |
|---|---|---|
| Gateways | One place where model calls are routed and each agent's tools are controlled; API gateways add keys, rate limits and logs | AgentCore Gateway for MCP tools; OpenRouter as the model route |
| Integrations | The usual systems of record (CRM, claims, ERP) plus documents, email and tickets | The UnderCover app's API, from its OpenAPI document |
| Context and data layer | The meaning of the data, which sources are authoritative and what the agent is allowed to see | Data governance's files, served as read-only MCP tools |
| Memory | The agent's own notes | AgentCore Memory, a namespace per customer (claim agent) or per handler (Copilot) |
| System of record | The database holding records and checkpoints | Supabase Postgres; business records are reached through the app's API, and the agent saves its own checkpoints in the same database |

Four sources of data and integration, each with a different owner (Week 3 Day 3):

| Source | Written by | The agent |
|---|---|---|
| Gateway rules | The security team | Cannot change it; every call goes through it |
| Context layer | The business teams, under data governance | Reads it, as tools |
| Memory | The agent | Reads and writes it |
| Database | The app and the agent | Reads and writes through the app's API |

Rules for this layer:

- **Start simple.** Avoid a big internal build and heavyweight opinionated products, keep prompts with the applications that use them, and plan for a redesign within a year. Ed's advice on gateways is the same: stay lightweight while the products keep changing.
- **The agent reaches business records through the app's API,** not the database. The app owns the rules, so every agent and user gets the same checks. (The agent's own checkpoints are the exception: its graph saves them straight to the database.)
- **Design the API for tools.** Each operation gets an `operation_id`, a one-line docstring and no optional inputs, because the OpenAPI document becomes the agent's MCP tools through the Gateway.
- **Layer the controls.** UnderCover keeps a payout within the rules at three layers: a model check on what goes in or out, a Gateway policy (no payout over $1,000, only the tools it needs), and the app's own API key and second limit. No single layer makes an agent safe.
- **Put each kind of knowledge in its owner's place:** policy wording and manuals in the context layer, the agent's own notes in memory.

Details: [context layer and integrations](context-layer-and-integrations.md), [RAG, memory and MCP](rag-memory-and-mcp.md), [security and guardrails](security-and-guardrails.md).

## Where the agent runs

Week 3 Day 1 groups the ways to host an agent in production into three (the full table, with examples as taught, is in [FDE lifecycle and governance](fde-lifecycle-and-governance.md#systems-architecture-and-where-the-agent-runs-brief)). Here is the choice by constraint:

| If you need... | Look at | Because |
|---|---|---|
| Full control, or you already have a platform and an ops team | Your own servers or containers (Lambda, ECS, Cloud Run, Kubernetes, Render) | Any framework and model work, but state and scaling are yours to build |
| Identity, memory and sessions without building them | A managed agent runtime (AgentCore Runtime, Google Agent Runtime, Microsoft Foundry, LangSmith Deployment) | It still accepts any framework and model, and supplies those pieces |
| The least to operate, and you accept one vendor | The model lab's hosted agents (Claude Managed Agents, OpenAI Agents API) | You get the lab's harness but only the lab's models, so model choice is closed |

For the AWS route taught in the course, the app and context layer run on Lambda and the agent runs on AgentCore Runtime, with state in Supabase. Sessions are short-lived, so progress must live in the database, not in the process. Detail in [production deployment on AWS](production-deployment-aws.md).

## Multi-agent topologies seen in the course

Each is one of the five reasons made concrete.

| Topology | Shape | Use when | Course example | Detail |
|---|---|---|---|---|
| **Work-item subagent in a fresh context** | An orchestrator keeps a to-do list and hands each item to a subagent that starts clean and reports in one line | Many independent items; context growth hurts quality or cost | Queue agent with a `work_claim` helper; the claim-handler subagent in the Day 5 labs | [harness engineering](harness-engineering.md) |
| **LLM-free dispatcher fanning out a swarm** | Code selects the items, fans out one worker per item with a concurrency cap and collects results | Batches; ordering is a fixed rule; wall-clock time matters | `Send` fan-out with `max_concurrency` and a retry policy; each claim has its own thread | [swarms and scale](swarms-and-scale.md) |
| **Independent checker or screening step** | A separate model call with its own framing that returns a structured verdict, before or after the main agent | Untrusted input; high-consequence action | Hidden-instruction check in the claim graph's first node; a claim it flags goes to a handler | [security and guardrails](security-and-guardrails.md) |
| **Improver agent** | An agent reads evaluation results and proposes a change to prompt, model or settings; a human approves; held-out evals decide keep or roll back | The agent's configuration should improve with evidence | Improver on a stronger model with a human-approval pause | [self-improvement](self-improvement.md) |
| **User-facing copilot** | A chat agent that acts with the user's identity, durable conversations and confirmation before consequential actions | People need to ask, inspect and act through the agent | The Copilot sidebar for handlers | [copilot pattern](copilot-pattern.md) |

Vocabulary from Week 2 Day 4: a **team** is a few agents on one task, a **swarm** is many agents in parallel, and a **fleet** is every agent a business runs. Treat a fleet like any software portfolio: an accountable owner, versions and permissions, and traces and spend recorded for every run.

Two moves in UnderCover show the judgement to apply. The pilot's code did all the organising (one claim at a time, the whole wording each time), and the Week 1 Day 5 build gave the planning to an agent. Then in Week 2 Day 4 the choice of the next claim, a fixed rule, went back to a dispatcher with no model. Give the agent the judgement and keep the rules in code.

## Autonomy limits are architecture

Autonomy is a risk decision made for each action, not for the agent as a whole. Assess each action on risk appetite, consequence, verifiability, reversibility, and security, privacy and IP, then put it in one of three bands: automatic, approval first, or prohibited. The full table is in [FDE lifecycle and governance](fde-lifecycle-and-governance.md#autonomy-is-a-risk-based-decision-for-each-action). In UnderCover, reads and arithmetic run automatically; money over the limit and changes to rules or models wait for a person; approving its own payout, changing the limit or reading the held-out answers is prohibited.

Architectural consequences:

- **Enforce thresholds outside the model**, in the system of record and the gateway, never in the prompt alone. The agent may approve a large claim, but the payment waits for a human, and the backend blocks it even if the agent tries.
- **Keep a referral and a held approval apart.** A referral means the agent could not decide. A held approval means it decided and the payment waits for a sign-off.
- **Design the human step as part of the system:** a review screen that lays out the evidence and offers approve, edit and reject, an audit trail of each step and who approved each payout, and a plan for delays (timeouts, escalation, no double payments).
- **The agent must not hold the keys to its own limits.** The threshold, the evaluation sets and the approvals belong to people.

See [durable state and HITL](durable-state-and-hitl.md) for pausing, resuming and paying once, and [FDE lifecycle and governance](fde-lifecycle-and-governance.md) for tollgates and ownership.

## Document decisions as ADRs

Record each significant choice in an architecture decision record with `../assets/templates/ADR.md`, and keep the overview in `../assets/templates/ARCHITECTURE.md`. Write an ADR for: agent or workflow, single or multi-agent, framework, build or buy, where the agent runs, the systems it must reach, and each autonomy threshold. Each ADR names the options considered, why one was chosen, the evidence (eval numbers, cost per unit of work) and what would trigger a revisit. Week 3 Day 1's stretch assignment asks for exactly this: build or buy, where the agent runs and the systems it needs, with options and reasons. Because the slides say to expect a redesign within a year, ADRs are how the next team learns what the assumptions were.

## Decisions to make with the developer

| Decision | Ask | Options | Sensible default |
|---|---|---|---|
| Agent or not | What is the measurable business goal? Can a single call meet it? | Single call, chain, workflow, agent | Build the single-call baseline and an eval first; escalate only on a measured gap or a path that varies |
| Single or multi-agent | Which of the five reasons applies, and what does the eval show? | One agent, subagents, dispatcher plus workers, copilot | One agent; add each extra only against one of the five reasons and a measured gain |
| Framework | Do we need durable pauses, model portability, a ready-made harness? | Direct calls, `create_agent`, Deep Agents, Claude Agent SDK, hand-written graph | `create_agent` or the team's existing framework; a hand-written graph once a human step or pay-once node is needed |
| What lives in code | Which parts have one right answer? | Prompt rules vs tools and validators | All calculations, rules, thresholds and limits in code; the model supplies inputs and judgement |
| Systems around the agent | Which systems must it reach, who owns each, what is the system of record? | Direct API, gateway, context layer, memory | Agent calls the app's API with a key; add a gateway, context layer or memory only when a need is shown |
| Where it runs | Model choice, ops capacity, identity and memory needs | Own infrastructure, managed runtime, model lab | Managed runtime for the agent with state in a database (AgentCore Runtime in the AWS route); prototype locally |
| Autonomy | Which actions are automatic, approval-first or prohibited? | Per-action bands | Human sign-off above a business-set threshold, enforced in the backend and gateway |

## Pitfalls and anti-patterns

- Choosing an agent because "agent" is the brief, with no single-call baseline.
- Building a cast of human-like agents (researcher, critic, manager) without an eval showing it helps.
- Writing step-by-step scripts in the prompt, then wondering why the agent is brittle and costly.
- Asking the model to do arithmetic or apply thresholds that a function could compute exactly.
- Enforcing a limit only in the prompt, or only in one layer.
- Treating a plausible demo as accuracy; judging a change on one noisy run of 25 items.
- Picking the framework or platform first and bending the problem to fit.
- Buying or building a heavyweight context or gateway platform before the need is clear.
- Giving one agent the powers of several jobs, such as the Copilot using the claim agent's key.
- Letting the agent own its own limits, evaluation sets or approvals.
- Mixing up "referred" and "held for sign-off" in metrics and in the UI.
- Skipping the ADR, so nobody remembers why it was built this way.

## In UnderCover

The architecture grew build by build, each change forced by a measured need:

1. **Pilot (Week 1).** One claim agent on `create_agent`, tools that call the backend's API. The Day 2 lab showed a single structured-output call matched the agent on this fixed task, so the agent's value had to come from harder work to follow.
2. **Harness (Week 1 Day 5).** A queue agent with a to-do list, a fresh-context helper per claim, and tools to search and read the policy wording and the claims manual.
3. **Payout tool (Week 2 Day 1).** Payout rules moved into code: 36 to 8 wrong of 75.
4. **Durable graph (Week 2 Day 3).** The claim agent became a hand-written LangGraph graph with checkpoints in Supabase, a separate pay step and an `interrupt()` for sign-off.
5. **Swarm (Week 2 Day 4).** An LLM-free dispatcher replaced the queue agent, with N claim agents at once and per-claim cost and time.
6. **Improver (Week 2 Day 5).** A second agent proposes configuration changes; a senior handler approves; held-out evaluation decides.
7. **Security, context, memory (Week 3 Days 2 and 3).** A screening node, the agent's API key, a Gateway with a Cedar policy, a context layer as its own MCP server, and AgentCore Memory per customer.
8. **Runtime and Copilot (Week 3 Days 4 and 5).** The agent on AgentCore Runtime, and the Copilot as a separate agent with the handler's identity.

Final shape (as built, Oct 2026):

```text
Dashboard --> UnderCover app (Lambda) <--> Supabase (records, checkpoints, sign-in)
                  | starts runs, resumes claims            ^ agent checkpoints
                  v                                        |
   Agent on AgentCore Runtime: dispatcher (no model) -> claim agents; improver
                  | tools as MCP calls
                  v
   AgentCore Gateway (Policy, Identity) --> app API (Lambda), context layer (Lambda)
   AgentCore Memory: the claim agent's notes per customer
   Copilot: its own Runtime and Memory (per handler), acting with the handler's sign-in
```

Why this shape: code owns the rules and the limit, the model owns judgement, each extra agent maps to one of the five reasons, and every outer system has one owner. See [UnderCover case study](undercover-case-study.md).

## Related

- [harness engineering](harness-engineering.md): tools, middleware, subagents, instructions
- [swarms and scale](swarms-and-scale.md): dispatchers, fan-out, rate limits
- [self-improvement](self-improvement.md): the improver loop and keep or roll back
- [copilot pattern](copilot-pattern.md): user-facing agents with the user's identity
- [security and guardrails](security-and-guardrails.md): layered controls, gateways, policy
- [context layer and integrations](context-layer-and-integrations.md): data owners, system of record
- [durable state and HITL](durable-state-and-hitl.md): checkpoints, interrupts, paying once
- [production deployment on AWS](production-deployment-aws.md): where the agent runs, in depth
- [evals and observability](evals-and-observability.md): measuring whether any of this helps
- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): discovery, tollgates, handover
- Templates: `../assets/templates/ADR.md`, `../assets/templates/ARCHITECTURE.md`

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK1.md` (Days 2 and 5), `AGENT_GUIDE_WEEK2.md` (Day 1), `AGENT_GUIDE_WEEK3.md` (Days 1 to 5), `AGENT_COURSE_GUIDE.md`
- Notebooks: `labs/week1day2.ipynb` (structured output vs agent), `labs/week2day1.ipynb` (payout tool), `labs/week1day5_lab1.ipynb` and `labs/week1day5_lab2.ipynb` (two harnesses), `labs/week2day3.ipynb` (`create_agent` to a graph), `labs/week2day4.ipynb` (dispatcher), `labs/week3day1free.ipynb` (ADR assignment)
- Slides: W3D1 slides 8, 9, 11, 12; W3D2 slides 29, 37; W3D3 slides 52, 53, 58; W3D4 slides 72, 75, 79; W3D5 slide 91
- Briefs: `labs/week1day5_product_HARNESS.md`, `labs/week2day4_product_SWARM.md`, `labs/week3day5_product_COPILOT.md`; `docs/SPEC.md`, `docs/TECH_STACK.md` on `main` and `origin/week3day5-end:docs/TECH_STACK.md`; `origin/week3day5-end:docs/HUMAN_REVIEW_HARNESS.md`

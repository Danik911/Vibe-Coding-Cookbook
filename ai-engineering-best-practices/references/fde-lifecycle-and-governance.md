# FDE role, agent lifecycle, discovery and governance

> When to read this: at the start of any new agent project (discovery, scoping, success criteria), when the developer asks "what should we decide before we build?", when planning autonomy limits, privacy or accountability, and when preparing a handover. Load it before `agent-architecture.md`: the architecture follows from the problem and the criteria set here.

## Contents

- [Key principles](#key-principles)
- [What an FDE is](#what-an-fde-is)
- [The two meanings of ADLC](#the-two-meanings-of-adlc)
- [The agent development lifecycle](#the-agent-development-lifecycle)
- [Discovery and ideation](#discovery-and-ideation)
- [Running discovery with a developer](#running-discovery-with-a-developer)
- [Writing requirements the way the customer would](#writing-requirements-the-way-the-customer-would)
- [Governance: levels, tollgates, autonomy, many agents](#governance-levels-tollgates-autonomy-many-agents)
- [Responsible AI](#responsible-ai)
- [Handover and adoption](#handover-and-adoption)
- [Systems architecture and where the agent runs](#systems-architecture-and-where-the-agent-runs-brief)
- [Decisions to make with the developer](#decisions-to-make-with-the-developer)
- [Pitfalls and anti-patterns](#pitfalls-and-anti-patterns)
- [In UnderCover](#in-undercover)

## Key principles

1. **Start from a measurable business problem, not from "an agent for X".** A use case that cannot be measured cannot be shown to work, and the project drifts into a demo.
2. **Write the success criteria, with a baseline and a target, before building.** The criteria decide the eval set, the architecture and the go/no-go; defining them afterwards makes them fit the result.
3. **Work in five phases and end each with a sponsor's sign-off.** A tollgate forces an explicit decision (scope, build, go/no-go, success, change) instead of letting work slide forward.
4. **Treat autonomy as a risk decision for each action, not for the agent as a whole.** Reading a record and paying a claim carry different consequences, so they get different controls.
5. **Enforce limits in code and permissions, not in the prompt.** A prompt rule can be argued with or injected around; a refused API call cannot.
6. **Manage agents like any other software asset.** Each has an accountable owner, versions, permissions, traces and a spend record. Do not invent a special regime unless the client already has one.
7. **Budget and plan for responsible AI during the project and after go-live.** The six pillars (safety, fairness and bias, security, privacy, transparency, accountability) cost time and money, so they belong in the plan, not in a last-week review.
8. **Everything in the context window goes to the model provider.** Minimise personal data, know the provider's training terms, and never assume that paying removes training.
9. **A human is always accountable.** The model is a tool, never the owner; name the person who answers for quality and outcomes.
10. **Design the handover on day one.** The test of an FDE engagement is that the client's team can run, measure and change the system without the FDE.
11. **Start the architecture as simple as possible and expect a redesign within a year.** Early heavyweight platforms lock in choices made before the use case is proven.

## What an FDE is

As taught in the course (Oct 2026): the role originated at Palantir (about 2007), and in 2026 OpenAI set up a company that places FDEs inside customers.

| Meaning | Definition |
|---|---|
| Narrow | A senior applied AI engineer embedded with a client, working on the client's problem inside the client's organisation. |
| Broad | An applied AI engineer who solves commercial problems and delivers to customers, whether or not embedded. |

Skills and disciplines the course teaches for the role:

| Discipline | What it covers |
|---|---|
| AI engineering (Week 1) | Agent loops and tools, model selection, frameworks, coding agents, open-source and local models, token cost, context and harness engineering. |
| AI architecture (Week 2) | Designing the whole system: agent design, evals and tracing, cost and latency trade-offs, agentic RAG and memory, MCP, durable state with a human in the loop, swarms, self-improvement. |
| Forward deployed engineering (Week 3) | Working with the customer: discovery, governance and compliance, security and guardrails, gateways, the context layer and integrations, cloud setup, production deployment, handover and user adoption. |

Two kinds of experience also count: solving real business problems and delivering to customers. In the course author's review of 316 job adverts from 184 employers, 89% asked for at least four of the five areas (three disciplines plus two kinds of experience). The review is a point-in-time market survey; re-check it before quoting it.

How the agent uses this: when the developer is acting as an FDE (or as an engineer inside the client), apply the FDE habits below even on a small project: ask about the business problem first, measure, name an owner, plan the handover.

## The two meanings of ADLC

The acronym is used for two different processes. Say which one you mean.

| | 1. Building agents with code | 2. Building code with agents |
|---|---|---|
| Subject | The product is an agent. The process covers risks and controls, evaluations, adoption, observability and maintenance. | The method is a coding agent. The process covers writing software with agents while staying accountable for the result. |
| Where in the course | Week 3 Day 1 (this file) and most of the course | Week 1 Day 3 |
| Read | This file | [building with coding agents](building-with-coding-agents.md) |

The two compose: the second is how you build each phase's deliverables fast; the first says what the deliverables are and who signs them off.

## The agent development lifecycle

Five phases, with ownership, governance, evals and change management running through all of them. The field is evolving; treat the phases as common practice, not a standard.

| Phase | What happens | The FDE's work | Tollgate (sponsor signs off) |
|---|---|---|---|
| 1. Discovery | Name the sponsors and the owner; make the business case; set the baseline and success criteria with an eval plan; plan adoption | Ideation at the client: shortlist use cases, measure today's baseline, draft the criteria | Agree scope and budget |
| 2. R&D | Prepare the data; run experiments scored by evals; decide how much autonomy the agent gets; pick the framework and architecture | Prototype: check data quality, build the first evaluation set and a working prototype | Approve the build |
| 3. Development | Build the agent and its harness; integrate with systems; test; add observability | Build beside the client's engineers: integrations, guardrails, evals, tracing | Go/no-go |
| 4. Implementation | Run a pilot with user acceptance; roll out in stages; train users; hand over and approve the release | Deploy and hand over: pilot, training, runbook, a named service owner | Program success |
| 5. Maintenance | Monitor; improve; collect human feedback; test for drift and bias; upgrade, merge or retire the agent | Report back to your employer: gaps in the product and what is worth productising | Change management |

Maintenance feeds back into discovery: the gaps found in the product become the next round of ideation. The loop is the point; a project that ends at go-live has no owner for drift.

Where to find the techniques for each phase (a mapping for navigation, not from the slides):

| Phase | Go to |
|---|---|
| Discovery | this file; [decision guide](decision-guide.md) |
| R&D | [models and cost](models-and-cost.md), [agent architecture](agent-architecture.md), [evals and observability](evals-and-observability.md) |
| Development | [harness engineering](harness-engineering.md), [durable state and HITL](durable-state-and-hitl.md), [security and guardrails](security-and-guardrails.md), [context layer](context-layer-and-integrations.md) |
| Implementation | [production deployment on AWS](production-deployment-aws.md), the handover section below |
| Maintenance | [self-improvement](self-improvement.md), [evals and observability](evals-and-observability.md) |

## Discovery and ideation

**Goal:** prioritise use cases that solve a measurable business problem. The bar for AI projects has risen: a demo that impresses is not enough; the project must move a number the business already cares about.

### The three categories

| Category | What kind of value | Illustration (ours, not the slides') |
|---|---|---|
| Automation | The same work, done more cheaply | Sorting incoming invoices without a person keying them in |
| Acceleration | The same work, done sooner | Cutting the time to a first quote for a new customer |
| Differentiation | Work the business could not do before | A service line that was too costly to offer by hand |

Use the category to choose the metric: automation is judged on cost per unit of work, acceleration on elapsed time, differentiation on a new outcome that did not exist before (this mapping is guidance, not from the slides). Automation is the easiest to baseline; differentiation the hardest, so expect to need more discovery.

### The three questions for each use case

Ask all three of every candidate before it goes on the shortlist:

1. Does it avoid the traps from Week 2?
2. Does it use your own data, connections and evals?
3. Is it automation, acceleration or differentiation?

How to apply them:

| Question | What to check | Why |
|---|---|---|
| 1. Avoids the Week 2 traps | Three traps. An "agent for X" with no measurable problem behind it (first try to solve it without agents). Human-like agents (start with one agent and add more only when they measurably help). Plausible versus accurate (score with evals; do not trust fluent output). See [agent architecture](agent-architecture.md) and [evals and observability](evals-and-observability.md). | These are the commonest reasons agent projects fail to show value. |
| 2. Uses your own data, connections and evals | The client holds data the agent can use, there are systems it can reach (see [context layer](context-layer-and-integrations.md)), and there is a way to score the work, ideally labelled examples. | A use case without data, access or a scoring method cannot be built or proven. |
| 3. Automation, acceleration or differentiation | Classify it, so the success metric and the business case match the kind of value. | A cost case, a speed case and a new-capability case need different evidence. |

### Success criteria: a baseline and a target for each

A success criterion is a measurable statement with three parts. Write each one this way before building:

| Part | Question | Example (UnderCover) |
|---|---|---|
| Measure | What is counted, over what set, by what method? | Share of claims decided straight through, over the whole held-out set, taken from the evaluation's own record |
| Baseline | What is the number today, without the agent? | Handlers' own rate on the Week 2 Day 1 set: 6 of 25 referred, so 76% not referred (week2day1). Today every claim waits for a handler; their decisions are the reference for accuracy |
| Target | What number counts as success, and who agreed it? | At least 70% straight through; accuracy at or above an agreed objective; every payout over the limit approved by a person |

Rules for good criteria:

- Include at least one **limit criterion** (a thing that must always hold, such as "every payout over $1,000 has a person's sign-off") next to the **performance criteria** (straight-through rate, accuracy). Performance can trade off; limits cannot.
- Say how each is measured and **who computes it**. Prefer a figure worked out in code from records over one a model reports about itself.
- State the cost of mistakes, not just the error rate: a wrongful decline and a needless referral are not equal. Details in [evals and observability](evals-and-observability.md).
- Agree the numbers with the sponsor at the first tollgate. Revisit them only through change management.
- The course ends every build with the same instruction: start by defining evals, and end by measuring them to decide success.

### What discovery produces

- A one-page **discovery note**: who has the problem, what it costs today, the success criteria with a baseline and a target for each. Template: [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md).
- **Architecture decision records (ADRs)** for the early big choices, such as build or buy, where the agent runs and which systems it must reach, each with the options considered and why one was chosen. Template: [ADR.md](../assets/templates/ADR.md).
- A named sponsor and owner, an adoption plan and a first scope-and-budget tollgate.

## Running discovery with a developer

You, the coding agent, can run discovery as a conversation. The goal is a discovery note the developer would show a sponsor, and ADRs for each real decision.

How to run it:

1. **Ask before proposing.** Ask five to eight questions at a time from the bank below, grouped by theme, not the whole list at once. Restate the answers in one paragraph and ask the developer to correct it.
2. **Offer a default for every question** so the developer can say "yes" quickly, and mark which answers are assumptions.
3. **Challenge the framing once.** Ask: could this be solved without an agent? Is there a fixed workflow where plain code or a single model call is enough? (In the course, a fixed workflow done as an agent took longer and cost more than a single structured call without being more accurate.)
4. **Record, do not remember.** Write answers into the discovery note as you go, with open questions listed with an owner and a date.
5. **Stop at the tollgate.** Do not start the R&D or the build until the developer confirms scope, budget, owner and success criteria.
6. **Turn each real decision into an ADR** when it is made, while the reasons are fresh.

Question bank:

| Theme | Ask |
|---|---|
| Problem and owner | Who has the problem and how often? What happens today, step by step? Who is the sponsor, and who will own the agent after launch? |
| Value and baseline | What does the problem cost now (time, money, errors)? What is the current accuracy, speed and volume? What would a good result be? |
| Category | Is this cheaper, faster or new? Which metric follows? |
| Data and evals | What data exists, who owns it, how clean is it? Are there past decisions we can use as labelled examples? Who decides what a correct answer is? |
| Systems | Which systems of record must the agent read or write? Are there APIs? Who approves access? |
| Autonomy and risk | Which actions are reversible? Which carry money, legal or safety consequences? Which must a person approve? What must the agent never do or see? |
| Users and adoption | Who uses the output? What would make them trust it or ignore it? Who trains them, and who champions it from above? |
| Privacy and compliance | What personal or confidential data will reach the model? Which provider terms apply, and do they allow training on the data? Which regulation applies? |
| Constraints | Budget, deadline, preferred cloud, existing platforms, languages and security rules? |
| Handover | Who runs it after we leave? What do they need: a runbook, dashboards, an escalation path? |

## Writing requirements the way the customer would

UnderCover's requirement documents are a model for the written brief a client gives you or you write with them. They are written in the customer's voice, by the person who asked, and the same sections recur in every build:

| Section | Purpose |
|---|---|
| How things work today | The current process in business words; the baseline in prose |
| What the agent should do | The behaviour, as a short list of observable actions |
| What the team needs to see | The screens and records people need to trust and check the work |
| Rules | Constraints that must hold whatever the agent does (limits, who may do what, data it must never see) |
| Our records | Where the data lives and who owns it |
| The success criteria we agreed | Numbered, measurable, each checkable from records |
| Not for now | Explicit non-goals, so scope stays under control |

Write the rules and non-goals as carefully as the features. "The system must block the payment until a handler signs off, even if the agent tries to pay" is a testable rule, and it puts the control in the system. A "Not for now" list (no sign-up, no real payments, no messages to customers) is what stops a pilot from growing.

## Governance: levels, tollgates, autonomy, many agents

### Three levels, and a tollgate at the end of each phase

| Level | Cadence | Decides | Who sits on it |
|---|---|---|---|
| Firmwide leadership | Monthly or quarterly | The company's AI portfolio, policies and how much risk it will accept | Senior executives from across the business |
| Project committee | Monthly | What one project may do, which risks it takes, when it is released | Sponsor, owner, plus security, audit and operations |
| Working group | Weekly | Day-to-day building, evaluating and running of the agent | Product, engineering, business users and the FDE |

A small project can merge the first two or run them lightly, but still name who decides each kind of question and when.

Suggested evidence to bring to each tollgate (guidance, not from the slides):

| Tollgate | Decision | Bring |
|---|---|---|
| End of discovery | Agree scope and budget | Discovery note, baseline, success criteria, risks, named owner |
| End of R&D | Approve the build | Eval results from a prototype against the baseline, the autonomy proposal, ADRs for architecture and hosting |
| End of development | Go/no-go | Eval results against the targets, security and guardrail tests, observability in place, cost per unit of work |
| End of implementation | Program success | Pilot and acceptance results, training done, runbook and service owner named, handover accepted |
| Maintenance | Change management | A change process: who approves a new prompt, model, rule or version, with its eval evidence |

### Autonomy is a risk-based decision for each action

Assess each action the agent can take on these dimensions: risk appetite, consequence, verifiability, reversibility, and security, privacy and IP. Then place it in one of three tiers. This is the one canonical table for the tier examples; other files link here.

The course's example (Week 3 Day 1, slide 11), reworded:

| Tier | Meaning | UnderCover's agent |
|---|---|---|
| Automatic | The agent acts without anyone's say-so | Looks up the claim, searches the policy wording, works out the payout, records approve, decline or refer, and pays amounts up to the $1,000 limit |
| Approval first | A person must approve before it takes effect | Payments above $1,000; changes to the prompt or rules; switching the model; changing the improver's recipe |
| Prohibited | The agent can never do it, whatever it is told | Signing off its own payout; moving the $1,000 limit; reading the held-out answers; editing the evaluation sets |

For every approval-first action, build the human step properly:

- a **review screen** that lays out the evidence and offers approve, edit and reject;
- an **audit trail** recording each step and who approved each payout;
- a **plan for delays**: timeouts, escalation, and no way to pay twice.

Enforce the tiers in the system (permissions, an API that refuses the call, a gateway policy, data the agent cannot reach), not only in instructions. See [security and guardrails](security-and-guardrails.md) and [durable state and human in the loop](durable-state-and-hitl.md) for the mechanisms.

Review the tiers at each tollgate: as evidence grows, an action may move from approval-first to automatic, but only through a recorded decision.

### Managing many agents

Some organisations manage a roster of agents as if they were staff. As taught in the course (Oct 2026), the examples were Microsoft Agent 365 with Entra Agent ID (a registry of agents and their identities), Workday's Agent System of Record (agents managed alongside employees), AWS Agent Registry (a governed catalogue) and OpenAI Frontier ("AI coworkers" with identities). The product list changes quickly; re-check it.

The course recommends the opposite default: treat an agent as one more software asset that solves a commercial problem. Keep four records for it, shown here with UnderCover's answers (reworded from slide 12):

| Record | UnderCover's answer |
|---|---|
| What it is | The dispatcher, the claim agents and the improver are parts of one product, not separate hires |
| Who answers for it | The owner of the claims product, not the model |
| Versions and permissions | Configuration lives in versions, and a handler approves each change |
| Traces and spend | Kept for every claim and every run |

Adopt a client's agent registry if it has one; do not build one for a single agent.

## Responsible AI

Six pillars belong in the plan: safety, fairness and bias, security, privacy, transparency and accountability. The most important step is to budget and plan for them during the project and after go-live.

| Pillar | Plan for | Where to look |
|---|---|---|
| Safety | Harmful or wrong actions, limits on consequences, human approval for high-impact steps | [security and guardrails](security-and-guardrails.md) |
| Fairness and bias | Tests for uneven results across customer groups, drift and bias checks in maintenance | [evals and observability](evals-and-observability.md) |
| Security | Prompt injection, the lethal trifecta, least privilege, gateways | [security and guardrails](security-and-guardrails.md) |
| Privacy | What data reaches the provider, retention, per-user isolation of memory | below |
| Transparency | Show what the agent did and why: steps, sources, decision records | [harness engineering](harness-engineering.md) |
| Accountability | A named owner, audit trail, a person approving consequential actions | below |

The right-hand column is a pointer to where the course teaches each topic; the slides name only the pillars.

### Privacy with LLM providers

- **Prompts are sent to an external company.** Everything in the context window goes to the model provider. Treat it as data sent to any third party, no better and no worse.
- **Business APIs usually don't train on your data; consumer chat products may.** Check the terms and the settings. Paying does not by itself stop a provider training on your data: read the terms and settings of the exact product you use.
- **Free models are different.** The privacy switches that unlock free models on routers such as OpenRouter allow providers that may train on prompts, so send them nothing confidential or personal.
- **Minimise personal data.** Send only what the task needs and redact or anonymise the rest where appropriate.
- **Use the vendor-trust yardstick.** If the client would trust a SOC 2 certified vendor with the data, a SOC 2 certified LLM provider is comparable.
- **Isolate memory by user.** Keep each person's stored facts available only for that person's work.

Ask the client's security and compliance owner to confirm provider, region and retention before the R&D tollgate, and record the answer in an ADR.

### Accountability

A person must always answer for the quality and the final outcomes of an agent's work. In practice:

- keep a person in the loop wherever it is sensible, and require approval for consequential actions;
- keep an audit trail, alerts and flags, and the means to watch the system and fix problems quickly;
- make ownership explicit: the model is a tool, not the owner;
- expect regulation to arrive (the course cites the EU AI Act; check which rules apply to the client's sector and region and their current dates (verify)).

## Handover and adoption

The test: the client's team can run the system without the FDE. The course (slide 16) names three handover areas and four adoption areas; the contents below are our elaboration.

| Handover area | What to leave behind |
|---|---|
| Ownership and escalation | A named service owner, who is called for what, and how problems move up |
| Knowledge transfer | A runbook, the decision records, and steps to deploy, rotate secrets, tear down and roll back; walk-throughs with the people who will operate it |
| Ongoing measurement | The success criteria, how each is computed, where the dashboards are, and who reviews them how often |

| Adoption area | What to do |
|---|---|
| Training and support | Train the people who use the output, and give them somewhere to ask for help |
| Sponsors and top-down change | Have a sponsor who expects the new way of working, so the tool is more than merely available |
| Demonstrating accuracy | Show users the evaluation results, so trust is earned rather than requested |
| Transparency on usage | Make visible how much the agent is used and what it costs |

Also hand over the cost picture (cost per unit of work and the budget alerts) and the teardown steps, so nothing keeps billing after the engagement. Use [HANDOVER.md](../assets/templates/HANDOVER.md) as the checklist. Build the handover evidence into the product where you can: a screen or an assistant that answers "are we meeting the success criteria?" from records makes the criteria part of daily operation.

## Systems architecture and where the agent runs (brief)

Around the agent sit three layers: gateways (a single place where model calls are routed and each agent's tool access is controlled), integrations with the usual systems of record (CRM, claims, ERP) plus documents, email and tickets, and a context and data layer (what the data means, which sources are trusted, what the agent may see, and its memory).

Keep the first version simple: avoid a big internal platform build and heavyweight opinionated products, keep prompts alongside the applications that use them, and plan for a redesign within a year.

Where to host an agent in production falls into three groups (examples as taught, Oct 2026):

| Hosting choice | Examples | Trade-off |
|---|---|---|
| Servers or containers you operate | AWS Lambda, ECS, Cloud Run, Kubernetes, Render | Free choice of framework and model; you build and run state, scaling and operations |
| A cloud's managed agent runtime | AWS AgentCore Runtime, Google Agent Runtime, Microsoft Foundry, LangSmith Deployment | Still free choice of framework and model; the platform supplies memory and identity |
| Hosted by the model lab itself | Claude Managed Agents, OpenAI Agents API | Least to run, but you accept that lab's harness and can use only its models |

This is where hosting and architecture become ADRs. Details live elsewhere: [agent architecture](agent-architecture.md) (agent or not, single or multi-agent, business logic in code), [context layer and integrations](context-layer-and-integrations.md), [security and guardrails](security-and-guardrails.md) (gateways) and [production deployment on AWS](production-deployment-aws.md) (AgentCore Runtime, Lambda, cost, teardown).

## Decisions to make with the developer

| Decision | Options | Sensible default |
|---|---|---|
| Is the use case worth building, and what category? | Automation, acceleration, differentiation; build now or defer | Prefer an automation use case with a measurable baseline and labelled examples; defer anything without data or a metric |
| Success criteria and targets | Number and type of criteria; targets; who agrees | Two or three: one or two performance criteria and one limit criterion, each with a measure, a baseline, a target and an owner |
| Autonomy per action | Automatic, approval first, prohibited | Read and compute automatically; approval first for money, irreversible or rule-changing actions; prohibited for anything that edits limits, evals or its own approvals |
| Governance weight | Three levels with tollgates, or a light version | Name a sponsor and an owner and hold a short tollgate at each phase end; add committees only when the client already has them |
| Privacy posture | Provider and terms; data minimisation; free models for dev | A business API on no-training terms, personal data minimised, nothing confidential on free models |
| Build or buy, and where it runs | Own infrastructure, managed runtime, model lab | Record an ADR; for the AWS-specific course route, see [production deployment on AWS](production-deployment-aws.md) |
| Handover scope | Runbook, training, owner, dashboards | Agree the handover checklist at discovery and review it at the implementation tollgate |

## Pitfalls and anti-patterns

- **Solution first.** Starting from "we need an agent" and looking for a problem. Write the problem and the metric first, and test a non-agent baseline.
- **Criteria after the build.** Setting targets once results exist. Fix them at the first tollgate.
- **A target with no baseline.** "90% accurate" means nothing without the current figure.
- **Only performance criteria.** Forgetting the limit criteria (what must never happen).
- **Autonomy by prompt.** Telling the model not to do something that the system still allows.
- **Responsible AI as an end-of-project review.** It needs budget and time in every phase, and again in maintenance.
- **Assuming payment equals privacy.** Paying a provider does not by itself stop training; read the terms.
- **Confidential data on free models.** The free tiers' privacy settings allow providers that may train on prompts.
- **No owner.** An agent with no accountable person, or one whose owner is "the AI team".
- **A new regime for every agent.** Building a registry or a special process for one agent. Use the client's existing software governance.
- **No handover.** The FDE as permanent operator, with no runbook, service owner or measurement the client can run.
- **No adoption plan.** A correct system nobody trusts or uses. Show the accuracy and the usage.
- **A heavyweight platform on day one.** Buying or building a large agent platform before one use case is proven.
- **Dumping the whole question bank.** Ask in small themed groups and confirm what you heard.

## In UnderCover

- **The brief.** The head of claims operations writes the pilot brief in business language: how claims work today, what the agent should do, what the team needs to see, rules, records and a "Not for now" list. Later briefs follow the same shape and each comes from the person who asked for the work.
- **The success metric.** The goal is claims decided without a handler, as accurately as the handlers decide them, with a person approving any payout over $1,000. By the final build this is three numbered criteria: a straight-through share of at least 70% on the whole held-out set, accuracy at or above the objective in Settings, and a person's approval on every payout over the limit. The straight-through share counts every claim that was not referred, including approvals held for sign-off. The third criterion is a limit; the first two are performance.
- **Autonomy tiers.** Automatic, approval-first and prohibited actions as in the table above. The over-$1,000 rule is enforced by the system: the backend refuses the agent's payment until a handler signs off, and later the AgentCore Gateway's policy refuses it too. The held-out answers sit where the claim agent cannot read them, and the improver cannot change the limits, evaluation sets or judge; nothing it proposes takes effect until a handler approves.
- **Governance as a software asset.** The dispatcher, claim agents and improver are parts of one product with one accountable owner (the owner of the claims product). The configuration is in versions and a handler approves every change; traces and spend are recorded for every claim and run. From Week 2 Day 5 only the senior handler can approve a payout over the limit, start improvement rounds or change settings.
- **Privacy.** Memory saves the claim and decision, never the customer's story or documents, and a customer's memories are recalled only when working that customer's claims. Masking personal fields for the agent was a deliberate "Not for now". The context-layer files each name a source, an owner and a review date, so data governance stays the owner of that data.
- **Handover.** On the last build day a Copilot lets a handler work the queue, ask why a claim needs them, send it back with a note, sign off a payout after a confirmation card, and ask "are we meeting the success criteria we agreed?"; the answer is computed in code from a held-out evaluation. The final teardown and cost checks end the engagement.

## Related

- [building with coding agents](building-with-coding-agents.md): the second meaning of ADLC, plans, quality gates and reviews
- [agent architecture](agent-architecture.md): agent or not, single or multi-agent, systems around the agent
- [evals and observability](evals-and-observability.md): turning criteria into measurements
- [security and guardrails](security-and-guardrails.md): enforcing autonomy limits
- [durable state and HITL](durable-state-and-hitl.md): building the approval step
- [context layer and integrations](context-layer-and-integrations.md): data owners and systems of record
- [production deployment on AWS](production-deployment-aws.md): where the agent runs, cost, teardown
- [decision guide](decision-guide.md) and [checklists](checklists.md): trees and review lists
- Templates: [DISCOVERY_NOTE.md](../assets/templates/DISCOVERY_NOTE.md), [ADR.md](../assets/templates/ADR.md), [HANDOVER.md](../assets/templates/HANDOVER.md)

## Sources

- Week 3 Day 1 slides 4-16 (the two ADLCs, lifecycle, FDE through the lifecycle, discovery, systems architecture, hosting, governance levels and tollgates, autonomy, managing many agents, responsible AI, privacy, accountability, handover and adoption) and slides 96, 98-101 (assignment, skills, job adverts, next step), as taught in the course (Oct 2026)
- `guides/for_agents/AGENT_GUIDE_WEEK3.md` (Day 1 and Day 5, including corrections on privacy and the straight-through definition); `guides/for_agents/AGENT_GUIDE_WEEK1.md` (Day 1 FDE meaning and job-advert correction, Day 2 success metric); `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Day 1 traps); `guides/for_agents/AGENT_COURSE_GUIDE.md`
- `labs/week3day1free.ipynb` (assignment: discovery note and ADR)
- `docs/SPEC.md` on `main` (pilot brief) and `origin/week3day5-end:docs/SPEC.md` (final requirements and the success criteria agreed)

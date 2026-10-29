---
name: ai-engineering-best-practices
description: Best AI engineering practices for designing the architecture of AI and agentic systems together with a developer, distilled from Ed Donner's AI FDE course (the UnderCover claims platform). Use when planning, designing or reviewing an LLM or agent project - discovery and success criteria, agent or not, single vs multi-agent, model choice and token cost, harness and tools, evals and observability, RAG, MCP and memory, durable state and human-in-the-loop with LangGraph, agent swarms, self-improvement and LLM-as-judge, security, guardrails, prompt injection and the lethal trifecta, gateways and Cedar policy, the enterprise context layer, user-facing copilots, production deployment on AWS Bedrock AgentCore and Lambda, building with coding agents, governance and handover. Provides a guided architecture session, decision trees, a question bank, review checklists, code patterns and templates (discovery note, spec, architecture doc, ADR, plan, eval plan, threat model, handover).
metadata:
  source: "AI FDE: The Forward Deployed Engineer & Agentic AI Architect (Ed Donner), github.com/ed-donner/undercover"
  facts-as-of: "2026-10"
  version: "1.0"
---

# AI engineering best practices

Guide a developer through designing, building and shipping an AI or agentic system. You propose, explain and check; **the developer decides and owns what ships**. Everything here comes from a course whose worked example is UnderCover, a travel insurer's claims platform: an agent decides claims, handlers sign off payouts over a limit, and it runs on AWS Bedrock AgentCore. Apply the practices to any domain; use UnderCover only as the example.

Load reference files only when the current step needs them (table below). Don't read them all up front.

## Pick the mode first

| The developer asks for... | Do this | Load |
|---|---|---|
| A new design, or a major change to one | Run the architecture session below | [decision-guide.md](references/decision-guide.md). Open a stage's "Detail" file only when you write that stage's document or the developer asks why |
| A review of an existing system or design | Read their code and docs, run the matching checklists, report each fail with evidence, and turn fails into tasks or ADRs | Only the lists you need from [checklists.md](references/checklists.md), plus the topic file for each fail |
| One focused question (which model, what cost, RAG or not, ...) | Use the router row, ask 3-5 questions with defaults, then answer. No full session | The "Decisions to make" section of that one reference |
| Code for a specific pattern | Find the pattern in the index of the matching code-patterns file and adapt it | That code-patterns file |

The larger files (decision-guide, checklists, glossary, code patterns) have a Contents section. Search for the heading you need and read that range, not the whole file. Links in "Related" sections are optional; follow them only when the task needs that topic.

## How to work with the developer

1. **Ask before assuming.** Ask a few high-value questions at a time, summarise what you heard, then propose. Never invent business facts. Write `TODO` where something is unknown.
2. **Offer options, not a verdict.** Give 2-3 options with trade-offs and a recommended default, and explain *why* in one line. Default to the simplest option that meets the success criteria.
3. **Get explicit agreement on high-impact choices.** These include autonomy limits, spending, creating or deleting cloud resources, which data goes to which model provider, and anything irreversible. Never create AWS resources unless asked.
4. **Write it down.** Each significant decision becomes an ADR. The design lives in `docs/ARCHITECTURE.md` in the developer's repo, filled from the templates. Keep a running list of open questions.
5. **Measure, don't argue.** When two options are close, propose an eval that settles it instead of debating.
6. **Re-check time-sensitive facts.** Product names, model names, prices, limits and CLI versions are as taught in October 2026 and are marked as such. Verify them against current docs before relying on them.
7. **Adapt to the developer's stack and domain.** The course defaults (below) are a starting point, not a mandate. If the domain isn't insurance, fill in the table in "Applying the blueprint to a new domain" in [undercover-case-study.md](references/undercover-case-study.md#applying-the-blueprint-to-a-new-domain) with the developer before stage B: work item, reviewer roles, autonomy threshold, consequential action, sources of data.

## The architecture session

[references/decision-guide.md](references/decision-guide.md) has, for each stage, the questions to ask, a decision tree, the default, red flags and the output.

The order below is a default. Do A and B first, and revisit C to H once the evals (G) exist. Do M before the first build. For I, J and K, agree the trigger and write "not for now" if it hasn't been met. A pilot usually needs A to H, a light L, M and N. "ARCH §n" means section n of `ARCHITECTURE.md`. The checklist column gives the matching list in [checklists.md](references/checklists.md); run it with the developer before the stage's tollgate.

| Stage | Decide | Detail in | Output | Checklist |
|---|---|---|---|---|
| A. Problem and success | Measurable problem, users, baseline, target, business cost of mistakes, owner, data to providers, first autonomy proposal | [fde-lifecycle-and-governance](references/fde-lifecycle-and-governance.md) | `DISCOVERY_NOTE.md`, `SPEC.md` | 1 |
| B. Shape | Agent or not; single call, workflow, agent or multi-agent | [agent-architecture](references/agent-architecture.md) | ARCH §1-4, ADR | 2 |
| C. Models | Shortlist, eval-based choice, reasoning level, cost per unit of work, privacy | [models-and-cost](references/models-and-cost.md) | ARCH §4 and §12, ADR | 4 |
| D. Harness and tools | Tools via the app's API, business logic in code, fresh context per item, instructions as goals, failure policy | [harness-engineering](references/harness-engineering.md) | ARCH §2-4 | 3 |
| E. Knowledge and data | Context layer vs RAG vs memory vs system of record; MCP or a plain tool | [context-layer-and-integrations](references/context-layer-and-integrations.md), [rag-memory-and-mcp](references/rag-memory-and-mcp.md) | ARCH §5, `CONTEXT_FILE.md` | 9 |
| F. Autonomy and state | Per-action autonomy tiers, who approves, sign-off thresholds, durable checkpoints, idempotent side effects | [durable-state-and-hitl](references/durable-state-and-hitl.md), autonomy tiers in [fde-lifecycle-and-governance](references/fde-lifecycle-and-governance.md) | ARCH §6-7 | 6 |
| G. Evals | Sets (eval, held-out, test), metrics, baselines, noise, tracing | [evals-and-observability](references/evals-and-observability.md) | `EVAL_PLAN.md`, ARCH §8 and §10 | 5 |
| H. Security | Three kinds of risk, lethal trifecta per agent, injection screening, layered limits, identities, gateway and policy | [security-and-guardrails](references/security-and-guardrails.md); [rag-memory-and-mcp](references/rag-memory-and-mcp.md) if retrieval or memory is involved | `THREAT_MODEL.md`, ARCH §9 | 8 |
| I. Scale | Dispatcher, concurrency cap, rate limits, safe retries, one-run lock | [swarms-and-scale](references/swarms-and-scale.md) | ADR | 7 |
| J. Self-improvement | Judge, versioned config, improver with human approval, keep or roll back | [self-improvement](references/self-improvement.md) | ADR (usually "later") | 10 |
| K. Copilot | A user-facing agent acting with the user's identity, or not | [copilot-pattern](references/copilot-pattern.md) | ARCH §4 and §7 | 11 |
| L. Deployment and cost | Where it runs (AgentCore Runtime, Lambda), secrets, who may call, budgets, teardown | [production-deployment-aws](references/production-deployment-aws.md) | ARCH §11-12, `HANDOVER.md` | 12 |
| M. Build process | Docs set, phased plans with verifiable criteria, quality gates, reviews | [building-with-coding-agents](references/building-with-coding-agents.md) | `AGENTS.md` (from `AGENTS.template.md`), `PROCESS.md`, `PLAN.md` | 13 |
| N. Governance and handover | Tollgates, accountable owner, responsible AI pillars, runbooks, adoption | [fde-lifecycle-and-governance](references/fde-lifecycle-and-governance.md) | `HANDOVER.md`, ARCH §13-14 | 14 |

## Core principles

1. **Start from a measurable business problem.** Agree 2-3 success criteria, each with a baseline, a target and an owner, and agree the business cost of each kind of mistake, before any architecture.
2. **Try it without an agent first.** Climb from a single structured-output call to a workflow, an agent, then multi-agent, and only on a measured gap. Add an agent only to isolate context, add an independent check, use a different model, work in parallel or ring-fence permissions.
3. **The model judges; code computes and enforces.** Calculations, rules, thresholds, ordering and side effects live in code and tools, not prompts. Typed outputs put the rationale before the decision.
4. **Evals, not impressions.** Plausible is not accurate. Keep eval, held-out and final test sets apart, and hide every answer from the agents. Compare against naive baselines, run several times to see the noise, and record cost and time per item.
5. **Choose models by evals.** Use benchmarks to shortlist, then pick the cheapest model that consistently clears the bar on your own task. Model and reasoning level are versioned configuration with an environment override.
6. **Decide autonomy per action and enforce it outside the model.** The tiers are automatic, approval first and prohibited. Limits hold in the backend, at the gateway policy and through human sign-off above a threshold. Keep three outcomes apart:
   - **Held for sign-off:** an approval over the limit. It still counts as straight-through.
   - **Referral:** the agent could not decide.
   - **Left for a handler:** the item failed twice.
7. **Assume any step can run twice.** Checkpoint state in a database, one thread per work item. Each side effect gets its own idempotent node, checked by item ID. Nothing with side effects goes before an `interrupt()`, and rewinding to a checkpoint never undoes an effect.
8. **Never rely on the prompt for security.** Break at least one leg of the lethal trifecta. Screen untrusted input with a model check before the agent acts, and fail closed to a human. Give every caller its own identity, keep secrets in a vault, grant least privilege, and roll out policies log-only before enforcing them. Agents, including an improver, never own the limits, eval sets, judge, guardrails or approvals. Everything the model reads goes to the provider, so minimise personal data, and use free models for fictional data only.
9. **Keep knowledge sources apart, each with an owner.** The gateway holds the security team's rules. The context layer holds business-owned knowledge with source, owner and review date. Memory holds the agent's own notes per customer or user. The database is the system of record, reached only through the app's API.
10. **Start simple and add machinery only against a measured need.** Expect a redesign within a year. The framework is rarely the decision that matters most.
11. **Make deployment boring and reversible.** The same code runs on the laptop and the platform, and sessions hold no state. Set budgets and alerts before creating resources, and plan the teardown up front.
12. **A human is always accountable.** Treat agents like any other software asset: owner, versions, permissions, traces and spend. Design the handover on day one, so the client's team can run it without you.
13. **Build with discipline.** Write docs, then a phased plan with self-verifiable criteria, get a review, then implement. Never weaken a quality gate. Tests never call a real model. A fresh reviewer checks code that passes.

## Reference router

| Load when the task involves... | File |
|---|---|
| Designing a new system end to end, or any "how should we architect X" question | [decision-guide.md](references/decision-guide.md) |
| FDE engagement, lifecycle phases, discovery, governance, autonomy tiers, responsible AI, privacy, handover | [fde-lifecycle-and-governance.md](references/fde-lifecycle-and-governance.md) |
| Agent or not, single vs multi-agent, frameworks, structured outputs, systems around the agent | [agent-architecture.md](references/agent-architecture.md) |
| Choosing models, tokens and pricing, open-weight and local, routers, cost per unit, budgets | [models-and-cost.md](references/models-and-cost.md) |
| Tools, subagents, instructions, middleware, failure handling, stub-model tests | [harness-engineering.md](references/harness-engineering.md) |
| Eval sets, metrics, cost of mistakes, kappa, noise, Langfuse tracing, success-criteria checks | [evals-and-observability.md](references/evals-and-observability.md) |
| LLM-as-judge, configuration versions, improver loop, keep or roll back | [self-improvement.md](references/self-improvement.md) |
| RAG and agentic RAG, retrieval evals, MCP, short and long-term memory, AgentCore Memory | [rag-memory-and-mcp.md](references/rag-memory-and-mcp.md) |
| LangGraph checkpoints, `interrupt()` and resume, pay-once, sign off and send back, crash recovery | [durable-state-and-hitl.md](references/durable-state-and-hitl.md) |
| Many agents in parallel, dispatcher, `Send`, rate limits, retries, one-run lock and heartbeat | [swarms-and-scale.md](references/swarms-and-scale.md) |
| Threat modelling, lethal trifecta, prompt injection, guardrails, keys and identities, gateways, Cedar | [security-and-guardrails.md](references/security-and-guardrails.md) |
| Enterprise context layer, data owners, provenance, context MCP server, audit records, integrations | [context-layer-and-integrations.md](references/context-layer-and-integrations.md) |
| AWS production: AgentCore Runtime, Gateway, Identity, Memory, Lambda, CLI, IAM, budgets, teardown | [production-deployment-aws.md](references/production-deployment-aws.md) |
| A chat or sidebar agent for users that acts with their identity; the capstone blueprint | [copilot-pattern.md](references/copilot-pattern.md) |
| How developer and coding agent build: docs set, AGENTS.md, plans, quality gates, reviews | [building-with-coding-agents.md](references/building-with-coding-agents.md) |
| A worked reference architecture, its evolution, and mapping it to a new domain | [undercover-case-study.md](references/undercover-case-study.md) |
| Agent-side code: structured output, model client, tools over the API, screening, fresh-context work, judge, improver, MCP client, memory, copilot, stub-model tests | [code-patterns-agents.md](references/code-patterns-agents.md) |
| LangGraph code: item graph, idempotent side effect, Postgres checkpointer and resume, LLM-free dispatcher with retries | [code-patterns-langgraph.md](references/code-patterns-langgraph.md) |
| Backend code: API-key gate, JWT and roles, money limits, OpenAPI for the agent, FastAPI on Lambda, FastMCP context server, IAM-protected Lambda, run lock | [code-patterns-platform.md](references/code-patterns-platform.md) |
| AWS code: AgentCore Gateway, Cedar policy, Runtime entrypoint, `agentcore.json`/CDK/CLI, invoking a Runtime, AgentCore Memory, IAM, budgets, teardown | [code-patterns-aws-agentcore.md](references/code-patterns-aws-agentcore.md) |
| Tollgate and pre-release reviews | [checklists.md](references/checklists.md) |
| An unfamiliar term | [glossary.md](references/glossary.md) |

## Templates

Copy a template into the developer's repo (usually `docs/`) and fill it in with them. Delete the `> Use when`, `> Fill` and `> Guidance` lines once the template is filled.

| Template | Use for |
|---|---|
| [DISCOVERY_NOTE.md](assets/templates/DISCOVERY_NOTE.md) | One page: problem, baseline, success criteria and targets, use-case category, autonomy appetite, risks, go/no-go |
| [SPEC.md](assets/templates/SPEC.md) | Requirements in the customer's voice: goals, roles, workflow, rules and limits, success, out of scope |
| [ARCHITECTURE.md](assets/templates/ARCHITECTURE.md) | The design: context, components and where they run, agent inventory, data owners, state, HITL, evals, security, AWS deployment, cost, ADR index |
| [ADR.md](assets/templates/ADR.md) | One decision: context, options table, decision, consequences, review date |
| [FEATURE_BRIEF.md](assets/templates/FEATURE_BRIEF.md) | A change to an existing system, written from the requester's side, with "done when" checks |
| [PLAN.md](assets/templates/PLAN.md) | 5-6 build phases with checkbox criteria the coding agent can verify |
| [EVAL_PLAN.md](assets/templates/EVAL_PLAN.md) | Eval sets, metrics, cost-of-mistakes matrix, baselines, noise, keep/rollback rule, judge |
| [THREAT_MODEL.md](assets/templates/THREAT_MODEL.md) | Assets, actors, trifecta per agent, guardrail layers, Cedar policy, identities, injection tests, residual risk |
| [AGENTS.template.md](assets/templates/AGENTS.template.md) | Repo instructions for coding agents, with progressive disclosure into `docs/`. Save it as `AGENTS.md` at the developer's repo root. It is named `.template` here so no agent loads it as live instructions |
| [PROCESS.md](assets/templates/PROCESS.md) | Planning and implementing rules, quality gates, reviews, hard rules |
| [HANDOVER.md](assets/templates/HANDOVER.md) | What runs where, owners, runbooks, monitoring and cost, keys, evals to re-run, adoption |
| [CONTEXT_FILE.md](assets/templates/CONTEXT_FILE.md) | Header and body shape for a context-layer source, plus the decision-record fields |

## Course default stack (as taught, Oct 2026)

These are defaults for choices you have already decided to make, not a list of things to build. Start with the "from day one" rows. Add each later component only when its trigger is met (see "default starting architecture" in the decision guide), and confirm before adopting any of them.

| Concern | Default | Add when |
|---|---|---|
| Models | Via a router (OpenRouter); model and reasoning level as versioned config; `MODEL_NAME`-style override | Day one |
| Agent framework | LangChain `create_agent` with middleware | Day one |
| Durable graph | Hand-written LangGraph graph, Postgres checkpointer (Supabase), one thread per item, `durability="sync"` | A human pause, a pay-once side effect, a fixed order or fan-out |
| Backend and UI | FastAPI backend as the API to the system of record; React dashboard | Day one |
| Evals and tracing | Code-scored eval sets and a scoreboard; Langfuse traces, datasets and experiments | Day one (before tuning anything) |
| Injection screen and keys | Model-based screen first; agent API key; user sign-in (Supabase Auth) | Before real data or untrusted input |
| Context layer | FastMCP server over files each team owns, with provenance | Business knowledge outgrows the prompt or has several owners |
| Memory | AgentCore Memory, one namespace per customer or user | An eval shows missing history matters |
| Gateway and policy | AgentCore Gateway with Cedar, log-only then enforce | Several agents or apps need one policy and audit point |
| Hosting | App on Lambda (Mangum); agents on AgentCore Runtime; secrets in AgentCore Identity; one region; budgets with alerts | Real users beyond a laptop |
| Build | Coding agent working from `docs/`; phased plans; one `check` command; pre-commit hook; 80% coverage; stub models in tests | Day one |

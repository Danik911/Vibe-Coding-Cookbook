# ai-engineering-best-practices

An Agent Skill that helps a coding agent and a developer design the architecture of an AI or agentic system together: from the first discovery questions to production on AWS, handover and teardown. This README is for you, the developer. Agents load `SKILL.md`, and open this file only if asked.

## What it is

The skill consolidates best practices from Ed Donner's course *AI FDE: The Forward Deployed Engineer & Agentic AI Architect* (repo: <https://github.com/ed-donner/undercover>). The course builds one commercial project, UnderCover, a fictional travel insurer's claims platform. Here UnderCover is only the worked example: every practice is written to apply to any domain, with a short "In UnderCover" section to make it concrete.

- **Audience:** an AI coding agent that guides the design session (asks the right questions, offers options with trade-offs, writes the architecture docs), and the developer who decides and owns what ships.
- **Scope:** all three weeks of the course, with Week 3 (security, gateways, the context layer, production deployment, the copilot) covered most deeply.
- **Deployment target:** AWS as taught in the course: Bedrock AgentCore (Runtime, Gateway, Identity, Policy, Memory) and Lambda. The patterns carry to other clouds; the CLI, roles and infrastructure code do not.
- **What you get:** a guided architecture session, decision trees and a question bank, review checklists, code patterns, a glossary, and fill-in templates for the documents a project needs.

## How to use it

Invoke it by name in Copilot CLI, or just mention it in a prompt:

```text
/ai-engineering-best-practices
Use /ai-engineering-best-practices to help me design the architecture for <project>.
Run the security checklist from /ai-engineering-best-practices on this design.
Use /ai-engineering-best-practices to fill in a discovery note and an eval plan for <project>.
```

The agent can also pick the skill up by itself when your prompt matches its description. Useful commands inside a session:

| Command | Does |
|---|---|
| `/skills list` | Lists the skills the CLI found |
| `/skills info ai-engineering-best-practices` | Shows the skill's description and where it was loaded from |
| `/skills reload` | Picks up a skill you added or edited during the session |

A good session starts with the problem, not the technology: tell the agent what the business needs measured, who the users are and what the agent may and may not do. The agent runs the stages in `SKILL.md` and writes the outputs (discovery note, architecture doc, ADRs, eval plan, threat model) into your repo.

## Where it lives

This is a **project skill**: it sits in `.github/skills/ai-engineering-best-practices/` of this repo, so it is available when you work here. To use it in every project, copy the folder into your personal skills directory (`~/.copilot/skills` or `~/.agents/skills`).

PowerShell, from the repo root (create the destination first, or the copy lands under the wrong name):

```powershell
New-Item -ItemType Directory -Force $HOME\.copilot\skills | Out-Null
Copy-Item -Recurse .github\skills\ai-engineering-best-practices $HOME\.copilot\skills\
```

macOS or Linux:

```bash
mkdir -p ~/.copilot/skills && cp -R .github/skills/ai-engineering-best-practices ~/.copilot/skills/
```

Then run `/skills reload`. A personal copy does not update itself when the project copy changes: copy again.

## How it is organised

The skill uses progressive disclosure, so the agent's context stays small until detail is needed:

1. `SKILL.md` is always loaded when the skill is used: the router, the core principles, how to work with you, and the architecture session stages.
2. `references/` files are loaded on demand, one topic each, only for the stage you are in. They are one level deep: `SKILL.md` links to each directly.
3. `assets/templates/` are filled in your repo (usually `docs/`) as you decide things, and are never loaded as instructions.

## File map

| File | Purpose |
|---|---|
| `SKILL.md` | Router, core principles, working agreements and the architecture session |
| `references/decision-guide.md` | Sit with the developer to design or review an architecture: questions, options, trees, outputs |
| `references/fde-lifecycle-and-governance.md` | Start a project: FDE role, ADLC phases, discovery, success criteria, autonomy, responsible AI, handover |
| `references/agent-architecture.md` | "Should this be an agent?", single vs multi-agent, frameworks, structured outputs, business logic in code |
| `references/models-and-cost.md` | Choose models and reasoning effort, open-weight vs frontier, cost per unit of work, where prompts go |
| `references/harness-engineering.md` | Design the code around the model: tools, instructions, subagents, middleware, failures, stub-model tests |
| `references/evals-and-observability.md` | Success metrics, eval sets, cost of mistakes, baselines, noise, tracing |
| `references/self-improvement.md` | LLM as a judge, configuration versions, the improver loop, keep or roll back |
| `references/rag-memory-and-mcp.md` | RAG and agentic RAG, MCP, short and long-term memory, AgentCore Memory |
| `references/durable-state-and-hitl.md` | Steps that wait for people, crash recovery, never paying twice (LangGraph checkpoints, interrupts) |
| `references/swarms-and-scale.md` | Batches in parallel: dispatcher, concurrency, rate limits, safe retries, one run at a time |
| `references/security-and-guardrails.md` | Threat modelling, lethal trifecta, prompt injection, guardrails, identities, gateways, Cedar |
| `references/context-layer-and-integrations.md` | Business knowledge for the agent: context layer, data owners, enterprise MCP, audit |
| `references/production-deployment-aws.md` | Where and how the agent runs on AWS: AgentCore Runtime, Lambda, accounts, budgets, teardown |
| `references/copilot-pattern.md` | A user-facing chat agent that acts with the user's identity; the capstone blueprint |
| `references/building-with-coding-agents.md` | Docs set, plans, quality gates and reviews when a coding agent builds the code |
| `references/undercover-case-study.md` | The reference architecture, how it evolved, and how to map it to a new domain |
| `references/code-patterns-agents.md` | Agent-side snippets: structured outputs, model client, tools, screening, judge, improver, MCP client, memory, copilot, stub-model tests |
| `references/code-patterns-langgraph.md` | LangGraph snippets: item graph, idempotent side effect, Postgres checkpointer and resume, LLM-free dispatcher, helpers |
| `references/code-patterns-platform.md` | Backend snippets: API key, JWT and roles, money limits, OpenAPI for the agent, Lambda, FastMCP context server, run lock |
| `references/code-patterns-aws-agentcore.md` | AWS snippets: Gateway, Cedar, Runtime entrypoint and CLI, invoking a Runtime, AgentCore Memory, IAM, budgets, teardown |
| `references/checklists.md` | Tollgate, pre-release, per-phase and handover reviews |
| `references/glossary.md` | Terms met in the skill and the course |
| `assets/templates/DISCOVERY_NOTE.md` | One page at the start: problem, baseline, success criteria, go/no-go |
| `assets/templates/SPEC.md` | Requirements in the customer's voice, before any design |
| `assets/templates/ARCHITECTURE.md` | What runs where, who owns what and why |
| `assets/templates/ADR.md` | One architecture decision that is costly to reverse |
| `assets/templates/FEATURE_BRIEF.md` | A change request to an existing system, from the requester's side |
| `assets/templates/PLAN.md` | Build phases with checkbox criteria the coding agent can verify |
| `assets/templates/EVAL_PLAN.md` | Eval sets, metrics, thresholds and schedule, from the success criteria |
| `assets/templates/THREAT_MODEL.md` | Before real data, tools or a public address: assets, actors, layers of defence |
| `assets/templates/AGENTS.template.md` | A short repo map for the coding agent, with progressive disclosure into `docs/`. Save it as `AGENTS.md` at the root of the developer's repo; it is named `.template` here so no agent loads it as live instructions |
| `assets/templates/PROCESS.md` | How the developer and coding agent plan, build, check and review |
| `assets/templates/HANDOVER.md` | What the client's team needs to run, measure, change and retire the system |
| `assets/templates/CONTEXT_FILE.md` | Shape of a context-layer file and of a decision record |

## Maintenance

- **Keep it small.** `SKILL.md` stays under 500 lines. Each reference is about 150 to 400 lines and at most about 450, one topic per file, linked directly from `SKILL.md`. Split a file that outgrows the cap rather than stretching it.
- **Re-check time-sensitive facts.** Product and model names, prices, limits, CLI versions and market surveys are marked "as taught in the course (Oct 2026)", and the frontmatter records `facts-as-of: "2026-10"`. Re-verify them against current documentation before quoting them to a customer, then update the marker.
- **Add a topic.** (1) Write `references/<topic>.md` in the same shape as the others: "When to read this", key principles with reasons, decisions to make with the developer, pitfalls, "In UnderCover", related, sources. (2) Add a row to the router in `SKILL.md`, a stage if it belongs in the session, and the trigger words in the description. (3) Add its terms to `references/glossary.md`. (4) Add items to `references/checklists.md` and questions to `references/decision-guide.md`. (5) Add a row to the file map above. (6) Run `/skills reload`.
- **Validate the frontmatter.** `name` must equal the folder name and use only lowercase letters, digits and hyphens. `description` must be present and at most 1,024 characters. Quick check from the repo root:

```powershell
$skill = ".github\skills\ai-engineering-best-practices"
$text = Get-Content "$skill\SKILL.md" -Raw
$front = [regex]::Match($text, '(?s)^---\r?\n(.*?)\r?\n---').Groups[1].Value
"name ok: " + ($front -match '(?m)^name: ai-engineering-best-practices\s*$')
"description chars: " + [regex]::Match($front, '(?m)^description: (.+)$').Groups[1].Value.Length
Get-ChildItem $skill -Recurse -Filter *.md | ForEach-Object { '{0,4} {1}' -f (Get-Content $_.FullName).Count, $_.FullName.Substring((Resolve-Path $skill).Path.Length + 1) }
```

- **Never add secrets or personal data**, and write in your own words: paraphrase the course, do not paste slides or notebooks.

## Attribution and disclaimer

These are personal study notes that paraphrase Ed Donner's course. They are not official course material and are not endorsed by the course author. UnderCover is a fictional company, and the figures quoted from the course's runs are illustrations of the shape of results, not benchmarks. Product names, model names, prices, limits and CLI versions are as of October 2026 and change quickly, so check them before relying on them. The lethal trifecta is Simon Willison's term, credited where it appears. The skill gives guidance and options; the developer decides and is accountable for what ships.

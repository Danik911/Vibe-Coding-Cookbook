# {{Project name}}

> Save as `AGENTS.md` at the root of the developer's repo.

> Use when: starting a repository that a coding agent will build in, to give it a short map of the project, the rules and where to read more.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Progressive disclosure. Keep this file short (about 100 lines) and put detail in `docs/`: the agent reads this map first, then the documents it needs. Say what to read in full and when. State rules as short imperatives with the reason where it is not obvious. Move anything long into a doc and link it. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

## The context

{{Two or three sentences: what the project is, who the customer is, who the developer is, and your role as their coding agent.}} The developer directs the work and reviews your plans and builds. The OS is {{Windows PowerShell | macOS}}; give commands that work there.

Example (UnderCover): UnderCover Travel Insurance is a fictional insurer. We build a claims platform: a backend, a dashboard for handlers, and an agent that decides claims. The developer is the forward deployed engineer; you are their coding agent.

## Start here

IMPORTANT: before you plan, build or change anything, or answer questions about the product, read each of these files in full:

1. `docs/SPEC.md`: what the business needs
2. `docs/TECH_STACK.md`: the tech choices
3. `docs/CODE_STANDARDS.md`: how to write the code
4. `docs/PROCESS.md`: how to plan, build and check the work
5. `docs/STATUS.md`: what is built and how to run it
6. `docs/PLAN.md`: the current plan. Later plans go in their own files, such as `docs/PLAN_{{NAME}}.md`

Read on demand: `docs/ARCHITECTURE.md` (design and decisions), `docs/EVAL_PLAN.md` (how success is measured), `docs/THREAT_MODEL.md` (security), `docs/adr/` (decision records), `docs/{{BRAND}}.md` (look and tone, if there is a UI).

## Your role

- The documents in `docs/` are the customer's requirements; treat them as such.
- Write plans the developer can review: say what each phase builds and why you chose that approach.
- Explain your work when asked, at the level asked. Then deliver to the standards in `docs/`.
- Build only what the documents in `docs/` ask for. Do not build ahead of the plan.
- Where a brief's notes on the existing build disagree with the code, follow the brief's intent.

## Work requests

| Say | You do |
| --- | --- |
| "Please plan {{work}}" | write `docs/PLAN_{{NAME}}.md` as `docs/PROCESS.md` says, write no code, then stop |
| "Please implement the plan for {{work}}" | build every phase in order, checking and committing each |
| Anything else | make the change, check it, review it, commit it |

## Folders

- `docs/`: specification, standards, plans, decisions
- `{{backend/}}`, `{{agent/}}`, `{{dashboard/}}`, `{{e2e/}}`: the product
- `{{context/}}`: the business's data files that become the context layer, each naming its source, owner and review date
- `{{data/}}`: business data; `{{data/evals/}}` holds the answer key
- `{{infra/}}`: deployment files from the platform team

## Rules

- Run `{{check command}}` before you hand work over. Never skip hooks, never lower a threshold, turn off a rule or exclude a file to get a green run; if a rule looks wrong, stop and ask.
- Add tests with each change. Tests never call a model; use a stub model.
- Do not open `{{answer key path}}` unless asked. The agent under test must never see it.
- Never create, change or delete cloud resources unless the developer asks. Never print, log or commit secrets; use `.env`, which is not in git.
- Never push. Commit each checked and reviewed change.
- Keep `docs/STATUS.md` current.
- Use {{uv | npm | the project's tools}}; everything must work on {{Windows and macOS}}.

## Reviewing and recording

- Have a fresh subagent review each change against `docs/CODE_STANDARDS.md` before you commit; see `docs/PROCESS.md`.
- Record significant decisions as an ADR in `docs/adr/`. When a review finds a problem that should never recur, add the rule to `docs/CODE_STANDARDS.md` or `docs/PROCESS.md`, and tell the developer.

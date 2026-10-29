# Building with Coding Agents

> When to read this: the developer is about to start (or restart) building an AI product with a coding agent, or asks how to set up docs, plans, quality gates and reviews so the agent's code is fit to ship. This is the "build code with agents" half of the ADLC. For designing the agent product itself, read [agent-architecture.md](agent-architecture.md) and [harness-engineering.md](harness-engineering.md).

## Contents

- Key principles
- Two meanings of ADLC, vibe coding vs working with coding agents
- Be the boss: what humans keep
- The docs set and AGENTS.md
- How the docs evolve
- The build loop: brief, plan, review, implement
- Writing a plan with checkable criteria
- Harness, Harden, Humans: quality gates
- Reviews and feedback loops
- Working practices (context, permissions, commits, MCP, Windows, weaker models)
- Starting a new project
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover, Related, Sources

## Key principles

1. **The developer owns what ships.** The coding agent writes; the human is accountable for the result. Why: "the agent did it" is not an answer a customer accepts.
2. **Write the requirements down, in the customer's voice, before any code.** A spec, a tech stack, code standards, a process and a status file give every fresh agent session the same starting point. Why: the agent has no memory between sessions; the repo is the memory.
3. **Plan first, in a file, with no code; review the plan; then implement.** Why: a bad plan is cheap to fix, a bad build is not, and the plan file survives context resets.
4. **Every phase has success criteria the agent can verify itself**, written as checkboxes: tests, commands with expected output, API calls, browser checks. Why: "done" must be provable without trusting the agent's say-so.
5. **Gate everything automatically**: formatter, linter, type checker, unit tests with a coverage threshold, end-to-end tests, a pre-commit hook, one `check` command. Why: generated code looks plausible; machines catch what eyes skip.
6. **Never weaken a gate to get green.** No `--no-verify`, no lowered threshold, no excluded file, no disabled rule: stop and ask. Why: a gate the agent can edit is not a gate.
7. **Passing checks is not the same as fit to merge.** Add a review by a fresh subagent against the code standards before each commit, and a human review at the end of each build. Why: the course's first agent build passed every test and still had code the developer would not accept.
8. **Turn every review finding into a rule in the docs.** Why: the same mistake otherwise returns on the next build, from a fresh context that never saw the review.
9. **Tests never call a model.** Use a stub model and stand-ins for external services. Why: tests stay free, fast, deterministic and runnable offline; live model runs are rare, planned and cost-capped.
10. **Small steps, frequent commits, fresh context per task.** Why: small diffs are reviewable, a commit is an undo point, and weaker or cheaper models only cope with small steps.

## Two meanings of ADLC, vibe coding vs working with coding agents

The course uses "ADLC" in two senses (numbered on its slides):

| | Meaning | Where covered |
| --- | --- | --- |
| 1 | **Building agents with code**: the agent development lifecycle (discovery, R&D, development, implementation, maintenance) | [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md), most of the course |
| 2 | **Building code with agents**: how a developer and a coding agent deliver a product together | this file |

**Vibe coding** is prompting an LLM for code and accepting what comes back. It is fine for small pieces. The course's tips for it still apply inside a larger process:

- Ask for short, simple code; LLMs pad it with needless checks that hide the real logic (this became a code-standards rule, see below).
- For chat-based code generation, give the current date and ask for the latest API versions; models often reach for outdated calls of their own vendor's API.
- Ask more than one model, or ask a second model to verify and simplify the first one's answer. Ask for three variations and pick the clearest.
- Never accept 100-200 lines you cannot debug. Break the work into small, independently testable steps, have the model write the tests too, and run them yourself.

**Working with a coding agent** adds structure around that: written requirements, a plan, verifiable phases, automated gates, review and commits. The shift is from "prompt and hope" to "specify, plan, verify". Golden rule from the guide: start small, work incrementally.

For AI products, do the science before the software. Start in a notebook: how will success be measured, what data exists, which small prototype proves the technique. Draw the architecture after that. Findings from experiments go back into the next brief (the final UnderCover brief has a "what our team learned" section for exactly this). See [evals-and-observability.md](evals-and-observability.md).

### The landscape (as taught in the course, Oct 2026; re-check)

| Kind | Examples | Note |
| --- | --- | --- |
| IDE with agents built in | Cursor | |
| Extension in an editor | GitHub Copilot | |
| Terminal coding agent | Claude Code, Codex, OpenCode | OpenCode with OpenCode Zen's free models is the free route |

A coding agent is itself a **harness around a model** (for example Claude Code around Claude Opus 5.5): instructions, tools, permissions, context management. So you are a harness *user* with your coding agent and a harness *builder* with the product's agent. Everything in [harness-engineering.md](harness-engineering.md) applies to both. The course demonstrates with Claude Code, but nothing here depends on one tool; names of config files, flags and commands differ per tool (verify per tool).

## Be the boss: what humans keep

Use the agent for speed, and keep these with people:

| Humans keep | In practice |
| --- | --- |
| **Accountability** | The developer answers for every line that ships. Read plans and diffs. |
| **Evaluations** | Humans decide what "good" means and own the labeled data and answer keys. The coding agent never reads them (see working practices). |
| **Judgment** | Trade-offs, scope, "is this the right thing to build", risk. |
| **Taste** | Clean, idiomatic, simple code and a UI that looks right. The agent's first pass is rarely there. |
| **The harness** | The docs, standards, gates and process that steer the agent are the human's design, and are improved after each build. |

Being the boss does not mean typing the code. It means directing precisely, reviewing critically and refusing work that is not fit to merge.

## The docs set and AGENTS.md

Keep a small set of Markdown files in `docs/` that the coding agent reads before it plans, builds or answers anything about the product. Templates: [SPEC](../assets/templates/SPEC.md), [PROCESS](../assets/templates/PROCESS.md), [PLAN](../assets/templates/PLAN.md), [FEATURE_BRIEF](../assets/templates/FEATURE_BRIEF.md).

| File | Voice and owner | Holds | How it changes |
| --- | --- | --- | --- |
| `SPEC.md` | The customer (UnderCover's head of claims operations) | How the work is done today, what is wanted, what the team must see, rules, records, "not for now" | Stable; updated when a brief says so |
| Per-feature brief (`<NAME>.md`) | The person at the customer who asked for the work | Where we're heading, numbered wants, what stays the same, what done looks like, not for now, lessons from experiments, planning instruction | One per build; copied into `docs/` at the start of that build |
| `TECH_STACK.md` | The engineering owner | Technology choices, one entry per folder, environment variables, versions | Grows into a precise inventory of modules as the product is built |
| `CODE_STANDARDS.md` | The engineering owner | Numbered rules the code and the reviewer are held to | Gains a rule whenever a review finds a repeatable mistake |
| `PROCESS.md` | The engineering owner | How to plan, implement, review and check; commands; hard rules | Tuned as the build gets bigger |
| `BRAND.md` | The brand owner | Fonts, colors, look | Rarely |
| `STATUS.md` | The agent keeps it | What is built, how to run it, known gaps | Updated every phase |
| `PLAN.md` / `PLAN_<NAME>.md` | Written by the agent, reviewed by the developer | Design plus phases with checkbox criteria | Ticked as phases finish; a finished plan stays as history |
| Review notes (`HUMAN_REVIEW_*`, `REVIEW_PLAN_*`, `UI_FEEDBACK`) | Human or second model | Findings that drive a refactor or a rule | One per review |

Write the spec and briefs as the customer would: outcomes, rules and what "done" looks like, not implementation. Tell the agent which parts are fixed (the rules, the stack, "tests never call a model") and which are out of scope ("not for now"). Where a brief's notes about earlier work disagree with the code, follow the brief's intent.

### AGENTS.md: a router, not an encyclopedia

`AGENTS.md` at the repo root is what the coding agent loads first. The template is [AGENTS.template.md](../assets/templates/AGENTS.template.md), stored under that name so agents do not load it as live instructions here; save it as `AGENTS.md` in the developer's own repo. Use **progressive disclosure**: keep it short and make it point to the docs, so the always-loaded context stays small and detail is read when needed. In UnderCover it holds:

- the context in two paragraphs (who the user is, what the product is);
- an ordered "read these in full before you plan, build or change anything" list: spec, tech stack, code standards, process, brand, status, current plan;
- the agent's role (you plan, build and check as the process says; explain plans so a human can review them);
- the table of builds: which brief maps to which doc and what it adds, plus "build only what `docs/` asks; do not build ahead";
- hard rules for dangerous actions (never create or delete cloud resources unless asked; never push);
- a folder map, and pointers to on-demand guides (git, course map) the agent reads only when the topic comes up;
- how to use a reference implementation (look only when stuck, and say so).

Rule of thumb: if a fact is needed on every task, it goes in a doc the agent must read; if it is needed on some tasks, link to it from AGENTS.md; do not paste it into AGENTS.md.

## How the docs evolve

Treat the docs as a product of their own. Compare the first `PROCESS.md` and `CODE_STANDARDS.md` with the final ones (after the Copilot build, Week 3 Day 5) to see what a real project added and why.

| Added | When | Why |
| --- | --- | --- |
| Plan starts with a **design** (modules, what each is for, dependencies) checked against the code standards; agent instructions described as goals | Harness build, Week 1 Day 5 | Human review of the first agent build found tangled modules and scripted prompts |
| **Reviewing** section: fresh subagent reviews every change before commit; whole-branch review against `main` at the end | Same | Passing checks did not mean mergeable |
| Code standards grew from 6 general rules to include **Structure** (one way to do each thing, one job per module, write a literal once, use the framework's own way, one job per function, fix before extending) and **The agent** (parts kept apart, instructions as goals) | Same | Each rule answers a finding in the human review |
| How to run (services, seed command, database variable); "checks need no network and never read `.env`"; read-only database MCP; reseed before live runs, cap live runs at five claims | Durable state, Week 2 Day 3 | State moved to a hosted database that live runs change and the agent always needs |
| Sign-in rules for browser checks; a named list of which live runs to do, with their spend reported | Improve, Week 2 Day 5; each build after | Pages need auth; live runs cost money, so the plan says exactly which ones to do |
| **Import checks per deployment target** (the backend, the context layer, the runtime file each import with only their deployment's dependency group, in a throwaway environment) | Secure, Context and Runtime builds | Catches "works locally, package missing in the cloud" before deploying |
| Checks run **in parallel** (`concurrently`, `pytest-xdist`), end-to-end tests on their own; while working run only the touched tests without coverage; full `check` once per phase; commit without rerunning (the hook reruns) | Runtime, Week 3 Day 4 | Keeps the growing suite from being run in full several times per phase (reason inferred from the change); e2e timeouts need an idle machine |
| Per-service **boundary rules** in code standards: which one module owns each URL, route, setting, memory or identity call; which modules may import which | Context, Runtime, Copilot | Standards became specific enough for a reviewer to check mechanically |
| Stand-ins listed for each cloud service the tests replace | Each build | Keeps tests offline as the system grows |

Pattern: **a failure in a build becomes a sentence in the docs.** After the first harness build, the human wrote a review (what was wrong, how it slipped through) and asked the agent to confirm it, fix it, look for the same problem elsewhere in the backend and dashboard, retest, and update PROCESS, CODE_STANDARDS and STATUS so it never repeats. Reuse that request shape after any review.

## The build loop: brief, plan, review, implement

Each build is two steps with the developer's review in between, started from a written brief.

| Step | Developer says | Agent does |
| --- | --- | --- |
| 0. Brief | Copies the brief into `docs/` | Nothing yet |
| 1. Plan | "Please plan the <work> in docs/<NAME>.md" | Reads all docs; writes `docs/PLAN_<NAME>.md`; **writes no code**; stops |
| 2. Review | Reads the plan; optionally has a second model review it; asks for changes | Revises the plan |
| 3. Implement | "Please implement the plan for the <work>" | Builds every phase in order without stopping, ticking criteria, updating STATUS, committing per phase |
| 4. Review | Reads the diff, the report, runs the product, writes review notes | Fixes findings; docs updated |

The first build works straight from `SPEC.md`; later builds from a brief. In the course the pilot's six phases built a backend, a dashboard and a first agent in about 32 minutes of agent time with a top-tier model at extra-high effort (as taught, Oct 2026).

### The per-phase implementation loop (final form of the process)

1. Build the phase with tests. While iterating, run only the tests for the code being changed, without coverage.
2. Verify every success criterion; fix failures. Run the full `check` once and fix failures.
3. Review the phase's changes with a fresh subagent against the code standards; fix what would block a PR. After the fixes run only the affected tests, plus end-to-end tests if the API or UI changed.
4. Tick the criteria in the plan; update `STATUS.md`.
5. Commit. The pre-commit hook reruns the gates; if it fails, fix and commit again (never `--no-verify`).

After the last phase: review the whole branch against `main` the same way, fix, commit, then report results including what the reviews found and changed. Do live runs with the real model last, after reseeding once, and report their cost from the application's own records and the provider's usage page.

### Reviewing the plan with a second model

For a big or risky build, have a different model review the plan before any code. In the Copilot build the course had Codex review the plan, then built it with Claude Code (as taught; Ed calls it a second opinion). The review checked the plan against the brief, the project docs, the existing code and the installed framework code, and returned: keep the six phases, plus seven targeted amendments. Typical value:

- It found a security detail a reader would miss (the cloud SDK's debug logging would write the user's token; the test must exercise the real client path, stubbing only the network send).
- It tightened race conditions and states (bind a confirmation to the turn the user saw; refuse late updates to a stopped turn; one sign-off per turn; run tools one at a time).
- It moved correctness from model text into code (the success-criteria table is written by code, not appended to free text).
- It also **held scope down**: it named mechanisms not to add (generation counters, reconciliation tables) and recorded accepted gaps for STATUS.

Give the reviewer the plan, the brief and the repo, ask it to review the design only (nothing is built yet), and ask for amendments mapped onto phases and a keep-or-replace verdict. The developer then decides which to apply.

## Writing a plan with checkable criteria

A plan the developer can review says what each phase builds and why that approach was chosen. Structure (template: [PLAN](../assets/templates/PLAN.md)):

1. **Opening**: what is built and the rule that each phase leaves the checks green and is committed.
2. **Design** before phases: modules and what each is for, dependencies, data model, API table, rules enforced by the backend, how the agent's instructions are described (by goal), test approach, and "checked against the code standards". Later plans also add "not in this plan".
3. **How criteria are checked**: which server, which seed, which browser tool, which parts use the real model.
4. **Phases**, usually 5 or 6, each building on the last, each with a one-paragraph goal and checkbox criteria.

Good criteria are specific, observable and self-verifiable by the agent. Mix kinds:

```markdown
- [ ] `seed` prints "Seeded 25 items ..." (exact output)
- [ ] `curl -s localhost:8000/api/items` returns 25 items in id order, all `waiting`
- [ ] `curl -s -o /dev/null -w '%{http_code}' localhost:8000/api/items/NOPE` prints `404`
- [ ] Test: paying above the limit without sign-off is refused with 403 and records nothing
- [ ] Test (the loop): with a stub model that calls tool A then B, the run has two steps in order and ends `done`
- [ ] A test reads `/openapi.json`: every operation has an id and a one-line description
- [ ] The test run leaves the real database file untouched (same modified time before and after)
- [ ] `grep -rn evals backend agent dashboard/src` finds nothing
- [ ] Browser (Playwright MCP): the queue page shows 25 rows, 25 Waiting; light and dark mode checked
```

Guidelines:

- Cover refusals, not-found, boundary and idempotency cases, not only the happy path.
- Include architecture guards as checks (a grep that proves the agent never touches the answer key).
- Mark criteria that need the real model "Live", keep them few, put them in the last phase, and cap their size.
- Put exact strings and numbers in criteria; vague criteria ("works well") cannot be ticked honestly.
- Phase wording must match what exists in that phase (a phase cannot assert a tool built later).

## Harness, Harden, Humans: quality gates

The course frames the second meaning of ADLC as three parts. Read it as: **Harness** is what you give the agent (docs, plan, tools, permissions); **Harden** is the automated gates that catch what it gets wrong; **Humans** is what stays with people (previous section).

### The gates in the course repo (as taught, Oct 2026)

| Gate | Python | TypeScript |
| --- | --- | --- |
| Format | ruff format | Prettier |
| Lint | ruff check | ESLint (with plugins for React hooks, accessibility, tests and code smells) |
| Types | pyright | `tsc`, strict mode, never `any` |
| Unit tests | pytest with 80% coverage threshold | vitest with 80% coverage threshold |
| End to end | Playwright, with its own backend and frontend on separate ports and a throwaway database, so it works while the dev server runs | (same) |
| Hook | lefthook pre-commit: formats staged files, then runs the Python or TypeScript checks for the files being committed | (same) |
| One command | `npm run check` runs everything; Playwright runs only there, not in the hook | (same) |

Replace the tools for another stack; keep the shape: format, lint, types, unit tests with a threshold, end-to-end, hook, one command.

### Rules for the gates

- Start from a **hello-world skeleton with every check already green** (one route, one tool, one page, one e2e test). The agent then extends a working harness instead of inventing one.
- Run gates through one command and the hook, so the agent and the developer run the same thing.
- **Never** run `git commit --no-verify`. **Never** loosen a threshold, switch a rule off or exclude a file just to get a green run. If a rule seems wrong, the agent stops and asks. Why: otherwise the agent will optimise for green.
- Add tests with every change. Tests never call a model: use a stub model and stand-ins for every external service (cloud gateway, memory, identity, runtime, tracing, auth provider, the judge). The checks need no network and never read `.env`. Test the real client code path where it matters and stub only the network send.
- Keep code standards short and checkable. Examples from the course: keep it simple; comments only when necessary; avoid overly defensive code and handle exceptions only when necessary (generated code over-defends); one way to call each service with each URL written once; one job per module and function; use the framework's own mechanism before hand-rolling; instructions as goals, and anything that must always happen is done by code.
- For each deployable unit, add an **import check** that imports it with only its deployment dependency group in a throwaway environment ([production-deployment-aws.md](production-deployment-aws.md)).
- Keep the hook fast; it runs on every commit. Move slow checks (end-to-end) to the full `check`.

## Reviews and feedback loops

| Loop | Who | When | Output |
| --- | --- | --- | --- |
| Fresh-subagent review | A subagent with no memory of writing the code, given the standards and the diff, told to act as a strict senior engineer deciding whether to merge | Before every commit; whole branch at the end | Findings fixed before commit; disagreements stated in the report, not skipped |
| Cross-model plan review | A different model | After the plan, before code | Amendments mapped to phases |
| Human code review | The developer | End of each build | A review note listing problems; the agent confirms, finds root cause ("how was this allowed"), fixes, checks the rest of the codebase, retests, updates the docs |
| UI feedback | The developer in the browser | After the build runs | A numbered list of changes; the agent applies and verifies in the browser |

What the first human review found (a useful checklist for generated agent code): over twenty hard-coded URLs and two ways to call the backend; one module importing another's request helper; the harness smeared across modules and mixed with business logic; tools scattered rather than in one module using the framework's context mechanism; instructions written as long step-by-step scripts instead of goals. All of these passed the tests.

What the UI feedback asked for (a checklist for generated dashboards): a header that looks like enterprise software (contrasting background, standard navigation instead of pills, user menu with initials holding settings and sign out); solid colored metric cards with icons; icons where they help, not decorative emojis; delete copy that sounds machine-written or states the obvious; plain labels such as "All versions of the agent's configuration".

## Working practices

### Fresh context per task

Start a new session for each task. The plan, `STATUS.md` and the docs carry state across sessions, not the chat. Keep the plan's checkboxes and the status file current so a fresh agent can pick up where the last one stopped.

### Permission modes

Coding agents ask before acting; modes relax this. The course author runs an autonomous mode ("auto" in the tool taught), relying on the gates, the hook and the written rules to contain mistakes. Choose per risk: relax permissions only as far as your gates and hard rules cover. Keep explicit hard rules for irreversible or costly actions (pushing, creating or deleting cloud resources, spending on live model runs).

### Commits and branches

Work on a branch per build. The agent commits after each checked, reviewed phase (outside a plan: after each checked change). The agent never pushes; the developer does. Frequent commits give undo points and readable history.

### MCP servers for the coding agent

MCP lets the coding agent use tools outside the editor. Two matter for this workflow:

| Server | Use | Notes |
| --- | --- | --- |
| Playwright MCP | The agent opens the app in a browser to check its own success criteria and the UI | Add per agent, for example `claude mcp add playwright -- npx -y @playwright/mcp@latest` (Claude Code), `codex mcp add playwright -- npx -y @playwright/mcp@latest` (Codex), `opencode mcp add` (OpenCode); uses Chrome (as taught, Oct 2026) |
| Database MCP (Supabase in the course) | Lets the agent inspect tables and connections | Add **read-only** and limited to the one project (query parameters `project_ref=<ref>` and `read_only=true` on the server URL), then authenticate in the browser |

Scope: a server added without a scope is **local** (this user, this project only). `--scope user` makes it available in all the user's projects; `-s project` shares it with the team through the repo. Choose local for anything with credentials, project for tool servers the whole team needs. MCP is the Model Context Protocol ([rag-memory-and-mcp.md](rag-memory-and-mcp.md)). Give a coding agent read-only access to data wherever you can.

### Windows and cross-platform

The student's terminal may be PowerShell or a Mac shell. Write package scripts as `uv run ...` commands, tools installed by the package manager, or small `.mjs` files; npm scripts on Windows run in the Command Prompt, so avoid shell-specific syntax. Add `.gitattributes` with `* text=auto eol=lf` so line endings match across systems (otherwise the formatter fails on Windows). Use `uv run`, never bare `python3`.

### Weaker or free models

Free or small coding models work if you shrink the step: one small change at a time, run `check` and commit after each, expect to retry two or three times, and keep the plan as the guide. The same applies to the product's own model: a `MODEL_NAME` environment override lets the product run on a free model ([models-and-cost.md](models-and-cost.md)).

### Never let the coding agent read the answer key

Held-out labeled data and handlers' real decisions are for **evaluation only**. Put the rule in PROCESS ("do not open the eval folder unless asked"), keep it out of the agent's tools and prompts, add the grep guard to the plan's first phase, and let only the seeding and scoring code read it. Otherwise the agent (or the product) may learn the answers and every metric becomes meaningless ([evals-and-observability.md](evals-and-observability.md)).

### Build only what the docs ask

Do not build ahead for later work, even if the agent knows what comes next. A brief becomes part of the build only once it is in `docs/`. Scope creep is a review cost.

## Starting a new project

Set up scaffolding before the first feature, as the course guide does: a folder and git; the Python project with uv (`uv init --bare`, pin the Python version, `uv add`, dev tools with `--dev`, commit `uv.lock`); the Node project with npm (`type=module`, `private`, dev tools with `-D`, pin versions a tool needs with `-E`); scripts in `package.json` (`prepare` installs the hook and the browser, so cloning needs no extra step); the gates; the lefthook hook; `.gitignore` for `.venv/`, `node_modules/`, `.env`; `.gitattributes`. Then write the docs set, then ask for a plan. Template: [PROCESS](../assets/templates/PROCESS.md).

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
| --- | --- | --- |
| Which docs and how much | Minimal (AGENTS.md, SPEC, PROCESS) is quick; full set gives the agent more to hold to | SPEC, TECH_STACK, CODE_STANDARDS, PROCESS, STATUS, plus BRAND when there is a UI; AGENTS.md as a short router listing them |
| Which gates and thresholds | More gates catch more but slow the hook; low thresholds let weak code through | Formatter, linter, types, unit tests at 80% coverage, e2e, pre-commit hook, one `check` command, all green on a skeleton on day one |
| Agent autonomy | Ask-always is safe but slow; auto is fast and relies on the gates | Autonomous within a branch, with hard rules (never push, no cloud resources without asking, no weakening gates) and a developer-reviewed plan |
| How much review | Tests only; plus subagent review; plus second-model plan review; plus human review | Subagent review before every commit, human review at the end of each build, second-model plan review for large or risky builds |
| Which MCP servers and scope | Fewer is safer; more saves steps | Browser automation for UI checks; read-only database access limited to one project; local scope unless the team needs it |
| Coding agent and model | Strong model plans and reviews; cheaper or free model for small steps | Strong model for plans and large builds; small steps with `check` and a commit after each for weaker models |

## Pitfalls and anti-patterns

- Accepting a big generated diff because the tests pass. Review for structure, duplication and idiom too.
- Many hard-coded URLs, two ways to call one service, modules importing each other's helpers, circular imports. Fix by one owner module per concern.
- Writing agent instructions as step-by-step scripts. Give a goal, inputs and what done looks like; do fixed order in code ([harness-engineering.md](harness-engineering.md)).
- Weakening a gate (skip hook, lower coverage, exclude a file, disable a rule) to "get green".
- Tests that call a model or the network: slow, costly and flaky.
- Plans with criteria like "works" or "looks good", or criteria that cannot be run by the agent.
- Stale `STATUS.md` or plan: the next fresh session starts blind and rebuilds what exists.
- A bloated AGENTS.md. Keep it a router.
- Letting the agent see the answer key, or reading it "just once" to debug.
- Running the full check twice per phase, or running live model calls without a cap. Cost and time grow silently.
- Treating the review subagent as final authority or silently ignoring it; the implementer may disagree but must say so.
- Using bash-only scripts or missing `.gitattributes` on a Windows team.
- Building ahead of the docs.
- Asking the agent to fix 300 lines it wrote in one go. Work incrementally so you always know what broke.

## In UnderCover

- Docs: `docs/SPEC.md` (head of claims operations: today's process, the pilot, what the team must see, rules such as sign-off over $1,000, "never see the answer key", "not for now"), `TECH_STACK.md`, `CODE_STANDARDS.md`, `PROCESS.md`, `BRAND.md`, `STATUS.md`, `PLAN.md`; each later day a brief copied to `docs/` and a `PLAN_<NAME>.md`. `AGENTS.md` lists the read-first docs, the build table and hard rules (build only what docs ask, never create AWS resources unprompted).
- Skeleton first: a hello-world backend, agent, dashboard and e2e test with every check wired (ruff, pyright, pytest 80%, ESLint, Prettier, tsc, vitest 80%, Playwright, lefthook, `npm run check`).
- Build 1 (pilot): "Please plan the pilot" produced a six-phase plan with a design section and checkbox criteria (curl outputs, 404 cases, an OpenAPI rules test, a temp-database test, the grep guard, Playwright MCP page checks); "Please implement the plan" built it, committing per phase.
- Build 2 (harness): green tests but unacceptable code. The human review (`HUMAN_REVIEW_HARNESS.md`) led to a refactor plus the Reviewing section and structure rules. Every later build started under those rules.
- Later builds added durable state, a swarm, an improver, security, a context layer, Runtime and the Copilot, each with a brief, a plan and a final live-check phase. The Copilot plan was reviewed by a second model (`REVIEW_PLAN_COPILOT.md`) before implementation, and the UI got a numbered feedback pass (`UI_FEEDBACK.md`).
- The check command grew parallel runs and per-target import checks; the docs grew from six to seventeen code-standards rules. The final `PROCESS.md` is a good model for a mature project.

## Related

- [fde-lifecycle-and-governance.md](fde-lifecycle-and-governance.md): the first meaning of ADLC and accountability for what ships
- [harness-engineering.md](harness-engineering.md): the harness around the product's agent; your coding agent is one too
- [evals-and-observability.md](evals-and-observability.md): why the answer key stays hidden; science before software
- [production-deployment-aws.md](production-deployment-aws.md): import checks per deployment target
- [security-and-guardrails.md](security-and-guardrails.md): secrets, `.env` and permission hygiene
- [undercover-case-study.md](undercover-case-study.md): how the product grew build by build
- Templates: [AGENTS.template.md](../assets/templates/AGENTS.template.md) (saved as `AGENTS.md` in the developer's repo), [PROCESS.md](../assets/templates/PROCESS.md), [PLAN.md](../assets/templates/PLAN.md), [FEATURE_BRIEF.md](../assets/templates/FEATURE_BRIEF.md), [SPEC.md](../assets/templates/SPEC.md)

## Sources

- Course W1D3 "Coding Agents & ADLC": `guides/for_agents/AGENT_GUIDE_WEEK1.md` (including its corrections on MCP scope, the hook and Playwright); W1D5 review note; `guides/for_agents/AGENT_COURSE_GUIDE.md` (two meanings of ADLC)
- `guides/for_agents/AGENT_GUIDE_WEEK3.md` Day 5 (plan reviewed by a second model; correction: "Copilot" means Codex in the video)
- W3 slides 40, 63, 82, 93 ("Building it with Claude Code": copy the brief, ask for a plan, implement, or check out the reference branch)
- `AGENTS.md`, `lefthook.yml`, `package.json`, `setup/INSTRUCTIONS.md` (MCP commands), `docs/PROCESS.md`, `CODE_STANDARDS.md`, `TECH_STACK.md`, `STATUS.md` on main
- `origin/week1day5-end` through `origin/week3day5-end`: `docs/PROCESS.md`, `docs/CODE_STANDARDS.md`, `docs/TECH_STACK.md`, `docs/PLAN.md`, `docs/PLAN_COPILOT.md`, `docs/HUMAN_REVIEW_HARNESS.md`, `docs/REVIEW_PLAN_COPILOT.md`, `docs/UI_FEEDBACK.md`
- `labs/week1day5_product_HARNESS.md`, `labs/week3day5_product_COPILOT.md` (brief structure); `labs/week2day3.ipynb` (read-only database MCP)
- `guides/14_setting_up_a_project.md`, `guides/12_starting_your_project.ipynb`, `guides/07_vibe_coding_and_debugging.ipynb`

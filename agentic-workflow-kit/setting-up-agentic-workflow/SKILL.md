---
name: setting-up-agentic-workflow
description: Sets up an agentic engineering workflow in a project, following the Vibe Coding Cookbook - interviews the user about the project, team, tools and risk level, then renders a tailored setup (CLAUDE.md or AGENTS.md, a docs skeleton, PRP, decision, task and issue templates, and at higher levels role subagents, a /task skill, permissions and a tested guard hook) and verifies it. Use when the user asks to set up, bootstrap or tailor their AI coding workflow or agent setup, or mentions the cookbook or this kit.
---

# Setting up an agentic workflow

You help one person build *their own* working environment for agentic engineering. There is no one size that fits
all: interview first, propose a plan that fits, create only what the user approves, and prove that it works.

The judgment is yours; the mechanics are a script's. `scripts/render.py` copies the templates from
`templates/project/`, keeps or drops level-specific lines, fills the placeholders, generates the guard config,
permissions and `.mcp.json`, and refuses to overwrite anything. Load a `references/` file only when a step names it.

## Ground rules
- **The user decides.** Ask one question at a time and give your recommended answer with each. If the repository can
  answer a question, look instead of asking.
- **Never overwrite.** Files that already exist are the user's; you propose changes, the user approves them.
- **No commits, pushes or installs** without the user's explicit approval. List missing tools and ask.
- **Fail loudly.** If a command fails, stop and show the full output. Never work around a failing check.
- **Evidence, not claims.** Show command output. Nothing is done until the user has checked it.

## Step 1 - Read the project (change nothing)
Summarise in at most 10 lines:
- Is it a git repository? Git is required (the undo button and the basis of locked tests). If not, offer `git init`.
- New or existing codebase; languages, frameworks, package manager; the real source and test folders; existing test
  and lint commands.
- Existing agent files: `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.mcp.json`, `.github/copilot-instructions.md`,
  `.github/instructions/`, `.github/agents/`, `.cursor/`, `.codex/`. CI and deployment files. `.env` files (note that
  they exist; never read them). `.gitignore`.
- Which agent tool is running you, the operating system, and the Python command that works here (`python` on
  Windows, `python3` on macOS and Linux; version 3.9 or later) - the render script and the guard need it.

## Step 2 - Interview
Follow `references/interview.md`: the questions in order, each with a recommended default and the reason. It covers
the level (the autonomy slider, below), the team's tools and operating systems, owned files, commands and MCP servers.

| Level | Creates | Fits |
|---|---|---|
| Starter | Instructions file, `docs/` skeleton (product, architecture, decisions, issues, lessons), `tasks/`, permissions, the test-integrity rule | A prototype, a first week with agents |
| Standard | Starter + skills `grill-me` and `managing-known-issues`, PRP, ADR and spec templates, the guard hook | Most real projects |
| Full | Standard + six role subagents and the `/task` skill with approval gates G1, G2, G3 | Production code, client deliverables, money, security or client data |

Using or setting up for an agent other than Claude Code? Read `references/tool-map.md` first.

## Step 3 - Write the answers and dry-run (gate S1)
1. Write the answers to `tasks/000-setup/answers.json` (schema in the docstring of `scripts/render.py`).
2. Run `<python> <skill-dir>/scripts/render.py --answers tasks/000-setup/answers.json --target . --dry-run`.
3. Show the user the output: the files that will be created, the generated guard config and permissions, and the
   placeholder values (the dry run shortens long values; show those in full from `answers.json`). Add what the script
   does not do (Step 5) and what you will not create, and why.
4. If the script reports existing files, resolve each one with the user first: merge by hand (show the diff), rename,
   or skip. Never delete or rewrite an existing file without approval.
5. Wait for approval; change the answers and dry-run again until the user approves.

## Step 4 - Render
Run the same command without `--dry-run`. It writes the files, merges `.gitignore` (and `settings.local.json` when the
hooks are personal), verifies that no placeholder or marker is left and every JSON file parses, and runs the
installed guard's `check`. Any failure: stop and show it.

## Step 5 - What the script does not do (your part)
- **Other tools' instruction files** (for example `.github/copilot-instructions.md`, `.cursor/rules/`): show the user
  their rules and propose moving the shared ones into a `## Conventions` section at the end of `AGENTS.md` (or
  `CLAUDE.md`). Change or delete the original files only with approval. Tell the user that the guard and the Claude Code permissions protect Claude Code sessions only; other
  tools need their own settings (`references/tool-map.md`).
- **Codex subagents:** at Full level with Codex users, also write one TOML file per role in `.codex/agents/`.
- **Project structure:** add a row to `docs/architecture/PROJECT_STRUCTURE.md` for every existing top-level folder
  or key file the template does not list (for example `.github/`, `.mcp.json`), so the map matches the repository.
- **Local hooks** (`"hooks_location": "local"`): the guard's hooks exist only in *your* `.claude/settings.local.json`,
  so teammates who clone the repository have no guard until they add them. Put the exact hooks block into
  `setup.md` with these instructions for each teammate: copy it into their own `.claude/settings.local.json`, replace
  the Python command with the one that works on their machine, add `allow` rules for the test commands in that form,
  run the guard's unit tests with it, and restart the session. Tell the user to share this with the team.
- **Personal notification hooks**, if the user asked for them: add them to `.claude/settings.local.json` (snippets in
  `references/guardrails.md`), next to the guard's hooks if those are local too, and check that the file still parses.
- **Anything the interview surfaced** that has no template (an extra rule, a known quirk): add it to the instructions
  file, briefly, with the user's approval.
- **Keep `tasks/000-setup/answers.json`** next to `setup.md`. To revise the setup later, change the answers and render
  again into a clean checkout or a branch; the script never overwrites, so it shows exactly what would change.

## Step 6 - Verify (show the output of each)
1. The render script's own final check passed (no placeholders or markers left, JSON valid, guard `check` OK).
2. Guard installed: `<python> -m unittest discover -s .claude/hooks/tests` passes.
3. The instructions file has at most 200 lines.
4. The project's test command, if it exists and there are tests: run it and record the result as the baseline (the
   set of failing test IDs; empty is normal, anything else must be explained). New project without tests yet: record
   "no tests yet".
5. Write `tasks/000-setup/setup.md`: line 1 `Verdict: DONE`, then the level and switches, the answers, what was
   created and merged, what was left out and why, which bootstrap steps are already done (test runner and one test,
   commands filled in, stack recorded) and which are not, the verification output and the test baseline. This is the
   first entry in the project's trail, and later tasks rely on it.

## Step 7 - Hand over
Tell the user, briefly:
1. What was created, one line per item, and what was deliberately left out.
2. **Restart the agent session** so it loads the new instructions, settings, hooks, skills and subagents. In Claude
   Code, `/hooks` shows the guard (if installed); at Full level `/agents` shows the six roles.
3. **Read `CLAUDE.md` (or `AGENTS.md`) line by line.** It shapes everything the agent does from now on. Change
   anything that is not true for this project.
4. **Review and commit the setup yourself**, for example `git add -A` then
   `git commit -m "chore: agentic workflow setup"`. This is the first save point.
5. **Next steps:** put the raw inputs into `docs/product/inputs/`, then use `references/prompts.md` to write the
   product spec, stress-test it (`/grill-me` from Standard up), write the PRP and record the first decisions. Then
   the first task: `/task <what to build>` at Full level, or plan mode and small test-first steps at the others.
6. **The habit that makes it improve:** when the agent makes the same mistake twice, add a rule to the instructions
   file; when a rule is broken anyway, move it into a hook, a linter or a test (`references/principles.md`).

# Project Structure

One row per directory (to depth 2) plus key files, each with a one-line purpose.
The doc-keeper updates it in the task that adds or removes a directory, and removes rows for paths that no longer exist. <!-- if:full -->
Update it in the change that adds or removes a directory, and remove rows for paths that no longer exist. <!-- if:lite -->
Layout rules: [ARCHITECTURE.md](ARCHITECTURE.md) › Principles.

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Claude Code instructions, loaded every session; imports this file | <!-- if:claude-only -->
| `CLAUDE.md` | Claude Code additions, loaded every session; imports `AGENTS.md` and this file | <!-- if:agents-md -->
| `AGENTS.md` | Shared instructions for every coding agent the team uses | <!-- if:agents-md -->
| `.gitignore` | Keeps secrets (`.env`) and personal settings (`.claude/settings.local.json`) out of git |
| `.claude/` | Claude Code setup: `settings.json` (shared permissions), `settings.local.json` (personal, not committed) |
| `.claude/agents/` | The 6 role subagents: planner, tester, developer, debugger, reviewer, doc-keeper | <!-- if:full -->
| `.claude/hooks/` | `guard.py` and `guard.config.json`: role write paths, protected files, locked tests, file sizes | <!-- if:guard --> <!-- if:full -->
| `.claude/hooks/` | `guard.py` and `guard.config.json`: protected files, locked tests, file sizes | <!-- if:guard --> <!-- if:lite -->
| `.claude/hooks/tests/` | Unit tests for `guard.py` | <!-- if:guard -->
| `.claude/rules/` | `tests.md`: test integrity, always loaded |
| `.claude/skills/` | `task` (the workflow, with the spec template), `grill-me`, `managing-known-issues` | <!-- if:full -->
| `.claude/skills/` | `grill-me`, `managing-known-issues` | <!-- if:lite --> <!-- if:skills -->
| {{SOURCE_DIRS}} | Source code |
| {{TEST_DIRS}} | Tests |
| `docs/` | Project documentation: the current state only |
| `docs/product/` | Raw inputs, product spec, PRPs and the PRP template (see its `README.md`) |
| `docs/architecture/` | Architecture index and principles, this file, topic docs |
| `docs/architecture/decisions/` | Architecture decision records (ADRs), their template and index |
| `docs/issues/` | Issue catalog (index), issue template, one file per issue |
| `docs/workflow/` | Lessons learned: the rationale behind the rules |
| `tasks/` | One folder per task, `NNN-slug/`, and `000-setup/` with the setup record and first test baseline (see its `README.md`) |

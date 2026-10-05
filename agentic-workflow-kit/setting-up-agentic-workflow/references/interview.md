# Interview: questions, defaults and reasons

Ask one question at a time, in this order, and give your recommended answer with each. Skip a question when the
repository already answers it (say what you found). Every answer ends up in `tasks/000-setup/answers.json`; the field
it fills is named after **Fills**. The full schema is in the docstring of `scripts/render.py`.

## 1. Name and goal
- **Ask:** "What is the project called? In two or three sentences: what are we building, for whom, and what changes
  for them when it works?"
- **Fills:** `values.PROJECT_NAME`, `values.PROJECT_PURPOSE`.
- **Why:** every later agent reads this first. A vague purpose produces vague work (cookbook Part 0).

## 2. Rules that the code must obey
- **Ask:** "Which business rules must never be broken? Where do numbers, prices, dates and statuses come from?"
- **Default:** "Figures, prices and statuses come from data and deterministic code, never from the language model.
  Nothing is invented; missing data is an error."
- **Fills:** `values.PRODUCT_RULES` (a Markdown bullet list).

## 3. New or existing codebase
- **Ask:** "Is this a new project, or are we adding the workflow to an existing codebase?"
- **Existing:** use the real folders and commands, run the existing tests first, and adapt to the conventions already
  there. Never restructure an existing codebase as part of the setup.

## 4. Tools and machines
- **Ask:** "Does everyone use Claude Code, or do people also use GitHub Copilot, Codex or Cursor? Is everyone on the
  same operating system?"
- **Default:** Claude Code only → `"instructions": "claude"`. Several tools → `"agents"` (shared rules in `AGENTS.md`,
  a thin `CLAUDE.md` that imports it; see `tool-map.md`). Everyone on the same OS → `"hooks_location": "shared"`.
  Mixed Windows and macOS/Linux → `"local"`: the Python command differs (`python` vs `python3`), and a hook whose
  command is missing fails *open* (the action goes through), so each person keeps the hooks in their own
  `.claude/settings.local.json` and checks them on their machine.
- **Fills:** `instructions`, `hooks_location`, `os`, `python_cmd` (the command that works on this machine).

## 5. Level (the autonomy slider)
- **Ask:** "How much is at stake: a prototype, a normal project, or production code for a client?"
- **Default:** Standard. Full when the code handles money, security, personal or client data, or goes to a client.
  Starter for a prototype or a first week with agents.
- **Why:** the lower the stakes, the more you let go; the higher the stakes, the more gates, tests and review.
- **Fills:** `level`.

## 6. What the user owns
- **Ask:** "Which files may the agent change only with your approval?" Show the default list and ask what to add.
- **Default (always protected):** `CLAUDE.md`, `AGENTS.md`, `.claude/**`, `.mcp.json`, other agents' setup files,
  CI workflows, `Dockerfile`, compose files, `infra/**`, Terraform, and `.env` files. On top of that, Claude Code's
  permissions deny *reading* `.env` (which also blocks its edit tools). Neither stops a script that opens the file by
  itself, so secrets stay out of the repository (`.env` in `.gitignore`, `.env.example` for the names).
- **Why:** the ownership split is the critical decision of the whole setup (cookbook Part 1).
- **Fills:** `owned_paths` (only the additions, for example `rates/*.csv`).

## 7. Stack and environment
- **Ask:** confirm what Step 1 found: languages, frameworks, versions, OS, shell and known quirks.
- **Fills:** `values.STACK` (one line), `values.ENVIRONMENT` (a Markdown bullet list).

## 8. Folders and commands
- **Ask:** confirm the source and test folders, and the exact test, lint and run commands.
- **Default for a new project:** propose the conventional layout for the stack. Leave a command empty rather than
  guessing (it renders as "not set up yet"); the first task sets up what is missing.
- **Fills:** `source_dirs`, `test_dirs`, `values.TEST_COMMAND`, `values.LINT_COMMAND`, `values.RUN_COMMAND`,
  `gitignore_extra` (build output and caches for the stack, for example `__pycache__/`, `node_modules/`, `dist/`).

## 9. Guard hook (Standard and Full)
- **Ask:** "Install the guard hook? It enforces the protected files, locks committed tests and caps file size at
  1000 lines. It needs Python 3.9 or later on every machine that runs it."
- **Default:** yes. Explain it in two lines (`guardrails.md`).
- **Fills:** `guard`.

## 10. MCP servers (optional)
- **Ask:** "Do you want current library documentation (Context7) or browser testing (Playwright)?"
- **Default:** Context7 yes. Playwright only for web UIs, and only pinned to a version: look up the current one
  (`npm view @playwright/mcp version`, after asking before any network call). A cloud provider's server only when
  building infrastructure; add it by hand after the render, with approval.
- **Fills:** `mcp.context7`, `mcp.playwright_version` (empty = no Playwright).

## 11. Personal preferences (optional, never in shared files)
- **Ask:** "Do you want a sound when the agent finishes or needs you? Do you dictate your prompts?"
- **Default:** add notification hooks to `.claude/settings.local.json` by hand after the render (snippets in
  `guardrails.md`). Dictation in Claude Code: `/voice` (needs a Claude.ai login; check your firm's policy first).

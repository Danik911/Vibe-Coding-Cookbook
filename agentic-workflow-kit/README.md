# Agentic Workflow Kit

The companion to **The Vibe Coding Cookbook**. The cookbook explains *why*; this kit lets your AI agent set up the
*how* in your own project, tailored to you.

**Read the cookbook first.** You need to understand the workflow before you hand it to an agent: you will approve
every step of the setup, and afterwards you steer the agent that runs it.

## What it is
One Agent Skill, `setting-up-agentic-workflow/`. The same `SKILL.md` format works in Claude Code, GitHub Copilot,
OpenAI Codex and Cursor. When you ask your agent to set up your workflow, it:

1. reads your project (without changing anything);
2. interviews you, one question at a time, with a recommended answer for each;
3. proposes a plan at the level you choose, and waits for your approval;
4. creates the files from the templates with a script, filled in for your project, without overwriting anything;
5. verifies the result and shows you the evidence;
6. hands over: what it created, what to read, and what to do next.

| Level | What you get | Fits |
|---|---|---|
| Starter | `CLAUDE.md` or `AGENTS.md`; a `docs/` skeleton for product, architecture, decisions, issues and lessons; `tasks/`; permissions; the test-integrity rule | A prototype, or your first week with agents |
| Standard | Starter, plus the `grill-me` and `managing-known-issues` skills, PRP, ADR and spec templates, and the guard hook | Most real projects |
| Full | Standard, plus six role subagents (planner, tester, developer, debugger, reviewer, doc-keeper) and the `/task` skill with approval gates | Production code, client deliverables |

## Install it
Copy the whole `setting-up-agentic-workflow/` folder into a place your tool reads skills from. A personal folder is
best: the kit is available in every project and stays out of your repositories.

| Tool | Personal | Project |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| GitHub Copilot | `~/.copilot/skills/` | `.github/skills/` or `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` or `.agents/skills/` |

Then open your project, start a new session and say: *"Set up my agentic workflow."* In Claude Code you can also type
`/setting-up-agentic-workflow`, and in Codex `$setting-up-agentic-workflow`.

**Requirements:** git, and Python 3.9 or later. The render script and the guard hook are plain Python with no
packages to install.

## Read it before you install it
This kit follows its own advice. Skills and hooks from other people run on your machine with your permissions, so
read them before you install them. Everything here is plain Markdown and JSON, plus two Python files:
- `scripts/render.py`, which creates the files;
- `templates/project/dot-claude/hooks/guard.py`, the guard.

Both ship with unit tests. Run them with `python -m unittest discover -s <folder>/tests`, where `<folder>` is
`setting-up-agentic-workflow/scripts` or `setting-up-agentic-workflow/templates/project/dot-claude/hooks` (use
`python3` on macOS and Linux).

## What is inside
```text
setting-up-agentic-workflow/
├── SKILL.md                 the procedure the agent follows
├── scripts/render.py        creates the files from your answers; never overwrites (with tests)
├── references/              loaded only when needed
│   ├── interview.md         questions, recommended defaults, reasons
│   ├── principles.md        the ownership split and the 15 principles
│   ├── guardrails.md        permissions, hooks, the guard, safety, git undo, notifications
│   ├── tool-map.md          where each piece lives in Claude Code, Copilot, Codex, Cursor
│   └── prompts.md           starter prompts for the steps after setup
└── templates/project/       copied into your project and filled in
    ├── CLAUDE.md.tmpl, AGENTS.md.tmpl, CLAUDE-wrapper.md.tmpl
    ├── docs/                product (PRP template), architecture, decisions (ADR template), issues, lessons
    ├── tasks/               one folder per task
    └── dot-claude/          becomes .claude/: agents, skills, rules, settings.json, hooks (guard + tests)
```

Two names inside `templates/project/` change when the files are copied: `dot-claude/` becomes `.claude/`, and
`*.tmpl` files lose the suffix. They are named that way so no agent loads the kit's templates as live instructions.

## Make it yours
There is no one size that fits all. After the setup, change anything that does not fit how you work, and keep
improving it:
- When the agent makes the same mistake twice, add a rule.
- When a rule gets broken anyway, move it into a hook, a linter or a test.

# Guardrails: permissions, hooks, the guard, safety (cookbook Part 5)

**Guidance vs enforcement.** `CLAUDE.md`, skills and agent prompts are advice the model usually follows. Permissions
and hooks are run by Claude Code itself and hold whether or not the model remembers them. If breaking a rule causes
real damage (a leaked secret, a weakened test, rewritten history, a 15,000-line file), enforce it.

## Permissions (`.claude/settings.json`)
- Rules are evaluated **deny, then ask, then allow**; the first match wins. A deny at any settings level beats an
  allow at any other. Levels, highest first: managed (IT), command line, `.claude/settings.local.json` (personal, not
  committed), `.claude/settings.json` (team), `~/.claude/settings.json` (user).
- The kit's defaults: **allow** only checks (tests, linters, the guard's check); **ask** for commits and installs;
  **deny** reading `.env` and secrets, pushing, amending, rebasing, `reset --hard` and `git clean`.
- **Limits to explain to the user:**
  - Deny rules do not stop a script (Python, Node) that opens a file by itself. Keep secrets out of the repository
    (`.env` in `.gitignore`, `.env.example` documents the names). A full sandbox needs macOS, Linux or WSL2.
  - Rules match text: `Bash(git push *)` does not match `git -C . push`. Pair important denies with a hook.
  - `bypassPermissions` mode skips most prompts (explicit `ask` rules still prompt). The guard turns its own "ask"
    into "deny" in that mode.
  - On Windows, write every Bash rule a second time as `PowerShell(...)`.

## Hooks
A hook is a command Claude Code runs at a fixed point: before a tool call (`PreToolUse`), after it (`PostToolUse`),
when the agent or a subagent wants to stop (`Stop`, `SubagentStop`), when it needs attention (`Notification`), and
more. Exit code 0 = carry on; exit code 2 = block, and stderr goes back to the agent as the reason. **Any other exit
code does not block**: a hook that crashes, or whose command is missing on this machine (`python3` on Windows,
`python` on some Macs), lets the action through. So a guard must fail closed (exit 2 on any error), and every machine
must run the hook with a command that exists there. That is why mixed-OS teams keep the hooks in each person's
`.claude/settings.local.json` (`"hooks_location": "local"`).

## The guard (`.claude/hooks/guard.py` + `guard.config.json`)
Stdlib Python, configured per project, tested by `.claude/hooks/tests/`. It enforces:
- **Protected paths** (`protected`): the main agent must ask the user; subagents are refused.
- **Roles** (`roles`): each subagent may write only its own paths (planner → `tasks/*/spec.md`, and so on). Other
  subagents are read-only when `unknown_subagents` is `"read-only"`. `"roles": {}` switches role checks off.
- **Locked tests** (`tests`, `test_writers`): once a test file is committed, only the tester may change it; the
  developer and debugger get a TEST-DISPUTE message instead. The main agent is asked.
- **File size** (`size_limits`): warn at 500 lines, block growth above 1000 (tighter caps for `CLAUDE.md`, task and
  issue files). Shrinking is always allowed.
- **Stop checks:** a subagent that changed a committed test or grew an oversized file (even through the shell) is
  sent back once; the main agent gets a message instead of being blocked.
- **`guard.py check [--since <commit>]`:** the same checks from the command line; the `/task` skill runs it.
When the guard blocks something legitimate, the fix is a config change the user approves, never a workaround through
the shell. Test the guard like code: run its unit tests after every change to it or its config.

## Order vs checks
A hook cannot make the session run a named subagent. Put the **order** of steps (planner → tester → developer → …
→ doc-keeper) in a skill (`/task`), and put the **checks** (tests, size, locked tests) in hooks and commands.

## Third-party skills, hooks and plugins
They are code and instructions written by strangers, and they run with the user's permissions; hooks run outside the
sandbox. Snyk's February 2026 scan of 3,984 public skills found 36.82% with a security flaw and 76 malicious payloads
(https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/). Before installing anything: read every
`SKILL.md`, script, `hooks/hooks.json`, `.mcp.json` and `bin/` file; prefer official marketplaces and known authors;
re-review after updates. Check `.claude/` and `.vscode/` of any cloned repository before opening it with an agent.
(The same applies to this kit: the user should read it before installing it.)

## Git is the undo button
Start from a clean `git status`; commit each step that works; experiment on a branch. `/rewind` (or `Esc` twice)
restores the agent's own edits, but not shell changes and usually not subagent edits. Commands for the user:
`git status`, `git diff`, `git restore <file>`, `git stash`, `git revert <commit>`, and `git reset --hard <commit>`
(destructive; the user's command, denied to the agent).

## Notifications (personal: `.claude/settings.local.json`)
Windows, a sound when the agent finishes (use `Asterisk` for `Notification`, "the agent needs you"):
```json
{ "hooks": { "Stop": [ { "hooks": [ { "type": "command", "command": "powershell",
  "args": ["-NoProfile", "-NonInteractive", "-Command",
           "[System.Media.SystemSounds]::Exclamation.Play(); Start-Sleep -Milliseconds 400"], "timeout": 10 } ] } ] } }
```
macOS: `osascript -e 'display notification "Claude Code needs your attention" with title "Claude Code"'`.
Linux: `notify-send 'Claude Code' 'Claude Code needs your attention'`. Some people prefer no notifications at all:
context switching is expensive. It is a personal choice.

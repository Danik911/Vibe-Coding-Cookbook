# Where each piece lives, per tool

Checked against the vendors' documentation on 2026-09-25. Tools change quickly: when something here does not match
what you see, check the current docs and tell the user.

| Piece | Claude Code | GitHub Copilot | OpenAI Codex | Cursor |
|---|---|---|---|---|
| Instructions | `CLAUDE.md`; `.claude/rules/*.md` (`paths:` to scope) | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` (`applyTo`); also reads `AGENTS.md` (and `CLAUDE.md`; in VS Code with `chat.useClaudeMdFile`) | `AGENTS.md` in each folder from the repo root down, closer files take precedence, 32 KiB default cap; `~/.codex/AGENTS.md` | `.cursor/rules/*.mdc` (`globs`, `alwaysApply`); also reads `AGENTS.md` (the CLI also reads `CLAUDE.md`) |
| Skills (same `SKILL.md` format everywhere) | `.claude/skills/`, `~/.claude/skills/` | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | `.agents/skills/`, `~/.agents/skills/` | `.cursor/skills/`, `.agents/skills/`, `.claude/skills/` |
| Subagents | `.claude/agents/*.md` | `.github/agents/*.agent.md` (VS Code also reads `.claude/agents/`) | TOML files in `.codex/agents/` (`name`, `description`, `developer_instructions`) | `.cursor/agents/*.md` (also reads `.claude/agents/`) |
| Hooks | `.claude/settings.json` → `hooks` | `.github/hooks/*.json` (`preToolUse`, `postToolUse`, `agentStop`, `subagentStop`); VS Code's local agent also reads `.claude/settings.json` hooks | `.codex/hooks.json` or `[hooks]` in `config.toml`; project hooks only when `.codex/` is trusted | `.cursor/hooks.json`; loads Claude Code hooks from `.claude/settings*.json` by default |
| Permissions | `permissions` allow / ask / deny in `.claude/settings.json` | CLI `--allow-tool` / `--deny-tool`; VS Code `chat.tools.edits.autoApprove`, `chat.tools.terminal.autoApprove` | `sandbox_mode` + `approval_policy`; `.codex/rules/*.rules` (experimental) | Run modes, `.cursor/permissions.json`, `.cursor/sandbox.json`; `.cursorignore` does not stop terminal or MCP reads |
| MCP servers | `.mcp.json` | `.vscode/mcp.json` or `.mcp.json` (VS Code); `~/.copilot/mcp-config.json`, `.github/mcp.json` (CLI) | `[mcp_servers.<name>]` in `~/.codex/config.toml` or a trusted `.codex/config.toml` | `.cursor/mcp.json` |
| Plan mode | Shift+Tab | `/plan` or the Plan agent (VS Code); Shift+Tab (CLI) | `/plan` | Shift+Tab (IDE), `/plan` (CLI) |

## What this means for the setup
- **Several tools in one team:** put the shared rules in `AGENTS.md` and make `CLAUDE.md` import it (`@AGENTS.md`).
  Claude Code reads `AGENTS.md` by itself only when there is no `CLAUDE.md`.
- **Skills** are portable: install the created skills where the team's tools look (`.claude/skills/` is read by
  Claude Code, Copilot and Cursor; Codex needs `.agents/skills/`).
- **Subagents:** create them in `.claude/agents/`. For Codex, also write one TOML file per role in `.codex/agents/`
  with the same instructions in `developer_instructions`.
- **The guard hook** is written and tested for Claude Code's hook payloads. Cursor and VS Code may load it from
  `.claude/settings.json`, but their payloads differ: do not rely on it there without testing. In those tools, lean on
  their own permission settings for the protected files.

# Principles (from the Vibe Coding Cookbook, Part 6)

Use these when you explain a choice to the user, and when a question is not covered elsewhere. They are a foundation,
not a standard: the user adapts them to their own style.

## The ownership split
| The user owns (the agent changes it only with approval, or never) | The agent may do (the user steers and checks) |
|---|---|
| CI/CD workflows, deployment and infrastructure files | PRPs, specs and acceptance criteria, drafted from the user's inputs |
| `.env` and every file with credentials (denied outright) | Issue records and lessons learned |
| Git history: commits, merges, pushes | Tests, written by a separate tester |
| New dependencies (every install) | Skills and memory |
| The agent's own setup: `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.mcp.json` | Documentation, kept current |
| Architecture decisions (the agent drafts options, the user decides) | Most of the code |
| Final acceptance of every task | |

## The principles
1. **The user keeps control.** They decide what gets built and approve each step. Nothing passes a gate without them.
2. **Pen and paper first.** Goal, done-when, out of scope, approach, how to check - before any prompt.
3. **Talk to the agent.** Speaking gives more context than typing. Restate what you understood before you start.
4. **Delegate what the agent does better; the user keeps what they do better** (judgment, customer needs, secrets,
   deployment, anything client-facing).
5. **Test it yourself.** Tests only check what someone thought of; the user runs the feature end to end at the end.
6. **Least code.** Reuse ladder: don't build → existing code → built-in → mature package → managed service → new code.
   No abstraction without two real callers. No features nobody asked for.
7. **Tests are the spec, and the coder never edits them.** One role writes failing tests from the spec; another
   writes the code; committed tests are locked. A wrong test becomes a TEST-DISPUTE for the user.
8. **Green means green.** Compare the *set* of failing test IDs with the baseline, never the count.
9. **The agent's knowledge is stale.** Check the installed version and current documentation before relying on a
   library, flag or API; prefer popular, stable libraries the model knows well.
10. **Fail loudly.** No silent fallbacks, default values or fake data that hide a failure. Sample data only when it is
    labelled as sample data.
11. **Small tasks, fresh context.** One task at a time, sized to be reviewed. Clear the context between tasks. After
    two failed corrections, start again with a better prompt.
12. **If it must always happen, enforce it.** Instructions are advice; permissions, hooks, linters and tests are
    enforcement. Move a rule down that list every time the agent breaks it.
13. **Leave a trail.** Every step writes a file. The next agent, or the next colleague, starts from files, not memory.
14. **Always keep a way back.** Start from a clean `git status`, commit each step that works, experiment on branches.
    `/rewind` does not undo subagent or shell edits; git does.
15. **Build while you learn.** Open the code, challenge the agent, ask about every decision. Never ship code you could
    not explain to someone else. Read by risk: money, security, client data and business rules first.

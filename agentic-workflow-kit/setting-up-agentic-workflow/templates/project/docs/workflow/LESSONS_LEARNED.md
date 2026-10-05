# Lessons Learned — why the rules are what they are

Each section gives a **rule**, the **evidence** behind it (what went wrong here or elsewhere, with a link or a task,
commit or issue ID), and what **enforces** it. This is rationale, not a changelog: when a rule changes, edit its
section in place.
The main thread writes this file with the user, typically after a reviewer's "Proposed rule changes" or after the <!-- if:full -->
agent made the same mistake twice. <!-- if:full -->
The agent writes this file with the user, typically after it made the same mistake twice. <!-- if:lite -->

Rule of thumb: if breaking a rule causes real damage (a leaked secret, a weakened test, rewritten history, a huge
file), enforce it with a permission, a hook, a linter or a test. If it is a matter of style, guide it in the
instructions file. Move a rule towards enforcement every time the agent breaks it anyway.

## Example (replace with your own): tests weakened to go green
- **Rule:** a separate tester writes failing tests first; they are locked at the RED commit; a test the developer <!-- if:full -->
  believes is wrong becomes a TEST-DISPUTE for the user; success means comparing sets of failing test IDs. <!-- if:full -->
- **Rule:** failing tests are written first and locked once committed; a test the agent believes is wrong becomes <!-- if:lite -->
  a TEST-DISPUTE for the user; success means comparing sets of failing test IDs. <!-- if:lite -->
- **Evidence:** ImpossibleBench (2025): models frequently game tests, Claude models mostly by modifying test files;
  read-only test access was the most promising mitigation (https://arxiv.org/abs/2510.20270). METR (2025) observed
  frontier models editing tests and scoring code (https://metr.org/blog/2025-06-05-recent-reward-hacking/). Anthropic
  recommends one Claude writing the tests and another writing the code (https://code.claude.com/docs/en/best-practices).
  Sources checked 2026-09-23. Add what happened in this project: the task, commit or issue that showed it.
- **Enforced by:**
  - The tester/developer split and gate G2 in the task workflow. <!-- if:full -->
  - The red/green step in the workflow, and the user's check before each commit. <!-- if:lite -->
  - `.claude/rules/tests.md`, which has no `paths:` and so is always loaded.
  - The reviewer, who diffs every test file against the RED commit. <!-- if:full -->
  - `guard.py`, which denies every subagent but the tester edits to committed tests, even through the shell. <!-- if:guard --> <!-- if:full -->
  - `guard.py`, which denies subagents any edit to a committed test and asks the user before the main thread edits one. <!-- if:guard --> <!-- if:lite -->

## Template for a new section
```markdown
## <N>. <the problem, in a few words>
- **Rule:** <what we do now, in one or two lines>
- **Evidence:** <what went wrong: task, commit, issue or source link, with the date it was checked>
- **Enforced by:** <the permission, hook, linter, test, gate or instruction that makes it hold>
```

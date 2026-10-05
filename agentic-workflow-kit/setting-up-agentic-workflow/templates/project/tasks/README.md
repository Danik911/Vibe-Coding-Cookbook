# Tasks

One folder per task, `tasks/NNN-slug/` (3-digit number, kebab-case slug), with fixed file names written by fixed <!-- if:full -->
roles. The workflow is the `task` skill (`.claude/skills/task/SKILL.md`); the spec template is <!-- if:full -->
`.claude/skills/task/assets/spec-template.md`. There is no status field anywhere: a task's state is which files <!-- if:full -->
exist plus the commit messages (`task-NNN: RED tests approved`, `task-NNN: done`). <!-- if:full -->
One folder per task, `tasks/NNN-slug/` (3-digit number, kebab-case slug), for any change bigger than a quick fix: <!-- if:lite -->
`spec.md` holds the plan the user approved, `evidence/` the screenshots and logs that show it works. <!-- if:lite -->
Copy the spec from [SPEC-TEMPLATE.md](SPEC-TEMPLATE.md). <!-- if:lite --> <!-- if:skills -->
There is no status field: a task's state is which files exist plus the commit messages. <!-- if:lite -->
<!-- if:full -->
| File | Written by | Allowed verdicts (line 1) | <!-- if:full -->
|---|---|---| <!-- if:full -->
| `spec.md` | planner (the main thread for LIGHT) | READY, NEEDS-INPUT | <!-- if:full -->
| `tests.md` | tester, RED mode | READY, BLOCKED | <!-- if:full -->
| `dev.md` | developer | DONE, BLOCKED, TEST-DISPUTE | <!-- if:full -->
| `verify.md` | tester, VERIFY mode | PASS, PARTIAL, FAIL | <!-- if:full -->
| `debug.md` | debugger, one section per round | RESOLVED, PARTIAL, FAILED, TEST-DISPUTE | <!-- if:full -->
| `review.md` | reviewer | APPROVE, CHANGES | <!-- if:full -->
| `docs.md` | doc-keeper | DONE, BLOCKED | <!-- if:full -->
| `evidence/` | tester, debugger | none: screenshots and logs with explicit names | <!-- if:full -->
<!-- if:full -->
Every file a role writes starts with `Verdict: <TOKEN>` on line 1 and stays under 300 lines; the reports after <!-- if:full -->
`spec.md` open with a `## Summary` of at most 10 lines. The role ends its turn with the reply `<VERDICT> <path>`, and <!-- if:full -->
the main thread checks both before the next stage. Anyone can pick a task up cold from its folder. <!-- if:full -->

## Setup record
`tasks/000-setup/setup.md` is written once, when the workflow is set up: what was created, and the first test
baseline (the test command and the set of failing test IDs at that time, or the note that no tests existed yet).
Later changes compare their test results with the last run before them, starting from this baseline.

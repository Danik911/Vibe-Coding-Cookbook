# Process

> Use when: setting up the working agreement between the developer and the coding agent for a project: how to plan, build, check and review. Save the filled file as `docs/PROCESS.md`.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: The checks show that the code works, not that it is fit to merge; the reviews cover the second part. Make the gates mechanical so the agent cannot talk its way past them: one command, hard thresholds, a hook. The course default stack is Python with uv, ruff, pyright and pytest, and TypeScript with ESLint, Prettier, tsc, vitest and Playwright; swap in your own. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

## Setup and the one check command

`{{install command}}` installs everything, including a git pre-commit hook. `{{dev command}}` starts the system.

`{{check command}}` runs every check:

- Python: {{ruff (lint and format), pyright, pytest with 80% coverage}}
- TypeScript: {{ESLint, Prettier, tsc, vitest with 80% coverage}}
- Deployment packages: {{each package imports with only its own dependency group installed}}
- End-to-end: {{Playwright tests}}

The pre-commit hook runs the format, lint, type and unit-test checks on every commit.

The checks need no network and never read `.env`: tests use a stub model and stand-ins for {{the gateway, memory, identity, runtime, tracing, the judge}}.

> Guidance: Coverage at 80% is the course's threshold. Set yours once and never lower it. Package-import checks catch a missing dependency before deployment.

## Planning

When asked to plan, as in "Please plan {{work}}", write the plan to `docs/PLAN_{{NAME}}.md` and write no code.

- Start with the design: the modules, what each is for, and how they depend on each other. Check it against `docs/CODE_STANDARDS.md` before writing the phases. Describe the agent's instructions by their goals, never as a list of steps.
- Split the work into phases, usually 5 or 6, each building on the last.
- Give each phase detailed success criteria that you can verify yourself: tests that pass, commands and their output, API calls and their responses, and pages checked in the browser. Write each as a checkbox.
- Then stop and wait until you are asked to implement the plan.

## Reviewing the plan

For a large plan, have a different model review it before implementation, then decide with the developer.

- The reviewer gets the plan, the brief it implements, the standards and the existing code.
- It writes `docs/REVIEW_PLAN_{{NAME}}.md`: a recommendation (keep, revise, redo), what the plan gets right, and numbered amendments, each with the plan changes and the acceptance tests that prove it.
- Apply the agreed amendments to the plan. Do not widen the scope.

## Implementing

When asked to implement the plan, build every phase in order without stopping. For each phase:

1. Build it, with tests. While you work, run only the tests for the code you are changing, without coverage.
2. Check every success criterion and fix whatever fails. Then run `{{check command}}` and fix whatever fails.
3. Review the phase's changes as below and fix what the review finds. Rerun only the tests the fixes touch, plus the end-to-end tests if they change the UI or the API.
4. Tick off the phase's criteria in the plan and update `docs/STATUS.md`.
5. Commit. The hook reruns the checks; if it fails, fix the problem and commit again.

When the last phase is done, review the whole branch against `main` in the same way, fix what it finds, commit, and report the results, including what the reviews found and what you changed.

## Reviewing code

Every code change gets a review before it is committed.

- The reviewer is a fresh subagent that did not write the code. Give it `docs/CODE_STANDARDS.md` and the diff, and ask it to review as a strict senior engineer deciding whether to merge the PR.
- It checks every standard, in particular: one way to call each service with each URL written once; modules that keep to their own job and do not borrow each other's helpers; the framework's own way over hand-rolled code; functions that do one job; agent instructions written as goals.
- Fix everything it would block the PR for. If you disagree with a finding, say so in your report instead of skipping it quietly.
- When the developer's own review finds a recurring problem, fix it, check whether similar problems exist elsewhere, then update `docs/CODE_STANDARDS.md` and this file so it cannot happen again, and say how.

## Rules

- Add tests with each change. Tests never call a model; use a stub model.
- Outside a plan, commit each change once you have checked and reviewed it, and run `{{check command}}` before you hand work over.
- Never use `git commit --no-verify`.
- Never lower a threshold, turn off a rule or exclude a file to get a green run. If a rule looks wrong, stop and ask.
- Keep `docs/STATUS.md` up to date.
- Never push.
- Do not open `{{answer key path}}` unless asked.
- Live runs with the real model happen once, last, in the plan's final phase, on a fresh seed; report what they spent from the system's records.
- Never create or delete cloud resources unless asked.
- Everything must work on {{Windows and macOS}}: write scripts as {{uv run commands or .mjs files}}.

Example (UnderCover): "Never lower a threshold, turn off a rule or exclude a file to get a green run. If a rule looks wrong, stop and ask."

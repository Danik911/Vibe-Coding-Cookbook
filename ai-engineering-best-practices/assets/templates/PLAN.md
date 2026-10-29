# Plan: {{what is being built}}

> Use when: the coding agent is asked to plan a build ("Please plan {{work}}") from a spec or feature brief. The plan is written for the developer to review before anything is implemented.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Write the plan and no code, then stop and wait to be asked to implement. Split the work into 5 or 6 phases, each building on the last and leaving the check command green. Give every phase success criteria you can verify yourself, each a checkbox: tests that pass, commands and their output, API calls and their responses, pages checked in the browser (for example with the Playwright MCP server). Explain what each phase builds and why, so the developer can review. If the system has no UI, skip the interface phases (4 and 5) or replace them with the phases it needs, such as an integration, a batch job or a handover, and drop "The interface" under Design. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.
This plan builds {{the spec or brief}} in {{5 or 6}} phases. Each phase leaves `{{check command}}` green and is committed before the next one starts.

SIDENOTE: {{Copy any sidenote from the brief here, as the brief asks.}}

When it's done, {{a short picture of the finished system: what the backend holds, what the agent does, what the user sees}}.

## Design

> Guidance: Start with the design: modules, what each is for, and how they depend on each other. Check it against `docs/CODE_STANDARDS.md` before writing the phases. Describe the agent's instructions by their goals, never as a list of steps; anything that must always happen is code.

### Modules

| Module | Job | Uses |
| --- | --- | --- |
| {{backend/...}} | {{one job}} | {{what it depends on}} |

### States and data

| State or table | Meaning | Moves to |
| --- | --- | --- |
| {{waiting}} | {{meaning}} | {{in_progress}} |

### API

| Operation | Route | What it does |
| --- | --- | --- |
| {{get_item}} | {{GET route}} | {{one line}} |

Rules the backend enforces: {{refusals with status codes, for example 409 for a wrong state, 403 over the limit}}.

### The agent

- Tools: {{tools, each named after the operation it calls}}
- Instructions: {{the goal, what it works from, what done looks like}}
- Entry point: {{how a unit of work is started and identified}}

### The interface

{{Pages, what each shows, how it refreshes, brand and tone rules.}}

### How the criteria are checked

{{Where API calls run (a freshly seeded database), where pages are checked, and which criteria are marked "Live" because they use the real model. Tests never call a model; they use a stub.}}

## Phase 1: {{Data and read operations}}

{{Goal: what this phase builds and why it comes first.}}

- [ ] `{{command}}` prints `{{expected output}}`
- [ ] `curl -s localhost:{{port}}/api/{{route}}` returns {{N items, the first being ...}}
- [ ] `curl -s -o /dev/null -w '%{http_code}' localhost:{{port}}/api/{{route}}/{{unknown id}}` prints `404`
- [ ] A test checks {{an API rule, such as every operation has an operation id and a one-line description}}
- [ ] `{{check command}}` passes

Example (UnderCover): `curl -s localhost:8000/api/claims` returns 25 claims in id order, all `waiting`.

## Phase 2: {{Rules and actions}}

{{Goal: the operations that change state and the rules the backend enforces.}}

- [ ] {{A refused action}} returns {{403}} with "{{message}}" and records nothing
- [ ] {{A valid action}} moves {{item}} to {{state}} and returns {{response}}
- [ ] {{An action in the wrong state}} returns 409
- [ ] `{{check command}}` passes

## Phase 3: {{The agent}}

{{Goal: the agent with its tools, working one unit end to end with a stub model in tests.}}

- [ ] Stub-model test: the agent works {{an item}} and records {{steps, decision}}
- [ ] A refused tool call goes back to the model as the backend's message, and the run carries on
- [ ] Live: `{{command to work one item}}` ends with {{expected state}}, with {{a decision, a reason of 2 or 3 sentences}}
- [ ] `{{check command}}` passes

## Phase 4: {{Interface: lists and detail}}

{{Goal: the screens that read the system.}}

- [ ] e2e: the test {{opens the list}} and sees {{N items with their states}}
- [ ] Browser: {{page}} shows {{content}}; light and dark mode both readable
- [ ] `{{check command}}` passes

## Phase 5: {{Interface: the agent at work, and human review}}

{{Goal: live steps while the agent works, and the human step: approve, send back, or reject.}}

- [ ] e2e: without a reload, the page shows each step and the final state
- [ ] e2e: an action over {{limit}} shows "Waiting for sign-off"; the approver signs off and the page shows {{the result, such as the payment and who signed off}}
- [ ] `{{check command}}` passes

## Phase 6: {{Working the queue, docs and the live checks}}

{{Goal: many units at once, the docs brought up to date, the real-model runs done once, last.}}

- [ ] Stub-model test: the run works each waiting item once and skips the others
- [ ] Live: on a fresh database, {{the run works all N items}}; no item is left `waiting` or `in_progress`
- [ ] Live: every action over {{limit}} is held for approval with no {{payment}}; every other is {{paid}} exactly once, for exactly its amount
- [ ] `docs/STATUS.md` says what is built, how to run it and the results of the live run
- [ ] `{{check command}}` passes

## Final check

- [ ] Every criterion above is ticked
- [ ] `{{check command}}` passes, including the end-to-end tests
- [ ] The branch is reviewed against `main` by a fresh reviewer ([PROCESS.md](PROCESS.md)) and what it found is fixed or answered
- [ ] Spend of the live runs is reported from the system's own records

## Not in this plan

- {{What the spec leaves out, and anything deferred to a later plan.}}

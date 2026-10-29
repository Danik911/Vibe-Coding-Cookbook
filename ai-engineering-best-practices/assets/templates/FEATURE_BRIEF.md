# {{Feature or change}}: brief

> Use when: a requester (security, operations, a business team) asks for a change to a system that already exists, and the coding agent will plan and build it. It is written in the requester's voice and says what to build, not how.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Ask the requester for the background and the outcome they need, then write requirements as what the system does, each one checkable, grouped into steps that can be built and checked one at a time. The coding agent turns this into a phased plan ([PLAN.md](PLAN.md)). Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

From {{the requesting team, e.g. our IT team, with information security}}.

SIDENOTE: {{Optional instruction for the plan's author, such as a reference implementation or notebook to follow for consistency, and what wins if it differs from this brief. Remove if not needed.}}

## Where we're heading

{{The direction of travel in a few sentences: what the system will become over the coming weeks, so the change is understood in context.}}

Example (UnderCover): UnderCover is moving onto our AWS account. The app goes first, at a public address handlers can reach, then a Gateway goes in front of the routes the agent uses.

## Background: what we found

- {{A problem, risk or opportunity, with evidence: an incident, a test, a measurement.}}
- {{Another.}}

## Step 1: {{first outcome}}

1. {{Requirement: what is true when it works, in business terms, with the exact names, limits and messages that matter.}}
2. {{Requirement.}}
3. {{What must stay as it is.}}
4. {{What happens when it fails or is not configured.}}

Done when:

- Tests cover {{the cases: no input, wrong input, right input, the edge you worry about}}.
- With the system running, {{a command or a page we can try, and what we expect to see}}.

Example (UnderCover): Every backend route that only the agent calls refuses a request without the right key with a 401, and `GET /api/health` stays open. Done when a `curl` to an agent route without the key gets a 401.

## Step 2: {{second outcome}}

1. {{Requirement.}}
2. {{Requirement.}}

Done when:

- {{Check.}}
- {{Check.}}

## Step N: {{...}}

{{Repeat. Keep each step small enough to build and check on its own, in the order they depend on each other.}}

## Constraints

- Must work with: {{existing systems, data, accounts, platform}}
- Must not: {{touch, delete, call, expose}}
- Security and privacy: {{rules}}
- Cost and timing: {{limits, deadline}}

## Not in scope

- {{Things we are not asking for now, so they are not built ahead of time.}}

## How it will be checked

| What | Who checks | How |
| --- | --- | --- |
| {{Each step's "Done when"}} | {{the coding agent, then the developer}} | {{tests, commands, browser checks}} |
| {{Business outcome}} | {{requester}} | {{the success criteria or evals that must still pass}} |

## Notes on the current build

> Guidance: Say where things are in the code today, so the agent does not have to guess. Say that where a note and the code disagree, the intent of this brief wins.

- {{Module or file: what it does today.}}
- {{Known gaps or things that changed since the last build.}}

# {{Project name}}: the specification

> Use when: writing down what the business needs, in the customer's own voice, before any technical design. It is the brief the coding agent builds from.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Write it as the requester would: "we", plain business language, what the system does and not how the code is organized. Every rule should be checkable. Keep technology choices out (they go in [ARCHITECTURE.md](ARCHITECTURE.md)). Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

From {{requester's role}} at {{organization}}.

## How the work is done today

{{Who does the work, on what, in what steps, at what volume. Name the decisions people make and where they need judgment or more information.}}

Example (UnderCover): Our three claims handlers work through a queue of claims by hand. For each claim, a handler reads the customer's story and documents and checks them against the policy and the policy wording. Then they approve with a payout, decline or refer.

## What we want

We want {{the system or agent}} to {{one-line goal}}. For each {{unit of work}} it should:

- {{read or gather what}}
- {{decide or produce what}}
- {{work out or calculate what}}
- {{explain or record what, for whom}}

Our goal is {{the success metric in one sentence, with the baseline it is compared to}}.

## Users and roles

| Role | What they do | What they may and may not do |
| --- | --- | --- |
| {{role}} | {{tasks}} | {{permissions, limits, e.g. who can approve over the limit}} |

## What the team needs to see

- {{The queue or list, with each item's state}}
- {{Each item in full, with the system's decision and reasons}}
- {{What the system is doing while it works, step by step}}
- {{Its instructions or configuration, and who changed them}}

> Guidance: Describe screens by what the user must learn from them, not by layout.

## Workflow and states

| State | Meaning | Who or what moves it on |
| --- | --- | --- |
| {{waiting}} | {{in the queue, not started}} | {{the agent starts it}} |

## Rules

> Guidance: Include limits that need a human, data the system must never see, amounts and units, and which source wins when two disagree. State what the system must do when the agent tries to break a rule: the system, not the prompt, enforces it.

- A {{payout or action}} over {{limit}} needs {{role}}'s sign-off. The system blocks it until then, even if the agent tries.
- Decisions follow {{authoritative document}}. It comes first; {{second document}} says how to read it.
- The agent must never see {{the answer key for evaluations, at path}}.
- One person's data is used only for that person's work.
- {{Currency, units, spelling, time zones.}}

Example (UnderCover): A payout over $1,000 needs a handler's sign-off. The agent can approve such a claim, but the system must block the payment until then, even if the agent tries to pay.

## Success criteria we agreed

| # | Criterion | Target | Measured how |
| --- | --- | --- | --- |
| 1 | {{criterion}} | {{target}} | {{method on which set, by whom}} |

Example (UnderCover): Over the limit | every payout over the approval limit has a handler's sign-off | counted from the records.

> Guidance: Copy these from the discovery note ([DISCOVERY_NOTE.md](DISCOVERY_NOTE.md)). Plan how each is measured before building ([EVAL_PLAN.md](EVAL_PLAN.md)).

## Our records

{{Where the data lives, what each source holds, who owns it, which parts are labeled examples for checking the work and stay out of the live queue.}}

## Not for now

- {{No real payments / no sign-up / no messages to customers / ...}}
- {{Things people will assume are included but are not.}}

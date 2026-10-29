# ADR-{{number}}: {{short decision title}}

> Use when: a decision shapes the architecture and would be costly to reverse or hard to explain later, such as build or buy, where the agent runs, which systems it reaches, or what goes in code and what goes in a prompt.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: One decision per record, written when it is made. Say what you considered and why you chose one, including the options you rejected. Never edit an accepted ADR: write a new one that supersedes it. Add it to the index in [ARCHITECTURE.md](ARCHITECTURE.md). Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

- **Status:** {{proposed | accepted | superseded by ADR-N | deprecated}}
- **Date:** {{date}}
- **Deciders:** {{names and roles}}
- **Review date:** {{when to revisit, e.g. in 6 months, or when a named trigger happens}}

## Context

{{The problem, the forces and the constraints: requirements, data, systems to reach, risk appetite, budget, team skills, deadlines. Link the discovery note and spec. State facts, not opinions, and say what is unknown.}}

## Decision

We will {{the decision, in one or two sentences, in the active voice}}.

## Options considered

| Option | Pros | Cons | Cost and effort | Verdict |
| --- | --- | --- | --- | --- |
| {{A: the chosen option}} | {{pros}} | {{cons}} | {{cost}} | chosen |
| {{B}} | {{pros}} | {{cons}} | {{cost}} | rejected: {{why}} |
| {{C: do nothing or a no-agent solution}} | {{pros}} | {{cons}} | {{cost}} | rejected: {{why}} |

> Guidance: Always include the simplest alternative, such as plain code or no agent. Judge options against the success criteria and the autonomy and risk constraints, not against taste.

Typical option sets in this domain:

- Build or buy: {{build in-house | buy a product | managed platform feature}}
- Where the agent runs: {{your own infrastructure (Lambda, containers) | a managed runtime such as AgentCore Runtime | the model lab's own harness}}
- Integration: {{direct API calls | MCP tools through a gateway}}
- Logic: {{in code | in the prompt | in a tool}}

## Consequences

- Positive: {{what gets easier}}
- Negative: {{what gets harder, lock-in, new costs, new risks}}
- Follow-up work: {{tasks, owners, dates}}
- Risks to watch, and the signal that means we should revisit: {{signal}}

## Evidence

{{Links to evals, prototypes, cost estimates, vendor docs with the date checked.}}

Example (UnderCover, abridged): "Calculate the payout in code, not in the prompt". Context: with the model doing the sums, decisions or amounts were wrong more often (Week 2 Day 1 lab). Decision: a payout tool backed by the plan rules. Options: the model works it out, or a payout tool in code. Consequence: the payout rules are testable and owned by the app; the agent explains the calculation but does not invent it.

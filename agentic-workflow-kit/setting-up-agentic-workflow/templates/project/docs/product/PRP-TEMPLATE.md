# PRP-NNN — <milestone name>

> **What this is:** the product requirements plan for <milestone>, built from [PRODUCT_SPEC](PRODUCT_SPEC.md) and the
> material in `inputs/`. Decided with the user on YYYY-MM-DD; research facts carry their source and date. Task specs
> are cut from §7. Update this file in place when a decision changes.

## 0. Must-know facts
<3–7 facts no agent may miss: deadline, hard constraints, what must never be faked or invented, systems not yet
verified, data and security limits. One numbered line each.>
1. …

## 1. Goal and success criteria
**Goal:** <the business outcome, not a feature: who does what differently, and what that is worth.>

**Success criteria** (observable; the user can check each one)
- …

## 2. Audience
<Who uses or judges this milestone, and what convinces them.>

## 3. Scope
**In scope**
- …

**Out of scope**
- …

## 4. Domain rules
<The deterministic business rules the code implements: states, calculations, limits, rounding. Each one testable.
Numbers and categories come from data or these rules, never from a language model's guess.>

## 5. Architecture
<The shape of the solution for this milestone, pointing to accepted ADRs in `docs/architecture/decisions/`. Open
decisions go to §9 and become ADRs before the task that needs them.>

## 6. Non-functional requirements
- <performance, availability, security, privacy, accessibility, where it runs>

## 7. Task breakdown
Each task fits one task run: a spec of at most ~20 acceptance criteria and under 150 lines. A task starts only when
the tasks it depends on are done. "Writes to" is the plan; each spec fixes the exact paths.

| # | Task | Depends | Writes to | Brings |
|---|---|---|---|---|
| 001 | <verb-first title> | — | <folders or layers> | <what later tasks can rely on> |

**Cut rule:** <what drops first if time runs out.>

## 8. Validation
<The acceptance checklist for the whole milestone, run by the user at the end: commands, journeys, figures to trace
back to their source.>

## 9. Risks and open questions
| Risk | Mitigation |
|---|---|
| … | … |

**Open questions**
1. …

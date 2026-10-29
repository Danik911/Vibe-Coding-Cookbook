# Discovery note: {{project_name}}

> Use when: starting an AI project with a client or team, before any design, to agree the problem, how success is measured and whether to go ahead. Keep it to one page.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Fill it in a conversation with the sponsor and the people who do the work today. Numbers beat adjectives: a success criterion without a baseline can't be judged, and one without a target can't be met. Remove the `> Use when`, `> Fill` and `> Guidance` lines when the note is done.

**Sponsor:** {{sponsor}} | **Accountable owner:** {{owner}} | **FDE:** {{developer}} | **Date:** {{date}} | **Status:** draft

## 1. Business problem

{{One or two sentences: who has the problem, what it costs today (time, money, errors, lost customers).}}

> Guidance: Describe the problem, not the solution. If the sentence contains "an agent for X", rewrite it as the measurable problem X causes.

Example (UnderCover): Three handlers work the claims queue by hand, reading each story and checking it against the policy wording. We want the same decisions, as accurately, without the manual reading.

## 2. Users and who is affected

| Group | Role in the process | What changes for them |
| --- | --- | --- |
| {{users}} | {{role}} | {{change}} |

## 3. Current process and volumes

- Steps today: {{numbered steps, who does each}}
- Volume: {{items per day or month}}, peak {{peak}}
- Time and cost per item: {{minutes, dollars}}
- Systems touched: {{systems}}

## 4. Baseline

| Measure | How measured | Baseline today | Source |
| --- | --- | --- | --- |
| {{measure}} | {{method}} | {{value or TODO}} | {{who or what measured it}} |

> Guidance: If nobody measures it today, the first task is to measure it on a sample, or to build a labeled set from the experts' own decisions (see [EVAL_PLAN.md](EVAL_PLAN.md)). The experts' accuracy is often the baseline.

## 5. Success criteria and targets

| # | Criterion | Baseline | Target | How measured | Checked by / when |
| --- | --- | --- | --- | --- | --- |
| 1 | {{criterion}} | {{baseline}} | {{target}} | {{method}} | {{owner, date}} |

Example (UnderCover): Straight through | share of claims decided without a referral | the handlers' rate on the same claims | at least 70% on the held-out set.

## 6. Use-case category and the three questions

Category: **{{automation (do things cheaper) | acceleration (do things faster) | differentiation (do different things)}}**. Why: {{one line}}

| Question | Answer |
| --- | --- |
| Does it avoid the three traps: an "agent for X" with no measurable problem, human-like agents where one agent would do, plausible output that is not measured as accurate? | {{answer}} |
| Does it use our own data, our own connections and our own evals? | {{answer}} |
| Is it automation, acceleration or differentiation, and does the target fit that category? | {{answer}} |

> Guidance: Try to solve the problem without an agent first (rules, search, a form). Say what the agent adds that those can't.

## 7. Data and systems available

| Data or system | Owner | Access today | Quality / gaps | Sensitive? |
| --- | --- | --- | --- | --- |
| {{source}} | {{owner}} | {{read, write, none}} | {{notes}} | {{yes/no, kind}} |

Labeled examples of the experts' decisions: {{exist? how many? who labeled them?}}

## 8. Constraints

- Privacy: {{what personal data reaches the model provider; training policy and terms checked?}}
- Regulation and policy: {{rules, audit needs, residency}}
- Security: {{who may see what; systems the agent must not reach}}
- Budget and timeline: {{ceiling, dates}}
- Platform: {{cloud and tools already chosen; default AWS Bedrock AgentCore as taught in the course (Oct 2026)}}

## 9. Autonomy appetite

| Action | Level | Reason |
| --- | --- | --- |
| {{action}} | automatic / approval first / prohibited | {{risk, consequence, reversibility}} |

> Guidance: Judge each action on risk appetite, consequence, verifiability, reversibility, and security, privacy and IP. Reads and calculations are usually automatic; money out, external messages and changes to the agent's own rules need approval; changing its own limits is prohibited.

Example (UnderCover): Pay up to $1,000: automatic. Pay over $1,000: approval first. Sign off its own payout: prohibited.

## 10. Risks

| Risk | Pillar (safety, fairness, security, privacy, transparency, accountability) | Mitigation | Owner |
| --- | --- | --- | --- |
| {{risk}} | {{pillar}} | {{mitigation}} | {{owner}} |

## 11. Go / no-go and next step

- Recommendation: **{{go | no-go | go after TODO is answered}}**, because {{reason}}.
- Next step: {{R&D: build the labeled set and a first prototype}} by {{date}}.
- Sponsor sign-off (agrees scope and budget): {{name, date}}

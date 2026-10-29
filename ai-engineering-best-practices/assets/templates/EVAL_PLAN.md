# Eval plan: {{project_name}}

> Use when: deciding how to measure whether the agent works, before building it, and again before each change to the agent. It turns the success criteria into eval sets, metrics, thresholds and a schedule.
> Fill with the developer; don't invent facts — leave TODO where unknown.

> Guidance: Define the evals first and end by measuring them; that is how success is judged. Agree the figures in the cost-of-mistakes matrix with the business before running any eval. Evals are separate from unit tests: tests never call a model (they use a stub); evals call the real model on labeled examples. Remove the `> Use when`, `> Fill` and `> Guidance` lines when done.

**Owner:** {{owner}} | **Business sign-off on costs and targets:** {{name, date}}

## 1. Success metric

| # | Success criterion (from the spec) | Metric | Baseline | Target | Measured on |
| --- | --- | --- | --- | --- | --- |
| 1 | {{criterion}} | {{metric}} | {{baseline}} | {{target}} | {{set}} |

Example (UnderCover): Accuracy | decision matches the handler's and the payout is within a dollar | the handlers' own accuracy | at or above the objective, on the whole held-out set.

## 2. Eval sets

| Set | Purpose | Size | Labeled by | Agent sees labels? | Improver sees? |
| --- | --- | --- | --- | --- | --- |
| Tiny | cheap smoke check on every change; a handful of units from the evaluation set | {{about 5}} | {{experts}} | never | as the evaluation set |
| Evaluation | find mistakes, learn from them | {{N}} | {{experts}} | never | results and the experts' reasons |
| Held-out | decide keep or roll back a version | {{N}} | {{experts}} | never | scores only |
| Test | one final check before release | {{N}} | {{experts}} | never | never |

> Guidance: Label with the people who do the work today, and record their reasons, not only their decisions. The held-out set's scores choose versions, so it is no longer unseen: keep a separate test set for the final check. Keep the answer key in a path the agent's tools cannot reach and that the coding agent does not open unless asked. Run evals on copies of the units, so they never appear in the live queue, nobody can approve them, and memory is off.

Sources and coverage: {{where examples came from; the hard cases and edge cases included; class balance}}

## 3. Metrics

| Metric | Definition | Why |
| --- | --- | --- |
| Accuracy | decision matches the expert's and the amount is within {{tolerance}} | the headline score |
| Decision accuracy | decision only, from the confusion matrix | separates decision errors from amount errors |
| Precision and recall | for the positive class ({{e.g. approve}}) | precision: of those it approved, how many were right; recall: of those it should have approved, how many it did |
| Cohen's kappa | agreement beyond chance | accuracy flatters a skewed set; in the course lab, approving everything got 56% of decisions right with a kappa of 0 |
| Straight-through rate | share of units decided without referral to a human | the automation benefit; counts items awaiting sign-off as handled |
| Cost of mistakes | sum of the matrix below | what errors cost the business |
| Cost and time per unit | model cost from the provider's usage, wall time | the cost model |
| Judge grade | the explanation graded against the expert's reason | quality of the reasoning |

## 4. Cost-of-mistakes matrix

> Guidance: Mistakes are not equal. Put dollars on each cell with the business. In UnderCover the business tolerates a wrongful payment more than a wrongful decline, which damages loyalty and reputation.

| Expert's decision \ Agent's decision | {{approve}} | {{decline}} | {{refer}} |
| --- | --- | --- | --- |
| {{approve}} | {{cost of a wrong amount: the difference}} | {{wrongful decline: $X}} | {{needless referral: $Y}} |
| {{decline}} | {{wrongful payment: the amount paid}} | 0 | {{needless referral: $Y}} |
| {{refer}} | {{wrongful payment: the amount paid}} | {{wrongful decline: $X}} | 0 |

Example (course lab): wrongful decline $1,500, needless referral $50, wrongful payment = the amount paid. Test whether changing the figures changes which version you would choose.

## 5. Baselines

| Baseline | Why | Score |
| --- | --- | --- |
| The experts today | what "as accurate as our people" means | {{score}} |
| Always the most common decision | tests whether accuracy is just class balance | {{score}} |
| Refer everything | zero wrong decisions, zero straight-through | {{score}} |
| No agent (rules, search) | does the agent add anything? | {{score}} |
| The previous version | is this change an improvement? | {{score}} |

## 6. Noise and the keep-or-roll-back rule

The same version scores differently from run to run. Measure that before judging any change.

| Setting | Value |
| --- | --- |
| Runs per version | {{e.g. 1 on the evaluation set, 2 on the held-out set}} |
| Objectives (floors on the held-out set) | {{accuracy >= X, judge grade >= Y}} |
| Noise (how far a score must improve to count) | {{per metric}} |
| Tolerance (how far a score may worsen when another improves) | {{per metric}} |

Model or prompt comparison: at least 3 runs each. Noise: run one version twice. Improver loop: 2 held-out runs per version, averaged.

Rule: keep a new version only if it meets the objectives, at least one score improves by more than the noise, and none worsens by more than the tolerance; otherwise roll back. Compare the average of the new version's runs with the average of the current version's. Course start values (Oct 2026, Week 2 Day 5 improver; replace them with values from your own measured noise): accuracy floor 0.6; noise: accuracy 0.10, grade 0.15, cost 15%, time 15%; tolerance: accuracy 0.10, grade 0.15, cost 100% (up to double), time 25%. Accuracy and grade are compared as differences; cost and time as fractions of the old value.

> Guidance: Objectives, noise, tolerance, the spending limit, the eval sets and the judge belong to the business. The improver and the agent cannot change them.

## 7. Judge design

- What is judged: {{explanations, summaries, tone}}; direct measurement is used for everything that has a right answer.
- Grounding: the judge sees the expert's reference reason and picks a grade ({{A, B, C, F, mapped to 3, 2, 1, 0}}) instead of writing free text.
- Calibration: run the judge on {{known cases}} and compare with human grades; recheck after changing the judge or its model.
- Independence: the judge is a different model from the agent, outside the improver's reach.
- Human review: {{who samples how many judged items, how often}}

## 8. Retrieval and context evals

| What | Metric | Set |
| --- | --- | --- |
| Search and lookup tools (RAG, context layer) | precision, recall, mean reciprocal rank | {{questions with the right sections or facts}} |
| Agentic retrieval | did the needed facts come back (a found-fact score) | {{units that need outside facts}} |
| Memory | does the agent recall the earlier fact when it helps, and never another person's | {{pairs of related units}} |

## 9. Security evals

Injection set and false-alarm rate: see [THREAT_MODEL.md](THREAT_MODEL.md).

## 10. When to run

| Trigger | Run | Cost cap |
| --- | --- | --- |
| Every change to instructions, tools or code | tiny set | {{$}} |
| Every new agent version | evaluation set once, held-out set {{N}} times | {{$ per round}} |
| Before release | test set, plus the held-out set | {{$}} |
| Model or provider change | all sets | {{$}} |
| In production | {{weekly sample against expert review; drift check}} | {{$}} |

## 11. Reporting

Scoreboard per run: {{the metrics above, cost and time per unit, run time}}, newest first, each run opening to its units beside the experts' decisions with the misses easy to spot. Traces and scores in {{tracing tool, e.g. Langfuse}}.

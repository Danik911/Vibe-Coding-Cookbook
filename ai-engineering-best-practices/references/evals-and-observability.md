# Evals and observability

> When to read this: at discovery (defining success criteria and a baseline), when designing or reviewing an eval plan, when choosing metrics or datasets, when results look too good or too noisy, when a developer asks "how do we know the agent works?", and when setting up tracing. For the judge model and the automated improvement loop, read [self-improvement](self-improvement.md).

## Contents

- Key principles
- Start before building: the success metric and the cost of mistakes
- Three kinds of evals
- Metrics (accuracy, confusion matrix, cost matrix, kappa, baselines, straight-through)
- Datasets: eval, held-out, harder, final test, tiny
- Noise
- Cost and time per item, and the scoreboard
- Running evals safely inside a product
- Observability with Langfuse
- Retrieval evals (brief)
- Evals across the lifecycle, and the success-criteria check in code
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover, Related, Sources

## Key principles

1. **Let evals, not impressions, drive architecture decisions.** A model's output is plausible by construction; only a measurement against known answers tells you whether it is accurate. Every "should we add a tool / an agent / a bigger model" question is answered by an experiment.
2. **Define the success metric and the business cost of mistakes before building.** Different mistakes cost the business different amounts, and the right design depends on that. Agree the figures with the business first, then run evals.
3. **Business cost is not API cost.** Cost of mistakes (a wrongful decline, a wrongful payment) is a business figure. Model cost and time per item are a separate pair of figures. Track both.
4. **Use the cheapest eval that answers the question.** Direct measurement in code first, an LLM judge only for what code cannot check, human review for what neither can.
5. **Score against naive baselines.** Accuracy flatters trivial agents. Run "approve everything" and "refer everything" through your metrics so you know what a number is worth.
6. **Keep the data sets separate and the answers hidden.** The agent being tested (and the coding agent building it) must never see the answers. Keep a held-out set the tuning loop never reads, and a separate final test set for the last check.
7. **Expect noise.** The same agent scores differently run to run, and 25 items cannot show a small gain. Run more than once, average, and set thresholds a change must clear.
8. **Record cost and time next to quality.** A better version that costs ten times more or takes twice as long is a trade-off, not a win. Put every run on one scoreboard.
9. **Evaluate on copies, never in the live data.** An eval run must not change the real queue, trigger payments or consume real approvals.
10. **Trace everything.** Without traces you cannot explain a wrong answer, only count it.
11. **Compute success criteria in code.** The model may fetch figures and phrase an answer, but arithmetic and verdicts come from code.

Template to fill in for a new project: [EVAL_PLAN](../assets/templates/EVAL_PLAN.md).

## Start before building: the success metric and the cost of mistakes

The course's first trap for evals is "plausible against accurate". An agent that writes confident, well-formed decisions looks fine in a demo; a labelled set shows how often it is wrong and what that costs.

Do this at discovery, with the business, before any architecture is chosen:

1. **Pick the unit of work** (a claim, an invoice, a ticket) and what "right" means for it. Decide whether "right" is the decision alone or the decision plus the amount (see strict versus decision accuracy below).
2. **Write the cost of each kind of mistake in money.** Get the numbers from the business and record who agreed them. Typical asymmetry: a wrongful rejection hurts reputation and loyalty more than a wrongful acceptance, so it is costed higher.
3. **Set the baseline**: what the current process achieves (accuracy, time, cost per item). It anchors the business case and the success criteria.
4. **Set success criteria with targets** (for example a straight-through share, an accuracy floor, a control that must always hold). Agree them while the project starts, not when it ends.
5. **Test the sensitivity of your choice to the costs.** Change the most contested cost (the lab's assignment changes the wrongful-decline cost) and see whether the preferred design changes. If it does, the business must settle that number.

UnderCover's cost of mistakes (as taught, set by the business; separate from API cost):

| Handler decided \ Agent decided | approve | decline | refer |
| --- | --- | --- | --- |
| approve | 0, or the payout difference if the amount is wrong | $1,500 (wrongful decline) | $50 (needless referral) |
| decline | the payout (wrongful approval, whether or not it was paid) | 0 | $50 |
| refer | the payout | $1,500 | 0 |

An item the agent never decided counts as a referral, since a person would have to pick it up.

```python
def mistake_cost(answer, expected):
    """What an answer costs the business against the expert's decision."""
    if answer.decision == expected.decision:
        return abs(answer.payout - expected.payout) if answer.decision == "approve" else 0
    if answer.decision == "decline":
        return WRONGFUL_DECLINE          # $1,500 in UnderCover
    if answer.decision == "approve":
        return answer.payout             # money paid, or held for sign-off, that was not owed
    return NEEDLESS_REFERRAL             # $50 in UnderCover
```

## Three kinds of evals

| Kind | Use it for | Strength | Weakness |
| --- | --- | --- | --- |
| Direct measurement (code compares output to a known answer) | Decisions, amounts, labels, retrieval hits, cost, time | Cheap, exact, repeatable | Only checks what has a single right answer |
| LLM as a judge | Whether free text (a rationale, a summary) is well grounded | Scales; handles open-ended output | It also generates plausible tokens; needs a reference answer, a fixed scale and calibration. See [self-improvement](self-improvement.md) |
| Human review | Sampling quality, edge cases, calibrating the judge, trust | The ground truth, in the end | Slow, expensive, inconsistent between people; decision fatigue |

Order of preference: measure directly wherever you can, add a grounded judge for explanations, and use people to sample and to calibrate. In UnderCover the decision and the payout are scored in code, the rationale by a judge, and the handlers' decisions are the labels everything is checked against.

## Metrics

### Strict accuracy versus decision accuracy

- **Accuracy (strict):** the decision matches the expert's and the amount is within a tolerance (UnderCover: within $1).
- **Decision accuracy:** only the decision matches.

Report both. The gap between them is the amount-calculation errors. In Week 2 Day 1 the payout was moved from the model's arithmetic into a Python tool (business logic belongs in code) and the wrong-decision-or-amount count fell, which decision accuracy alone would have hidden.

### Confusion matrix, precision and recall

A confusion matrix has one row per expert decision and one column per agent decision. The diagonal is agreement; every off-diagonal cell is a named kind of mistake (a wrongful decline, a wrongful payment, a needless referral). It counts decisions only, so an approval with the wrong amount still sits on the diagonal; the cost of mistakes catches the amount.

Precision and recall come from the same matrix once you pick a positive class (the lab uses "approve"):

- **Precision:** of what the agent approved, the share the expert approved.
- **Recall:** of what the expert approved, the share the agent approved.

With several classes, weight the off-diagonal cells by their business cost (the table above) and report the total as the **cost of mistakes**. This is the figure the business cares about; accuracy alone treats a $50 referral and a $1,500 decline as equal.

### Cohen's kappa

Kappa measures agreement beyond chance: 1 is perfect agreement, 0 is no better than guessing from each side's decision frequencies. Use it because accuracy depends on the class mix.

```python
def kappa(table):
    """table has columns 'agent' and 'handler'."""
    observed = (table["agent"] == table["handler"]).mean()
    a = table["agent"].value_counts(normalize=True)
    h = table["handler"].value_counts(normalize=True)
    expected = sum(a.get(d, 0) * h.get(d, 0) for d in DECISIONS)
    return (observed - expected) / (1 - expected)
```

### Naive baselines (with the corrected numbers)

Run the dumbest policies through the same scoring first. On UnderCover's 25 harder claims (14 approvals, 6 referrals, as taught):

| Baseline | What it shows |
| --- | --- |
| Approve everything | Gets 56% of decisions right (14 of 25) with a kappa of 0, because every claim lands in the approve column. Accuracy alone would call that decent. |
| Refer everything | Never pays or declines wrongly, but nothing goes straight through (0%), and the 19 referrals that weren't needed cost $50 each: $950 across the 25 claims, an average of $38 a claim (not $50, as the lecture said). The handlers themselves refer 6 of 25, so their rate is 76%. |

Lessons: a metric that a do-nothing policy can score well on needs a partner metric (kappa, straight-through rate); a safe-looking agent that refers everything has no business value; and an agent that does not beat the naive baselines on cost of mistakes is not earning its place. Keep the **human baseline** (what the current process achieves) as well as the naive ones.

### Straight-through rate

**Definition:** the share of items the agent handles without referring them to a person. It counts every item that is not a referral, including approvals that a person must still sign off (an approval over the $1,000 limit is held for sign-off, not referred). An item the agent failed to decide counts as referred.

Always report it beside accuracy and the cost of mistakes: it is the automation gain, accuracy is the quality, and neither is meaningful alone.

### The measures UnderCover records for each run

| Measure | Means |
| --- | --- |
| `decision_accuracy`, `accuracy` | Decision matches; decision matches and amount within tolerance |
| `precision`, `recall`, `kappa` | From the confusion matrix (approve as positive) and chance-corrected agreement |
| `cost_of_mistakes` | Business cost, from the cost matrix |
| `straight_through` | Share not referred |
| `grade` | The judge's average grade on the rationales (see [self-improvement](self-improvement.md)) |
| `llm_cost` / cost per item, `seconds_per_item`, run time | Model cost and active time |
| `found_fact` | Retrieval: did the searches bring back the needed fact (only for items that need one) |

## Datasets: eval, held-out, harder, final test, tiny

| Set | Purpose | Rules |
| --- | --- | --- |
| **Eval (development) set** | What you look at, tune on and learn from. UnderCover: the 25 queue claims. | The tuning loop may read its mistakes and the experts' reasons. |
| **Held-out set** | Checks that an improvement generalises. Same blend as the eval set. UnderCover: 25 more claims. | Keep it out of sight while writing a prompt or a rule; score it afterwards. Only scores, never the items, reach the improver. |
| **Harder sets** | Stress a design choice: long item lists and deductibles (payout tool), facts not in the claim (retrieval). | Add when the easy set stops discriminating; compare runs with the same settings. |
| **Adversarial set** | Security cases such as a prompt injection. | Keep apart from the quality sets so a security case never skews accuracy. See [security](security-and-guardrails.md). |
| **Separate final test set** | The last, independent check before you report or hand over. | Touched once, by nobody who tunes. Needed because the held-out set's scores choose which versions are kept, so it slowly becomes a tuning set. |
| **Tiny subsets** | A handful of items (UnderCover: five per set, one of each kind) for quick checks and free-model allowances. | Good for smoke tests and plumbing; never for conclusions or model rankings. |

Labels come from domain experts and should carry the expert's **reason** and the **reference** it rests on (a policy section), plus tags such as difficulty and what the case tests. The reason is what makes a grounded judge possible later. Treat the sets as part of the product: version them, keep the answers in one owned place, and refresh them when the business changes.

## Noise

Models vary run to run, so a single score is a sample.

- **One item is a big step.** With 25 items, one item is 4 points of accuracy. A small gain cannot show up in one run; a lucky run can fake a large one. Do not rank models from a single 25-item run.
- **Run N times and average.** Ed runs each experiment three times in the Week 2 Day 1 lab (`N_TIMES = 3`; the shipped notebook has 1). Add the confusion matrices of the runs and average the scores.
- **Measure the noise.** Run the same version twice on the same set and see how far each score moves with no change. Then give every candidate the same number of runs (the improver runs each new version twice on the held-out set and compares averages).
- **Set noise thresholds.** A change counts only if a measure improves by more than its noise, and it is allowed to worsen only within a tolerance (details in [self-improvement](self-improvement.md)). The lab's figures were rough: accuracy 0.10, grade 0.15, cost and time 15% (as taught).
- **Compare like with like.** Same model, same reasoning setting, same set. A day's runs at one reasoning level are not comparable with another day's at a different one.
- **Know what moves for other reasons.** A repeated prompt is cheaper the second time because of the provider's prompt cache. Time per item rises when many agents wait for database connections (Ed measured 12.4 s at 3 agents and 21.4 s at 25 in the product, after a lab tolerance measured with no database), so measure time in the production-like setup.
- **Size the set for the gain you care about.** If the set is too small to show that gain above the noise, grow it before you build a tuning loop on top of it.

## Cost and time per item, and the scoreboard

Record, for every item and every run:

- **Model cost** from the provider's own usage report on each reply (Ed's build uses OpenRouter's `usage.cost`), summed per item. Include failed attempts in the run's total. Record the **judge's cost** separately from the agent's.
- **Active time** the agent spends on the item, leaving out any wait for a human sign-off. A run's time is first start to last finish; per-item time is the average.
- **The run's identity**: set, version, model, reasoning level, number of agents at once, the run id. Items worked outside any run have no run.

Put every evaluation on one **scoreboard**: newest first, every measure as a column, each row opening to its items with the expert's answer beside the agent's, misses easy to spot and each item linked to its page. A score without cost and time invites choosing the slowest, dearest model. See [models and cost](models-and-cost.md) for cost per unit of work, and [swarms and scale](swarms-and-scale.md) for why N agents at once shortens the run but not the cost per item (the slowest item sets the clock).

## Running evals safely inside a product

- **Work copies.** An evaluation runs on copies of the labelled items through the same dispatcher and agent as real work. Copies never appear in the real queue, real dispatches never pick them up, nobody can sign them off, an approval held for sign-off counts as finished, and their saved progress is cleared. A run that stopped partway shows as stopped.
- **The answer key lives in the backend.** The scorer reads the key from the system's own records. The agent's service never asks for the decisions, the agent's API client has no function that reads the scoreboard (UnderCover has a test that checks the function names), and reading an evaluation copy returns nothing from the expert's answer.
- **Never let the agent see the answers.** Not in its prompt, tools, memory or retrieval index. For the improver, show only the eval set's mistakes with the experts' reasons, and scores alone from the held-out set.
- **Keep the answer key away from the coding agent too.** By default tell the coding agent not to open the answer files; grant access task by task when a change needs it (UnderCover's brief for seeding the key says so explicitly). A coding agent that reads the answers can tune prompts or code to them, and the eval stops measuring anything.
- **One run at a time**, with a refusal that names what is running, so two runs do not share connections or budgets.
- **Unit tests never call a model.** Tests check the code with a stub model (including that scores match hand-worked figures); evals check the agent's judgement with the real model. Do not mix the two.

## Observability with Langfuse

Langfuse is an open-source platform for tracing and evaluating LLM applications, self-hosted or on Langfuse Cloud, which has a free Hobby plan (as taught, Oct 2026). Four ideas:

| Concept | What it is | UnderCover use |
| --- | --- | --- |
| **Trace** | Every model call with its prompt, reply, tokens and time, and each tool call between them | A callback handler passed in the agent's `config` traces everything. One trace per claim, grouped by a session id per claim. |
| **Dataset** | Test inputs with their expected outputs and metadata | The labelled claims; the item id is the claim id, so re-uploading updates in place; metadata holds the `tiny` flag |
| **Experiment** | A task run over every dataset item, scored by evaluators | `run_experiment` with an item evaluator (right or wrong, mistake cost) and a run evaluator (accuracy, kappa, cost of mistakes, straight-through) |
| **Score** | A named number on a trace or run | Run scores appear as columns when you compare runs side by side |

```python
result = langfuse.run_experiment(
    name="Payout tool",
    data=items,                       # dataset items, or the tiny subset
    task=payout_tool_task,
    evaluators=[score_item],          # one item: right, mistake_cost
    run_evaluators=[score_run],       # the whole run: accuracy, kappa, cost, ...
    max_concurrency=1,
)
```

Practices:

- **Trace first, before you score.** Open the trace of one wrong item (UnderCover's lab traces a Rome burglary claim) and read what the agent saw and did. Many "model errors" are missing context or a missing tool.
- **Tag traces with the run.** In a swarm each item keeps its own thread and session, so tag every item's trace with its dispatch or evaluation id to find a whole run together. One giant trace for a whole run gets unwieldy.
- **Score runs in Langfuse as well as in your own scoreboard**, so engineers can compare experiments where the traces are.
- **Be careful with clean-up.** The lab's optional clean-up cell deletes every trace in the Langfuse project for the keys in use. Use a project made for the course, and note the free plan limits trace deletions per day (as taught: 50).
- **In production**, runtime logs go to the cloud provider's logging (UnderCover: CloudWatch from AgentCore Runtime; see [production deployment](production-deployment-aws.md)). AgentCore's own suite also lists Evaluations (scores agents from their traces) and Optimization (tests suggested prompt changes) as services (as taught, Oct 2026; check their current state before building the same thing).

## Retrieval evals (brief)

When an agent searches a knowledge base, measure retrieval separately from the final answer. Classic retrieval measures are precision, recall and mean reciprocal rank. For agentic RAG, where the agent writes its own queries and searches repeatedly, the practical measure is whether the needed facts came back at all. UnderCover's `found_fact` is true when the agent's searches retrieved every fact the item needs, and is left out for items that need no fact. In Ed's run the claim agent fully got 14 of 25 right without memory and all 25 with it (compare runs with the same model settings). Design details are in [RAG, memory and MCP](rag-memory-and-mcp.md).

## Evals across the lifecycle, and the success-criteria check in code

Evals run through the whole agent development lifecycle (Week 3 Day 1, slides 5 and 6):

| Phase | Evals work | What the FDE does |
| --- | --- | --- |
| Discovery | Evals, baseline, success criteria | Use cases, a baseline and success criteria |
| R&D | Data curation, experiments with evals | Data quality, an evaluation set, a prototype |
| Development | Evals and observability alongside the build | Integrations, guardrails, evals and observability |
| Implementation | Pilot and user acceptance, then evidence against the criteria at handover | Deployment, handover, adoption |
| Maintenance | Monitoring, improvement, human feedback, drift and bias tests | Feedback to the employer on what to productize |

Ed's closing advice to an FDE is to start by defining evals and end by measuring them to decide whether the project succeeded. See [FDE lifecycle and governance](fde-lifecycle-and-governance.md). The Week 3 Day 1 assignment is a one-page discovery note with success criteria, a baseline and a target for each.

**Check the agreed criteria in code.** UnderCover agreed three criteria when the pilot started: a straight-through share (target 70% in Ed's build), accuracy at or above the accuracy objective in Settings (60% to start), and every payout over the approval limit signed off by a person. At handover the Copilot answers "are we meeting the success criteria we agreed?" by running an evaluation of the whole held-out set, waiting for it, and building a table; every figure is computed by code from the evaluation and from the app's records, never by the model.

```python
class Row(NamedTuple):
    criterion: str
    target: str
    figure: str
    met: bool | None          # None when the figure is not known

def verdict(table):
    known = [r.met for r in table if r.met is not None]
    if len(known) < len(table):
        return "Only the third can be judged without the evaluation's figures."
    return {3: "All three are met.", 2: "Two of the three are met.",
            1: "One of the three is met.", 0: "None of the three is met."}[sum(known)]
```

Rules to copy: say "not known" if the evaluation could not start or stopped partway (never guess); count straight-through the same way the scoreboard does (every item not referred, including approvals awaiting sign-off); take targets from settings or constants, not from the model's memory; return the finished table as the tool's answer. See [copilot pattern](copilot-pattern.md).

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
| --- | --- | --- |
| What does "right" mean? | Decision only, or decision plus amount within a tolerance | Report both; tolerance in business units (UnderCover: $1) |
| Cost of each mistake | Business-set money values; asymmetric | Ask the business; record who agreed; run a sensitivity check on the most contested one |
| Which sets? | Eval, held-out, harder, adversarial, final test | Eval + held-out from day one; add a separate final test set before any tuning loop |
| Source of labels | Domain experts with reasons, past decisions, synthetic | Experts, with reason and reference per item |
| Set size | Small is cheap, noisy; large is slow | Enough that one item is a small step; start at about 25 for a pilot but do not read small gains from it |
| Runs per comparison | 1 (smoke) to N | 3 for a comparison, 1 on a tiny subset for plumbing; measure noise before setting thresholds |
| Judge or not | Code only, plus a grounded judge, plus human sampling | Code for decisions and amounts; add a judge only for explanations, calibrated against humans |
| Tracing tool | Langfuse, a cloud provider's, your own | Langfuse; trace every item; tag by run |
| Success criteria | Which measures, which targets, who signs | Three or fewer, agreed at discovery, computed in code at handover |

## Pitfalls and anti-patterns

- Reporting accuracy without kappa, a baseline or the cost of mistakes.
- Counting approvals held for sign-off as referrals when computing straight-through.
- Letting the agent, the retrieval index or the coding agent see the answer key.
- Tuning on the held-out set, then quoting its score as the final result.
- Reading a gain from one run of 25 items, or ranking models from it.
- Comparing runs made with different model or reasoning settings.
- Running evals against the live queue, or letting copies be signed off or paid.
- Ignoring the cost and time of a better score.
- Letting the model write the success-criteria verdict or do its arithmetic.
- Using tiny subsets for conclusions; they exist for quick checks and small allowances.
- Running the Langfuse clean-up in a project you care about.

## In UnderCover

| Build | Evals and observability work |
| --- | --- |
| Week 1 Day 2 | Score decisions against the handlers' on the 25-claim queue; accuracy needs the decision and a payout within $1; a model comparison (Jev got 17 of 25 decisions right in that lab) |
| Week 2 Day 1 | Langfuse tracing, the 25 harder claims, the cost matrix, kappa, baseline versus payout tool: across Ed's three runs, wrong decisions or amounts fell from 36 to 8 of 75, neither version wrongly approved, the baseline wrongly declined four times and the payout-tool version once |
| Week 2 Day 2 | `found_fact` for retrieval; 14 of 25 fully right without memory, all 25 with it |
| Week 2 Day 4 build | Cost and active time recorded per claim and per run; evaluations on copies of the queue or the held-out set; a Scoreboard page; every claim's trace tagged with its run |
| Week 2 Day 5 | A judge, the held-out set, noise measured by running the same version twice, a keep-or-roll-back rule ([self-improvement](self-improvement.md)) |
| Week 3 Day 5 | The success-criteria check in code, run by the Copilot on the held-out set |

Reference code in Ed's final build (`origin/week3day5-end`): `backend/scoring.py` (right, mistake cost, measures), `backend/scoreboard.py` (runs scored from the backend's own records; a version's scores as the average of its evaluations), `agent/copilot/criteria.py` (the check). For the worked history see [UnderCover case study](undercover-case-study.md).

Note on the final check: Ed's success-criteria check evaluates the held-out set, which also chooses improver versions. A new project should add a separate final test set that no loop reads.

## Related

- [Self-improvement](self-improvement.md): the judge, configuration versions, the improver loop
- [RAG, memory and MCP](rag-memory-and-mcp.md): retrieval design and `found_fact`
- [Models and cost](models-and-cost.md): cost per unit of work, model comparison
- [Swarms and scale](swarms-and-scale.md): running evals with many agents
- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): success criteria, baseline, handover
- [Agent architecture](agent-architecture.md): evals decide whether to add an agent, tool or model
- [Template: EVAL_PLAN](../assets/templates/EVAL_PLAN.md)

## Sources

- `guides/for_agents/AGENT_COURSE_GUIDE.md` ("The scores", "The $1,000 limit"); `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Days 1, 2, 4, 5, including corrections); `guides/for_agents/AGENT_GUIDE_WEEK3.md` (Days 1 and 5)
- Notebooks `labs/week2day1.ipynb`, `week2day2.ipynb`, `week2day4.ipynb`, `week2day5.ipynb`; briefs `labs/week2day4_product_SWARM.md`, `labs/week2day5_product_IMPROVE.md`; `data/README.md`
- `origin/week3day5-end:backend/scoring.py`, `backend/scoreboard.py`, `agent/copilot/criteria.py`
- Week 3 slides 5 and 6 (lifecycle), 11 (autonomy), 33 (AgentCore suite), 95 and 96 (handover and criteria)

# Self-improvement: the judge, configuration versions and the improver loop

> When to read this: when a developer wants an agent that grades its own work, an LLM as a judge, versioned prompts and models, an "improver" that proposes changes, rules for keeping or rolling back a change, or asks what recursive self-improvement means in practice. Read [evals and observability](evals-and-observability.md) first: the loop only works on top of a good eval set, a held-out set, noise estimates and a cost of mistakes.

## Contents

- Key principles
- Preconditions
- LLM as a judge
- Configuration versions
- The improver loop
- Keep or roll back
- Recipe ordering and the recursive part
- Overfitting and the final test set
- Permissions and governance
- Cost of rounds and free-model limits
- Recursive self-improvement in context
- Decisions to make with the developer
- Pitfalls and anti-patterns
- In UnderCover, Related, Sources

## Key principles

1. **A judge is also generating plausible tokens, so ground it.** Give it an expert's reference answer, a fixed grade scale and a written rubric. Never ask it for an open-ended opinion of its own.
2. **The judge picks a grade from a fixed scale; it does not write prose.** A grade can be averaged, compared and tracked across versions. Prose cannot.
3. **Calibrate the judge before you trust it.** Test it on cases where you already know the grade you would give, and keep checking.
4. **Keep the agent's configuration (prompt, model, reasoning level) in versions** with a diff, a reason, a proposer, an approver and a time. Every run records the version it used.
5. **The improver proposes; code decides; a human approves.** The improver reads evaluation results and proposes a change. A person approves it before it takes effect. A rule in code, not the improver, keeps or rolls it back.
6. **Decide keep-or-roll-back on the held-out set** using objectives, noise thresholds, tolerances and a budget that the business owns and the improver cannot change.
7. **Try cheap, reversible levers first.** In the recipe, try other models and reasoning levels before adding rules to the prompt, so a round shows what one lever alone does.
8. **The recipe improves itself, under the same approval.** That is the recursive part, and it stays bounded because a human approves each new recipe.
9. **The held-out set is not final.** The improver never reads it, but its scores pick the versions, so a final check needs a separate test set.
10. **Permissions are enforced in the backend.** Only a senior reviewer can start rounds, approve proposals or change settings; the improver cannot touch objectives, limits, eval sets or the judge.
11. **Cap the cost twice**: a per-round spending limit in code, and a credit limit on the model provider's key.

## Preconditions

Do not build an improver until you have:

- a labelled eval set and a separate held-out set, with the experts' reasons (see [evals and observability](evals-and-observability.md));
- measured noise (run the same version twice), so thresholds are not guesses;
- a cost of mistakes the business agreed and cost and time per item recorded;
- human sign-in and roles, so an approval means something.

If the agent has no labelled past decisions, improve it by hand first. The course's commercial point: any agent with a labelled set of past decisions (support replies, invoice checks, contract reviews) can keep improving after the project team leaves, with the business setting the objectives and a person approving each change.

## LLM as a judge

Use a judge for a judgement code cannot check, such as whether an agent's explanation rests on the same grounds as the expert's. Keep code checks for everything with a single right answer (decision, amount).

**Its weakness.** A judge model is also generating plausible tokens, so it can be fluent, confident and wrong. **How to ground it:**

- **Give it a reference answer**, best of all an expert's. UnderCover's judge compares the agent's rationale with the handler's reason and the policy section it rests on.
- **Make it choose from a fixed scale** with a written rubric for each level, not write a paragraph.
- **Ask narrow yes/no questions** beside the grade (same grounds? same section?), which make the grade explainable.
- **Judge one thing**: the explanation. Decision and amount stay with the code.

**The rubric UnderCover used** (grades are numbered by position, F first, so the scale is 0 for F to 3 for A; 1 is a C and 2 is a B, not the other way round as the lecture said):

| Grade | Score | Meaning |
| --- | --- | --- |
| F | 0 | Different grounds from the handler's reason, or contradicts it |
| C | 1 | Partly the same: a ground or the section is missing, or an extra ground is added |
| B | 2 | The same grounds and the same section as the handler's |
| A | 3 | The same grounds and section, and clearly better expressed (clearer for the customer, with figures, shorter, no jargon). A high bar. |

**The judge as taught (Oct 2026; time-sensitive).** The judge is Jev, a decision model from TypeSafe AI (`typesafe/jev-1.13`), reached through OpenRouter's Decisions endpoint, which is in alpha. A single call poses three questions over a shared state (the handler's decision, reason and reference next to the agent's decision, reason and section): a `score` question over the graded levels and two `noul` yes/no questions. Jev returns a probability for each level and the score is weighted by them; it writes no explanation. Any judge that returns a constrained grade works the same way, for example an LLM with a structured-output enum, but then calibrate it and keep it a different model from the agent.

How to use the result:

- The **score** is the grade (0 to 3). The **letter** is whichever level the judge rates most probable, not the score rounded. Show the two yes/no checks as plain yes or no.
- Average the grades over the claims that were graded. A claim the agent never decided gets an F without a judge call. A claim the judge could not grade is shown as not graded and left out of the average. When no claim in a run is graded, the run has no grade, and a version without one is rolled back.
- **Run the judge in the backend that holds the answers**, so the experts' reasons never leave it. Grade claims in parallel when an evaluation finishes, each call with a short timeout (10 s) and no retries, so finishing is fast and one slow call never stops an evaluation. Record the judge's cost with the evaluation, apart from the agent's.
- Write the call once, in one module, because the endpoint is in alpha and its address is read from the environment.

**Calibrate it.** Before trusting the judge, run it on a case where you know the answer. UnderCover's lab uses four rationales for one claim, where the grade you would give is known: the handler's own reason with its reference (roughly a B), a reason from a different claim (an F), a vague one (low) and one written to be clearer than the handler's (an A). The lab does not print target letters, so write yours down first. Re-run to see how much the grade moves: it barely moves but is not fully deterministic. For a project of your own, also compare the judge's grades with a human's on a sample (kappa works here too, see [evals and observability](evals-and-observability.md)) and recalibrate when you change the judge or the rubric.

## Configuration versions

A **configuration** is everything the improver may change about the agent: its instructions, its model and its reasoning level. Keep them together; every change makes a new version. Version 1 is the agent as it stands.

Each version records:

- the full configuration, the version it was based on, and what changed as a **diff** (UnderCover's backend computes it with Python's `difflib`; the page shows additions and removals in color, plus the model and reasoning level before and after);
- the **reason**, who proposed it (the round, for an improver's proposal), who approved it and when;
- its status: current, kept, rolled back or under test, and its **held-out scores**.

Rules that make the history trustworthy:

- Versions are **owned by the backend**, seeded from files; the agent's service fetches the version a run uses and holds no scores.
- A dispatch uses the current version; an evaluation records which version it ran; a version's scores are the mean of the whole-set evaluations run on it during rounds.
- **Models allowed** (with their reasoning levels and prices) live in a data file the page can list but not edit, and a proposal outside it never reaches a human; it goes straight back to the improver.
- Seeding rebuilds version 1; a reset must clear versions and scores together.

## The improver loop

The improver is an agent whose instructions are a recipe. One round:

```text
1. read_results      current version, scores on both sets, the claims it got wrong and the
                     right ones it explained least well (with the expert's reason and the
                     judge's grade), earlier rounds, objectives, noise, tolerance, rule,
                     budget left, models allowed.  Held-out set: scores only.
2. propose_change    new instructions + model + reasoning level + reason   -> a HUMAN approves
3. run_evaluation    1 run on the eval set, 2 on the held-out set -> CODE keeps or rolls back
4. propose_recipe    improved recipe + reason                              -> a HUMAN approves
```

Design points (as built in the course):

- **Four tools, named in the recipe**, because the recipe refers to them by name.
- **Human in the loop on the two propose tools.** LangChain's `HumanInTheLoopMiddleware` pauses the run when the improver calls `propose_change` or `propose_recipe`, and resumes with approve or reject. A rejection carries the reviewer's reason back so the improver can propose again. The pause needs a checkpointer (see [durable state and HITL](durable-state-and-hitl.md)): in the product a round waiting for approval survives a restart.
- **The improver does not see the held-out items.** From that set it gets scores only; the claims stay out of sight so they show whether a change works on claims nobody tuned for.
- **Changes stay general.** Instruct the improver that a change never names a claim, a customer or a claim's figures.
- **Turn parallel tool calls off** so one reply never holds two proposals.
- **Cap the improver's own model calls per round** and record their cost with the round.
- **Only one round open at a time**, and a round works to the settings as they stood when it started. Dispatches and evaluations can run while a round waits for a handler.
- **If the current version lacks its baseline runs**, the round first runs one evaluation-set run and two held-out runs, then improves.
- **Make the stages visible**: first evaluations, the improver working, a change awaiting approval, evaluations, the verdict, a recipe awaiting approval, finished or stopped. A round stopped before its verdict leaves the current version as it was.
- Write the improver's instructions as goals around the recipe: what the agent it improves works from, what holds whatever it does, what "done" looks like.

```python
approval = HumanInTheLoopMiddleware(interrupt_on={
    "propose_change": {"allowed_decisions": ["approve", "reject"]},
    "propose_recipe": {"allowed_decisions": ["approve", "reject"]},
})
improver = create_agent(model=improver_model, tools=[read_results, propose_change, run_evaluation, propose_recipe],
                        system_prompt=system_prompt, middleware=[approval], checkpointer=saver)
# resume: Command(resume={"decisions": [{"type": "approve"}]})
#     or: Command(resume={"decisions": [{"type": "reject", "message": "why"}]})
```

## Keep or roll back

The business owns these settings and they live in code or the backend's settings, where the improver cannot change them (values as taught in the lab and the build, Oct 2026; the lab calls them rough):

| Setting | Meaning | UnderCover start values |
| --- | --- | --- |
| Objectives | Floors on held-out accuracy and on the judge's grade | accuracy 0.6, grade 1.0 |
| Noise | How far a measure must improve to count | accuracy 0.10, grade 0.15, cost 15%, time 15% |
| Tolerance | How far a measure may worsen while another improves | accuracy 0.10, grade 0.15, cost 100% (up to double), time 25% |
| Spending limit | What a round may spend on evaluations, judge and improver | $0.50 |
| Models allowed | Models and reasoning levels the agent may use | a data file |
| Agents at once | Concurrency in the improver's evaluations | 25 |

**The rule:** keep a new version only if it meets the objectives on the held-out set, improves at least one measure by more than that measure's noise, and worsens none by more than its tolerance. Otherwise roll back. Accuracy and grade are compared as differences; cost and time per claim as fractions of the old value (0.15 is 15%, 1.0 is double). Compare the **average of the new version's two held-out runs** with the current version's scores.

```python
def keep_or_roll_back(new, old, s):
    if new is None or new.grade is None:
        return False, "it has no grade"
    missed = [m for m, floor in s.objectives.items() if value(new, m) < floor]
    if missed:
        return False, f"it missed the objectives on {', '.join(missed)}"
    better, worse = compare(new, old, s)       # beyond noise / beyond tolerance
    if worse:
        return False, f"{', '.join(worse)} got worse"
    if not better:
        return False, "no score improved by more than the noise"
    return True, f"{', '.join(better)} improved"
```

Notes:

- A change can be rolled back even though a score moved the right way: **higher accuracy or grade is better, but it must clear the noise threshold.** (When Ed's first change was rolled back its grade had risen by less than the noise threshold; the lecture said a higher grade was worse, which is wrong.)
- Other rollbacks are logged with a reason: its evaluations were stopped, the round could not afford to evaluate it, the improver did not evaluate it, the round stopped before its verdict.
- A new version may cost up to double at first (a new prompt is not yet in the provider's prompt cache), hence the generous cost tolerance.
- A run of 25 claims is small, so a lucky run can still pass. Treat thresholds as a filter, not a proof, and re-measure the noise when the set or the model changes.

## Recipe ordering and the recursive part

**The lab's first recipe** is simple: read results; for each mistake add a rule to the instructions; propose the change; run the evaluation; then improve the recipe (always the last step).

**Ed's final build changed the order** (as taught): after reading results, look at the model and reasoning level of the current version and of every version earlier rounds tried. If a model allowed, at a reasoning level allowed for it, has not been tried, try it this round, starting with a higher reasoning level on the current model, and keep the instructions unchanged. Only when none is left, add rules for the mistakes. The improver's instructions say an untried allowed model or level is always worth trying, and that the round may end without a proposal only when none is left and nothing else looks worth proposing. Reasons:

- Model and reasoning changes are cheap, reversible and isolated: the round shows what that one lever does.
- A prompt grows with every rule, costs more per call forever, and invites rules that fix one claim and nothing else (overfitting).
- Per-claim rules are the most likely to overfit, so they come last.

(Ed's final build seeds the claim agent on GPT-6 Luna at no reasoning, as taught, so there is room to try higher levels first; the lab and the brief start at low. The improver uses a stronger model than the agent it improves: GPT-6.1 Sol at medium in the build, Luna at medium in the lab.)

**The recursive part.** The recipe's last step makes the improver improve its own recipe. A new recipe is a versioned record like a configuration, shown as a diff and approved by a human. The next round starts from the newest approved recipe, and each round records the recipe version it followed. This is recursive self-improvement on a small scale: the improver gets better from round to round, bounded by business-owned objectives and a human approving each change. Keep the recipe as data the improver follows (a list of steps), not code.

## Overfitting and the final test set

- **Eval set:** the improver reads its mistakes. A rule written for one claim fixes that claim, so the score rises whether or not the rule helps elsewhere. That is overfitting, and why the eval-set score is not the decision.
- **Held-out set:** the improver never reads it, and code decides from its scores alone. If the improver could read it, it could write rules for it and the scores would stop meaning anything.
- **But selection leaks.** Every round picks a winner by its held-out scores, so after several rounds the held-out set has shaped which version you hold. The guide's correction: the improver never sees the held-out claims, but their scores pick the versions, so **a final check needs a separate test set**, touched once, by nobody who tunes.
- Ed's handover check runs on the held-out set; a new project should reserve a third set for the final result.
- Refresh the sets with real cases over time, and do not let anyone paste a held-out item into a prompt, a rule or a test.

## Permissions and governance

- **Autonomy by action.** The course's tier table (Week 3 Day 1, slide 11) is in [FDE lifecycle and governance](fde-lifecycle-and-governance.md#autonomy-is-a-risk-based-decision-for-each-action); each level is a risk decision on appetite, consequence, verifiability, reversibility and security, privacy and IP. For the improver: reading results and evaluating a proposal run automatically; applying a new prompt, rule, model or recipe needs a person's approval; changing the approval limit, reading the held-out answers or editing the evaluation sets is prohibited.
- **What the improver cannot change:** the objectives, the noise and tolerance thresholds, the spending limit, the list of allowed models, the approval limit, the eval sets and the judge. Nothing it proposes takes effect until a person approves it.
- **Only a senior reviewer** can start or stop a round, approve or reject proposals and change settings (UnderCover: only Dana, who can also sign off over the limit, from `week2day5-end`). Others see a page that says what they cannot do and why, and **the backend refuses it too**: checking in the UI alone is not a control.
- **Sign-in.** Handlers sign in through Supabase Auth with no sign-up (turn sign-ups off); the dashboard sends the session token with each action; the backend verifies it against the project's public keys (JWKS, audience `authenticated`) and finds the handler by email. No Supabase secret is needed because the project signs with asymmetric keys.
- **Audit.** Each round logs the recipe version it followed, the settings in force, the version it tried and why, the held-out scores before and after, the verdict with its reason, who approved or rejected each item and when, and what the round cost. Each settings change logs who made it and when.

## Cost of rounds and free-model limits

- A round is one evaluation-set run plus two held-out runs of the new version (and the first evaluations if the current version has none), plus the judge and the improver's own calls. The lab costs about 10 cents; the spending limit per round starts at $0.50.
- **Estimate before you spend.** Refuse an evaluation likely to cost more than what is left of the round's limit (claims times the highest cost per claim seen for that model; for a model with no runs, scale from the current model's by the larger of the input and output price ratios). Once the limit is spent, start no new claim; a cut-short evaluation shows as stopped and its version is rolled back.
- **A hard backstop outside your code**: put a credit limit on the model provider's key (the lab suggests about $5, optionally resetting daily, weekly or monthly). A bug in the code that enforces the budget could still spend money; the provider's limit holds whatever the code does.
- **Free models (as taught, Oct 2026):** free models allow about 50 requests a day and 20 a minute; a round needs far more than that. With `MODEL_NAME` set the improver and the agent use that model, it is the only model allowed and the judge is skipped (claims show as not graded). Free-route students build and test the improvement features but do not run rounds; the free lab uses one claim from each set. A run of 25 claims is not a ranking of models. See [models and cost](models-and-cost.md).

## Recursive self-improvement in context

Recursive self-improvement (RSI) means a system that improves the process that improves it. The course's version is deliberately small: the improver edits the claim agent's configuration, and its recipe edits itself, inside business limits with a human approving each step. Karpathy's autoresearch is a recent example of such a loop, though not the first; check its current details before citing it. AgentCore's suite also lists an Optimization service that tests suggested prompt changes (as taught, Oct 2026); check what it offers before building your own. In the lifecycle this is the maintenance phase: monitoring, improvement and human feedback ([FDE lifecycle and governance](fde-lifecycle-and-governance.md)).

## Decisions to make with the developer

| Decision | Options and trade-offs | Sensible default |
| --- | --- | --- |
| Do we need an improver now? | Manual improvement versus an automated loop | Manual until there is a labelled eval set, a held-out set, measured noise and sign-in; then automate |
| Levers the improver may change | Prompt, model, reasoning level, tools, retrieval, concise versus full wording | The course's three (prompt, model, reasoning level); add one lever at a time |
| Recipe order | Rules first or model and reasoning first | Model and reasoning first; rules last and general |
| Judge | None, LLM with a rubric, a decision model | A grounded judge with the expert's reason, a fixed scale, yes/no checks, and a calibration step |
| Thresholds | Start from the lab's or derive from your data | Measure noise with two runs of one version, then set noise just above it and tolerance by what the business can accept |
| Who approves | Anyone, any senior, a named role | One senior role, enforced in the backend, with an audit trail |
| Budget | Per round, per day, provider limit | A per-round limit in code plus a credit limit on the key |
| Final check | Reuse the held-out set or reserve another | Reserve a separate final test set |

## Pitfalls and anti-patterns

- An ungrounded judge that grades its own taste, or one that is the same model as the agent.
- Letting the judge write prose or rounding its score to name a letter.
- Trusting the judge without a calibration check on known cases.
- Letting the improver see the held-out items, edit objectives, noise, limits, models or the eval sets, or approve its own change.
- Approving by clicking through: read each diff and its reason.
- Adding per-claim rules to the prompt before trying model and reasoning changes.
- Keeping a change because one score rose by less than the noise.
- Treating the held-out score as the final result after many rounds.
- Enforcing roles only in the UI, or leaving sign-ups on.
- No spending cap outside the code.
- Running rounds on free models and expecting results.

## In UnderCover

- **Week 2 Day 5 lab (`week2day5`)**: calibrate the judge on CLM-1001 with four rationales, run version 1 on both sets, measure noise by running it twice on the held-out set, then run the improver with the human in the loop for two rounds; the second round starts from the improved recipe.
- **IMPROVE build:** sign-in, versioned configuration with a Configuration page (diffs and held-out scores), a Settings page, the judge in evaluations, and an Improvement page where the senior handler starts rounds and approves each change and recipe. In Ed's version 1 the claim agent reached 80% decision accuracy on the evaluation set, and each miss was an approval of a claim the handlers had declined or referred; it also ended its turn without recording a decision about once in fourteen claims, which gave the improver something to fix first.
- **Reference code in Ed's final build (`origin/week3day5-end`):** `backend/judge.py` (the judge call), `backend/verdict.py` (keep or roll back), `backend/configuration.py` (versions, settings, models allowed), `backend/improvement.py` (rounds, proposals, spending), `agent/improver.py` (the improver, human approval, call cap), `backend/instructions/improver.md` and `recipe.md`, and `data/improvement.json` (start values).
- Case-study timeline: [UnderCover case study](undercover-case-study.md).

## Related

- [Evals and observability](evals-and-observability.md): sets, metrics, noise, scoreboard, tracing
- [Durable state and HITL](durable-state-and-hitl.md): checkpointers and interrupts behind the approval pause
- [Harness engineering](harness-engineering.md): middleware used by the improver
- [Models and cost](models-and-cost.md): model and reasoning trade-offs the improver explores
- [Security and guardrails](security-and-guardrails.md): permissions and what an agent must not do
- [FDE lifecycle and governance](fde-lifecycle-and-governance.md): autonomy levels, change management
- Template: [EVAL_PLAN](../assets/templates/EVAL_PLAN.md)

## Sources

- `guides/for_agents/AGENT_GUIDE_WEEK2.md` (Day 5 and its corrections), `AGENT_COURSE_GUIDE.md`, `AGENT_GUIDE_FREE.md`
- `labs/week2day5.ipynb`, `labs/week2day5_product_IMPROVE.md`, `labs/week2day4_product_SWARM.md`
- `origin/week3day5-end:backend/judge.py`, `backend/verdict.py`, `backend/scoring.py`, `backend/configuration.py`, `backend/improvement.py`, `backend/instructions/improver.md`, `backend/instructions/recipe.md`, `agent/improver.py`, `data/improvement.json`
- Week 3 slides 11 (autonomy) and 33 (AgentCore suite)

# Starter prompts for the steps after setup

Give these to the user at hand-over. Replace the parts in angle brackets.

**1. Turn raw inputs into a product spec**
```text
Read everything in docs/product/inputs/ (requirements, user stories, call transcripts, notes). Write
docs/product/PRODUCT_SPEC.md: vision, the business problem, users, core flows, rules the software must obey, what is
out of scope, and open questions. Keep every number and name exactly as the sources state it; mark anything you
inferred as an assumption. Do not invent figures. Ask me about contradictions instead of choosing.
```

**2. Stress-test it**
```text
/grill-me on docs/product/PRODUCT_SPEC.md. One question at a time, with your recommended answer. If the codebase or
the docs can answer a question, look it up instead of asking me.
```

**3. Write the PRP**
```text
Using docs/product/PRODUCT_SPEC.md and my answers, write docs/product/PRP-001-<slug>.md from docs/product/PRP-TEMPLATE.md.
Each task in the breakdown must be small enough for one spec of at most ~20 acceptance criteria.
```

**4. Research before deciding**
```text
Before we decide how to build <feature>, research existing solutions: mature packages, managed services and
open-source repositories. For each: current version, licence, last release, fit with our installed versions, source
URL. Recommend the option with the least new code. Do not write code yet.
```

**5. Record a decision**
```text
We chose <option>. Write docs/architecture/decisions/NNNN-<slug>.md from 0000-template.md (context, options least
code first with evidence, decision, consequences, revisit when), add it to the index, and update ARCHITECTURE.md so
it describes the new current state.
```

**6. Start a session on existing work**
```text
First run the tests. Then review the changes made today (git log and git diff) and summarise where we are.
```

**7. Understand code you did not write**
```text
Read the source and then plan a linear walkthrough of the code that explains how it all works in detail
```

**8. Record an issue**
```text
Search docs/issues/ISSUE-CATALOG.md for this problem first. If it is new, create the next ISSUE-NNN file from
ISSUE-TEMPLATE.md: symptoms, exact reproduction, root cause (or "unknown"), fix, verification, a dated log line.
Update the catalog index.
```

**9. Bring the docs back to the current state**
```text
Compare the docs with the code changed since <commit>. Update PROJECT_STRUCTURE.md, ARCHITECTURE.md and the READMEs so
they describe the system as it is now. Edit in place; no dated "update" sections. List what you changed.
```

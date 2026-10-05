# Test integrity (always loaded)

Tests are the executable specification. A failing test means the code is wrong until the user rules otherwise.

- The **tester** writes tests from the approved spec before any implementation (RED). They are committed as <!-- if:full -->
  `task-NNN: RED tests approved` and locked from then on. <!-- if:full -->
- Tests are written from the approved plan or spec before any implementation, and must fail first (RED). Once <!-- if:lite -->
  committed they are locked: a committed test changes only with the user's approval. <!-- if:lite -->
- `guard.py` denies every subagent but the tester edits to committed tests, and asks the user before the main thread edits one. <!-- if:guard --> <!-- if:full -->
- `guard.py` denies subagents any edit to a committed test, and asks the user before the main thread edits one. <!-- if:guard --> <!-- if:lite -->
- Never weaken a test to get green: no deleting, skipping (`skip`, `xfail`, `.only`, `.todo`), loosening assertions
  or tolerances, catching broad exceptions, mocking the unit under test, or editing runner config or snapshots.
  Do not route around the lock through the shell (`sed`, `rm`, `git checkout`, a script): the reviewer diffs every <!-- if:full -->
  test file against the RED commit. <!-- if:full -->
  Do not route around the lock through the shell (`sed`, `rm`, `git checkout`, a script): `git diff` shows every <!-- if:lite -->
  change to a committed test, and the user checks the diff before each commit. <!-- if:lite -->
- "Do not hard-code values or create solutions that only work for specific test inputs. Tests are there to verify
  correctness, not to define the solution." No test-aware production code.
- "If any of the tests are incorrect, inform me rather than working around them." Report
  `TEST-DISPUTE: <test> | <AC-n> | evidence | proposed change`; the user decides.
  Only the tester applies an approved amendment (`task-NNN: RED amended`). <!-- if:full -->
  An approved change to a test is committed on its own, with the reason in the message. <!-- if:lite -->
- Green means green: compare the **set** of failing test IDs with the baseline, never just the counts.
  A red baseline is never normal.
- Prove a new test can fail: before the fix it fails for the right reason (an assertion, or a missing symbol the
  spec creates), never because of a syntax, collection or unrelated import error.
- Fakes and mocks only at boundaries (network, LLM, cloud, clock). They mirror the documented behaviour of the
  installed version and cite the doc URL; a fake built on a guess hides real bugs.
- Cover the error and edge paths the acceptance criteria imply, not only the happy path. No vacuous assertions.

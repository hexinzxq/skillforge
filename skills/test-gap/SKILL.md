---
name: test-gap
description: Finds genuinely untested behavior in a diff, module or bugfix — error paths, boundaries, encoding, time, concurrency, state transitions — and adds focused tests that would fail on a plausible bug rather than padding coverage. Use when the user asks for tests, when coverage looks high but bugs still slip through, or right after fixing a bug.
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
  category: workflow
compatibility: Requires the project's test runner. No extra packages.
---

# Test gap

Coverage measures which lines ran, not which mistakes would be caught. A module
at 95% coverage can still ship a bug in every error path, because the happy path
is the only thing the tests exercise.

## Protocol

1. **List behaviors, not functions.** For the code in scope, enumerate what it
   promises: parses X, rejects Y, returns Z on empty, is idempotent, never loses
   a row, errors instead of silently truncating. Write the list down before
   reading any test file.
2. **Find the covered set.** Run the suite with coverage if it is available
   (`coverage run -m pytest`, `--cov`, `c8`), then read which *branches* have no
   test — uncovered `else:` and `except:` are the highest-yield spots. Coverage
   is a lead generator, never the target.
3. **Rank the gaps** by (probability a real bug hides there) × (cost if it
   does). The ranking almost always starts with: error paths, then boundaries,
   then input encoding, then time, then concurrency, then state machines.
4. **For each gap, name the bug the test catches.** One sentence, before writing
   the test: "this fails if the parser drops the last element". If you cannot
   name a plausible wrong implementation, the test is ceremony — skip it.
5. **Write the smallest test that fails on that bug.** One behavior per test,
   a name that reads as a sentence (`test_search_falls_back_to_like_when_fts_is_missing`),
   a fixture with only the fields the behavior needs. Assert on the observable
   contract (return value, error type, persisted state), not on internal calls.
6. **Run them against the current code.** They should pass; if one fails, you
   found a bug — report it, do not "fix the test".
7. **Report the gap table**: behavior, why it was likely to break, test added.
   If a gap was left untested, say why (needs a real network, needs a fake clock).

`references/edge-case-menu.md` is the checklist to run through when the code is
new to you and you do not yet know where the edges are.

## What earns a test

- An error path that a user can reach (bad input, missing file, timeout, 404).
- A boundary: 0, 1, max-1, max, empty string, single element, 10k elements.
- Encoding and text handling: CJK, emoji, combining marks, RTL, vs a `LIKE`
  pattern that treats `%` as a wildcard.
- Time: day boundaries, DST, UTC vs local, timestamps with and without a zone.
- Idempotency and retries: calling twice must not duplicate.
- State transitions: pending → paid cannot go back to pending.
- Round-trips: serialize then parse must return an equal value.
- A bug that already happened once (regression test, non-negotiable).

## What does not

- Getters, constants, dataclass field ordering, framework behavior.
- That a function calls a private helper — that is the implementation talking.
- Assertions on log strings or exact float formatting.
- A test that would pass with the function body replaced by a hardcoded return.

## Rules

- Deterministic: no `sleep`, no real clock, no network, no dependence on test
  order or on `$HOME`. Fake the clock, stub the client at the seam you own.
- Never weaken an existing assertion to make a new change pass; if an old test
  conflicts with the new intent, the test encodes an old contract — change it
  deliberately and say so.
- Do not chase a coverage number in the reply. Report behaviors covered.
- If the project has no tests and no runner, add the runner only if the user
  agrees; otherwise deliver the gap list as the artifact.
- Write the summary in the user's language.

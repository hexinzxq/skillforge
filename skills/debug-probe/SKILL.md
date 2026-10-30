---
name: debug-probe
description: Diagnoses a failing command, test or runtime error by building a ranked hypothesis tree and running the smallest possible probe for each, evidence before edits. Use when something errors out, a test fails, behavior is "weird" or "flaky", or the user pastes a stack trace and asks why it happens.
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
  category: workflow
compatibility: Requires the ability to run shell commands in the failing project.
---

# Debug probe

The rule this skill enforces: **do not edit code until a probe has told you
which hypothesis is true.** Guessing produces a diff that sometimes works and a
user who learns nothing.

## Protocol

1. **Stabilize the reproduction.** Get one command that fails, reliably, in
   under a minute. Shrink it: fewer flags, smaller input, single test, one
   module. A reproduction you can run repeatedly is worth more than any theory.
   If it is flaky, first characterize the flake rate (`for i in $(seq 20)`), not
   the cause.
2. **Read the error literally.** Quote it. Note the exact file and line, the
   exact type name, the exact value. Most wrong turns come from reading a
   similar-looking error instead of this one. Check: is it our code or a
   dependency's? Does the traceback include the *real* frame or only the
   wrapper?
3. **Write 3–5 ranked hypotheses.** Rank by prior, not by imagination. The
   usual priors, strongest first:
   - the code was changed recently (check `git log -p` / `git bisect`)
   - the input is not what it is assumed to be (charset, timezone, None, NaN,
     empty list, dict key order)
   - the environment differs from the one that worked (version, env var, cwd,
     locale, PATH, python/node version)
   - state from a previous run (cache, lockfile, sqlite WAL, stale build)
   - concurrency or ordering
   - actual library/framework bug (rare — keep it last)
4. **One probe per hypothesis**, each falsifiable, each cheap. A probe is a
   command or a three-line script that prints a value which would be different
   if the hypothesis were true. Prefer printing to asserting. See
   `references/probe-patterns.md` for a catalog.
5. **Record results as you go.** A small table in the reply: hypothesis, probe,
   result, verdict. Include the probes that failed — "it's not X" is progress.
6. **Fix the one thing that was true.** Then run the reproduction again, then
   the surrounding test suite. If the fix needs a change in more than one place,
   check whether a contract is missing (a validator, a type, an invariant).
7. **Leave a regression test** for exactly the reproduction you built, and
   mention it. A bug that can come back is not fixed.

## Probe design

- Change one variable per probe. Two variables, unreadable result.
- Prefer observing over changing: print the value, don't patch the code to
  "see if it helps".
- Cheap first: `python -c`, `node -e`, `curl -v`, `env | grep`, `git diff`,
  `print(repr(x))`, `EXPLAIN`. Heavy tooling (profilers, debuggers, packet
  captures) only after cheap probes narrow it down.
- If a probe needs to modify code, make it a throwaway print, and remove it
  before fixing — leftover debug output is itself a bug.
- Timebox: if two hypotheses die and the third needs an hour of setup, stop and
  report what is known, what to try next, and what you need.

## Do not

- Do not "restart and see" or "clear the cache" without a hypothesis that says
  why that would matter.
- Do not add try/except, retries, or sleeps to make the symptom disappear.
- Do not rewrite the surrounding code while debugging; unrelated changes hide
  the cause and make the diff unreviewable.
- Do not claim a fix without re-running the original reproduction.
- Write the report in the user's language.

---
name: commit-craft
description: Turns the current diff into a well-formed commit — imperative subject under 72 characters, a body that explains why rather than what, and a decision on whether to split — matching the repository's existing commit convention. Use when the user says commit, "写个 commit", "帮我提交", or when a change is finished and the message still needs writing.
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
  category: workflow
compatibility: Requires git. scripts/commit_context.sh needs a POSIX shell.
---

# Commit craft

The commit message is the only part of this work a future reader sees without
opening the diff. Optimize for them, not for the diff viewer.

## Protocol

1. **Collect context, cheaply.** Run `scripts/commit_context.sh`. It prints the
   branch, the last 15 subjects (that is the convention you must match), the
   diffstat, and the diff itself when it is small enough. Do not read whole
   files to write a message.
2. **Find the intent.** Read the diff and answer: what was broken or missing
   before this change? If the answer is only "these lines changed", the diff is
   doing two things — go to step 3.
3. **Decide split or single.** Split when the diff contains changes with
   independent reasons to exist (a refactor + a bugfix, a feature + its
   formatter churn). One commit, one intent. If splitting, commit in an order
   where each commit leaves tests green.
4. **Write it.** Subject: imperative, ≤ 72 chars, no trailing period, no
   `[tags]` unless the repo already does that. Body: why, wrapped at 72, with
   the failure mode it prevents. Trailers (`Refs:`, `Fixes:`, `Co-authored-by:`)
   only when the repo uses them.
5. **Commit with a heredoc**, never `-m` twice:

```bash
git commit -F - <<'MSG'
fix(store): allow sqlite connections across FastAPI threads

FastAPI runs sync endpoints in a thread pool, so every request after the first
hit "SQLite objects created in a thread can only be used in that same thread".
Opening with check_same_thread=False is safe here because the store serializes
writes through one connection per request scope.

Refs: #12
MSG
```

6. **Verify**: `git log -1 --stat` and `git status`. Say what was committed.

## Writing the body

A good body answers one of these, in this order of usefulness:

1. What went wrong with the naive version (the bug, the dead end, the rejected
   alternative).
2. Why this design and not the obvious one.
3. What the reader must know to change this code safely later.

A body that lists the files touched is noise — the diff already says that.

## Rules

- Match the repo's language. A Chinese repo gets a Chinese body; the subject
  stays short either way. Never mix two languages inside one commit.
- No emoji unless the last 15 subjects have them.
- No `update`, `fix bug`, `wip`, `minor changes`, `some improvements`. If the
  change is genuinely tiny, say what tiny thing: `chore: drop unused import in cli`.
- Do not amend or force-push to rewrite someone else's commits.
- Do not commit secrets, `.env`, or generated artifacts the repo ignores —
  check `git status --short` before staging, and stage paths explicitly rather
  than `git add -A` when the tree is dirty in unrelated ways.
- If tests were not run, say so in the reply; do not claim they passed.
- Write the explanation to the user in their language.

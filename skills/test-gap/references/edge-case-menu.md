# Edge case menu

Run down this list against the code under test and keep only the rows where the
answer is "no idea" or "probably not" — those are the gaps.

## Input space

- empty string, `None`/`null`, `undefined`, missing key, extra key
- whitespace-only, leading/trailing whitespace, zero-width chars, NBSP
- very long (10k chars), very many (10k items), deeply nested
- Unicode: CJK, emoji (surrogate pairs), combining marks, RTL, full-width
  digits, case folding for Turkish `i`/`I`
- numbers: 0, -0, 1, -1, max int, overflow, NaN, Infinity, float precision
  (`0.1 + 0.2`), scientific notation, leading zeros, `1e400`
- dates: epoch 0, 2038, leap day, DST spring-forward gap, end-of-month
  arithmetic, timezone-less input where a zone is expected
- files: missing, empty, 0 bytes, permission denied, is a directory, symlink
  loop, path with spaces/newlines, path traversal `../`
- SQL/`LIKE`: `%`, `_`, existing wildcard escaping, single quotes, CJK
- URLs/JSON: malformed JSON, trailing comma, duplicate keys, huge payload,
  wrong content-type, 204 with a body

## Boundaries between modules

- who validates — caller, callee, both, neither
- what a function returns on error: exception, `None`, empty list, `False`,
  partially-written state (the worst one)
- encoding boundary: bytes in, str out — where does decoding happen
- time boundary: where is the naive datetime, where the aware one

## State and repetition

- called twice: idempotent? duplicated rows? doubled counters?
- interrupted mid-way (kill -9, exception after the write, before the commit)
- concurrent access to the same row/file/connection
- order of operations from two clients, last-write-wins surprises
- restart: does state survive, is it re-read, is it migrated

## Error paths

- every `except` / `catch`: is there a test that reaches it
- does the error message carry enough to debug (value, path, id) without leaking
  secrets
- partial failure: 3 of 5 items fail — is the result all-or-nothing, and is that
  documented
- timeouts and retries: does a retry duplicate a side effect

## Serialization

- round-trip: object → bytes → object equals the original (including `None` vs
  missing key, and float precision)
- schema change: old payload against new parser, and the reverse
- field ordering, key case, `null` vs absent

## Output contracts

- what the API returns on empty result: `[]`, `null`, or 404 — pick one and test
- pagination: last page, page beyond the end, page size 0/huge
- sorting: stable? ties? non-ASCII collation?
- caching: does a cache key include every input that changes the answer

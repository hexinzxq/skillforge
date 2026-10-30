# Critique report template

```markdown
## What I looked at
<one line: screenshot / URL / file, viewport size if known>

## Findings

| # | severity | where | measured | fix |
|---|----------|-------|----------|-----|
| 1 | high | … | … | … |

## Leave alone
- <decision that is working, and why>

## Highest-leverage change
<one sentence>
```

## Severity

Use three levels, not five — they force a ranking.

- **high** — costs the user something real: unreadable text, an unreachable
  action, a missing error state, a broken grouping.
- **medium** — visible friction or inconsistency the user feels but tolerates.
- **low** — polish: 1px alignment, a slightly off optical margin.

## Examples of a row that carries its weight

| severity | where | measured | fix |
|---|---|---|---|
| high | form label → input vs input → next input | both 12px | label gap → 6px, keep 16px between fields |
| high | placeholder text on `--surface-2` | 3.1:1 | `#94a3b8` → `#64748b` (4.6:1) |
| medium | stat cards, 3 visible at 1440px | grid 2 columns | 3 columns, min-width 280px |
| low | save button vs cancel button | both filled, same size | cancel → ghost button |

## Anti-patterns

- A row whose "fix" is "improve spacing" — no value, not actionable.
- Twelve findings with no ranking — the user ships nothing.
- Critique of the design's *idea* rather than its execution — out of scope
  unless the user asked for a concept review.

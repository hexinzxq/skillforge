# Contrast checking — how scripts/contrast.py works

Load this when a contrast check fails, when you're about to pass flags other
than plain `--css tokens.css`, or when the sheet uses names you don't recognize.

## Invocation

```bash
python3 scripts/contrast.py --css tokens.css        # derive pairs from naming conventions
python3 scripts/contrast.py --fg "#111" --bg "#fafafa" --min 4.5
python3 scripts/contrast.py --pair "text:oklch(0.145 0 0) on bg:oklch(1 0 0)"
python3 scripts/contrast.py --css sheet.css --block .dark --quiet
```

Exit codes: `0` all pairs pass · `1` at least one failure (the report is the
fix list) · `2` usage/input error.

## What gets derived from a token sheet

| Convention | Check |
|---|---|
| `--<role>-contrast` / `--on-<role>` | against `--<role>` at 4.5:1 |
| `--<role>-foreground` (shadcn) | against `--<role>` at 4.5:1 |
| `foreground` on `background` (shadcn) | 4.5:1 |
| `text` / `muted` against `bg`, and both against `surface` / `panel` / `card` | 4.5:1 |
| `ring` / `focus-ring` / `focus` against `bg` (or `background`) | 3:1 — a focus ring is a state indicator, no ambiguity |
| `border` against `bg` | reported against 3:1, **advisory** (see below) |

shadcn's `-foreground` convention is honored because it is the most-copied
sheet on the internet — running it against their real `globals.css` finds real
issues: dark `--destructive-foreground` sits at **1.66:1** on `--destructive`
(red on red), light `muted-foreground` 4.35:1, light `border` 1.26:1, and its
default `ring` (`oklch(0.708 0 0)`, 2.58:1 on white) — a focus ring below 3:1
is the one thing every shadcn sheet ships broken.

Border rows are **advisory**: they are printed with their ratio and marked
`ADVISORY`, and they do not fail the run. `--border` is an input outline in
shadcn and a card divider in plenty of shipped sites (one real blog sits at
1.39:1 on purpose); WCAG 1.4.11 asks 3:1 of the borders that identify a
component, and the token sheet does not say which usage is which. Read where
the token is used: if it outlines an input, button, or focus ring, fix it to
3:1; if it separates sections, a subtle line is correct. `--pair` is always
hard — pass the threshold you mean when you want the run to fail.

## Value formats

hex (3/4/6/8 digit), `rgb()`, `rgba()`, `hsl()`, `hsla()`, `oklch()`,
`oklab()` — including percent forms and legacy comma syntax. Real sheets are
written in oklch now (Tailwind v4, shadcn); a checker that only reads hex
tells those projects they have no colors at all.

Non-literal values (`var(--x)`, `color-mix()`) are skipped, not guessed.

## Alpha is composited, not dropped

Dark themes ship translucent borders (`oklch(1 0 0 / 10%)`). Checking them as
opaque white reported 19.8:1 for a hairline that renders at 1.24:1. The script
blends the foreground's alpha over the pair's own background — that is what
actually renders. This includes legacy `rgba(r, g, b, a)` where the alpha is
the fourth argument, not a `/` segment.

## Multi-theme sheets refuse to guess

Sheets that define the same names in several blocks (`:root` plus `.dark`)
make flat reading ambiguous: last-wins silently checks only the dark theme, or
worse, pairs a light fg with a dark bg on sheets that override just some vars.
The script refuses such sheets until you pick a scope:

```bash
python3 scripts/contrast.py --css tokens.css --block :root
python3 scripts/contrast.py --css tokens.css --block .dark
python3 scripts/contrast.py --css tokens.css --all-blocks   # both, in one report
```

The same applies to `@media (prefers-color-scheme: dark)` overrides: a `:root`
inside that query is a different scope from the top-level `:root`, even though
both selectors read the same. The block name carries the condition
(`@media (prefers-color-scheme: dark) :root`), and `--block :root` still means
the plain one — an exact name wins over a substring.

Check both, fix both — a token that passes in light mode can fail in dark.
`--all-blocks` is the one-command version: each pair is prefixed with the block
it came from, and the exit code covers every block (this is how shadcn's real
sheet reports light muted-foreground 4.35:1 and dark destructive-foreground
1.66:1 together).

## When something fails

Change the token, not the threshold. If the accent is too light for white
text, darken the accent or switch to dark text on it. Never edit `--min` to
make a report go green.

## Values the sheet computes

Modern sheets rarely spell a colour out. Three forms are resolved before
checking, and anything still unknown is reported as **not checked** rather than
counted as a pass:

- `var(--x)` chains — two-layer design systems (a role token pointing at a
  palette token) are followed up to four levels; a missing reference without a
  fallback is listed by name.
- `color-mix(in srgb|oklab|oklch, A p%, B)` — interpolated with real colour
  math (OKLab matrices, hue arc for oklch). Bootstrap's entire palette is
  built this way.
- `light-dark(a, b)` — one declaration, two themes. Both are checked; rows are
  prefixed `light:` / `dark:` only when the two actually disagree, so a
  theme-independent pair is not printed twice.

Hue units are honoured (`240`, `240deg`, `4.19rad`, `0.667turn`, `266grad`).

## Which pairs are inferred, and which are not

Inference is limited to pairings the names actually promise:

- ours: `--<role>-contrast` / `--on-<role>` on `--<role>`
- shadcn: `--<role>-foreground` on `--<role>`, `--foreground` on `--background`
- Bootstrap: `--<role>-contrast` on `--<role>-bg`

`--<role>-fg` is deliberately **not** paired with `--<role>-bg`. On real
Bootstrap, `-fg` is a foreground used on the page surface
(`.fg-warning { color: var(--bs-warning-fg) }`), so pairing it with the
`-bg` fill reported 36 unreadable combinations that do not exist. Add your own
with `--pair "text:#fff on accent:#1d4ed8"` when a sheet uses its own names.

In `--all-blocks` mode the blocks are read as one cascade: a utility block
whose `var()` points at `:root` resolves (before this, every utility block on
Bootstrap showed up as 832 "not checked" tokens). Blocks that declare colours
but follow no convention are summarized in one line instead of one line each —
Bootstrap's sheet has 249 of them. Non-colour tokens (shadows, timings, font
stacks) are never listed as unchecked, because a shadow value contains `rgb()`
and would otherwise look like a colour.

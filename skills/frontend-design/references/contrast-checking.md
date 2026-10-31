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
| `text` / `muted` against `bg`, `text` against `surface` | 4.5:1 |
| `border` against `bg` | 3:1 (UI component threshold, WCAG 1.4.11) |

shadcn's `-foreground` convention is honored because it is the most-copied
sheet on the internet — running it against their real `globals.css` finds real
issues: dark `--destructive-foreground` sits at **1.66:1** on `--destructive`
(red on red), light `muted-foreground` 4.35:1, light `border` 1.26:1.

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
```

Check both, fix both — a token that passes in light mode can fail in dark.

## When something fails

Change the token, not the threshold. If the accent is too light for white
text, darken the accent or switch to dark text on it. Never edit `--min` to
make a report go green.

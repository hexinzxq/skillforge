# Role names

The point of a token set is that a component asks for a *role*, and the theme
decides the color. If components reference shades, dark mode breaks; if they
reference roles, dark mode is one more assignment.

## Core roles (the minimum)

| token | means | not |
|---|---|---|
| `--color-bg` | the page behind everything | "white" |
| `--color-surface-1` | cards, panels, sheets | "gray 50" |
| `--color-surface-2` | nested surfaces: inputs, hover rows, code blocks | |
| `--color-border` | hairline separators, input outlines | decorative lines |
| `--color-border-strong` | focusable/active bounds, selected cards | |
| `--color-text` | primary body and headings | |
| `--color-text-muted` | secondary labels, metadata, placeholders | disabled text |
| `--color-text-disabled` | disabled controls | |
| `--color-accent` | the one interactive brand color | |
| `--color-accent-hover` | accent, one ramp step toward the background | |
| `--color-accent-contrast` | text/icons *on* accent | |
| `--color-success` / `-warning` / `-danger` | status | brand variety |
| `--color-on-*` | text on that status background | |

## Add later, and only when a screen needs it

`--color-overlay` (modal scrim), `--color-focus-ring`, `--color-chart-1..6`
(a categorical ramp, distinguishable in grayscale), `--shadow-*`, `--radius-*`,
`--space-*`, `--text-*`.

## Naming rules

- `--color-<role>` / `--color-<role>-<variant>`; role first, variant second.
  `--color-surface-2-hover`, never `--color-hover-surface-2`.
- Numbers only where there is a real ladder (`surface-1`, `surface-2`), never
  as decoration (`surface-primary-2`).
- No component names in the token layer (`--color-button-bg` is a component
  token; it should alias `--color-accent`).
- Ramp values live in a separate block, prefixed `--ramp-`, and are allowed to
  be dumb: `--ramp-accent-500`.

## Dark mode checklist

1. Re-assign every role; do not invert the ramp.
2. Elevation goes *up* in lightness (bg < surface-1 < surface-2), because
   shadows read as nothing on dark.
3. Text: `#e5e7eb`-ish, not `#ffffff` — pure white on dark vibrates.
4. Accent: check `accent-contrast` and `text-muted` again in dark; both usually
   need one step up.
5. Borders: one step more visible than in light mode; hairlines vanish.
6. Re-run the contrast table for dark separately — passing light says nothing.

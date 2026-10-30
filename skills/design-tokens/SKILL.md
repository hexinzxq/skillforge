---
name: design-tokens
description: Generates a semantic design-token set (light and dark, CSS custom properties plus JSON and optional Tailwind theme) from a brand color, a reference image or an existing palette, with contrast-checked pairs and role-based names. Use when starting a UI, adding a dark mode, or when the user gives a brand color or screenshot and asks for tokens, a palette, a theme, "配色" or "设计变量".
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
  category: frontend
compatibility: Requires Python 3.10+ for scripts/gen_tokens.py. No third-party packages.
---

# Design tokens

Turns one input (a brand color, a reference screenshot, or a mess of existing
hex values) into a small semantic token set that survives an implementation and
a dark mode. The deliverable is a file the project imports, not a list in chat.

## Pick the input

- **Brand color** — the usual case. Derive the ramp, keep the hue.
- **Reference image** — sample 3–6 pixels (dominant saturated color, the
  background, the text) and confirm with the user which one is the accent.
  Do not derive a full palette from a photo's mood.
- **Existing palette** — map the values onto roles first, then only fill gaps.
  Do not re-invent hues the project already ships.

## Protocol

1. **Fix the accent hue.** Convert the brand color to OKLCH and keep `h`.
   Hue from RGB is unstable across lightness; OKLCH is not — that is why the
   ramp holds together when a plain HSL ramp goes muddy.
2. **Neutral hue = accent hue**, chroma tiny (0.004–0.018). A neutral with the
   brand's hue reads as intentional; pure gray reads as default.
3. **Generate the ramp**, not a color wheel: lightness steps, roughly even in
   perceived lightness, chroma tapering at both ends (gamut).
4. **Assign roles, not shades.** `--color-surface-1`, not `--gray-100`.
   Minimum viable set: bg, surface-1, surface-2, border, border-strong, text,
   text-muted, accent, accent-hover, accent-contrast, plus success, warning,
   danger. Resist adding more until the UI needs them.
5. **Verify pairs, not colors.** A palette is fine as swatches and broken as
   pairs. Check: text/bg, text/surface-1, text/surface-2, text-muted/bg,
   accent-contrast/accent, border/surface-1.
6. **Dark mode is a re-assignment, not an inversion.** Backgrounds get darker
   but not 0; text gets lighter but not 255; the accent usually needs to rise in
   lightness to keep 4.5:1 against a dark surface. Shadows become borders.

Run the generator:

```bash
python3 scripts/gen_tokens.py --brand "#3b82f6" --out ./tokens
```

It writes `tokens/tokens.css` and `tokens/tokens.json`, prints the contrast
table for the pairs above, and exits non-zero if a text pair falls below 4.5:1.

## Output contract

- `tokens.css` — `:root` (light) and `[data-theme="dark"]` blocks, one token per
  line, grouped by role with a short comment per group.
- `tokens.json` — `{ "light": {...}, "dark": {...} }`, hex strings, for
  scripts, tests, and the Tailwind `@theme` block.
- In the reply: the contrast table (from the script), and two sentences on what
  the palette is optimized for (e.g. "data-dense dashboard, low chroma so
  charts keep the color budget").

Read `references/naming.md` before renaming anything — the role list there is
what makes a token set portable between projects.

## Rules

- One accent. A second accent is a variation (`accent-warm`) or a status color,
  not a second brand.
- Never ship a token you cannot name by role. `--blue-500` is a swatch; it
  belongs in the ramp, not in the API.
- Never generate 10 gray steps and use 3. Generate 5 and use 5.
- Do not hand-pick "nice" hexes for status colors from the ramp: use hue 150
  (success), 85 (warning), 25 (danger) at matching lightness, so they read as
  the same system.
- If the user's project already has tokens, produce a *migration*: old name →
  new name, one line each, and only rename what has an exact equivalent.
- Write the reply in the user's language.

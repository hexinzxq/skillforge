# Slop tells — what sloplint.py checks, and what it can't

Load this when `scripts/sloplint.py` reports something and you need to decide
whether to fix or waive it.

The prose sections of SKILL.md cover choices that need judgement. A scanner
can't judge — it can only catch the tells that have a mechanical signature.
That split is deliberate: what's here is checkable, everything else stays in
the skill.

## FAIL — mechanically broken, fix it (exit 1)

| rule | what it catches | why |
|---|---|---|
| `transition-all` | `transition: all` | also animates layout on resize; name the properties |
| `animate-geometry` | transition/animation of a layout property (width/height/inset/margin/padding/font-size/line-height/border-width) | layout thrash — animate `transform`/`opacity`; paint properties like `border-left-color` are fine |
| `no-focus-replacement` | `outline: none` with no `:focus`/`:focus-visible` rule anywhere | the keyboard loses the cursor |
| `viewport-vh` | `100vh` in a `height`/`min-height`/`max-height` value, including `calc()` | breaks under mobile browser chrome — use `100dvh` (a `--x-height: 100vh` token is fine) |
| `hidden-overflow` | `overflow-x: hidden` on `html`/`body` | masks a real horizontal overflow instead of fixing it |
| `img-alt` | `<img>` without `alt` | screen readers announce the filename; `alt=""` only when decorative |
| `no-h1` | a full document that has `<h2>`–`<h6>` but no `<h1>` | the outline has no top — the page title is a `<div>` and screen-reader navigation starts below the page; make the visible title the `h1` |
| `no-viewport` | a full document (`<!doctype`/`<html>`) with no `<meta name="viewport">` | phones lay it out at 980px and shrink it; fragments/partials are exempt; a print target (`@page`) gets a tell instead of a failure — the PDF has no viewport, only a screen copy would need one |
| `zoom-lock` | viewport with `user-scalable=no` or `maximum-scale` below 5 | pinch-zoom is an accessibility feature (WCAG 1.4.4); low-vision users cannot read a page that forbids it |
| `missing-stylesheet` | a relative `<link rel="stylesheet">` whose file does not exist | the page ships unstyled — a renamed or typo'd path renders exactly like a design decision; a root-relative href is looked up under the page's ancestors (export root), and only CDN or `<base>`-relative hrefs fall back to a note |
| `dangling-var` | `var(--x)` is one or two edits from a token declared in this scan, and has no fallback | it is a typo — the reference resolves to nothing and the element renders with no colour |

## TELL — the default a model falls into, waivable on the record (exit 0)

| rule | what it catches | why |
|---|---|---|
| `literal-color` | hex/rgb/hsl/oklch/lab/lch/`color()` literal outside a token declaration (a `color-mix()` built from tokens is fine) | components should reference roles, so a theme swap stays possible |
| `eyebrow` | `text-transform: uppercase` + `letter-spacing` in one rule | tracked-out ALL-CAPS labels above every section are the generated look |
| `focus-not-visible` | `outline: none` replaced on `:focus` only | works, but every mouse click flashes the ring — `:focus-visible` shows it only for keyboard use |
| `viewport-vw` | a bare `width: 100vw` / `min-width: 100vw` (a `calc(100vw - 24px)` gutter is fine) | 100vw counts the scrollbar — the block scrolls sideways by its width; use `100%` on a full-bleed section |
| `no-reduced-motion` | a file that declares `transition`/`animation` and never mentions `prefers-reduced-motion` | an entrance animation or parallax that ignores the OS setting; either form counts (`reduce` or `no-preference`), and a 150ms colour fade is a legitimate waive |

`--strict` makes TELLs fail too — use it on a project that has already
committed to a token layer, where a literal colour is a real defect. It also
overrides `--quiet` for tells: a run that exits 1 must print why.

Coverage: a root-relative href (`/_next/static/css/...`) is resolved against
the page's ancestors — a static export puts it under the export root, so it
gets linted. What is left over — a CDN sheet, or a relative href on a page
with `<base href>` — gets a `note:` line naming it. A relative href whose
file is missing (and that no `<base>` redirects) is not a note: it is the
`missing-stylesheet` failure above. Zero findings then means "nothing wrong
in the files I could read", not "the page is fine". Read the skipped sheet
yourself against the tables above.

Findings point at `file:line`; on a minified line (over 400 characters) they
gain a column (`file:1:48213`) because a static export is one line and the
`near:` snippet alone may match the file more than once.

Vendored bundles are real code you still cannot edit — `_next/` CSS, a
`*.min.css` dependency. `--exclude '*/_next/*'` (repeatable) keeps them out of
the scan, and the run then names what it skipped: `note: 1 file(s) not scanned
(--exclude): …`. Exclude the file you cannot fix; do not silence a finding you
can.

## Waiving a tell

Fix it, or waive it **on the record**: one line in the handoff saying which
tell, where, and why the exception is right for this brief. A waiver without a
reason is a failure with extra steps.

## What the scanner deliberately does not check

- Whether the design is distinctive (that's §2's default test and the human read).
- Missing hover/disabled/loading states (needs render + interaction).
- Emoji-as-icon, invented metrics, filler copy — too much language judgement
  for a regex; the prose rules still apply.

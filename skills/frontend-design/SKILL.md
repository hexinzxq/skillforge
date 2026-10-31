---
name: frontend-design
description: Builds production-grade, visually distinctive web interfaces — a design plan with real tokens, then code that passes an enterprise quality floor (responsive, focus-visible, contrast-checked, state-complete). Use when the user asks for a page, landing page, dashboard, component, or redesign, when output "looks like an AI template", or when they say 前端设计 / 页面太丑 / 做个好看点的界面 / redesign.
license: MIT
metadata:
  version: "1"
  author: hexinzxq
---

# Frontend Design

You are the design lead at a studio whose work is not mistaken for anyone else's. The client has already rejected templated proposals and is paying for a point of view. Every choice — palette, type, layout, motion, copy — must be traceable to *this* brief, not to what you'd produce for the last ten briefs.

Two failures matter equally:

- **Generic** — it looks like every other AI page.
- **Beautiful but broken** — it looks good in a screenshot and falls apart on a phone, at 200% zoom, on the keyboard, or with a long name.

This skill optimizes for neither alone. Both, or it isn't done.

---

## 1. Pin the brief before designing

If the brief doesn't say what the product is, decide a concrete subject, audience, and primary job, then state it back in one line before building.

| Field | Example |
|---|---|
| Subject | A payroll tool for 40-person agencies |
| Audience | Ops managers, 30–45, desktop-first, low patience |
| Primary job | See who's unpaid this cycle and fix it in two clicks |
| Constraint | Must match an existing warm-grey brand, no new fonts |

Distinctive design comes from the subject's material vocabulary — its tools, documents, units, language. A payroll tool and a music player should not share a palette or a layout rhythm.

If memory or repository files contain brand tokens, fonts, or a design system, **use them**; don't invent a parallel one.

---

## 2. Write the design plan (short, before any code)

Produce this block first. It is the contract the code must satisfy.

```
PALETTE   bg / surface / text / muted / accent / accent-contrast   (6 colors + role)
TYPE      display + body faces, scale ratio, weights used
GRID      max width, columns, gutter, breakpoints, baseline unit
RHYTHM    section padding scale (e.g. 24/48/96/160)
MOTION    one orchestrated moment, or none
HERO      the single most characteristic thing in the subject's world
RISK      the one deliberate, defensible aesthetic bet
```

Then run the **default test**: mentally build the same page for a different subject. If your plan wouldn't change, it's a default — revise it and say what you changed.

---

## 3. Typography

Type carries personality. Use one family, or two that are *clearly* different (a display face + a workhorse), never two that are almost-the-same.

**Scale** — pick a ratio and stick to it; don't hand-tune every heading.

- Dense UI: 1.125–1.2 (Material-ish, 12/14/16/20/24/32)
- Marketing: 1.25–1.333 (16/20/25/31/39/49/61)
- Body never below 16px on web; 14px only for dense tabular data or meta.

**Measure and leading**

- Line length 45–75 characters (hard ceiling 80). Serif can run ~5% longer.
- Body leading 1.5–1.65 (serif 1.55–1.7); headings 1.1–1.25; UI labels 1.3.
- Tracking: tighten display sizes (−0.01em to −0.02em above 32px), never loosen body.

**Tells to avoid** — these read as generated:

- Bolding/coloring exactly one word in a headline.
- So-called eyebrows: tracked-out ALL-CAPS labels above every section.
- Numbered markers (01 / 02 / 03) when the content isn't actually sequential.
- A display font used at three sizes with no relationship.

**Weight and contrast are hierarchy**: 2 weights (400/500 or 400/600) outrank 5 weights used decoratively. Never fake bold.

---

## 4. Color

Roles, not shades. Six roles are enough:

```
--bg            page background
--surface       cards, sheets, inputs
--text          primary content
--muted         secondary text, icons
--accent        single action color
--accent-contrast  text on accent
```

Rules that prevent 90% of bad palettes:

- **One accent.** A second accent is a decision to justify, not a default.
- Text on background ≥ **4.5:1**; large text (≥24px or ≥19px bold) ≥ **3:1**; UI borders and focus rings ≥ **3:1**.
- Never encode meaning in hue alone (error/red + icon + words).
- Dark mode is not inverted light mode: raise surfaces slightly (`+4–8%` lightness per elevation step), desaturate accents ~10%, and keep shadows subtle/absent — use surface steps for depth.
- Tinted near-black (`#0B0B0B`) as "black", and warm cream (`#F4F1EA`) with a clay accent are the two most common generated palettes. Use them only if the brief asks.

**Check contrast with the script, not in your head.** Guessing luminance is
how a palette ships at 3.9:1:

```bash
python3 scripts/contrast.py --css tokens.css   # exits 1 on any failure
```

The naming conventions above become the test: the script derives the pairs, so
a convention-following sheet checks itself. It reads hex/rgb()/hsl()/oklch(),
honors shadcn's `-foreground` convention, composites translucent values, and
refuses to guess between `:root` and `.dark` — details and failure recipes in
references/contrast-checking.md. A failing pair means change the token, not
the threshold.

---

## 5. Layout and space

- **8px baseline** for spacing; radii and gaps snap to it. 4px only for icon-to-label gaps.
- Vertical rhythm: one scale (`24 / 48 / 96 / 160`) for section padding. Don't mix three different paddings at the same level.
- **Max content width** 1100–1280px for marketing, 1440–1600px for dashboards; text columns 60–75ch.
- Alignment: one dominant axis per page. Centered text only for short (≤2 lines) statements; everything else left-aligned.
- **Density is a choice**: a data tool at 32px rows is as valid as a marketing page at 160px sections — but pick it per subject.
- Responsive floor: 360 / 768 / 1024 / 1440. Test at 360 first — mobile is where generated layouts break.

Borders, dividers, numbering, and labels are **information**, not decoration. Add a border only if it groups, separates, or indicates interactivity.

---

## 6. Component state completeness

Every interactive element ships with all of these. Missing states are the fastest way to look fake:

```
default · hover · active · focus-visible · disabled · loading · error · empty · success
```

- `:focus-visible` ring: 2px accent at 2px offset, never `outline: none` without a replacement.
- Disabled: ≥ 3:1 contrast for text if still readable, `cursor: not-allowed`, no hover effect.
- Loading: skeleton or inline spinner, never a layout shift when data lands.
- Empty: says what belongs here and offers the first action.
- Error: what happened + what to do next, in the interface's voice.

Forms: label above input (not placeholder-as-label), inline errors under the field, one primary action.

---

## 7. Motion

- One orchestrated moment (page-load sequence or a single reveal) beats effects sprinkled everywhere.
- Fade-and-slide-up on every section and hover-scale on every card are the generic default. Cut them.
- Duration 120–200ms for UI feedback, 240–400ms for entrances; ease-out for entering, ease-in for exiting.
- Respect `prefers-reduced-motion` — and don't let removing motion break meaning.
- Motion that answers a user action is always welcome; motion that plays at the user is usually noise.

---

## 8. Copy is design material

Words exist to make the interface usable, not to decorate.

- Name things by what users understand, not how the system is built ("Notifications", not "Webhook config").
- Active voice; the CTA states the outcome ("Save changes"), and the toast repeats the same verb ("Changes saved").
- Errors: no apology, no vagueness — what failed, why, what to do.
- Empty states are invitations, not moods.
- No filler ("Empower your workflow", "Seamlessly integrate"). If a line could sit on any product page, delete it.
- Sentence case for UI text. ALL CAPS only if the brief demands it.
- Each element says one thing.

---

## 9. Build rules (CSS/JS specifics that keep it from breaking)

- Use a token layer (`:root` custom properties); components reference tokens, not literals.
- Keep specificity flat: prefer single-class or `:where()` resets; avoid a `.section` padding fighting an element selector.
- `clamp()` for type and section padding — one line that works at 360 and 1440.
- Use `gap` over margins for stacks; `min-height: 100dvh`, not `100vh`.
- Images: explicit `aspect-ratio` + `width/height` to prevent shift; `object-fit: cover`.
- Long strings: `overflow-wrap: anywhere` on user content, `min-width: 0` on flex children.
- No layout that depends on a specific viewport height; no `position: fixed` footer on mobile.
- Test with a 40-character name, an empty state, and a 1,000-row table before declaring done.

---

## 10. Self-critique loop (do this, don't skip)

1. **Screenshot** at 1440 and 360. If the environment can screenshot, look at it; a picture beats guessing.
2. Run the checklist below against the actual render, not your intentions.
3. Remove one accessory. If removing something doesn't hurt, it was decoration.
4. State what you changed and why — one or two lines, not a report.

### Ship checklist

- [ ] Palette has 6 named roles; accent used once per view
- [ ] `scripts/contrast.py --css <tokens>` exits 0 (all text ≥ 4.5:1, borders and focus rings ≥ 3:1)
- [ ] One type scale ratio; body ≥ 16px; measure ≤ 80ch
- [ ] Every interactive element has hover / focus-visible / disabled / loading
- [ ] Empty, error, and long-content states render correctly
- [ ] Works at 360px with no horizontal scroll
- [ ] Keyboard-only pass: tab order logical, no traps, skip link if long
- [ ] `prefers-reduced-motion` respected
- [ ] No default AI tells: single-word headline accent, ALL-CAPS eyebrows, 01/02/03 markers, identical rounded cards, terracotta-on-cream, tinted-black
- [ ] One memorable element; everything else quiet

---

## 11. Output shape

Deliver runnable code, not screenshots of intent:

- Single page → one `index.html` with a `<style>` token block, or React + CSS modules.
- Multi-section or reusable → components + a `tokens.css`.
- Always include: the design plan block (§2), the tokens, the component code, and a two-line note on the risk taken and what was cut.

If the user's repo already has a design system, extend it — new tokens go in the existing file, not a parallel one.

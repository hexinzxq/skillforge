---
name: ui-critique
description: Reviews a UI screenshot, mockup, URL or component source and returns a prioritized critique of hierarchy, spacing rhythm, contrast, density and state coverage, every finding paired with a concrete value to change. Use when the user shares a screen and asks whether it looks good, why it feels off, how to make it better, or wants a design review before shipping.
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
  category: frontend
---

# UI critique

A design review that produces numbers instead of vibes. The failure mode this
skill exists to prevent: "looks a bit plain, maybe add more whitespace" — an
answer the user cannot act on and cannot disagree with.

## Inputs

Accept any of: a screenshot, a URL you can fetch, a component's source, or a
rendered static export. If none is available, ask for one — do not review from
a description of the design.

If the screenshot is too small or cropped to judge a lens, say which lens you
skipped and why. Never guess at pixel values you cannot see.

## Protocol

Go through five lenses in this order. For each, **measure first, then judge**.
Write down what you measured (gap sizes, type sizes, ratios) — it is the
evidence for the finding.

### 1. Hierarchy

- Squint test: if the screen were a grayscale blur, what survives? The primary
  action must.
- Count primary-styled actions (filled buttons). More than one per view is a
  finding; none is a finding.
- Count distinct type sizes. A page needs a scale, not a spread: 3–4 sizes is
  usually right, 6+ is noise. List them.
- Check that the title is not competing with the CTA for the same job (e.g. a
  giant hero heading directly above an equally giant button).

### 2. Spacing rhythm

- List every distinct gap you can measure: section gaps, card padding, control
  gaps, label→field gaps.
- Flag values that are not on a 4px grid at all (`13px`, `0.7rem`, `margin: 17px`).
- Check proximity, which is the one people get wrong: the gap inside a pair
  (label→its field, icon→its label) must be *smaller* than the gap between
  groups. If they are equal, the grouping is unreadable.
- Check that padding is not accidentally larger than the gap between siblings
  (cards look welded together).

### 3. Contrast

Measure, do not eyeball. For any body text / background pair, compute the WCAG
ratio with `scripts/contrast.py`:

```bash
python3 scripts/contrast.py "#6b7280" "#ffffff" "#0f172a" "#1e293b"
```

Thresholds: body text ≥ 4.5:1, large text (≥ 24px, or ≥ 18.66px bold) ≥ 3:1,
UI borders and icons ≥ 3:1, disabled states are exempt but must still be
visibly distinct from enabled. Placeholder text at 4.5:1 is a common miss.

Also check the *non-ratio* contrast problems: a 1px border on a card whose
surface is 2% lighter than the page reads as noise; a focus ring that is only a
color change disappears for color-blind users.

### 4. Density

- Rows or cards above the fold: count them. A data screen that shows 3 rows
  where 8 would fit is paying for air with information.
- Control heights: 32/36/40px are the sane ladder. Mixed heights in one row
  look broken.
- Table cells: vertical padding under 8px reads cramped, over 16px reads airy
  for a data table.
- Line length: body copy over ~75 characters per line is a reading tax.

### 5. State coverage

Enumerate what the screen looks like when: empty, loading, error, disabled,
with very long text, with 0 items and with 500 items, and at 375px wide. Any
state that has no design is a finding — usually the highest-severity one,
because it is what users hit on a bad day.

## Output

A table sorted by severity, at most 8 rows, then a short "leave alone" list.
Use `references/report-template.md` as the shape. Each row needs: where (element,
not "the page"), what is measured, why it hurts, and the exact replacement value.

```
| # | severity | where | measured | fix |
|---|----------|-------|----------|-----|
| 1 | high | card padding vs card gap | padding 24px, gap 24px | gap → 16px so cards separate |
```

"Leave alone" matters as much as the findings: name the two or three decisions
that are working (a restrained accent, one clear CTA) so the next revision
does not flatten them.

Close with the single change that buys the most, in one sentence.

## Rules

- No adjective without a number. "Feels cramped" → "row height 28px for a
  40-character label".
- Do not invent a brand direction. Restraint is a valid endpoint; "make it
  bolder" is not a critique.
- Do not review content (copywriter) or brand (logo) unless asked — stay on
  layout, type, color, states.
- Prefer removing to adding: most "too busy" screens need deletions, and
  saying what to delete is more useful than what to add.
- Write in the user's language.

#!/usr/bin/env python3
"""WCAG contrast checker for the frontend-design skill — stdlib only.

Why this exists: the skill used to tell the model to compute (L1+0.05)/(L2+0.05)
by hand. Models get relative luminance wrong on hex colors, quietly, and the
palette ships failing 4.5:1. Arithmetic belongs in a script.

Understands hex, rgb()/rgba(), hsl()/hsla() and oklch()/oklab(). Real token
sheets are written in oklch() now (Tailwind v4, shadcn), and a checker that
only reads hex calls every one of them "no colors found".

    # one pair
    python3 scripts/contrast.py --fg "#111827" --bg "#ffffff"

    # every pair implied by a token sheet (--text/--bg, --muted/--bg,
    # --text/--surface and every --<role>-contrast against --<role>)
    python3 scripts/contrast.py --css tokens.css

    # explicit pairs
    python3 scripts/contrast.py --pair "text:#111827 on bg:#ffffff" --min 4.5

Exit status is 1 when any pair misses the threshold, 2 on bad input, so CI can
gate on it.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FUNC_RE = re.compile(r"^(rgba?|hsla?|oklch|oklab)\(([^)]*)\)$", re.I)
VAR_RE = re.compile(r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);")
WCAG_TEXT, WCAG_LARGE, WCAG_UI = 4.5, 3.0, 3.0


def _angle(token: str) -> float:
    """Hues arrive as 240, 240deg, 4.19rad, 0.667turn, 266grad — all of them legal."""
    text = token.strip().lower()
    for unit, factor in (("deg", 1.0), ("grad", 0.9), ("rad", 180.0 / math.pi),
                         ("turn", 360.0)):
        if text.endswith(unit):
            return float(text[: -len(unit)]) * factor
    return float(text)


def _num(token: str) -> float:
    """Number or percentage -> plain float (`63.7%` -> 0.637, `25.331` -> 25.331)."""
    token = token.strip().lower()
    if token.endswith("%"):
        return float(token[:-1]) / 100
    return float(token)


def parse_hex(value: str) -> tuple[int, int, int]:
    m = HEX_RE.match(value.strip())
    if not m:
        raise ValueError(f"not a hex color: {value!r}")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    h = h[:6]  # ignore alpha: contrast is measured against an opaque backdrop
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _encode(c: float) -> int:
    """Linear sRGB channel -> gamma-encoded 0-255."""
    c = min(1.0, max(0.0, c))
    s = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(s * 255)


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    h = (h % 360) / 360
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h * 6) % 2 - 1))
    m = l - c / 2
    sextant = int(h * 6) % 6
    rgb1 = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][sextant]
    return tuple(round((v + m) * 255) for v in rgb1)


def _oklab_to_rgb(L: float, a: float, b: float) -> tuple[int, int, int]:
    """OKLab (Björn Ottosson's matrices) -> gamma-encoded sRGB. Out-of-gamut
    chroma is clamped in linear light, which bends saturation before hue."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return _encode(r), _encode(g), _encode(bl)


def _parse_color_alpha(value: str) -> tuple[int, int, int, float]:
    """Like parse_color but also returns alpha in 0..1 when the syntax carries
    one (`oklch(1 0 0 / 10%)`, `rgba(...)`, 8-digit hex)."""
    v = value.strip()
    if HEX_RE.match(v):
        r, g, b = parse_hex(v)
        digits = v.lstrip("#")
        a = int(digits[6:], 16) / 255 if len(digits) == 8 else 1.0
        return (r, g, b, a)
    m = FUNC_RE.match(v)
    if not m:
        raise ValueError(f"unsupported color: {value!r}")
    name, inner = m.group(1).lower(), m.group(2)
    parts = inner.split("/")
    args = [a for a in re.split(r"[\s,]+", parts[0].strip()) if a]
    if not args:
        raise ValueError(f"empty color function: {value!r}")
    alpha = 1.0
    if len(parts) > 1 and parts[1].strip():
        raw = parts[1].strip()
        alpha = _num(raw) if raw.endswith("%") else float(raw)
    elif name in ("rgba", "hsla") and len(args) > 3:  # legacy comma syntax
        raw = args[3].strip()
        alpha = _num(raw) if raw.endswith("%") else float(raw)
    alpha = min(1.0, max(0.0, alpha))
    if name in ("rgb", "rgba"):
        vals = [(_num(a) * 255 if a.strip().endswith("%") else float(a)) for a in args[:3]]
        rgb = tuple(min(255, max(0, round(x))) for x in vals)
        return (rgb[0], rgb[1], rgb[2], alpha)  # type: ignore[return-value]
    if name in ("hsl", "hsla"):
        r, g, b = _hsl_to_rgb(_angle(args[0]), _num(args[1]), _num(args[2]))
        return (r, g, b, alpha)
    if name == "oklch":
        L, c = _num(args[0]), _num(args[1])
        h = math.radians(_angle(args[2])) if len(args) > 2 else 0.0
        r, g, b = _oklab_to_rgb(L, c * math.cos(h), c * math.sin(h))
        return (r, g, b, alpha)
    # oklab
    r, g, b = _oklab_to_rgb(_num(args[0]), _num(args[1]), _num(args[2]))
    return (r, g, b, alpha)


def parse_color(value: str) -> tuple[int, int, int]:
    """hex | rgb() | rgba() | hsl() | hsla() | oklch() | oklab() -> sRGB 0-255.
    Alpha, when present, is dropped here; ratio() composites it instead."""
    r, g, b, _ = _parse_color_alpha(value)
    return (r, g, b)


def luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    """Contrast of fg over bg. If fg carries alpha (`--border: oklch(1 0 0 / 10%)`,
    common in dark themes), it is composited over bg first — that is what actually
    renders. Alpha on bg is treated as opaque (its own backdrop is unknowable)."""
    fr, fgc, fb, fa = _parse_color_alpha(fg)
    br, bgc, bb, _ = _parse_color_alpha(bg)
    if fa < 1.0:
        fr, fgc, fb = (round(fr * fa + br * (1 - fa)),
                       round(fgc * fa + bgc * (1 - fa)),
                       round(fb * fa + bb * (1 - fa)))
    l1, l2 = luminance((fr, fgc, fb)), luminance((br, bgc, bb))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")


COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def _strip_css_comments(css: str) -> str:
    """Comments can hold braces and token names (`:root light + .dark`), which
    would otherwise leak into selectors and make --block match prose."""
    return COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), css)


def _scopes(css: str) -> list[tuple[str, dict[str, str]]]:
    """(selector, {name: value}) per block that holds at least one literal color,
    in document order. Nested blocks (@media …) match separately, which is how
    token sheets actually nest. Selector is normalized to its last token."""
    out: list[tuple[str, dict[str, str]]] = []
    for sel, body in BLOCK_RE.findall(_strip_css_comments(css)):
        vals: dict[str, str] = {}
        for name, value in VAR_RE.findall(body):
            value = value.strip()
            # Keep values we can resolve later: a literal, light-dark(a, b), or a
            # var() chain. Anything else (color-mix, calc) is not ours to guess.
            keep = value.lower().startswith("light-dark(") or "var(" in value
            if not keep:
                try:
                    parse_color(value)
                except ValueError:
                    continue
            vals[name] = value
        if vals:
            # Keep the whole selector: a block can list several
            # (`:root,\n[data-bs-theme=light] {`) and naming it after the last one
            # hides the others from --block.
            words = [w for w in sel.replace("\n", " ").split() if w]
            name = " ".join(words).strip().strip(",") or "?"
            # BLOCK_RE starts at the previous `}`, so an at-rule statement
            # (@charset "UTF-8"; @layer a, b;) lands in front of the selector.
            if ";" in name:
                name = name.rsplit(";", 1)[1].strip() or name
            out.append((name, vals))
    return out


VAR_REF = re.compile(r"var\(\s*--([\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


def _split_top(value: str) -> list[str]:
    """Split on top-level commas only — `light-dark(a, b)` args contain parens."""
    parts, depth, cur = [], 0, []
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [part.strip() for part in parts]


def expand_light_dark(tokens: dict[str, str]) -> list[tuple[str | None, dict[str, str]]]:
    """`light-dark(a, b)` tokens carry both themes in one declaration.

    Real sheets do this increasingly (Bootstrap 5.3's tokens are all
    light-dark() over var() indirection), so a checker that sees one value
    per token checks half a palette without saying so.
    """
    light, dark = {}, {}
    for name, value in tokens.items():
        text = value.strip()
        if text.lower().startswith("light-dark(") and text.endswith(")"):
            inner = text[len("light-dark("):-1]
            args = _split_top(inner)
            if len(args) == 2:
                light[name], dark[name] = args
                continue
        light[name] = value
        dark[name] = value
    if light == dark:
        return [(None, tokens)]
    return [("light", light), ("dark", dark)]


def resolve_tokens(tokens: dict[str, str], depth: int = 4) -> tuple[dict[str, str], set[str]]:
    """Replace var(--x) with the referenced value so two-layer sheets resolve.

    Returns the resolved map and the names that could not be resolved (missing
    reference without fallback, or a cycle). Those are reported, never silently
    treated as "no colour".
    """
    resolved: dict[str, str] = {}
    unresolved: set[str] = set()

    def expand(value: str, seen: tuple[str, ...], level: int) -> str | None:
        if level > depth:
            return None
        def sub(match: re.Match[str]) -> str:
            ref, fallback = match.group(1), match.group(2)
            if ref in seen:
                raise _Cycle()
            if ref in tokens:
                inner = expand(tokens[ref], seen + (ref,), level + 1)
                if inner is None:
                    raise _Cycle()
                return inner
            if fallback is not None and fallback.strip():
                return fallback.strip()
            raise _Cycle()
        try:
            return VAR_REF.sub(sub, value)
        except _Cycle:
            return None

    for name, value in tokens.items():
        out = expand(value, (name,), 0)
        if out is None:
            unresolved.add(name)
        else:
            resolved[name] = out
    return resolved, unresolved


class _Cycle(Exception):
    pass


def _rgb_to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_linearize(c / 255.0) for c in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _linearize(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _oklab_to_oklch(L: float, a: float, b: float) -> tuple[float, float, float]:
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)


def _oklch_to_oklab(L: float, C: float, h_deg: float) -> tuple[float, float, float]:
    h = math.radians(h_deg)
    return (L, C * math.cos(h), C * math.sin(h))


MIX_SPLIT = re.compile(r"^\s*color-mix\(\s*in\s+([a-z0-9-]+)\s*,(.*)\)\s*$", re.S | re.I)
MIX_PERCENT = re.compile(r"^(.*?)(?:\s+([\d.]+)%)?$", re.S)


def evaluate_color(value: str, tokens: dict[str, str], depth: int = 6) -> tuple[int, int, int] | None:
    """Resolve a token value to sRGB: literals, var() chains, and color-mix().

    Bootstrap's whole palette is `color-mix(in oklch, var(--bs-white) 94%,
    oklch(...))`, so a checker that only reads literals sees none of it.
    """
    if depth <= 0:
        return None
    try:
        text = VAR_REF.sub(lambda m: _resolve_ref(m, tokens, depth), value.strip())
    except (_Unresolvable, ValueError):
        return None
    try:
        return parse_color(text)[:3]
    except ValueError:
        pass
    match = MIX_SPLIT.match(text)
    if not match:
        return None
    space = match.group(1).lower()
    parts = _split_top(match.group(2))
    if len(parts) != 2:
        return None
    colors, weights = [], []
    for part in parts:
        color_text, weight = MIX_PERCENT.match(part.strip()).groups()
        rgb = evaluate_color(color_text, tokens, depth - 1)
        if rgb is None:
            return None
        colors.append(rgb)
        weights.append(float(weight) if weight else None)
    if weights[0] is None and weights[1] is None:
        weights = [50.0, 50.0]
    elif weights[0] is None:
        weights = [100.0 - weights[1], weights[1]]
    elif weights[1] is None:
        weights = [weights[0], 100.0 - weights[0]]
    total = (weights[0] + weights[1]) or 1.0
    t = weights[1] / total
    if space in ("oklch", "oklab"):
        lab_a = _rgb_to_oklab(colors[0])
        lab_b = _rgb_to_oklab(colors[1])
        if space == "oklch":
            La, Ca, Ha = _oklab_to_oklch(*lab_a)
            Lb, Cb, Hb = _oklab_to_oklch(*lab_b)
            delta = (Hb - Ha + 540) % 360 - 180
            mixed = _oklch_to_oklab(La + (Lb - La) * t, Ca + (Cb - Ca) * t, Ha + delta * t)
        else:
            mixed = tuple(a + (b - a) * t for a, b in zip(lab_a, lab_b))
        return _oklab_to_rgb(*mixed)
    mixed = tuple(round(a + (b - a) * t) for a, b in zip(colors[0], colors[1]))
    return mixed  # type: ignore[return-value]


def _resolve_ref(match: re.Match[str], tokens: dict[str, str], depth: int) -> str:
    ref, fallback = match.group(1), match.group(2)
    if ref in tokens:
        return tokens[ref]
    if fallback is not None and fallback.strip():
        return fallback.strip()
    raise _Unresolvable(ref)


class _Unresolvable(Exception):
    pass


COLORISH_NAME = re.compile(
    r"(^|[-_])(color|colours?|bg|background|fg|foreground|text|border|contrast|"
    r"accent|primary|secondary|muted|surface|line|fill|stroke)([-_]|$)", re.I)
COLORISH_VALUE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\b(rgb|rgba|hsl|hsla|oklch|oklab|color-mix|light-dark)\(",
    re.I)


NON_COLOR_NAME = re.compile(
    r"(shadow|gradient|blur|font|spacing|radius|z-?index|opacity|duration|"
    r"timing|transform|ease|transition|animation|size|width|height)", re.I)


def _looks_like_color(name: str, value: str) -> bool:
    """Only report tokens that were plausibly meant to be colours.

    A Bootstrap sheet has 832 tokens; most are box-shadows, font stacks and
    timings (a shadow value even contains rgb(), which is why matching on the
    value alone is not enough). Listing those as "not checked" buries the gaps
    that matter.
    """
    if NON_COLOR_NAME.search(name):
        return False
    if COLORISH_NAME.search(name):
        return True
    try:
        parse_color((value or "").strip())
        return True
    except ValueError:
        return False


def rows_for(tokens: dict[str, str], prefix: str = "",
             pool: dict[str, str] | None = None) -> tuple[
        list[tuple[str, str, str, float]], list[str]]:
    """Resolve var() indirection, split light-dark(), and build checkable rows.

    Anything that still cannot be resolved is returned as a label so the caller
    can report it — a token the tool could not read must not look like a pass.
    """
    skipped: list[str] = []
    per_variant: list[tuple[str | None, list[tuple[str, tuple[int, int, int],
                                                     tuple[int, int, int], float]]]] = []
    for variant, values in expand_light_dark(tokens):
        # The cascade: a utility block's var() may point at :root's token, so
        # resolve against the whole sheet but only derive pairs in this block.
        scope = dict(pool or {})
        scope.update(values)
        resolved, unresolved = resolve_tokens(scope)
        block = {name: resolved.get(name, value) for name, value in values.items()}
        unresolved = {name for name in unresolved if name in values}
        produced = []
        for label, fg, bg, threshold in pairs_from_tokens(block):
            fg_rgb = evaluate_color(fg, resolved)
            bg_rgb = evaluate_color(bg, resolved)
            if fg_rgb is None or bg_rgb is None:
                skipped.append(f"{variant + ': ' if variant else ''}{prefix}{label}")
                continue
            produced.append((label, fg_rgb, bg_rgb, threshold))
        skipped += [f"{prefix}--{name}" for name in sorted(unresolved)
                    if _looks_like_color(name, values.get(name, ""))]
        per_variant.append((variant, produced))

    if len(per_variant) == 1 or per_variant[0][0] is None:
        single = per_variant[0][1]
        return [(f"{prefix}{label}", fg, bg, thr) for label, fg, bg, thr in single], skipped

    # Only label a row with its theme when the two themes actually disagree —
    # a sheet where one token uses light-dark() does not make @media-independent
    # pairs differ, and printing them twice invents findings.
    light_rows = {label: (fg, bg, thr) for label, fg, bg, thr in per_variant[0][1]}
    dark_rows = {label: (fg, bg, thr) for label, fg, bg, thr in per_variant[1][1]}
    rows: list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]] = []
    for label, (fg, bg, thr) in light_rows.items():
        if label in dark_rows and dark_rows[label] == (fg, bg, thr):
            rows.append((f"{prefix}{label}", fg, bg, thr))
        else:
            rows.append((f"{prefix}light: {label}", fg, bg, thr))
    for label, (fg, bg, thr) in dark_rows.items():
        if label in light_rows and light_rows[label] == (fg, bg, thr):
            continue
        rows.append((f"{prefix}dark: {label}", fg, bg, thr))
    return rows, skipped


def read_tokens(css: str, block: str | None = None) -> dict[str, str]:
    """Collect `--name: <color>` declarations into one flat dict.

    Real sheets define the same names in several scopes (`:root` plus `.dark`).
    Flat last-wins reading silently takes the dark values — or worse, mixes a
    light fg with a dark bg on sheets that only override some vars — so that is
    an error unless `--block` picks a scope. `block` is a case-insensitive
    substring matched against block selectors (".dark", ":root", "html.dark").
    Values that are not literal colors (var(), color-mix(), calc()) are skipped.
    """
    scopes = _scopes(css)
    if block is not None:
        needle = block.lower()
        scopes = [s for s in scopes if needle in s[0].lower()]
        if not scopes:
            raise ValueError(f"no block matching --block {block!r}")
    if block is None:
        owners: dict[str, set[str]] = {}
        for sel, vals in scopes:
            for name in vals:
                owners.setdefault(name, set()).add(sel)
        multi = sorted((n, sorted(s)) for n, s in owners.items() if len(s) > 1)
        if multi:
            shown = ", ".join(f"{n} ({' / '.join(s)})" for n, s in multi[:6])
            more = "" if len(multi) <= 6 else f" … +{len(multi) - 6} more"
            raise ValueError(
                "same tokens defined in multiple blocks — flat reading would mix "
                f"scopes: {shown}{more}. Pass --block :root or --block .dark, or "
                "split the sheet into one scope per file.")
    tokens: dict[str, str] = {}
    for _sel, vals in scopes:
        tokens.update(vals)
    return tokens


def pairs_from_tokens(tokens: dict[str, str]) -> list[tuple[str, str, str, float]]:
    """Return (label, fg, bg, threshold) tuples for the pairs the skill promises.

    Two conventions are honored because both are everywhere in the wild:
    - ours (§4): `--<role>` is a surface, `--<role>-contrast` / `--on-<role>` is
      the text that sits on it;
    - shadcn's (the most-copied token sheet on the internet): `--background` /
      `--foreground` and `--<role>-foreground` for the text on each surface.
    Anything following either naming gets checked automatically, which is the
    point: the naming convention becomes a test.
    """
    out: list[tuple[str, str, str, float]] = []
    if "text" in tokens and "bg" in tokens:
        out.append(("text on bg", tokens["text"], tokens["bg"], WCAG_TEXT))
    if "muted" in tokens and "bg" in tokens:
        out.append(("muted on bg", tokens["muted"], tokens["bg"], WCAG_TEXT))
    if "text" in tokens and "surface" in tokens:
        out.append(("text on surface", tokens["text"], tokens["surface"], WCAG_TEXT))
    if "foreground" in tokens and "background" in tokens:
        out.append(("foreground on background",
                    tokens["foreground"], tokens["background"], WCAG_TEXT))
    for name, fg in tokens.items():
        if name.endswith("-contrast"):
            base = name[: -len("-contrast")]
            if base in tokens:
                out.append((f"{name} on {base}", fg, tokens[base], WCAG_TEXT))
        if name.endswith("-foreground") and name != "foreground":
            base = name[: -len("-foreground")]
            if base in tokens:
                out.append((f"{name} on {base}", fg, tokens[base], WCAG_TEXT))
        if name.startswith("on-"):
            base = name[len("on-"):]
            if base in tokens:
                out.append((f"on-{base} over {base}", tokens[name], tokens[base], WCAG_TEXT))
    # Bootstrap's shape is `--<role>-bg` (the fill) plus `--<role>-contrast` (the
    # text meant to sit on it). Only that pair is safe to infer: measured on
    # Bootstrap itself, `--<role>-fg` is a foreground used on the PAGE surface
    # (`.fg-warning { color: var(--bs-warning-fg) }`), so pairing it with
    # `--<role>-bg` reported 36 unreadable combinations that do not exist.
    for name, fg in tokens.items():
        if name.endswith("-contrast"):
            base = name[: -len("-contrast")]
            if f"{base}-bg" in tokens and base not in tokens:
                out.append((f"{name} on {base}-bg", fg, tokens[f"{base}-bg"], WCAG_TEXT))
    # Focus rings identify a state, so 1.4.11 applies without the border
    # ambiguity: shadcn's own default ring (oklch(0.708 0 0)) sits at ~2.1:1 on
    # white, and nothing else in the sheet would ever report that.
    for name in ("ring", "focus-ring", "focus"):
        if name in tokens and "bg" in tokens:
            out.append((f"{name} on bg", tokens[name], tokens["bg"], WCAG_UI))
        if name in tokens and "background" in tokens and "bg" not in tokens:
            out.append((f"{name} on background", tokens[name], tokens["background"], WCAG_UI))
    if "border" in tokens and "bg" in tokens:
        out.append(("border on bg", tokens["border"], tokens["bg"], WCAG_UI))
    if "border" in tokens and "background" in tokens and "bg" not in tokens:
        out.append(("border on background",
                    tokens["border"], tokens["background"], WCAG_UI))
    return out


def parse_pair(spec: str) -> tuple[str, str, str]:
    """`text:#111827/bg:#ffffff` or `text:#111827 on bg:#ffffff` -> (label, fg, bg)."""
    text = spec.strip()
    on = re.split(r"\s+on\s+", text)
    if len(on) == 2:
        left, right = on
    elif "/" in text:
        left, right = text.split("/", 1)
    else:
        raise ValueError(f"pair needs '<fg> on <bg>' or '<fg>/<bg>': {spec!r}")

    def split(side: str) -> tuple[str, str]:
        if ":" not in side:
            raise ValueError(f"pair side needs '<role>:<color>': {side!r}")
        label, _, color = side.partition(":")
        return label.strip(), color.strip()

    lf, fg = split(left)
    lb, bg = split(right)
    return f"{lf} on {lb}", fg, bg


def ratio_rgb(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def hexstr(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


# A `border` token is a control outline in some sheets (shadcn draws inputs
# with it) and a divider in others (the blog's card rules sit at 1.39:1 on
# purpose). Static analysis cannot tell them apart, and WCAG 1.4.11 only asks
# 3:1 of the ones that identify a component — so border rows are reported and
# never fail the run.
ADVISORY_ROW = re.compile(r"\bborder on \b")


def render(rows: list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]]
           ) -> tuple[str, int, int]:
    lines, failures, advisories = [], 0, 0
    width = max((len(r[0]) for r in rows), default=0)
    for label, fg, bg, minimum in rows:
        value = ratio_rgb(fg, bg)
        ok = value >= minimum
        advisory = bool(ADVISORY_ROW.search(label))
        if not ok:
            if advisory:
                advisories += 1
            else:
                failures += 1
        if ok:
            mark = "PASS"
        elif advisory:
            mark = f"ADVISORY (control outlines need {minimum:g}:1)"
        else:
            mark = f"FAIL (needs {minimum:g}:1)"
        lines.append(f"{label:<{width}}  {hexstr(fg)} on {hexstr(bg)}  {value:5.2f}:1  {mark}")
    return "\n".join(lines), failures, advisories


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="WCAG contrast ratios for a palette")
    p.add_argument("--fg", help="foreground color (hex, rgb(), hsl(), oklch())")
    p.add_argument("--bg", help="background color")
    p.add_argument("--pair", action="append", default=[], metavar="'role:#hex on role:#hex'")
    p.add_argument("--css", action="append", default=[], metavar="FILE",
                   help="token sheet to read custom properties from")
    p.add_argument("--block", metavar="SELECTOR",
                   help="when the sheet defines tokens in several blocks "
                        "(:root plus .dark), pick one by selector substring")
    p.add_argument("--all-blocks", action="store_true",
                   help="check every block that declares tokens (:root and .dark in "
                        "turn) instead of refusing an ambiguous sheet")
    p.add_argument("--min", type=float, default=WCAG_TEXT,
                   help=f"threshold for --fg/--bg and --pair (default {WCAG_TEXT})")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    rows: list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]] = []
    skipped_rows: list[str] = []
    tokens: dict[str, str] = {}
    try:
        if args.fg and args.bg:
            rows.append(("custom pair", parse_color(args.fg), parse_color(args.bg), args.min))
        for spec in args.pair:
            label, fg, bg = parse_pair(spec)
            rows.append((label, parse_color(fg), parse_color(bg), args.min))
        if args.all_blocks and args.block:
            print("error: --all-blocks checks every block; drop --block", file=sys.stderr)
            return 2
        for path in args.css:
            css_text = Path(path).expanduser().read_text(encoding="utf-8")
            if args.all_blocks:
                merged: dict[str, dict[str, str]] = {}
                for selector, scope in _scopes(css_text):
                    merged.setdefault(selector, {}).update(scope)
                if not merged:
                    print(f"{path}: no literal color declarations found "
                          f"(hex, rgb(), hsl(), oklch())", file=sys.stderr)
                    return 1
                empty_blocks: list[str] = []
                pool: dict[str, str] = {}
                for scope in merged.values():
                    pool.update(scope)
                for selector, scope in merged.items():
                    block_rows, skipped = rows_for(scope, prefix=f"{selector} ", pool=pool)
                    skipped_rows += skipped
                    if not block_rows:
                        empty_blocks.append(selector)
                        continue
                    rows += block_rows
                if empty_blocks:
                    shown = ", ".join(empty_blocks[:3])
                    more = "" if len(empty_blocks) <= 3 else f" … +{len(empty_blocks) - 3}"
                    print(f"{path}: {len(empty_blocks)} block(s) declare colours but no "
                          f"pair follows the naming conventions: {shown}{more}",
                          file=sys.stderr)
            else:
                tokens = read_tokens(css_text, args.block)
                if not tokens:
                    print(f"{path}: no literal color declarations found "
                          f"(hex, rgb(), hsl(), oklch())", file=sys.stderr)
                    return 1
                file_rows, skipped = rows_for(tokens)
                skipped_rows += skipped
                rows += file_rows
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not rows:
        if args.css:
            print("error: sheet parsed but no checkable pairs — it has colors but none "
                  "follow the --<role> / --<role>-contrast convention, and there is no "
                  "text/bg/muted/border to fall back on. Pass --pair explicitly.\n"
                  "roles seen: " + ", ".join(sorted(tokens)[:12]), file=sys.stderr)
            p.exit(2)
        p.error("nothing to check: pass --fg/--bg, --pair, or --css")

    if skipped_rows:
        shown = ", ".join(skipped_rows[:5])
        more = "" if len(skipped_rows) <= 5 else f" … +{len(skipped_rows) - 5} more"
        print(f"note: {len(skipped_rows)} token(s) not checked (unresolvable value): "
              f"{shown}{more}", file=sys.stderr)

    # `--css tokens.css --css brand.css` is normal: a palette is often split
    # across files, and both halves redeclare "text"/"bg" so the subpage works
    # standalone. Printing the identical pair twice made a 4-row check look like
    # a 7-row one; keep the first occurrence.
    seen_rows: set[tuple[str, tuple[int, int, int], tuple[int, int, int], float]] = set()
    unique_rows = []
    for row in rows:
        if row in seen_rows:
            continue
        seen_rows.add(row)
        unique_rows.append(row)
    rows = unique_rows

    out, failures, advisories = render(rows)
    print(out)
    if not args.quiet:
        if failures:
            verdict = f"{failures} pair(s) below threshold"
        elif advisories:
            verdict = ("all text pairs pass — " if any(not ADVISORY_ROW.search(r[0]) for r in rows)
                       else "") + (
                f"{advisories} border row(s) below 3:1, advisory: only control outlines "
                f"and focus rings must reach it")
        else:
            verdict = "all pairs pass"
        print(f"\n{verdict}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

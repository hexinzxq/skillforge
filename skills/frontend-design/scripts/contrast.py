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
        r, g, b = _hsl_to_rgb(_num(args[0]), _num(args[1]), _num(args[2]))
        return (r, g, b, alpha)
    if name == "oklch":
        L, c = _num(args[0]), _num(args[1])
        h = math.radians(_num(args[2])) if len(args) > 2 else 0.0
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


def _scopes(css: str) -> list[tuple[str, dict[str, str]]]:
    """(selector, {name: value}) per block that holds at least one literal color,
    in document order. Nested blocks (@media …) match separately, which is how
    token sheets actually nest. Selector is normalized to its last token."""
    out: list[tuple[str, dict[str, str]]] = []
    for sel, body in BLOCK_RE.findall(css):
        vals: dict[str, str] = {}
        for name, value in VAR_RE.findall(body):
            value = value.strip()
            try:
                parse_color(value)
            except ValueError:
                continue
            vals[name] = value
        if vals:
            words = sel.split()
            out.append((words[-1] if words else "?", vals))
    return out


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


def render(rows: list[tuple[str, str, str, float]]) -> tuple[str, int]:
    lines, failures = [], 0
    width = max((len(r[0]) for r in rows), default=0)
    for label, fg, bg, minimum in rows:
        value = ratio(fg, bg)
        ok = value >= minimum
        failures += 0 if ok else 1
        mark = "PASS" if ok else f"FAIL (needs {minimum:g}:1)"
        lines.append(f"{label:<{width}}  {fg} on {bg}  {value:5.2f}:1  {mark}")
    return "\n".join(lines), failures


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

    rows: list[tuple[str, str, str, float]] = []
    tokens: dict[str, str] = {}
    try:
        if args.fg and args.bg:
            parse_color(args.fg), parse_color(args.bg)
            rows.append(("custom pair", args.fg, args.bg, args.min))
        for spec in args.pair:
            label, fg, bg = parse_pair(spec)
            parse_color(fg), parse_color(bg)
            rows.append((label, fg, bg, args.min))
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
                for selector, scope in merged.items():
                    tokens = scope
                    pairs = pairs_from_tokens(scope)
                    if not pairs:
                        print(f"{path}: block {selector} has colors but no pairs from "
                              f"the naming conventions", file=sys.stderr)
                        continue
                    rows += [(f"{selector} {label}", fg, bg, thr)
                             for label, fg, bg, thr in pairs]
            else:
                tokens = read_tokens(css_text, args.block)
                if not tokens:
                    print(f"{path}: no literal color declarations found "
                          f"(hex, rgb(), hsl(), oklch())", file=sys.stderr)
                    return 1
                rows += pairs_from_tokens(tokens)
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

    out, failures = render(rows)
    print(out)
    if not args.quiet:
        verdict = "all pairs pass" if not failures else f"{failures} pair(s) below threshold"
        print(f"\n{verdict}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

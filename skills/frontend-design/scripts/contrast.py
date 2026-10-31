#!/usr/bin/env python3
"""WCAG contrast checker for the frontend-design skill — stdlib only.

Why this exists: the skill used to tell the model to compute (L1+0.05)/(L2+0.05)
by hand. Models get relative luminance wrong on hex colors, quietly, and the
palette ships failing 4.5:1. Arithmetic belongs in a script.

    # one pair
    python3 scripts/contrast.py --fg "#111827" --bg "#ffffff"

    # every pair implied by a token sheet (--text/--bg, --muted/--bg,
    # --text/--surface and every --<role>-contrast against --<role>)
    python3 scripts/contrast.py --css tokens.css

    # explicit pairs
    python3 scripts/contrast.py --pair "text:#111827 on bg:#ffffff" --min 4.5

Exit status is 1 when any pair misses the threshold, so CI can gate on it.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
VAR_RE = re.compile(r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);")
WCAG_TEXT, WCAG_LARGE, WCAG_UI = 4.5, 3.0, 3.0


def parse_hex(value: str) -> tuple[int, int, int]:
    m = HEX_RE.match(value.strip())
    if not m:
        raise ValueError(f"not a hex color: {value!r}")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    h = h[:6]  # ignore alpha: contrast is measured against an opaque backdrop
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    l1, l2 = luminance(parse_hex(fg)), luminance(parse_hex(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def read_tokens(css: str) -> dict[str, str]:
    """Collect `--name: #hex` declarations; last one wins, like the cascade."""
    tokens: dict[str, str] = {}
    for name, value in VAR_RE.findall(css):
        value = value.strip().split()[0] if value.strip() else ""
        if HEX_RE.match(value):
            tokens[name] = value
    return tokens


def pairs_from_tokens(tokens: dict[str, str]) -> list[tuple[str, str, str, float]]:
    """Return (label, fg, bg, threshold) tuples for the pairs the skill promises.

    Convention from the skill's §4: `--<role>` is a surface and `--<role>-contrast`
    is the text that sits on it. Anything following that naming gets checked
    automatically, which is the point: the naming convention becomes a test.
    """
    out: list[tuple[str, str, str, float]] = []
    if "text" in tokens and "bg" in tokens:
        out.append(("text on bg", tokens["text"], tokens["bg"], WCAG_TEXT))
    if "muted" in tokens and "bg" in tokens:
        out.append(("muted on bg", tokens["muted"], tokens["bg"], WCAG_TEXT))
    if "text" in tokens and "surface" in tokens:
        out.append(("text on surface", tokens["text"], tokens["surface"], WCAG_TEXT))
    for name, fg in tokens.items():
        if name.endswith("-contrast"):
            base = name[: -len("-contrast")]
            if base in tokens:
                out.append((f"{name} on {base}", fg, tokens[base], WCAG_TEXT))
        if name.startswith("on-"):
            base = name[len("on-"):]
            if base in tokens:
                out.append((f"on-{base} over {base}", tokens[name], tokens[base], WCAG_TEXT))
    if "border" in tokens and "bg" in tokens:
        out.append(("border on bg", tokens["border"], tokens["bg"], WCAG_UI))
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
            raise ValueError(f"pair side needs '<role>:<hex>': {side!r}")
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
    p.add_argument("--fg", help="foreground hex")
    p.add_argument("--bg", help="background hex")
    p.add_argument("--pair", action="append", default=[], metavar="'role:#hex on role:#hex'")
    p.add_argument("--css", action="append", default=[], metavar="FILE",
                   help="token sheet to read custom properties from")
    p.add_argument("--min", type=float, default=WCAG_TEXT,
                   help=f"threshold for --fg/--bg and --pair (default {WCAG_TEXT})")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    rows: list[tuple[str, str, str, float]] = []
    try:
        if args.fg and args.bg:
            rows.append(("custom pair", args.fg, args.bg, args.min))
        for spec in args.pair:
            label, fg, bg = parse_pair(spec)
            rows.append((label, fg, bg, args.min))
        for path in args.css:
            css_text = Path(path).expanduser().read_text(encoding="utf-8")
            tokens = read_tokens(css_text)
            if not tokens:
                print(f"{path}: no --custom-property: #hex declarations found", file=sys.stderr)
                return 1
            rows += pairs_from_tokens(tokens)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not rows:
        p.error("nothing to check: pass --fg/--bg, --pair, or --css")

    out, failures = render(rows)
    print(out)
    if not args.quiet:
        verdict = "all pairs pass" if not failures else f"{failures} pair(s) below threshold"
        print(f"\n{verdict}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

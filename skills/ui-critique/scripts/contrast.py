#!/usr/bin/env python3
"""WCAG contrast ratios for hex color pairs, no dependencies.

Usage:
    python3 contrast.py TEXT BG [TEXT BG ...]
    python3 contrast.py --check 4.5 "#94a3b8" "#1e293b"

Prints the ratio for each pair and marks pass/fail against the threshold
(4.5 for body text by default, 3.0 for large text / UI borders).
Exit code is 1 if any pair fails, so it can gate a CI check.
"""

from __future__ import annotations

import argparse
import sys


def parse_hex(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise SystemExit(f"not a hex color: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _channel(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = luminance(a), luminance(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="WCAG contrast ratio checker")
    p.add_argument("--check", type=float, default=4.5,
                   help="fail threshold (default 4.5; use 3.0 for large text)")
    p.add_argument("colors", nargs="+", help="pairs of TEXT BG hex colors")
    args = p.parse_args(argv)

    if len(args.colors) % 2:
        p.error("colors must come in pairs (text, background)")
    failed = 0
    for i in range(0, len(args.colors), 2):
        fg, bg = args.colors[i], args.colors[i + 1]
        r = ratio(parse_hex(fg), parse_hex(bg))
        ok = r >= args.check
        failed += 0 if ok else 1
        print(f"{fg:>9} on {bg:<9} {r:5.2f}:1  "
              f"{'pass' if ok else 'FAIL'} (need {args.check:g})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

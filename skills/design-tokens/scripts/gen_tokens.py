#!/usr/bin/env python3
"""Generate a semantic design-token set from one brand color.

OKLCH-based: the ramp keeps a constant perceived hue and tapers chroma at the
gamut edges, which is why the steps stay in family when a HSL ramp goes muddy.
No third-party packages.

    python3 gen_tokens.py --brand "#3b82f6" --out ./tokens
    python3 gen_tokens.py --brand "#e11d48" --print

Writes tokens.css and tokens.json, prints the contrast table, and exits 1 if a
text/background pair falls below its threshold (4.5 for text, 3.0 for borders).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# ---------------------------------------------------------------- color math


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise SystemExit(f"not a hex color: {value!r}")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    out = []
    for c in rgb:
        v = max(0.0, min(1.0, c))
        out.append(round(_lin_to_srgb(v) * 255))
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in out)


def _srgb_to_lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin_to_srgb(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def rgb_to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_lin(c / 255) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linrgb(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklch(lch: tuple[float, float, float]) -> tuple[float, float, float]:
    """OKLCH -> linear sRGB, clipping chroma until in gamut."""
    L, C, H = lch
    rad = math.radians(H)
    lo, hi = 0.0, C
    lab = (L, C * math.cos(rad), C * math.sin(rad))
    rgb = oklab_to_linrgb(lab)
    if all(-1e-4 <= c <= 1 + 1e-4 for c in rgb):
        return rgb
    for _ in range(24):  # bisect chroma down into gamut
        mid = (lo + hi) / 2
        lab = (L, mid * math.cos(rad), mid * math.sin(rad))
        rgb = oklab_to_linrgb(lab)
        if all(-1e-4 <= c <= 1 + 1e-4 for c in rgb):
            lo = mid
        else:
            hi = mid
    return oklab_to_linrgb((L, lo * math.cos(rad), lo * math.sin(rad)))


def lch_hex(L: float, C: float, H: float) -> str:
    return rgb_to_hex(oklch((L, C, H)))


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_lin(c / 255) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(hex_to_rgb(a)), luminance(hex_to_rgb(b))
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


# ------------------------------------------------------------------- palette

STATUS_HUE = {"success": 150.0, "warning": 85.0, "danger": 25.0}


def build(brand: str, neutral_chroma: float | None = None) -> dict:
    L0, a0, b0 = rgb_to_oklab(hex_to_rgb(brand))
    hue = math.degrees(math.atan2(b0, a0)) % 360
    chroma = math.hypot(a0, b0)
    nc = neutral_chroma if neutral_chroma is not None else min(0.016, max(0.004, chroma * 0.12))

    accent_light = min(max(L0, 0.46), 0.74)
    accent_dark = max(L0, 0.70)
    acc = lch_hex(accent_light, max(chroma, 0.06), hue)
    acc_dark = lch_hex(accent_dark, max(chroma * 0.9, 0.06), hue)

    def on(background: str) -> str:
        white, ink = "#ffffff", lch_hex(0.18, nc, hue)
        return white if contrast(white, background) >= contrast(ink, background) else ink

    light = {
        "bg": lch_hex(0.985, nc * 0.6, hue),
        "surface-1": lch_hex(0.965, nc * 0.8, hue),
        "surface-2": lch_hex(0.935, nc, hue),
        "border": lch_hex(0.89, nc, hue),
        "border-strong": lch_hex(0.62, nc, hue),
        "text": lch_hex(0.22, nc * 1.5, hue),
        "text-muted": lch_hex(0.48, nc * 1.2, hue),
        "text-disabled": lch_hex(0.68, nc, hue),
        "accent": acc,
        "accent-hover": lch_hex(max(accent_light - 0.07, 0.30), max(chroma, 0.06), hue),
        "accent-contrast": on(acc),
    }
    dark = {
        "bg": lch_hex(0.17, nc * 1.2, hue),
        "surface-1": lch_hex(0.215, nc * 1.2, hue),
        "surface-2": lch_hex(0.26, nc * 1.1, hue),
        "border": lch_hex(0.33, nc, hue),
        "border-strong": lch_hex(0.56, nc, hue),
        "text": lch_hex(0.94, nc * 0.6, hue),
        "text-muted": lch_hex(0.70, nc, hue),
        "text-disabled": lch_hex(0.50, nc, hue),
        "accent": acc_dark,
        "accent-hover": lch_hex(min(accent_dark + 0.07, 0.95), max(chroma * 0.9, 0.06), hue),
        "accent-contrast": on(acc_dark),
    }
    for theme, lv in (("light", 0.50), ("dark", 0.72)):
        target = light if theme == "light" else dark
        for name, h in STATUS_HUE.items():
            target[name] = lch_hex(lv, 0.13, h)
            target[f"on-{name}"] = on(target[name])
    return {"light": light, "dark": dark, "meta": {"brand": brand, "hue": round(hue, 1),
                                                  "chroma": round(chroma, 4)}}


PAIRS = [
    ("text", "bg", 4.5), ("text", "surface-1", 4.5), ("text", "surface-2", 4.5),
    ("text-muted", "bg", 4.5), ("text-muted", "surface-1", 4.5),
    ("accent-contrast", "accent", 4.5),
    ("border-strong", "surface-1", 3.0),
]


def css(tokens: dict) -> str:
    def block(sel: str, vals: dict, title: str) -> list[str]:
        lines = [f"/* {title} */", f"{sel} {{"]
        for k, v in vals.items():
            if k.startswith("on-"):
                continue
            lines.append(f"  --color-{k}: {v};")
            if k in STATUS_HUE:
                lines.append(f"  --color-on-{k}: {vals[f'on-{k}']};")
        lines.append("}")
        return lines

    out = ["/* generated by skills/design-tokens/scripts/gen_tokens.py — edit the generator, not this file */"]
    out += block(":root", tokens["light"], "light")
    out += [""]
    out += block('[data-theme="dark"]', tokens["dark"], "dark")
    return "\n".join(out) + "\n"


def report(tokens: dict) -> int:
    failures = 0
    for theme in ("light", "dark"):
        print(f"\n{theme}:")
        vals = tokens[theme]
        for fg, bg, need in PAIRS:
            r = contrast(vals[fg], vals[bg])
            ok = r >= need
            failures += 0 if ok else 1
            print(f"  {fg:>16} on {bg:<14} {r:5.2f}:1  {'pass' if ok else 'FAIL'} (need {need})"
                  if ok else
                  f"  {fg:>16} on {bg:<14} {r:5.2f}:1  FAIL (need {need})")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="generate OKLCH semantic design tokens")
    p.add_argument("--brand", required=True, help="brand hex color, e.g. #3b82f6")
    p.add_argument("--out", help="directory for tokens.css / tokens.json")
    p.add_argument("--neutral-chroma", type=float, default=None,
                   help="chroma for neutrals (default derived from brand, 0.004-0.016)")
    p.add_argument("--print", dest="to_stdout", action="store_true", help="print CSS only")
    args = p.parse_args(argv)

    tokens = build(args.brand, args.neutral_chroma)
    code = report(tokens)
    text = css(tokens)
    if args.to_stdout or not args.out:
        print("\n" + text)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "tokens.css").write_text(text)
        (out / "tokens.json").write_text(json.dumps(tokens, indent=2) + "\n")
        print(f"\nwrote {out/'tokens.css'} and {out/'tokens.json'}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

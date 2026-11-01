#!/usr/bin/env python3
"""Scan shipped HTML/CSS for the mechanical tells this skill promises to avoid.

The prose in SKILL.md is for choices that need judgement. This script only
does what a scanner can do reliably, so "we avoid AI slop" becomes checkable
instead of aspirational. Two severities:

  FAIL  mechanically broken or measurably wrong (exit 1)
  TELL  the default a model falls into — waivable with a reason on the record
        (exit 0 unless --strict)

Usage:
  python3 scripts/sloplint.py page.html styles.css [--strict] [--quiet]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR = re.compile(r'\sstyle="([^"]*)"', re.I)
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
COLOR_LITERAL = re.compile(
    r"(#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\([^)]*\))"
)
THEME_SELECTOR = re.compile(r":root|\[data-theme", re.I)
# Animating any of these makes the browser re-layout every frame. Matching is
# on the whole property name: `border-left-color` paints, it does not reflow,
# and a substring match on `left` reported it as layout (found on a real blog).
LAYOUT_PROP = re.compile(
    r"(?:width|height|min-width|max-width|min-height|max-height|top|right|bottom|left"
    r"|inset(?:-\w+)?|margin(?:-\w+)?|padding(?:-\w+)?"
    r"|font-size|line-height|border-\w+-width|border-width)", re.I
)
TRANSITION_DECL = re.compile(
    r"(?:^|;)\s*(transition|animation)\s*:\s*([^;]+)", re.I
)


class Finding:
    def __init__(self, path: str, line: int, severity: str, rule: str, message: str):
        self.path = path
        self.line = line
        self.severity = severity
        self.rule = rule
        self.message = message

    def render(self) -> str:
        return f"{self.path}:{self.line}  {self.severity:4s}  {self.rule}  {self.message}"


def _line_at(text: str, pos: int, base_line: int) -> int:
    return base_line + text.count("\n", 0, pos)


def _regions(path: Path, text: str) -> list[tuple[int, str]]:
    """CSS text regions with their 1-based starting line."""
    if path.suffix.lower() in (".css",):
        return [(1, text)]
    regions = []
    for match in STYLE_BLOCK.finditer(text):
        regions.append((_line_at(text, match.start(1), 1), match.group(1)))
    for match in STYLE_ATTR.finditer(text):
        regions.append((_line_at(text, match.start(1), 1), match.group(1)))
    return regions


def _transition_target(part: str) -> str:
    """First token that isn't a time — the animated property, or "" if none."""
    for token in part.strip().lower().split():
        if re.fullmatch(r"[\d.]+m?s", token):
            continue
        return token
    return ""


def check_css(path: Path, line: int, css: str, focus_kind: str) -> list[Finding]:
    out: list[Finding] = []
    for rule in CSS_RULE.finditer(css):
        selector = " ".join(rule.group(1).split())
        body = rule.group(2)
        body_line = _line_at(css, rule.start(2), line)
        theme = bool(THEME_SELECTOR.search(selector.split(",")[0].strip()))

        for decl in TRANSITION_DECL.finditer(body):
            value = decl.group(2).strip().rstrip(";")
            line_no = _line_at(css, rule.start(2) + decl.start(), line)
            targets = [_transition_target(part) for part in value.split(",")]
            if "all" in targets:
                out.append(Finding(str(path), line_no, "FAIL", "transition-all",
                                   "`transition: all` — name the properties; `all` also "
                                   "animates layout on resize"))
            layout = [prop for prop in targets if prop != "all" and LAYOUT_PROP.fullmatch(prop)]
            if layout:
                out.append(Finding(str(path), line_no, "FAIL", "animate-geometry",
                                   f"`{decl.group(1)}` animates layout geometry "
                                   f"({', '.join(layout)}) — animate transform/opacity instead"))

        if re.search(r"\boutline\s*:\s*(?:none|0)\b", body, re.I):
            if focus_kind == "none":
                out.append(Finding(str(path), body_line, "FAIL", "no-focus-replacement",
                                   "`outline: none` with no `:focus`/`:focus-visible` rule "
                                   "anywhere — the keyboard loses the cursor"))
            elif focus_kind == "focus":
                out.append(Finding(str(path), body_line, "TELL", "focus-not-visible",
                                   "`outline: none` replaced on `:focus` only — works, but "
                                   "mouse clicks flash the ring too; prefer `:focus-visible`"))

        if re.search(r"\b(?:min-)?height\s*:\s*100vh\b", body, re.I):
            out.append(Finding(str(path), body_line, "FAIL", "viewport-vh",
                               "`100vh` breaks under mobile browser chrome — use `100dvh`"))

        if re.search(r"\boverflow-x\s*:\s*hidden\b", body, re.I) and re.search(
            r"^(?:html|body)\b|,\s*(?:html|body)\b", selector, re.I):
            out.append(Finding(str(path), body_line, "FAIL", "hidden-overflow",
                               "`overflow-x: hidden` on html/body masks a real horizontal "
                               "overflow — fix the offending element instead"))

        if not theme:
            for decl in body.split(";"):
                if re.match(r"\s*--[\w-]+\s*:", decl):  # token declaration: literals belong here
                    continue
                for color in COLOR_LITERAL.finditer(decl):
                    snippet = decl.strip().replace("\n", " ")[:60]
                    out.append(Finding(str(path), body_line, "TELL", "literal-color",
                                       f"literal colour outside the token block (`{color.group(0)}`) — "
                                       f"add a role token and use var(); near: {snippet!r}"))
            if "uppercase" in body.lower() and re.search(r"letter-spacing\s*:\s*[0-9.]+em",
                                                         body, re.I):
                out.append(Finding(str(path), body_line, "TELL", "eyebrow",
                                   "tracked-out ALL-CAPS label — the eyebrow tell; labels are "
                                   "body face, sentence case, untracked"))
    return out


def check_html(path: Path, text: str) -> list[Finding]:
    out: list[Finding] = []
    for match in IMG_TAG.finditer(text):
        tag = match.group(0)
        if not re.search(r"\balt\s*=", tag, re.I):
            out.append(Finding(str(path), _line_at(text, match.start(), 1), "FAIL", "img-alt",
                               "`<img>` without `alt` — set `alt=\"\"` only for decorative images"))
    return out


def scan(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings = check_html(path, text) if path.suffix.lower() in (".html", ".htm") else []
    regions = _regions(path, text)
    joined = "\n".join(region for _line, region in regions)
    if ":focus-visible" in joined:
        focus_kind = "visible"
    elif ":focus" in joined:
        focus_kind = "focus"
    else:
        focus_kind = "none"
    for line, css in regions:
        findings += check_css(path, line, css, focus_kind)
    return findings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="sloplint",
        description="Scan shipped HTML/CSS for mechanical AI-default tells (see SKILL.md).",
    )
    p.add_argument("paths", nargs="+", metavar="FILE", help="HTML or CSS files to scan")
    p.add_argument("--strict", action="store_true",
                   help="treat TELL findings as failures too")
    p.add_argument("--quiet", action="store_true", help="only print failures and the summary")
    args = p.parse_args(argv)

    findings: list[Finding] = []
    for raw in args.paths:
        path = Path(raw).expanduser()
        if not path.is_file():
            print(f"error: no such file: {raw}", file=sys.stderr)
            return 2
        findings += scan(path)

    for finding in findings:
        if args.quiet and finding.severity == "TELL":
            continue
        print(finding.render())

    fails = [f for f in findings if f.severity == "FAIL"]
    tells = [f for f in findings if f.severity == "TELL"]
    if fails or (tells and args.strict):
        print(f"\n{len(fails)} failure(s), {len(tells)} tell(s) — fix failures; "
              f"waive tells on the record.", file=sys.stderr)
        return 1
    print(f"\nclean: {len(tells)} tell(s) wairable, 0 failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

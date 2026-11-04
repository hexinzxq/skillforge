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
LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
HREF_ATTR = re.compile(r'\bhref\s*=\s*["\']([^"\']+)["\']', re.I)
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
COLOR_LITERAL = re.compile(
    r"(#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\([^)]*\))"
)
THEME_SELECTOR = re.compile(r":root|\[data-theme", re.I)
FULL_DOC = re.compile(r"<!doctype\s+html|<html\b", re.I)
VIEWPORT_META = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']?viewport\b", re.I)
VIEWPORT_TAG = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']?viewport\b[^>]*>", re.I)
CONTENT_ATTR = re.compile(r"\bcontent\s*=\s*([\"'])(.*?)\1", re.S | re.I)
MAX_SCALE = re.compile(r"maximum-scale\s*=\s*[\"']?\s*([0-9.]+)", re.I)
USER_SCALABLE = re.compile(r"user-scalable\s*=\s*[\"']?\s*(?:no|0)\b", re.I)
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
# The declaration, not just the literal, so `calc(100vh - 4rem)` is covered.
HEIGHT_DECL = re.compile(r"(?:^|;)\s*((?:min-|max-)?height)\s*:\s*([^;{}]+)", re.I)
VAR_USE = re.compile(r"var\(\s*--([\w-]+)\s*(,?)")
VAR_DECL = re.compile(r"--([\w-]+)\s*:")


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

        # Real pages rarely write a bare `height: 100vh`; they write
        # `min-height: calc(100vh - 4rem)` so a sticky header fits. Matching the
        # whole value keeps the same bug visible in the form people actually use.
        for decl in HEIGHT_DECL.finditer(body):
            if re.search(r"\b100vh\b", decl.group(2), re.I):
                out.append(Finding(str(path), _line_at(css, rule.start(2) + decl.start(), line),
                                   "FAIL", "viewport-vh",
                                   "`100vh` (including inside calc()) breaks under mobile "
                                   "browser chrome — use `100dvh`"))

        if re.search(r"\boverflow-x\s*:\s*hidden\b", body, re.I) and re.search(
            r"^(?:html|body)\b|,\s*(?:html|body)\b", selector, re.I):
            out.append(Finding(str(path), body_line, "FAIL", "hidden-overflow",
                               "`overflow-x: hidden` on html/body masks a real horizontal "
                               "overflow — fix the offending element instead"))

        if not theme:
            for decl in body.split(";"):
                if re.match(r"\s*--[\w-]+\s*:", decl):  # token declaration: literals belong here
                    continue
                # A literal inside var(--x, #fff) is a deliberate fallback, not a
                # component hard-coding a colour.
                decl = re.sub(r"var\([^)]*\)", "var()", decl)
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
    # A fragment (a partial, a template) is not a page: only full documents own
    # the <head>. Without the viewport meta every phone lays the page out at
    # 980px and shrinks it, which is the single most common "looks fine on my
    # laptop" report.
    if FULL_DOC.search(text) and not VIEWPORT_META.search(text):
        out.append(Finding(str(path), 1, "FAIL", "no-viewport",
                           "full page has no `<meta name=\"viewport\">` — phones lay it "
                           "out at 980px and shrink the text; add "
                           "`width=device-width, initial-scale=1`"))
    # Zoom is an accessibility feature, not a design knob: WCAG 1.4.4 wants the
    # page to reach 200% without loss. `user-scalable=no` and a low
    # maximum-scale take that away from low-vision users.
    for tag in VIEWPORT_TAG.finditer(text):
        content = CONTENT_ATTR.search(tag.group(0))
        if not content:
            continue
        declaration = content.group(2)
        blocked = USER_SCALABLE.search(declaration) is not None
        limit = MAX_SCALE.search(declaration)
        if limit and float(limit.group(1)) < 5:
            blocked = True
        if blocked:
            out.append(Finding(str(path), _line_at(text, tag.start(), 1), "FAIL", "zoom-lock",
                               "viewport disables pinch-zoom (`user-scalable=no` or a low "
                               "`maximum-scale`) — WCAG 1.4.4 needs 200%; drop it"))
    for match in IMG_TAG.finditer(text):
        tag = match.group(0)
        if not re.search(r"\balt\s*=", tag, re.I):
            out.append(Finding(str(path), _line_at(text, match.start(), 1), "FAIL", "img-alt",
                               "`<img>` without `alt` — set `alt=\"\"` only for decorative images"))
    return out


def _nearest_token(name: str, declared: set[str], limit: int = 2) -> str | None:
    """The declared token this name is a plausible misspelling of, if any."""
    best: tuple[int, str] | None = None
    for candidate in declared:
        if abs(len(candidate) - len(name)) > limit:
            continue
        d = _edit_distance(name, candidate)
        if d <= limit and (best is None or d < best[0]):
            best = (d, candidate)
    return best[1] if best else None


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, capped by simple length check at the call site."""
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def linked_stylesheets(path: Path) -> tuple[list[Path], list[str]]:
    """Local stylesheets an HTML page pulls in, plus the ones we cannot reach.

    Linting a page but not its CSS reports nothing on sites whose whole design
    lives in a <link>. The second half matters as much: a root-relative href
    (`/_next/static/css/x.css`) or a CDN sheet cannot be resolved from disk, and
    dropping it silently made a page whose entire design lived there read as
    "clean: 0 failures". The caller says out loud what it skipped instead.
    """
    if path.suffix.lower() not in (".html", ".htm"):
        return [], []
    text = path.read_text(encoding="utf-8")
    found: list[Path] = []
    skipped: list[str] = []
    for tag in LINK_TAG.finditer(text):
        if "stylesheet" not in tag.group(0).lower():
            continue
        match = HREF_ATTR.search(tag.group(0))
        if not match:
            continue
        href = match.group(1)
        if href.startswith(("http://", "https://", "//", "data:")) or href.startswith("/"):
            skipped.append(href)
            continue
        candidate = (path.parent / href.split("?")[0]).resolve()
        if candidate.is_file():
            if candidate not in found:
                found.append(candidate)
        elif href not in skipped:
            skipped.append(href)
    return found, skipped


COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def _strip_comments(css: str) -> str:
    """Drop /* … */ but keep the newlines, so line numbers stay honest. A
    `var(--x-*)` written in prose about the tokens is not a reference."""
    return COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), css)


def focus_scope(texts: list[tuple[Path, str]]) -> str:
    """Whether the keyboard keeps a cursor anywhere in this scan.

    The rule's message says "anywhere", and real projects split it: a reset sets
    `outline: none` while a focus sheet adds `:focus-visible`. Judging each file
    alone reported the reset as a failure even though the scan's own focus sheet
    replaced the ring.
    """
    joined = []
    for path, text in texts:
        for _line, region in _regions(path, text):
            joined.append(_strip_comments(region))
    whole = "\n".join(joined)
    if ":focus-visible" in whole:
        return "visible"
    return "focus" if ":focus" in whole else "none"


def scan(path: Path, text: str, focus_kind: str) -> list[Finding]:
    findings = check_html(path, text) if path.suffix.lower() in (".html", ".htm") else []
    for line, raw_css in _regions(path, text):
        findings += check_css(path, line, _strip_comments(raw_css), focus_kind)
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
    declared: set[str] = set()
    uses: list[tuple[Path, int, str, bool]] = []
    sources: list[tuple[Path, str]] = []
    queue: list[Path] = []
    skipped_stylesheets: list[str] = []
    for raw in args.paths:
        path = Path(raw).expanduser()
        if not path.is_file():
            print(f"error: no such file: {raw}", file=sys.stderr)
            return 2
        queue.append(path)
        found, skipped = linked_stylesheets(path)
        queue.extend(found)
        skipped_stylesheets.extend(href for href in skipped if href not in skipped_stylesheets)
    seen_paths: set[Path] = set()
    texts: list[tuple[Path, str]] = []
    for path in queue:
        if path.resolve() in seen_paths:
            continue
        seen_paths.add(path.resolve())
        texts.append((path, path.read_text(encoding="utf-8")))
    focus_kind = focus_scope(texts)
    for path, text in texts:
        sources.append((path, text))
        findings += scan(path, text, focus_kind)
        for line, raw_css in _regions(path, text):
            css = _strip_comments(raw_css)
            declared.update(VAR_DECL.findall(css))
            for match in VAR_USE.finditer(css):
                uses.append((path, _line_at(css, match.start(), line),
                             match.group(1), bool(match.group(2))))

    # Measured on 36 real stylesheets: flagging every undeclared var produced
    # 1,053 findings, because host apps inject runtime tokens (--dsw-*) and the
    # scan cannot see them. An undeclared name is only evidence of a bug when it
    # is one or two edits away from a token we can actually see - that is a typo,
    # not an inherited token.
    for path, line, name, has_fallback in uses:
        if name in declared or has_fallback:
            continue
        near = _nearest_token(name, declared)
        if near is not None:
            findings.append(Finding(
                str(path), line, "FAIL", "dangling-var",
                f"`var(--{name})` is not declared and is one edit from "
                f"`--{near}` — probably a typo; that reference resolves to nothing"))

    fails = [f for f in findings if f.severity == "FAIL"]
    tells = [f for f in findings if f.severity == "TELL"]
    # --quiet hides tells because they do not fail the run — except under
    # --strict, where every tell is a failure. Hiding those printed nothing and
    # still exited 1, which reads as a linter bug rather than a finding.
    for finding in findings:
        if args.quiet and finding.severity == "TELL" and not args.strict:
            continue
        print(finding.render())

    if skipped_stylesheets:
        shown = ", ".join(skipped_stylesheets[:4])
        if len(skipped_stylesheets) > 4:
            shown += f", … (+{len(skipped_stylesheets) - 4} more)"
        print(f"\nnote: {len(skipped_stylesheets)} linked stylesheet(s) not scanned "
              f"(remote, root-relative, or missing): {shown}", file=sys.stderr)

    if fails or (tells and args.strict):
        promoted = f" (+{len(tells)} tell(s) promoted by --strict)" if args.strict and tells else ""
        print(f"\n{len(fails)} failure(s){promoted}, {len(tells)} tell(s) — fix failures; "
              f"waive tells on the record ({len(seen_paths)} file(s) scanned).",
              file=sys.stderr)
        return 1
    print(f"\nclean: {len(tells)} tell(s) wairable, 0 failures "
          f"({len(seen_paths)} file(s) scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

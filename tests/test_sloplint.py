"""Tests for skills/frontend-design/scripts/sloplint.py.

The linter exists so the "no default AI tells" checklist is executable: each
test pins one rule that SKILL.md promises, plus the severity split (FAIL exits
1, TELL only with --strict) the CI step depends on.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "frontend-design" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import sloplint  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = sloplint.main(list(argv))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue() + err.getvalue()


class FixtureTests(unittest.TestCase):
    def test_clean_page_passes(self):
        code, out = run(str(FIXTURES / "slop-good.html"))
        self.assertEqual(code, 0)
        self.assertIn("clean", out)

    def test_bad_page_fails_with_every_rule(self):
        code, out = run(str(FIXTURES / "slop-bad.html"))
        self.assertEqual(code, 1)
        for rule in ("transition-all", "animate-geometry", "no-focus-replacement",
                     "viewport-vh", "hidden-overflow", "img-alt"):
            self.assertIn(rule, out)
        self.assertIn("eyebrow", out)


class RuleTests(unittest.TestCase):
    def scan_css(self, css: str) -> tuple[int, str]:
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            return run(path)
        finally:
            Path(path).unlink()

    def test_transition_all_is_a_failure(self):
        code, out = self.scan_css(".a { transition: all 200ms; }")
        self.assertEqual(code, 1)
        self.assertIn("transition-all", out)

    def test_animating_geometry_is_a_failure(self):
        code, out = self.scan_css(".a { transition: width 200ms ease; }")
        self.assertEqual(code, 1)
        self.assertIn("animate-geometry", out)

    def test_transitioning_transform_is_fine(self):
        code, _ = self.scan_css(".a { transition: transform 160ms; }")
        self.assertEqual(code, 0)

    def test_paint_transitions_are_not_layout_geometry(self):
        # Found on a real blog: border-left-color/background repaint only.
        code, out = self.scan_css(
            ".p { transition: border-left-color .2s ease, background .2s ease; }")
        self.assertEqual(code, 0)
        self.assertNotIn("animate-geometry", out)

    def test_focus_only_replacement_is_a_tell_not_a_failure(self):
        code, out = self.scan_css(".a { outline: none; } .a:focus { outline: 2px solid red; }")
        self.assertEqual(code, 0)
        self.assertIn("focus-not-visible", out)

    def test_outline_none_without_focus_visible_fails(self):
        code, out = self.scan_css(".a { outline: none; }")
        self.assertEqual(code, 1)
        self.assertIn("no-focus-replacement", out)

    def test_outline_none_with_a_focus_visible_rule_passes(self):
        code, _ = self.scan_css(".a { outline: none; } .a:focus-visible { outline: 2px solid red; }")
        self.assertEqual(code, 0)

    def test_100vh_fails_and_100dvh_passes(self):
        code, out = self.scan_css("body { min-height: 100vh; }")
        self.assertEqual(code, 1)
        self.assertIn("viewport-vh", out)
        self.assertEqual(self.scan_css("body { min-height: 100dvh; }")[0], 0)

    def test_100vh_inside_calc_is_still_the_mobile_bug(self):
        # Real pages write `min-height: calc(100vh - 4rem)` to fit a sticky
        # header; the bare-literal match missed every one of them.
        code, out = self.scan_css(".hero { min-height: calc(100vh - 4rem); }")
        self.assertEqual(code, 1)
        self.assertIn("viewport-vh", out)

    def test_a_height_token_may_hold_100vh(self):
        # The token is the right place for a raw viewport unit: changing the
        # token once beats hunting every height declaration.
        code, out = self.scan_css(
            ":root { --hero-height: 100vh; } .x { height: var(--hero-height); }")
        self.assertEqual(code, 0)
        self.assertNotIn("viewport-vh", out)

    def test_hidden_overflow_on_body_fails_but_on_a_carousel_is_fine(self):
        self.assertEqual(self.scan_css("body { overflow-x: hidden; }")[0], 1)
        self.assertEqual(self.scan_css(".carousel { overflow-x: hidden; }")[0], 0)

    def test_img_without_alt_fails_and_empty_alt_passes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write('<img src="a.png">')
            bad = handle.name
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write('<img src="a.png" alt="">')
            good = handle.name
        try:
            code, out = run(bad)
            self.assertEqual(code, 1)
            self.assertIn("img-alt", out)
            self.assertEqual(run(good)[0], 0)
        finally:
            Path(bad).unlink()
            Path(good).unlink()

    def test_literal_color_outside_tokens_is_a_tell_not_a_failure(self):
        code, out = self.scan_css(".card { background: #ffffff; }")
        self.assertEqual(code, 0)  # waivable
        self.assertIn("literal-color", out)
        self.assertEqual(self.scan_css(".card { background: #ffffff; }")[0], 0)

    def test_token_declarations_may_hold_literals(self):
        code, out = self.scan_css(":root { --bg: #fafafa; } .card { background: var(--bg); }")
        self.assertEqual(code, 0)
        self.assertNotIn("literal-color", out)

    def test_strict_turns_tells_into_failure(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(".eyebrow { text-transform: uppercase; letter-spacing: 0.1em; }")
            path = handle.name
        try:
            code, out = run(path)
            self.assertEqual(code, 0)
            self.assertIn("eyebrow", out)
            code, out = run(path, "--strict")
            self.assertEqual(code, 1)
        finally:
            Path(path).unlink()

    def test_quiet_hides_tells(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(".card { background: #ffffff; }")
            path = handle.name
        try:
            code, out = run(path, "--quiet")
            self.assertEqual(code, 0)
            self.assertNotIn("literal-color", out)
        finally:
            Path(path).unlink()

    def test_misspelled_var_is_a_failure(self):
        code, out = run(str(FIXTURES / "slop-dangling.html"))
        self.assertEqual(code, 1)
        self.assertIn("dangling-var", out)
        self.assertIn("--accent-constrast", out)
        self.assertIn("one edit from `--accent-contrast`", out)

    def test_unknown_vars_from_a_host_app_are_not_flagged(self):
        # 1,053 findings on 36 real sheets came from flagging these; a name that
        # is not near any declared token is far more likely inherited than wrong.
        code, out = run(str(FIXTURES / "slop-dangling.html"))
        self.assertNotIn("--surface", out)

    def test_var_written_in_a_comment_is_not_a_reference(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(":root { --accent-contrast: #fff; }\n"
                         "/* the host reads var(--accent-contrast) here */\n"
                         ".a { color: var(--accent-constrast); }\n")
            path = handle.name
        try:
            code, out = run(path)
            self.assertEqual(code, 1)          # the real typo on line 3
            self.assertNotIn(":2", out)        # the comment on line 2 is silent
        finally:
            Path(path).unlink()

    def test_var_with_fallback_is_not_dangling(self):
        code, out = run(str(FIXTURES / "slop-dangling.html"))
        self.assertNotIn("var(--accent,", out)

    def test_component_only_scan_does_not_invent_dangling_vars(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(".card { background: var(--surface); }")
            path = handle.name
        try:
            code, out = run(path)
            self.assertEqual(code, 0)
            self.assertNotIn("dangling-var", out)
        finally:
            Path(path).unlink()

    def test_html_follows_its_local_stylesheet(self):
        code, out = run(str(FIXTURES / "slop-linked.html"))
        self.assertEqual(code, 1)
        self.assertIn("slop-linked.css", out)   # found through <link>, not passed in
        self.assertIn("transition-all", out)
        self.assertIn("2 file(s) scanned", out)

    def test_remote_stylesheets_are_not_fetched(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write('<html><head><link rel="stylesheet" '
                         'href="https://example.com/x.css"></head></html>')
            path = handle.name
        try:
            code, out = run(path)
            self.assertEqual(code, 0)
            self.assertIn("1 file(s) scanned", out)
        finally:
            Path(path).unlink()

    def test_missing_file_is_an_input_error(self):
        code, out = run("/nonexistent/page.html")
        self.assertEqual(code, 2)
        self.assertIn("no such file", out)


class ShippedSkillTests(unittest.TestCase):
    def test_script_compiles_and_has_output(self):
        source = (SCRIPTS / "sloplint.py").read_text()
        compile(source, "sloplint.py", "exec")
        self.assertTrue(source.startswith("#!/usr/bin/env python3"))


if __name__ == "__main__":
    unittest.main()

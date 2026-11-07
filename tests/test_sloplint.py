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
    def test_unreachable_stylesheet_is_named_not_dropped(self):
        # Next/Vite exports link `/_next/static/css/x.css`; resolving that from
        # disk is impossible, but reporting "0 failures" while the whole design
        # was never opened is worse than saying what was skipped.
        html = (
            '<!doctype html><html><head>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="stylesheet" href="/_next/static/css/app.css">'
            '</head><body><p>hi</p></body></html>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(html)
            code, out = run(str(page))
            self.assertEqual(code, 0, out)
            self.assertIn("not scanned", out)
            self.assertIn("/_next/static/css/app.css", out)

    def test_base_href_makes_relative_links_unresolvable_not_missing(self):
        # With <base href="/wiki/"> a relative href resolves against the server,
        # not this folder; calling it missing failed a correct page.
        html = (
            '<!doctype html><html><head><base href="/wiki/">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="stylesheet" href="style.css">'
            '</head><body><p>hi</p></body></html>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(html)
            code, out = run(str(page))
            self.assertEqual(code, 0, out)
            self.assertIn("not scanned", out)


        # A relative href that does not resolve is not "unscanned" like a CDN
        # sheet — the page ships unstyled. Renames and typos land here.
        html = (
            '<!doctype html><html><head>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="stylesheet" href="assets/styles.css">'
            '</head><body><p>hi</p></body></html>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(html)
            code, out = run(str(page))
            self.assertEqual(code, 1, out)
            self.assertIn("missing-stylesheet", out)
            self.assertIn("assets/styles.css", out)


        html = (
            '<!doctype html><html><head>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<link rel="stylesheet" href="https://cdn.example.com/site.css">'
            '</head><body><p>hi</p></body></html>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "index.html"
            page.write_text(html)
            code, out = run(str(page))
            self.assertEqual(code, 0, out)
            self.assertIn("https://cdn.example.com/site.css", out)

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

    def scan_html(self, html: str) -> tuple[int, str]:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write(html)
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

    def test_focus_sheet_in_a_separate_file_counts(self):
        # Real projects split reset.css (`outline: none`) from focus.css
        # (`:focus-visible`). The rule's message says "anywhere", so the whole
        # argument set is the scope — judging each file alone failed the reset.
        with tempfile.TemporaryDirectory() as tmp:
            reset = Path(tmp) / "reset.css"
            reset.write_text("* { outline: none; }\n")
            focus = Path(tmp) / "focus.css"
            focus.write_text(":focus-visible { outline: 2px solid red; }\n")
            code, out = run(str(reset), str(focus))
            self.assertEqual(code, 0, out)
            # Alone, the reset really does leave the keyboard nowhere to be.
            self.assertEqual(run(str(reset))[0], 1)

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

    def test_a_print_document_is_not_made_to_ask_for_a_viewport(self):
        # An A4/PDF build (@page) has no viewport at all; demanding one is
        # advice that cannot be followed. It stays visible as a tell.
        html = ('<!doctype html><html><head><title>cv</title>'
                '<style>@page { size: A4; margin: 0 }</style></head>'
                '<body><p>hello</p></body></html>')
        code, out = self.scan_html(html)
        self.assertEqual(code, 0, out)
        self.assertIn("no-viewport", out)
        self.assertIn("print-target", out)

    def test_a_root_relative_stylesheet_is_resolved_on_disk(self):
        # A static export writes `/_next/static/css/x.css` at the export root;
        # walking the page's ancestors finds it, so the CSS is actually linted
        # instead of the page passing while every rule in it went unscanned.
        with tempfile.TemporaryDirectory() as root:
            export = Path(root) / "out"
            (export / "_next" / "static" / "css").mkdir(parents=True)
            (export / "_next" / "static" / "css" / "app.css").write_text(
                ".card { background: #ffffff; }")
            page = export / "index.html"
            page.write_text('<!doctype html><html><head><meta name="viewport" '
                            'content="width=device-width, initial-scale=1">'
                            '<link rel="stylesheet" href="/_next/static/css/app.css">'
                            '</head><body></body></html>')
            code, out = run(str(page))
            self.assertEqual(code, 0, out)   # literal-color is a tell
            self.assertIn("app.css", out)
            self.assertIn("literal-color", out)
            self.assertNotIn("not scanned", out)

    def test_a_root_relative_stylesheet_with_no_export_root_is_a_note(self):
        with tempfile.TemporaryDirectory() as root:
            page = Path(root) / "index.html"
            page.write_text('<!doctype html><html><head><meta name="viewport" '
                            'content="width=device-width, initial-scale=1">'
                            '<link rel="stylesheet" href="/nowhere/at/all.css">'
                            '</head><body></body></html>')
            code, out = run(str(page))
            self.assertEqual(code, 0, out)
            self.assertIn("not scanned", out)

    def test_full_page_without_viewport_fails(self):
        code, out = self.scan_html(
            '<!doctype html><html lang="en"><head><title>t</title></head>'
            '<body><p>x</p></body></html>')
        self.assertEqual(code, 1)
        self.assertIn("no-viewport", out)

    def test_viewport_meta_without_quotes_still_counts(self):
        code, out = self.scan_html(
            '<!doctype html><html lang="en"><head>'
            '<meta name=viewport content="width=device-width, initial-scale=1">'
            '</head><body><p>x</p></body></html>')
        self.assertEqual(code, 0)
        self.assertNotIn("no-viewport", out)

    def test_zoom_may_not_be_switched_off(self):
        for meta in ('width=device-width, user-scalable=no',
                     'width=device-width, maximum-scale=1'):
            code, out = self.scan_html(
                '<!doctype html><html lang="en"><head>'
                f'<meta name="viewport" content="{meta}">'
                '</head><body><p>x</p></body></html>')
            self.assertEqual(code, 1, meta)
            self.assertIn("zoom-lock", out)

    def test_a_generous_maximum_scale_is_fine(self):
        # iOS honours maximum-scale; 5 is the default ceiling, so writing it
        # changes nothing for the user.
        code, out = self.scan_html(
            '<!doctype html><html lang="en"><head>'
            '<meta name="viewport" content="width=device-width, maximum-scale=5">'
            '</head><body><p>x</p></body></html>')
        self.assertEqual(code, 0)
        self.assertNotIn("zoom-lock", out)

    def test_fragment_is_not_a_page(self):
        # Partials and templates do not own <head>; demanding the meta there
        # would report every server-side include as broken.
        code, out = self.scan_html('<section class="card"><p>hi</p></section>')
        self.assertEqual(code, 0)
        self.assertNotIn("no-viewport", out)

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

    def test_wide_gamut_color_function_is_a_literal(self):
        # `color(display-p3 ...)` is a literal exactly like `#ff0000`; wide-gamut
        # accents ship this way now, and the rule asks for a token instead.
        code, out = self.scan_css(".badge { color: color(display-p3 0.8 0.2 0.1); }")
        self.assertEqual(code, 0, out)
        self.assertIn("literal-color", out)
        self.assertIn("color(display-p3", out)
        # A token-based mix is not a literal: nothing to flag.
        code, out = self.scan_css(
            ".card { background: color-mix(in oklab, var(--accent) 20%, transparent); }")
        self.assertNotIn("literal-color", out)

    def test_token_declarations_may_hold_literals(self):
        code, out = self.scan_css(":root { --bg: #fafafa; } .card { background: var(--bg); }")
        self.assertEqual(code, 0)
        self.assertNotIn("literal-color", out)

    def test_exclude_skips_a_vendored_bundle_and_says_so(self):
        import tempfile as tf
        with tf.TemporaryDirectory() as root:
            vendor = Path(root, "next")
            vendor.mkdir()
            (vendor / "a.css").write_text(".a{height:100vh}\n")
            page = Path(root, "p.html")
            page.write_text('<!doctype html><html><head><meta name="viewport" '
                            'content="width=device-width"><link rel="stylesheet" '
                            'href="next/a.css"></head><body></body></html>\n')
            code, out = run(str(page))
            self.assertEqual(code, 1, out)          # the vendored file is scanned
            code, out = run("--exclude", "*/next/*", str(page))
            self.assertEqual(code, 0, out)
            self.assertIn("not scanned (--exclude)", out)

    def test_motion_without_a_reduced_motion_query_is_a_tell(self):
        code, out = self.scan_css(".toast { opacity: 0; transition: opacity .2s; }")
        self.assertEqual(code, 0, out)
        self.assertIn("no-reduced-motion", out)

    def test_a_reduced_motion_query_settles_the_rule(self):
        # `no-preference` is the better idiom: motion is opt-in. Either form
        # must silence the rule.
        css = ("@media (prefers-reduced-motion: no-preference) {"
               " .enter { animation: enter .3s forwards } }")
        code, out = self.scan_css(css)
        self.assertNotIn("no-reduced-motion", out)
        css = ("@media (prefers-reduced-motion: reduce) { .x { transition: none } }"
               " .toast { transition: opacity .2s }")
        code, out = self.scan_css(css)
        self.assertNotIn("no-reduced-motion", out)

    def test_a_quiet_sheet_gets_no_motion_tell(self):
        code, out = self.scan_css(".card { color: #111 }")
        self.assertNotIn("no-reduced-motion", out)

    def test_a_literal_points_at_its_own_declaration(self):
        css = ".card {\n  display: grid;\n  color: #eeeeee;\n}\n"
        code, out = self.scan_css(css)
        self.assertIn(":3  TELL  literal-color", out)
        self.assertNotIn(":1  TELL  literal-color", out)

    def test_a_bare_100vw_is_a_tell_but_a_calc_gutter_is_not(self):
        code, out = self.scan_css(".shell { width: 100vw; height: 40px }")
        self.assertEqual(code, 0, out)
        self.assertIn("viewport-vw", out)
        code, out = self.scan_css(".toolbar { max-width: calc(100vw - 24px); }")
        self.assertNotIn("viewport-vw", out)

    def test_a_multiline_rule_reports_the_declaration_line(self):
        css = ".hero {\n  color: #fff;\n  transition: all .2s;\n}\n"
        code, out = self.scan_css(css)
        self.assertEqual(code, 1, out)
        self.assertIn(":3  FAIL  transition-all", out)
        self.assertNotIn(":2  FAIL  transition-all", out)

    def test_a_minified_line_gets_a_column(self):
        # A static export is one 100KB line: "line 1" locates nothing, and the
        # near: snippet can match the same declaration twice.
        css = ".a{color:#111}" + ".b{color:#222}" * 120 + ".c{background:#fff}"
        self.assertGreater(len(css), 400)
        code, out = self.scan_css(css)
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r":1:\d+\s+TELL  literal-color")

    def test_a_readable_line_has_no_column(self):
        code, out = self.scan_css(".card { background: #ffffff; }")
        self.assertIn(":1  TELL  literal-color", out)

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

    def test_strict_quiet_still_shows_what_failed(self):
        # --quiet hides tells because they pass; under --strict they fail, and a
        # run that exits 1 while printing no finding is a linter bug.
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(".card { background: #ffffff; }")
            path = handle.name
        try:
            code, out = run(path, "--strict", "--quiet")
            self.assertEqual(code, 1)
            self.assertIn("literal-color", out)
            self.assertIn("promoted by --strict", out)
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
            handle.write('<html lang="en"><head>'
                         '<meta name="viewport" content="width=device-width, initial-scale=1">'
                         '<link rel="stylesheet" href="https://example.com/x.css">'
                         '</head></html>')
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

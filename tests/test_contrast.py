"""Tests for skills/frontend-design/scripts/contrast.py.

The script exists because the arithmetic is the part models get wrong, so the
tests pin the arithmetic (WCAG reference values), the naming convention that
turns a token sheet into a checklist, and the exit codes CI depends on.
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
sys.path.insert(0, str(ROOT))

import contrast  # noqa: E402


def run(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = contrast.main(list(argv))
        except SystemExit as exc:  # argparse errors and p.exit(2)
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue() + err.getvalue()


class ReferenceValuesTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(contrast.ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_same_color_is_1(self):
        self.assertAlmostEqual(contrast.ratio("#1d4ed8", "#1d4ed8"), 1.0, places=4)

    def test_ratio_is_symmetric(self):
        self.assertAlmostEqual(
            contrast.ratio("#111827", "#ffffff"), contrast.ratio("#ffffff", "#111827"), places=6)

    def test_short_hex_and_alpha(self):
        self.assertEqual(contrast.parse_hex("#fff"), (255, 255, 255))
        self.assertEqual(contrast.parse_hex("#111827ff"), (0x11, 0x18, 0x27))

    def test_rejects_non_hex(self):
        with self.assertRaises(ValueError):
            contrast.parse_hex("white")


class TokenSheetTests(unittest.TestCase):
    def test_reads_custom_properties(self):
        tokens = contrast.read_tokens((FIXTURES / "tokens-good.css").read_text())
        self.assertEqual(tokens["text"], "#111827")
        self.assertEqual(tokens["accent-contrast"], "#ffffff")

    def test_convention_pairs_are_derived(self):
        tokens = {
            "text": "#111827", "bg": "#ffffff", "surface": "#f7f7f8", "muted": "#5b6472",
            "accent": "#1d4ed8", "accent-contrast": "#ffffff", "on-accent": "#ffffff",
            "border": "#7b8494",
        }
        labels = [row[0] for row in contrast.pairs_from_tokens(tokens)]
        self.assertIn("text on bg", labels)
        self.assertIn("muted on bg", labels)
        self.assertIn("accent-contrast on accent", labels)
        self.assertIn("on-accent over accent", labels)
        self.assertIn("border on bg", labels)

    def test_focus_ring_is_checked_at_the_ui_threshold(self):
        # shadcn's default ring is oklch(0.708 0 0) — 2.58:1 on white. Nothing
        # else in a token sheet reports that, and a focus ring is a state
        # indicator, so 1.4.11 applies without the border ambiguity.
        css = ":root { --bg: #ffffff; --text: #0a0a0a; --ring: oklch(0.708 0 0); }"
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 1, out)
            self.assertIn("ring on bg", out)
            self.assertIn("2.58:1", out)
        finally:
            Path(path).unlink()

    def test_ring_falls_back_to_background_and_passes_when_dark(self):
        css = ":root { --background: #ffffff; --ring: #222222; }"
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 0, out)
            self.assertIn("ring on background", out)
            self.assertIn("PASS", out)
        finally:
            Path(path).unlink()


        tokens = {"bg": "#ffffff", "border": "#e5e7eb"}
        (_, _, _, threshold), = contrast.pairs_from_tokens(tokens)
        self.assertEqual(threshold, 3.0)

    def test_panel_and_card_are_treated_as_surfaces(self):
        # A real Next.js app calls its raised panel `--panel`; text on it is as
        # visible as text on the page, and `--surface` was the only name the
        # tool knew, so those pairs went unchecked.

        css = ":root { --bg: #edf1f7; --panel: #ffffff; --card: #ffffff; --text: #14171f; --muted: #777777; }"
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 1, out)   # muted on panel/card is 4.48:1
            for label in ("text on panel", "muted on panel", "text on card", "muted on card"):
                self.assertIn(label, out)
            self.assertIn("4.48:1", out)
        finally:
            Path(path).unlink()

    def test_missing_roles_are_skipped_not_crashed(self):
        self.assertEqual(contrast.pairs_from_tokens({"text": "#000"}), [])


class PairSpecTests(unittest.TestCase):
    def test_both_pair_syntaxes(self):
        self.assertEqual(
            contrast.parse_pair("text:#111827 on bg:#ffffff"),
            ("text on bg", "#111827", "#ffffff"))
        self.assertEqual(
            contrast.parse_pair("text:#111827/bg:#ffffff"),
            ("text on bg", "#111827", "#ffffff"))

    def test_pair_without_background_is_rejected(self):
        with self.assertRaises(ValueError):
            contrast.parse_pair("text:#111827")


class ExitCodeTests(unittest.TestCase):
    def test_passing_sheet_exits_zero(self):
        code, out = run("--css", str(FIXTURES / "tokens-good.css"))
        self.assertEqual(code, 0, out)
        self.assertIn("all pairs pass", out)

    def test_failing_sheet_exits_one_and_names_the_pair(self):
        code, out = run("--css", str(FIXTURES / "tokens-bad.css"))
        self.assertEqual(code, 1, out)
        self.assertIn("muted on bg", out)
        self.assertIn("FAIL", out)

    def test_single_pair_threshold_is_configurable(self):
        self.assertEqual(run("--fg", "#ffffff", "--bg", "#facc15")[0], 1)
        self.assertEqual(run("--fg", "#ffffff", "--bg", "#facc15", "--min", "1.5")[0], 0)

    def test_missing_file_exits_two(self):
        code, _ = run("--css", str(FIXTURES / "nope.css"))
        self.assertEqual(code, 2)

    def test_sheet_without_hex_tokens_is_an_error(self):
        code, _ = run("--css", str(FIXTURES / "tokens-empty.css"))
        self.assertEqual(code, 1)

    def test_no_arguments_at_all_is_a_usage_error(self):
        code, _ = run()
        self.assertEqual(code, 2)


class ColorFunctionTests(unittest.TestCase):
    """Modern sheets are written in oklch(); the checker must read them or it
    tells the user their real project has no colors at all (this happened with
    Tailwind v4's theme.css before parse_color grew function support)."""

    def test_oklch_anchors(self):
        self.assertEqual(contrast.parse_color("oklch(1 0 0)"), (255, 255, 255))
        self.assertEqual(contrast.parse_color("oklch(0 0 0)"), (0, 0, 0))

    def test_oklch_gray_keeps_the_L_cubed_luminance_invariant(self):
        # For achromatic colors OKLab luminance is exactly Y = L**3.
        rgb = contrast.parse_color("oklch(0.5 0 0)")
        self.assertEqual(rgb[0], rgb[1], rgb[2])
        self.assertAlmostEqual(contrast.luminance(rgb), 0.5 ** 3, places=2)

    def test_tailwind_red_500_matches_its_published_srgb_value(self):
        # oklch(63.7% 0.237 25.331) is Tailwind v4's --color-red-500, documented
        # as #fb2c36. Percent-L and chromatic hue must both parse.
        self.assertEqual(contrast.parse_color("oklch(63.7% 0.237 25.331)"), (251, 44, 54))

    def test_shadcn_foreground_matches_published_value(self):
        self.assertEqual(contrast.parse_color("oklch(0.145 0 0)"), (10, 10, 10))

    def test_rgb_variants_and_percentages(self):
        self.assertEqual(contrast.parse_color("rgb(255 0 0)"), (255, 0, 0))
        self.assertEqual(contrast.parse_color("rgb(255, 0, 0)"), (255, 0, 0))
        self.assertEqual(contrast.parse_color("rgb(100% 0% 0%)"), (255, 0, 0))
        self.assertEqual(contrast.parse_color("rgb(255 0 0 / 50%)"), (255, 0, 0))

    def test_hsl_reference_values(self):
        self.assertEqual(contrast.parse_color("hsl(0 100% 50%)"), (255, 0, 0))
        self.assertEqual(contrast.parse_color("hsl(120, 100%, 25%)"), (0, 128, 0))

    def test_non_literal_values_are_rejected(self):
        for bad in ("var(--x)", "color-mix(in oklch, red, blue)", "currentColor", ""):
            with self.assertRaises(ValueError):
                contrast.parse_color(bad)

    def test_oklch_sheet_auto_derives_shadcn_convention_pairs(self):
        # shadcn's -foreground naming is now a first-class convention, so the
        # same fixture that used to exit 2 ("no checkable pairs") derives real
        # pairs — and its real border value fails the 3:1 UI threshold.
        tokens = contrast.read_tokens((FIXTURES / "tokens-oklch.css").read_text())
        labels = [label for label, _fg, _bg, _t in contrast.pairs_from_tokens(tokens)]
        self.assertIn("foreground on background", labels)
        self.assertIn("primary-foreground on primary", labels)
        self.assertIn("border on background", labels)
        # shadcn's border is 1.26:1; it is reported, but advisory — whether it
        # outlines an input (must reach 3:1) or a card (may stay subtle) is not
        # in the token sheet.
        code, out = run("--css", str(FIXTURES / "tokens-oklch.css"))
        self.assertEqual(code, 0, out)
        self.assertIn("border on background", out)
        self.assertIn("1.26:1", out)
        self.assertIn("ADVISORY", out)

    def test_advisory_border_does_not_mask_a_real_failure(self):
        css = (":root { --bg: #ffffff; --text: #bbbbbb; --border: #f5f5f5; }")
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 1, out)   # text on bg is 1.9:1
            self.assertIn("text on bg", out)
            self.assertIn("FAIL", out)
            self.assertIn("ADVISORY", out)
        finally:
            Path(path).unlink()

    def test_explicit_oklch_pair_checks_normally(self):
        code, out = run("--pair", "text:oklch(0.145 0 0) on bg:oklch(1 0 0)")
        self.assertEqual(code, 0)
        self.assertIn("19.80:1", out)


class AlphaTests(unittest.TestCase):
    """Dark themes ship translucent borders (`oklch(1 0 0 / 10%)`). Checking
    them as opaque white reported 19.8:1 for a hairline that renders at 1.24:1
    — the alpha must be composited over the pair's background."""

    def test_alpha_is_composited_over_the_paired_bg(self):
        value = contrast.ratio("oklch(1 0 0 / 10%)", "oklch(0.145 0 0)")
        self.assertAlmostEqual(value, 1.24, delta=0.02)
        self.assertLess(value, 3.0)  # opaque white would say 19.8:1

    def test_alpha_in_rgba_and_8_digit_hex(self):
        self.assertAlmostEqual(contrast.ratio("rgba(255, 255, 255, 0.1)", "#0a0a0a"),
                               1.24, delta=0.02)
        self.assertAlmostEqual(contrast.ratio("#ffffff1a", "#0a0a0a"), 1.24, delta=0.02)

    def test_parse_color_still_drops_alpha_for_anchors(self):
        self.assertEqual(contrast.parse_color("#ffffff80"), (255, 255, 255))
        self.assertEqual(contrast.parse_color("rgba(255, 0, 0, 0.5)"), (255, 0, 0))
        self.assertEqual(contrast.parse_color("oklch(0.985 0 0 / 90%)"),
                         contrast.parse_color("oklch(0.985 0 0)"))


class DualScopeTests(unittest.TestCase):
    """Real sheets define the same names in :root and .dark. Flat last-wins
    reading silently checked only the dark theme — or mixed light fg with dark
    bg on sheets that override just some vars. Both must be impossible."""

    DUAL = FIXTURES / "tokens-dual-scope.css"

    def test_flat_read_of_dual_scope_refuses(self):
        with self.assertRaises(ValueError) as ctx:
            contrast.read_tokens(self.DUAL.read_text())
        self.assertIn("--block", str(ctx.exception))
        self.assertIn(".dark", str(ctx.exception))

    def test_block_selects_each_scope(self):
        css = self.DUAL.read_text()
        dark = contrast.read_tokens(css, block="dark")
        light = contrast.read_tokens(css, block=":root")
        self.assertEqual(dark["muted-foreground"], "#71717a")
        self.assertEqual(light["muted-foreground"], "#52525b")

    def test_scope_choice_changes_the_verdict(self):
        # light passes 4.5:1, dark fails it — scoping must be load-bearing
        code_light, _ = run("--css", str(self.DUAL), "--block", ":root")
        code_dark, out_dark = run("--css", str(self.DUAL), "--block", "dark")
        self.assertEqual(code_light, 0)
        self.assertEqual(code_dark, 1)
        self.assertIn("muted-foreground on muted", out_dark)

    def test_block_with_no_match_is_an_error(self):
        code, out = run("--css", str(self.DUAL), "--block", "light")
        self.assertEqual(code, 2)
        self.assertIn("no block matching", out)

    def test_all_blocks_checks_each_scope_in_turn(self):
        code, out = run("--css", str(self.DUAL), "--all-blocks")
        self.assertEqual(code, 1)
        self.assertIn(":root foreground on background", out)
        self.assertIn(".dark foreground on background", out)
        self.assertIn("muted-foreground on muted", out)

    def test_all_blocks_rejects_a_block_flag(self):
        code, out = run("--css", str(self.DUAL), "--all-blocks", "--block", ":root")
        self.assertEqual(code, 2)
        self.assertIn("drop --block", out)

    def test_cli_without_block_on_dual_scope_exits_two(self):
        code, out = run("--css", str(self.DUAL))
        self.assertEqual(code, 2)
        self.assertIn("multiple blocks", out)


class ForegroundConventionTests(unittest.TestCase):
    def test_foreground_naming_derives_pairs_without_our_convention(self):
        tokens = {"background": "#ffffff", "foreground": "#111111",
                  "card": "#ffffff", "card-foreground": "#111111",
                  "border": "#888888"}
        labels = [label for label, _fg, _bg, _t in contrast.pairs_from_tokens(tokens)]
        self.assertEqual(labels, ["foreground on background",
                                  "card-foreground on card",
                                  "border on background",
                                  "border on card"])

    def test_a_line_token_is_a_border_under_another_name(self):
        # A sheet checked here names its only stroke `--line` and borders every
        # button and input with it; `--border` does not exist, so the divider
        # advisory never ran on it. The row must appear for the page surface
        # and each raised one, and stay advisory (a hairline divider is legal).
        css = (":root { --bg: #0b0d12; --panel: #12151d; --text: #e6e9f0;"
               " --line: #232838; }")
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 0, out)
            self.assertIn("line on bg", out)
            self.assertIn("line on panel", out)
            self.assertIn("ADVISORY", out)
        finally:
            Path(path).unlink()

    def test_a_second_rung_of_the_surface_ladder_is_checked(self):
        # Sheets ladder their raised surfaces (`--panel-2` for hovers and
        # toasts). Text on the second rung was never paired, so a low-muted
        # value there passed silently. This one must fail.
        css = (":root { --bg: #12151d; --text: #e6e9f0; --muted: #6b7280;"
               " --panel: #171b25; --panel-2: #1f2430; }")
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(css)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 1, out)
            self.assertIn("muted on panel-2", out)
            self.assertIn("FAIL", out)
        finally:
            Path(path).unlink()

    def test_mixed_conventions_coexist(self):
        tokens = {"bg": "#ffffff", "text": "#111111",
                  "accent": "#1d4ed8", "accent-contrast": "#ffffff",
                  "muted": "#f4f4f5", "muted-foreground": "#52525b"}
        labels = [label for label, _fg, _bg, _t in contrast.pairs_from_tokens(tokens)]
        self.assertIn("text on bg", labels)           # ours
        self.assertIn("accent-contrast on accent", labels)  # ours
        self.assertIn("muted-foreground on muted", labels)  # shadcn's


class UncheckedReportingTests(unittest.TestCase):
    def test_non_color_tokens_are_not_reported_as_unchecked(self):
        sheet = (":root { --bg: #ffffff; --text: #111111;"
                 " --box-shadow: 0 1px 2px rgba(0,0,0,.1);"
                 " --timing: cubic-bezier(.2,.8,.2,1);"
                 " --unknown-thing: var(--missing); }")
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(sheet)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 0)
            self.assertNotIn("not checked", out)
        finally:
            Path(path).unlink()

    def test_a_colour_token_that_cannot_resolve_is_reported(self):
        sheet = ":root { --bg: #ffffff; --text: #111; --accent: var(--gone); --accent-contrast: #fff; }"
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(sheet)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertIn("not checked", out)
            self.assertIn("--accent", out)
        finally:
            Path(path).unlink()


class CascadeTests(unittest.TestCase):
    """--all-blocks must follow the cascade, not read each block in isolation."""

    SHEET = FIXTURES / "tokens-cascade.css"

    def test_utility_block_resolves_root_tokens(self):
        code, out = run("--css", str(self.SHEET), "--all-blocks")
        self.assertEqual(code, 0)
        self.assertIn(".card accent-contrast on accent", out)
        self.assertNotIn("not checked", out)  # --brand came from :root

    def test_at_rule_statements_are_not_part_of_the_selector(self):
        _, out = run("--css", str(self.SHEET), "--all-blocks")
        self.assertNotIn("@charset", out)
        self.assertNotIn("@layer", out)

    def test_blocks_without_pairs_are_summarized_once(self):
        _, out = run("--css", str(self.SHEET), "--all-blocks")
        self.assertIn("2 block(s) declare colours but no pair", out)
        self.assertEqual(out.count("declare colours but no pair"), 1)


class PrefersColorSchemeTests(unittest.TestCase):
    """`@media (prefers-color-scheme: dark) { :root { ... } }` is the most
    common way a sheet carries two themes. Both blocks used to collapse into
    one scope named `:root`, so flat reading kept whichever came last and the
    other theme was never checked at all."""

    SHEET = (":root { --bg: #ffffff; --text: #111111; --muted: #d0d0d0; }\n"
             "@media (prefers-color-scheme: dark) {\n"
             "  :root { --bg: #111111; --text: #eeeeee; --muted: #2a2a2a; }\n"
             "}\n")

    def test_flat_read_refuses_and_names_the_media_scope(self):
        with self.assertRaises(ValueError) as ctx:
            contrast.read_tokens(self.SHEET)
        self.assertIn("prefers-color-scheme: dark", str(ctx.exception))

    def test_exact_block_name_beats_the_substring(self):
        tokens = contrast.read_tokens(self.SHEET, block=":root")
        self.assertEqual(tokens["bg"], "#ffffff")
        tokens = contrast.read_tokens(self.SHEET, block="prefers-color-scheme: dark")
        self.assertEqual(tokens["bg"], "#111111")

    def test_all_blocks_checks_the_light_theme_too(self):
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(self.SHEET)
            path = handle.name
        try:
            code, out = run("--css", path, "--all-blocks")
            self.assertEqual(code, 1, out)
            self.assertIn(":root muted on bg", out)      # 1.54:1, was invisible
            self.assertIn("1.54:1", out)
        finally:
            Path(path).unlink()


class ColorMixTests(unittest.TestCase):
    """Bootstrap's palette is `color-mix(in oklch, var(--bs-white) 94%, …)`.
    A checker that only reads literals sees none of it."""

    def test_srgb_mix_at_equal_weights(self):
        self.assertEqual(contrast.evaluate_color(
            "color-mix(in srgb, #000 50%, #fff 50%)", {}), (128, 128, 128))

    def test_weights_are_the_second_argument_percentage(self):
        # 94% white + 6% blue is nearly white, not a mid-blue
        mixed = contrast.evaluate_color(
            "color-mix(in srgb, #ffffff 94%, #0000ff)", {})
        self.assertGreater(mixed[0], 230)
        self.assertGreater(mixed[2], 230)

    def test_oklch_mix_resolves_a_var_chain(self):
        tokens = {"bs-white": "#ffffff", "bs-blue-500": "#0087fe"}
        mixed = contrast.evaluate_color(
            "color-mix(in oklch, var(--bs-white) 94%, var(--bs-blue-500))", tokens)
        self.assertIsNotNone(mixed)
        self.assertGreater(mixed[0], 220)  # still a tint, not the blue

    def test_unknown_value_returns_none_instead_of_guessing(self):
        self.assertIsNone(contrast.evaluate_color("color-mix(in lch, red, blue)", {}))
        self.assertIsNone(contrast.evaluate_color("var(--missing)", {}))

    def test_hue_angle_units(self):
        # real sheets say `240deg`, `0.667turn`; only bare numbers are not enough
        self.assertEqual(contrast.parse_color("oklch(60% 0.24 240deg)"),
                         contrast.parse_color("oklch(60% 0.24 240)"))
        self.assertEqual(contrast.parse_color("hsl(120deg 100% 25%)"),
                         contrast.parse_color("hsl(120 100% 25%)"))


class ThemeSplitTests(unittest.TestCase):
    """light-dark(a, b) carries both themes in one declaration."""

    SHEET = FIXTURES / "tokens-light-dark.css"

    def test_both_themes_are_checked(self):
        code, out = run("--css", str(self.SHEET))
        self.assertEqual(code, 0)
        self.assertIn("light: text on bg", out)
        self.assertIn("dark: text on bg", out)
        self.assertIn("#111827 on #ffffff", out)
        self.assertIn("#f3f4f6 on #000000", out)

    def test_a_pair_that_does_not_differ_is_not_printed_twice(self):
        text = (":root { --bg: #ffffff; --text: #111111;"
                " --accent: light-dark(#111111, #eeeeee);"
                " --accent-contrast: #ffffff; }")
        with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
            handle.write(text)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 1)  # only the accent pair disagrees
            self.assertEqual(out.count("text on bg"), 1)  # same values: printed once
        finally:
            Path(path).unlink()

    def test_tokens_inside_a_page_are_read(self):
        # A single-file tool or a static export keeps its palette in an inline
        # <style>. Copying it into a .css file first is how the check stops
        # happening; an .html path is read for those blocks directly.
        page = """<!doctype html><html lang="zh-CN"><head>
        <style>:root { --bg: #0f1216; --text: #e6edf3; --muted: #9aa7b4; }</style>
        </head><body><p>hi</p></body></html>"""
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write(page)
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 0)
            self.assertIn("text on bg", out)
            self.assertIn("PASS", out)
        finally:
            Path(path).unlink()

    def test_a_page_without_a_style_block_says_so(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write("<!doctype html><html lang=en><body><p>hi</p></body></html>")
            path = handle.name
        try:
            code, out = run("--css", path)
            self.assertEqual(code, 2)
            self.assertIn("no inline <style> block", out)
        finally:
            Path(path).unlink()

    def test_the_same_palette_in_two_sheets_is_printed_once(self):
        # Splitting tokens.css from a subpage sheet is normal, and both halves
        # redeclare text/bg so the subpage works standalone. Same pair, same
        # verdict: one line.
        css = ":root { --bg: #ffffff; --text: #111111; }"
        paths = []
        try:
            for _ in range(2):
                with tempfile.NamedTemporaryFile("w", suffix=".css", delete=False) as handle:
                    handle.write(css)
                    paths.append(handle.name)
            code, out = run("--css", paths[0], "--css", paths[1])
            self.assertEqual(code, 0)
            self.assertEqual(out.count("text on bg"), 1)
        finally:
            for path in paths:
                Path(path).unlink()


        # `-fg` is a foreground on the page surface, so pairing it with `-bg`
        # invents unreadable combinations (36 of them on real Bootstrap).
        code, out = run("--css", str(FIXTURES / "tokens-bootstrap-shape.css"))
        self.assertEqual(code, 1)
        self.assertIn("bs-primary-contrast on bs-primary-bg", out)
        self.assertNotIn("bs-primary-fg on bs-primary-bg", out)

    def test_comments_cannot_smuggle_a_block_name(self):
        code, out = run("--css", str(FIXTURES / "tokens-dual-scope.css"),
                        "--block", "light")  # only appears inside a /* comment */
        self.assertEqual(code, 2)
        self.assertIn("no block matching", out)


if __name__ == "__main__":
    unittest.main()

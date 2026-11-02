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

    def test_border_uses_the_ui_threshold(self):
        tokens = {"bg": "#ffffff", "border": "#e5e7eb"}
        (_, _, _, threshold), = contrast.pairs_from_tokens(tokens)
        self.assertEqual(threshold, 3.0)

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
        code, out = run("--css", str(FIXTURES / "tokens-oklch.css"))
        self.assertEqual(code, 1)
        self.assertIn("border on background", out)
        self.assertIn("1.26:1", out)

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
                                  "border on background"])

    def test_mixed_conventions_coexist(self):
        tokens = {"bg": "#ffffff", "text": "#111111",
                  "accent": "#1d4ed8", "accent-contrast": "#ffffff",
                  "muted": "#f4f4f5", "muted-foreground": "#52525b"}
        labels = [label for label, _fg, _bg, _t in contrast.pairs_from_tokens(tokens)]
        self.assertIn("text on bg", labels)           # ours
        self.assertIn("accent-contrast on accent", labels)  # ours
        self.assertIn("muted-foreground on muted", labels)  # shadcn's


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

    def test_role_contrast_is_paired_with_role_bg_only(self):
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

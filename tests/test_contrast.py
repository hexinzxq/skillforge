"""Tests for skills/frontend-design/scripts/contrast.py.

The script exists because the arithmetic is the part models get wrong, so the
tests pin the arithmetic (WCAG reference values), the naming convention that
turns a token sheet into a checklist, and the exit codes CI depends on.
"""

from __future__ import annotations

import contextlib
import io
import sys
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

    def test_oklch_sheet_parses_but_has_no_convention_pairs(self):
        tokens = contrast.read_tokens((FIXTURES / "tokens-oklch.css").read_text())
        self.assertIn("--color-red-500".lstrip("-"), tokens)  # key name without dashes
        self.assertEqual(contrast.pairs_from_tokens(tokens), [])
        code, out = run("--css", str(FIXTURES / "tokens-oklch.css"))
        self.assertEqual(code, 2)
        self.assertIn("no checkable pairs", out)

    def test_explicit_oklch_pair_checks_normally(self):
        code, out = run("--pair", "text:oklch(0.145 0 0) on bg:oklch(1 0 0)")
        self.assertEqual(code, 0)
        self.assertIn("19.80:1", out)


if __name__ == "__main__":
    unittest.main()

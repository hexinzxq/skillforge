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
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = contrast.main(list(argv))
    return code, buf.getvalue()


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
        with self.assertRaises(SystemExit):
            run()


if __name__ == "__main__":
    unittest.main()

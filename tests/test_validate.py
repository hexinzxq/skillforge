"""Tests for tools/validate_skills.py — the validator is what keeps the spec honest."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.validate_skills import (  # noqa: E402
    bucket, check_skill, discover_vendor, parse_frontmatter,
)

GOOD = """---
name: sample-skill
description: Does a specific thing for the project and reports what changed. Use when the user asks for that thing.
license: MIT
metadata:
  author: hexinzxq
  version: "1.0.0"
---

# Sample

## Steps

1. Do the thing.
"""


def make_skill(root: Path, dir_name: str, text: str, extra: dict[str, str] | None = None) -> Path:
    d = root / dir_name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    for rel, content in (extra or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_and_nested_map(self):
        fields, body, err = parse_frontmatter(GOOD)
        self.assertIsNone(err)
        self.assertEqual(fields["name"], "sample-skill")
        self.assertEqual(fields["metadata"]["version"], "1.0.0")
        self.assertIn("Do the thing", body)

    def test_missing_opening_delimiter(self):
        _, _, err = parse_frontmatter("name: x\n---\nbody\n")
        self.assertIn("delimiter", err)

    def test_unclosed_frontmatter(self):
        _, _, err = parse_frontmatter("---\nname: x\ndescription: y\n")
        self.assertIn("not closed", err)

    def test_indented_value_without_parent(self):
        _, _, err = parse_frontmatter("---\n  author: x\n---\nbody\n")
        self.assertIn("parent key", err)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_skill(self):
        d = make_skill(self.root, "sample-skill", GOOD)
        errors, _ = check_skill(d)
        self.assertEqual(errors, [])

    def test_missing_skill_md(self):
        d = self.root / "nope"
        d.mkdir()
        errors, _ = check_skill(d)
        self.assertTrue(any("missing SKILL.md" in e for e in errors))

    def test_name_must_match_directory(self):
        d = make_skill(self.root, "other-dir", GOOD)
        errors, _ = check_skill(d)
        self.assertTrue(any("does not match directory" in e for e in errors))

    def test_name_must_be_kebab_case(self):
        bad = GOOD.replace("name: sample-skill", "name: Sample_Skill")
        d = make_skill(self.root, "Sample_Skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("kebab-case" in e for e in errors))

    def test_reserved_name(self):
        bad = GOOD.replace("name: sample-skill", "name: claude")
        d = make_skill(self.root, "claude", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("reserved" in e for e in errors))

    def test_description_needs_trigger(self):
        bad = GOOD.replace(
            "description: Does a specific thing for the project and reports what changed. Use when the user asks for that thing.",
            "description: Does a specific thing for the project and reports what changed afterwards.",
        )
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("when to use" in e for e in errors))

    def test_description_length_limit(self):
        bad = GOOD.replace("Does a specific thing", "Does " + "very " * 220 + "a thing")
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("description is" in e and "max 1024" in e for e in errors))

    def test_unknown_field_rejected(self):
        bad = GOOD.replace("license: MIT", "license: MIT\nwhen-to-use: always")
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("unknown frontmatter" in e for e in errors))

    def test_unquoted_numeric_version_is_flagged(self):
        # YAML types an unquoted `1` as an int; the spec wants strings.
        bad = GOOD.replace('version: "1.0.0"', "version: 1")
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("metadata.version must be a string" in e for e in errors))

    def test_dotted_version_without_quotes_is_a_string(self):
        # YAML keeps `1.0.0` a string (two dots), so this must pass.
        fine = GOOD.replace('version: "1.0.0"', "version: 1.0.0")
        d = make_skill(self.root, "sample-skill", fine)
        errors, _ = check_skill(d)
        self.assertEqual(errors, [])

    def test_dangling_reference_detected(self):
        bad = GOOD + "\nRead `references/missing.md` before starting.\n"
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("does not exist" in e for e in errors))

    def test_reference_present_is_fine(self):
        text = GOOD + "\nRead `references/guide.md`.\n"
        d = make_skill(self.root, "sample-skill", text, {"references/guide.md": "# guide\n"})
        errors, _ = check_skill(d)
        self.assertEqual(errors, [])

    def test_compatibility_length_limit(self):
        bad = GOOD.replace("license: MIT", "license: MIT\ncompatibility: " + "x" * 501)
        d = make_skill(self.root, "sample-skill", bad)
        errors, _ = check_skill(d)
        self.assertTrue(any("compatibility is" in e for e in errors))

    def test_empty_body_rejected(self):
        bare = "---\nname: sample-skill\ndescription: Does a thing for the project. Use when asked.\n---\n"
        d = make_skill(self.root, "sample-skill", bare)
        errors, _ = check_skill(d)
        self.assertTrue(any("body is empty" in e for e in errors))


class RelaxedVendorTests(unittest.TestCase):
    """Vendored copies: only structural problems are errors, convention is a warning."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_style_violation_is_a_warning_not_an_error(self):
        no_trigger = GOOD.replace(
            " Use when the user asks for that thing.", "")
        d = make_skill(self.root, "sample-skill", no_trigger)
        strict_errors, _ = check_skill(d)
        self.assertTrue(strict_errors, "strict mode should still reject it")
        relaxed_errors, relaxed_warnings = check_skill(d, strict=False)
        self.assertEqual(relaxed_errors, [])
        self.assertTrue(any("state when to use" in w for w in relaxed_warnings))

    def test_structural_problem_still_fails_relaxed(self):
        wrong_name = GOOD.replace("name: sample-skill", "name: other-skill")
        d = make_skill(self.root, "sample-skill", wrong_name)
        relaxed_errors, _ = check_skill(d, strict=False)
        self.assertTrue(any("does not match directory name" in e for e in relaxed_errors))

    def test_missing_description_fails_relaxed(self):
        stripped = GOOD.replace(
            "description: Does a specific thing for the project and reports what changed. Use when the user asks for that thing.\n",
            "")
        d = make_skill(self.root, "sample-skill", stripped)
        relaxed_errors, _ = check_skill(d, strict=False)
        self.assertTrue(any("missing required field 'description'" in e for e in relaxed_errors))

    def test_dangling_reference_is_a_warning_in_relaxed_mode(self):
        dangling = GOOD + "\nSee `references/nope.md`.\n"
        d = make_skill(self.root, "sample-skill", dangling)
        relaxed_errors, relaxed_warnings = check_skill(d, strict=False)
        self.assertEqual(relaxed_errors, [])
        self.assertTrue(any("does not exist" in w for w in relaxed_warnings))


class ReferenceScanTests(unittest.TestCase):
    """Paths in fenced code blocks are templates, not links."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_fenced_example_paths_are_ignored(self):
        text = GOOD + "\n```\nscripts/tool.sh   # template\n```\n"
        d = make_skill(self.root, "sample-skill", text)
        errors, _ = check_skill(d)
        self.assertEqual(errors, [])

    def test_inline_paths_are_still_checked(self):
        text = GOOD + "\nRun `scripts/tool.sh` to start.\n"
        d = make_skill(self.root, "sample-skill", text)
        errors, _ = check_skill(d)
        self.assertTrue(any("scripts/tool.sh" in e for e in errors))


class VendorDiscoveryTests(unittest.TestCase):
    def test_finds_nested_vendor_skills_and_buckets_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vendor" / "lib" / "category" / "vendor-skill"
            nested.mkdir(parents=True)
            text = GOOD.replace("name: sample-skill", "name: vendor-skill").replace(
                "metadata:\n  author: hexinzxq\n  version: \"1.0.0\"\n", "")
            (nested / "SKILL.md").write_text(text, encoding="utf-8")
            self.assertEqual(discover_vendor(root), [nested])
            _, warnings = check_skill(nested, strict=False)
            self.assertEqual(bucket(warnings), "1 no metadata.version")

    def test_no_vendor_dir_is_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(discover_vendor(Path(tmp)), [])


class RealSkillsTests(unittest.TestCase):
    """The repo's own skills must pass their own validator."""

    def test_every_skill_in_repo_is_valid(self):
        skills = ROOT / "skills"
        dirs = sorted(d for d in skills.iterdir() if d.is_dir())
        self.assertGreaterEqual(len(dirs), 1)
        for d in dirs:
            with self.subTest(skill=d.name):
                errors, _ = check_skill(d)
                self.assertEqual(errors, [], f"{d.name}: {errors}")

    def test_every_vendored_skill_is_loadable(self):
        for d in discover_vendor(ROOT):
            with self.subTest(skill=str(d.relative_to(ROOT))):
                errors, _ = check_skill(d, strict=False)
                self.assertEqual(errors, [], f"{d.relative_to(ROOT)}: {errors}")


if __name__ == "__main__":
    unittest.main()

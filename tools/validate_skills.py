#!/usr/bin/env python3
"""Validate every skill in this repository against the Agent Skills spec.

Checks (errors fail the build):
  - skills/<name>/SKILL.md exists, exact filename, UTF-8
  - frontmatter is delimited by '---' lines and parses as YAML subset
  - `name` present, matches the directory, kebab-case, <= 64 chars, not reserved
  - `description` present, 1..1024 chars, states when to use it ("Use when")
  - `compatibility` <= 500 chars, `license` <= 50
  - `metadata` is a map of string keys to string values
  - only the six spec fields are used (Claude Code errors on unexpected keys)
  - every path mentioned in the body as references/ scripts/ assets/ exists
  - every script under scripts/ compiles (a script that cannot run is worse than none)
  - body is not empty

Vendored skills (`vendor/**/SKILL.md`) are checked too, in relaxed mode: only the
structural problems that stop a skill from loading (missing/mismatched name, no
description, unparseable frontmatter, empty body) fail the build. Everything else
is reported as a warning, because those files are copies of someone else's work
and the fix has to go upstream, not here.

Paths inside fenced code blocks are templates (``bash scripts/tool.sh``) and are
not resolved, otherwise every skill that shows a layout example would fail.

Warnings do not fail: long bodies (progressive-disclosure smell), a body with no
markdown headings, missing metadata.version.

    python3 tools/validate_skills.py [--root .] [--quiet] [--no-vendor]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = {"claude"}
REF_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")
# Paths shown inside fenced code blocks are templates, not links to real files.
FENCE_RE = re.compile(r"```.*?```", re.S)
MAX_NAME, MAX_DESC, MAX_LICENSE, MAX_COMPAT = 64, 1024, 50, 500


def parse_frontmatter(text: str) -> tuple[dict, str, str | None]:
    """Return (fields, body, error). A deliberately small YAML subset: scalars,
    quoted strings and one level of nested mapping."""
    if not text.startswith("---\n") and text != "---":
        return {}, text, "file must start with a '---' frontmatter delimiter"
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text, "frontmatter is not closed by a '---' line"
    header = text[4:end]
    body = text[end + 4:].lstrip("\n")
    fields: dict = {}
    current_map: dict | None = None
    for lineno, raw in enumerate(header.splitlines(), start=2):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            if current_map is None:
                return {}, body, f"line {lineno}: indented value without a parent key"
            key, _, value = line.strip().partition(":")
            current_map[key.strip()] = _unquote(value.strip())
            continue
        key, sep, value = line.partition(":")
        if not sep:
            return {}, body, f"line {lineno}: expected 'key: value', got {line!r}"
        key = key.strip()
        value = value.strip()
        if value == "":
            current_map = {}
            fields[key] = current_map
        else:
            current_map = None
            fields[key] = _unquote(value)
    return fields, body, None


class Bare(str):
    """An unquoted scalar that YAML would type as a number or boolean."""

    yaml_typed = True


BARE_TYPED = re.compile(r"^(?:-?\d+(?:\.\d+)?|true|false|null|~)$", re.I)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if BARE_TYPED.match(value):
        return Bare(value)
    return value


SH_INTERPRETERS = ("sh", "bash", "zsh")


def check_scripts(skill_dir: Path, soft) -> None:
    """Scripts are the part of a skill that executes, so a syntax error there is a
    runtime failure the model will blame on its own command. Compile them."""
    sdir = skill_dir / "scripts"
    if not sdir.is_dir():
        return
    for f in sorted(sdir.rglob("*")):
        if not f.is_file() or f.name.startswith(".") or "__pycache__" in f.parts:
            continue
        if f.suffix not in (".py", ".sh", ".bash", ".zsh"):
            continue
        rel = f.relative_to(skill_dir)
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            soft(f"{skill_dir.name}: {rel} is not UTF-8")
            continue
        first = text.splitlines()[0] if text.strip() else ""
        if f.suffix == ".py":
            try:
                compile(text, str(rel), "exec")
            except SyntaxError as exc:
                soft(f"{skill_dir.name}: {rel} does not compile "
                     f"({exc.msg}, line {exc.lineno})")
                continue
            if not first.startswith("#!"):
                soft(f"{skill_dir.name}: {rel} has no shebang line")
            elif "python" not in first:
                soft(f"{skill_dir.name}: {rel} shebang does not name python ({first!r})")
        elif f.suffix in (".sh", ".bash", ".zsh"):
            if not first.startswith("#!"):
                soft(f"{skill_dir.name}: {rel} has no shebang line")
            elif not any(i in first for i in SH_INTERPRETERS):
                soft(f"{skill_dir.name}: {rel} shebang is not a shell ({first!r})")


def check_skill(skill_dir: Path, strict: bool = True) -> tuple[list[str], list[str]]:
    """Check one skill directory. In relaxed mode (vendor copies) only structural
    problems are errors; style and convention violations become warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    def soft(msg: str) -> None:
        (errors if strict else warnings).append(msg)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md (exact name, case-sensitive)"], warnings
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"{skill_dir.name}: SKILL.md is not UTF-8 ({exc})"], warnings

    fields, body, err = parse_frontmatter(text)
    if err:
        return [f"{skill_dir.name}: {err}"], warnings

    unknown = set(fields) - SPEC_FIELDS
    if unknown:
        soft(f"{skill_dir.name}: unknown frontmatter field(s) {sorted(unknown)}; "
             f"allowed: {sorted(SPEC_FIELDS)}")

    name = fields.get("name")
    if not isinstance(name, str) or not name:
        errors.append(f"{skill_dir.name}: missing required field 'name'")
    else:
        if len(name) > MAX_NAME:
            errors.append(f"{skill_dir.name}: name is {len(name)} chars (max {MAX_NAME})")
        if not NAME_RE.match(name):
            errors.append(f"{skill_dir.name}: name {name!r} must be lowercase kebab-case "
                          f"(a-z, 0-9, single hyphens)")
        if name in RESERVED:
            errors.append(f"{skill_dir.name}: name {name!r} is reserved")
        if name != skill_dir.name:
            errors.append(f"{skill_dir.name}: name {name!r} does not match directory name")

    desc = fields.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append(f"{skill_dir.name}: missing required field 'description'")
    else:
        if len(desc) > MAX_DESC:
            errors.append(f"{skill_dir.name}: description is {len(desc)} chars (max {MAX_DESC})")
        if not re.search(r"\buse (it )?when\b", desc, re.I):
            soft(f"{skill_dir.name}: description must state when to use the skill "
                 f"(e.g. 'Use when the user asks ...')")
        if len(desc) < 40:
            warnings.append(f"{skill_dir.name}: description is very short ({len(desc)} chars); "
                            f"name the capability and the trigger")

    lic = fields.get("license")
    if isinstance(lic, str) and len(lic) > MAX_LICENSE:
        soft(f"{skill_dir.name}: license is {len(lic)} chars (max {MAX_LICENSE})")
    compat = fields.get("compatibility")
    if isinstance(compat, str) and len(compat) > MAX_COMPAT:
        soft(f"{skill_dir.name}: compatibility is {len(compat)} chars (max {MAX_COMPAT})")

    meta = fields.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            soft(f"{skill_dir.name}: metadata must be a mapping of key: value")
        else:
            for k, v in meta.items():
                if not isinstance(v, str) or getattr(v, "yaml_typed", False):
                    soft(f"{skill_dir.name}: metadata.{k} must be a string "
                         f"(quote values YAML would type as numbers, e.g. version: \"1\")")
    if not isinstance(meta, dict) or "version" not in meta:
        warnings.append(f"{skill_dir.name}: metadata.version missing")

    tools = fields.get("allowed-tools")
    if tools is not None and not isinstance(tools, str):
        soft(f"{skill_dir.name}: allowed-tools must be a space-separated string")

    if not body.strip():
        errors.append(f"{skill_dir.name}: body is empty")
    else:
        if "##" not in body:
            warnings.append(f"{skill_dir.name}: body has no '##' sections")
        body_lines = len(body.splitlines())
        if body_lines > 220:
            warnings.append(f"{skill_dir.name}: body is {body_lines} lines — move detail into "
                            f"references/ so it loads only when needed")

    for rel in sorted(set(REF_RE.findall(FENCE_RE.sub("", body)))):
        if not (skill_dir / rel).exists():
            soft(f"{skill_dir.name}: body references `{rel}` which does not exist")

    check_scripts(skill_dir, soft)

    for stale in ("references", "scripts", "assets"):
        d = skill_dir / stale
        if d.is_dir() and not any(d.rglob("*")):
            warnings.append(f"{skill_dir.name}: empty {stale}/ directory")
    return errors, warnings


def discover_vendor(root: Path) -> list[Path]:
    """Every directory under vendor/ that holds a SKILL.md (the upstream libraries
    nest them by category, so one level of iterdir is not enough)."""
    vendor = root / "vendor"
    if not vendor.is_dir():
        return []
    return sorted({p.parent for p in vendor.rglob("SKILL.md") if ".git" not in p.parts})


WARNING_KINDS = (
    ("lines — move detail", "long body"),
    ("metadata.version missing", "no metadata.version"),
    ("state when to use", "no trigger phrase"),
    ("references `", "dangling reference"),
    ("body has no", "no ## sections"),
    ("description is very short", "short description"),
    ("empty ", "empty directory"),
    ("does not compile", "script does not compile"),
    ("no shebang", "script without shebang"),
    ("shebang", "wrong shebang"),
)


def bucket(warnings: list[str]) -> str:
    """Collapse 50 warnings into one readable line. A check nobody reads is dead."""
    counts: dict[str, int] = {}
    for w in warnings:
        for needle, label in WARNING_KINDS:
            if needle in w:
                counts[label] = counts.get(label, 0) + 1
                break
        else:
            counts["other"] = counts.get("other", 0) + 1
    return ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="validate skills against the Agent Skills spec")
    p.add_argument("--root", default=".", help="repository root (default: cwd)")
    p.add_argument("--quiet", action="store_true", help="only print problems")
    p.add_argument("--no-vendor", action="store_true", help="skip vendor/**/SKILL.md")
    p.add_argument("--vendor-detail", action="store_true",
                   help="list every vendored warning instead of one summary line")
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print(f"no skills/ directory under {root}", file=sys.stderr)
        return 1

    dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
    if not dirs:
        print("skills/ contains no skill directories", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for d in dirs:
        errors, warnings = check_skill(d)
        all_errors += errors
        all_warnings += warnings
        if not args.quiet:
            print(f"{'FAIL' if errors else 'ok  '} {d.name}")

    vendor_dirs = [] if args.no_vendor else discover_vendor(root)
    vendor_errors: list[str] = []
    vendor_warnings: list[str] = []
    for d in vendor_dirs:
        errors, warnings = check_skill(d, strict=False)
        rel = d.relative_to(root)
        vendor_errors += [f"vendor: {rel}: {e}" for e in errors]
        vendor_warnings += [f"vendor: {w}" for w in warnings]
        if not args.quiet and errors:
            print(f"FAIL {rel}")
    all_errors += vendor_errors

    for w in all_warnings:
        print(f"warn  {w}")
    if vendor_warnings:
        if args.vendor_detail:
            for w in vendor_warnings:
                print(f"warn  {w}")
        elif not args.quiet:
            print(f"warn  vendor: {len(vendor_warnings)} convention warning(s) "
                  f"across {len(vendor_dirs)} skills — {bucket(vendor_warnings)}")
            print("      (--vendor-detail to list them; these are copies, fixes go upstream)")
    for e in all_errors:
        print(f"error {e}", file=sys.stderr)

    if all_errors:
        print(f"\n{len(all_errors)} error(s), "
              f"{len(all_warnings) + len(vendor_warnings)} warning(s)", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"\n{len(dirs)} skill(s) valid, {len(vendor_dirs)} vendored "
              f"({len(vendor_errors)} hard error(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

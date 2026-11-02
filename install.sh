#!/usr/bin/env bash
# Install the skills in this repo into a skills directory, by symlink (default)
# or copy. Our own skills install by default; --vendor adds the vendored
# libraries (61 more, same directory-name rule: ours wins a clash).
# Safe to re-run: it replaces only links it owns.
#
#   ./install.sh                          # -> ~/.claude/skills
#   ./install.sh --project ~/code/myapp   # -> ~/code/myapp/.claude/skills
#   ./install.sh --only frontend-design,security-review
#   ./install.sh --vendor                 # + the 61 vendored skills
#   ./install.sh --copy                   # copy instead of symlink
#   ./install.sh --list
#   ./install.sh --remove                 # uninstall the linked ones
#   ./install.sh --dry-run
#
# Works on macOS bash 3.2.

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")" && pwd)
SKILLS_SRC="$REPO_DIR/skills"
VENDOR_SRC="$REPO_DIR/vendor"
TARGET="${HOME}/.claude/skills"
MODE="symlink"
ONLY=""
ACTION="install"
DRY=""
WITH_VENDOR=""

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project) TARGET="$2/.claude/skills"; shift 2 ;;
    --target)  TARGET="$2"; shift 2 ;;
    --only)    ONLY="$2"; shift 2 ;;
    --copy)    MODE="copy"; shift ;;
    --list)    ACTION="list"; shift ;;
    --remove)  ACTION="remove"; shift ;;
    --dry-run) DRY="1"; shift ;;
    --vendor)  WITH_VENDOR="1"; shift ;;
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 2 ;;
  esac
done

[ -d "$SKILLS_SRC" ] || { echo "no skills/ next to install.sh" >&2; exit 1; }

resolve_src() {
  name="$1"
  if [ -f "$SKILLS_SRC/$name/SKILL.md" ]; then
    echo "$SKILLS_SRC/$name"
    return 0
  fi
  if [ -d "$VENDOR_SRC" ]; then
    candidate=$(find "$VENDOR_SRC" -type f -name SKILL.md -path "*/$name/SKILL.md" \
      | sort | head -n 1)
    if [ -n "$candidate" ]; then
      echo "${candidate%/SKILL.md}"
      return 0
    fi
  fi
  return 1
}

# name|source|origin for every skill that will be touched, deduped by name.
each_selected() {
  {
    if [ -z "$ONLY" ]; then
      for d in "$SKILLS_SRC"/*/; do
        [ -f "${d}SKILL.md" ] || continue
        printf '%s|%s|own\n' "$(basename "$d")" "${d%/}"
      done
      # vendored libraries nest one or two levels deep (vendor/lib/name and
      # vendor/lib/group/name), so walk instead of globbing one level.
      if [ -n "$WITH_VENDOR" ] && [ -d "$VENDOR_SRC" ]; then
        find "$VENDOR_SRC" -type f -name SKILL.md | sort | while read -r manifest; do
          dir="${manifest%/SKILL.md}"
          rel="${dir#"$VENDOR_SRC"/}"
          printf '%s|%s|vendor/%s\n' "$(basename "$dir")" "$dir" "$(echo "$rel" | cut -d/ -f1)"
        done
      fi
    else
      echo "$ONLY" | tr ',' ' ' | tr ' ' '\n' | while read -r name; do
        [ -n "$name" ] || continue
        src=$(resolve_src "$name") || { echo "no such skill: $name" >&2; exit 1; }
        printf '%s|%s|x\n' "$name" "$src"
      done
    fi
  } | awk -F'|' '!seen[$1]++'
}

run() {
  if [ -n "$DRY" ]; then echo "would: $*"; else "$@"; fi
}

case "$ACTION" in
  list)
    # Listing is about what is IN the repo, so it always includes vendor.
    WITH_VENDOR="1"
    echo "skills in $REPO_DIR:"
    each_selected | while IFS='|' read -r name src origin; do
      desc=$(sed -n '3,4p' "$src/SKILL.md" | tr '\n' ' ' \
        | sed 's/^description: //' | cut -c1-70)
      printf '  %-34s %s\n' "$name" "$desc"
    done
    exit 0
    ;;
  remove)
    # Removing is about what IS linked; announcing 60 "not installed" lines for
    # skills the caller never installed is noise.
    each_selected | while IFS='|' read -r name src origin; do
      link="$TARGET/$name"
      if [ -L "$link" ]; then
        run rm -f "$link"; echo "unlinked $name"
      elif [ -e "$link" ]; then
        echo "skip $name: exists and is not a symlink (remove it yourself)" >&2
      fi
    done
    exit 0
    ;;
esac

[ -n "$DRY" ] || mkdir -p "$TARGET"

each_selected | while IFS='|' read -r name src origin; do
  dest="$TARGET/$name"
  rm -f "$dest" 2>/dev/null || true
  if [ "$MODE" = "symlink" ]; then
    run ln -sfn "$src" "$dest"
  else
    run rm -rf "$dest"
    run cp -R "$src" "$dest"
  fi
  printf 'installed %-34s -> %s\n' "$name" "$dest"
done

echo
echo "target: $TARGET ($MODE)"
echo "restart your agent so it re-reads the skills directory."

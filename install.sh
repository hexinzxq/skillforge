#!/usr/bin/env bash
# Install the skills in this repo into a skills directory, by symlink (default)
# or copy. Safe to re-run: it replaces only links it owns.
#
#   ./install.sh                          # -> ~/.claude/skills
#   ./install.sh --project ~/code/myapp   # -> ~/code/myapp/.claude/skills
#   ./install.sh --only ui-critique,test-gap
#   ./install.sh --copy                   # copy instead of symlink
#   ./install.sh --list
#   ./install.sh --remove                 # uninstall the linked ones
#   ./install.sh --dry-run
#
# Works on macOS bash 3.2.

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")" && pwd)
SKILLS_SRC="$REPO_DIR/skills"
TARGET="${HOME}/.claude/skills"
MODE="symlink"
ONLY=""
ACTION="install"
DRY=""

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
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
    -h|--help) usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 2 ;;
  esac
done

[ -d "$SKILLS_SRC" ] || { echo "no skills/ next to install.sh" >&2; exit 1; }

selected() {
  if [ -z "$ONLY" ]; then
    for d in "$SKILLS_SRC"/*/; do
      [ -f "${d}SKILL.md" ] && basename "$d"
    done
  else
    echo "$ONLY" | tr ',' ' ' | tr ' ' '\n' | while read -r n; do
      [ -n "$n" ] && echo "$n"
    done
  fi
}

validate_only() {
  for name in $(selected); do
    [ -f "$SKILLS_SRC/$name/SKILL.md" ] || { echo "no such skill: $name" >&2; exit 1; }
  done
}

run() {
  if [ -n "$DRY" ]; then echo "would: $*"; else "$@"; fi
}

case "$ACTION" in
  list)
    echo "skills in $SKILLS_SRC:"
    for name in $(selected); do
      [ -f "$SKILLS_SRC/$name/SKILL.md" ] || continue
      desc=$(sed -n '3,4p' "$SKILLS_SRC/$name/SKILL.md" | tr '\n' ' ' \
        | sed 's/^description: //' | cut -c1-88)
      printf '  %-16s %s\n' "$name" "$desc"
    done
    exit 0
    ;;
  remove)
    for name in $(selected); do
      link="$TARGET/$name"
      if [ -L "$link" ]; then
        run rm -f "$link"; echo "unlinked $name"
      elif [ -e "$link" ]; then
        echo "skip $name: exists and is not a symlink (remove it yourself)" >&2
      else
        echo "skip $name: not installed"
      fi
    done
    exit 0
    ;;
esac

validate_only
[ -n "$DRY" ] || mkdir -p "$TARGET"

for name in $(selected); do
  src="$SKILLS_SRC/$name"
  dest="$TARGET/$name"
  rm -f "$dest" 2>/dev/null || true
  if [ "$MODE" = "symlink" ]; then
    run ln -sfn "$src" "$dest"
  else
    run rm -rf "$dest"
    run cp -R "$src" "$dest"
  fi
  printf 'installed %-16s -> %s\n' "$name" "$dest"
done

echo
echo "target: $TARGET ($MODE)"
echo "restart your agent so it re-reads the skills directory."

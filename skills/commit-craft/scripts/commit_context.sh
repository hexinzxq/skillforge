#!/bin/sh
# Print the minimal context needed to write a commit message.
#
#   ./commit_context.sh          # staged if anything is staged, else working tree
#   ./commit_context.sh --staged # force the index
#   ./commit_context.sh --all    # everything unstaged + staged
#
# Deliberately POSIX sh: works in macOS bash 3.2, dash, busybox.

set -eu

mode="auto"
case "${1:-}" in
  --staged) mode="staged" ;;
  --all)    mode="all" ;;
  "")       ;;
  *) echo "usage: $0 [--staged|--all]" >&2; exit 2 ;;
esac

git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository" >&2; exit 1; }

if [ "$mode" = "auto" ]; then
  if [ -n "$(git diff --cached --name-only)" ]; then mode="staged"; else mode="all"; fi
fi

echo "== branch"
git branch --show-current 2>/dev/null || echo "(detached)"

echo
echo "== recent subjects (match this convention)"
git log -15 --format='%s' 2>/dev/null || echo "(no commits yet)"

echo
echo "== status"
git status --short

echo
echo "== diffstat"
if [ "$mode" = "staged" ]; then
  git diff --cached --stat
else
  { git diff --stat; git diff --cached --stat; } 2>/dev/null
fi

echo
echo "== diff"
if [ "$mode" = "staged" ]; then
  diff_text=$(git diff --cached)
else
  diff_text=$( { git diff; git diff --cached; } 2>/dev/null )
fi

if [ -z "$diff_text" ]; then
  echo "(nothing to commit)"
  exit 0
fi

lines=$(printf '%s\n' "$diff_text" | wc -l | tr -d ' ')
if [ "$lines" -gt 500 ]; then
  echo "(diff is $lines lines — showing the file list and the first 400 lines)"
  printf '%s\n' "$diff_text" | head -400
  echo "... truncated, run git diff yourself for the rest"
else
  printf '%s\n' "$diff_text"
fi

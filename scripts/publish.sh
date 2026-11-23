#!/usr/bin/env bash
# Publish this skill (the authoring source) to its public GitHub repo.
#
# Usage:
#   scripts/publish.sh -m "message"            # test, sync, commit, push
#   scripts/publish.sh -m "message" --dry-run  # everything except commit/push
#   scripts/publish.sh -m "message" --no-push  # commit locally, do not push
#
# Env:
#   ORCHESTRA_PUBLISH_DIR    clone path (default: ~/.cache/Oh-My-Orkestra)
#   ORCHESTRA_PUBLISH_URL    clone URL (default: the public repo)
#   ORCHESTRA_PUBLISH_REMOTE remote name (default: origin)
#   ORCHESTRA_PUBLISH_BRANCH branch name (default: main)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ORCHESTRA_PUBLISH_DIR:-$HOME/.cache/Oh-My-Orkestra}"
URL="${ORCHESTRA_PUBLISH_URL:-https://github.com/dontworryplz/Oh-My-Orkestra.git}"
REMOTE="${ORCHESTRA_PUBLISH_REMOTE:-origin}"
BRANCH="${ORCHESTRA_PUBLISH_BRANCH:-main}"
MSG=""
DRY_RUN=0
PUSH=1

die() { printf 'publish: %s\n' "$1" >&2; exit "${2:-1}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    -m|--message) MSG="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-push) PUSH=0; shift ;;
    -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" 2 ;;
  esac
done

[ -n "$MSG" ] || die "a commit message is required (-m \"...\")" 2

printf 'publish: source %s\n' "$SRC"
printf 'publish: target %s\n' "$DEST"

if [ ! -d "$DEST/.git" ]; then
  printf 'publish: cloning %s\n' "$URL"
  git clone -q "$URL" "$DEST"
fi

printf 'publish: running tests\n'
python3 -m unittest discover -s "$SRC/tests" -p "test_*.py" >/dev/null

printf 'publish: syncing files\n'
rsync -a --delete \
  --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.DS_Store' --exclude '.orchestra' --exclude '*.prev.md' \
  "$SRC/" "$DEST/"

cd "$DEST"
git add -A
if git diff --cached --quiet; then
  printf 'publish: already in sync, nothing to commit\n'
  exit 0
fi

printf 'publish: changes\n'
git diff --cached --stat | tail -n 20

if [ "$DRY_RUN" -eq 1 ]; then
  printf 'publish: dry run, commit and push skipped\n'
  exit 0
fi

git commit -q -m "$MSG"
printf 'publish: committed %s\n' "$(git log --oneline -1)"

if [ "$PUSH" -eq 0 ]; then
  printf 'publish: --no-push given, push skipped\n'
  exit 0
fi

git push "$REMOTE" "$BRANCH"
printf 'publish: pushed to %s/%s\n' "$REMOTE" "$BRANCH"

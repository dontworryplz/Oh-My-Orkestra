#!/usr/bin/env bash
set -euo pipefail

# Run a writable AGY specialist inside an isolated temporary git worktree.
# Usage:
#   worktree-run.sh --role sonnet-worker --repo /path/to/repo --prompt "..." [--keep]

ROLE="sonnet-worker"
REPO="."
PROMPT=""
KEEP=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --prompt) PROMPT="$2"; shift 2 ;;
    --keep) KEEP=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "Error: --prompt is required" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$REPO" rev-parse --show-toplevel)"
WT_DIR="/tmp/orchestra-wt-${ROLE}-$$"
BRANCH="orchestra/${ROLE}-$$"

cleanup() {
  if [[ "$KEEP" == "false" && -d "$WT_DIR" ]]; then
    git -C "$REPO_ROOT" worktree remove --force "$WT_DIR" >/dev/null 2>&1 || true
    git -C "$REPO_ROOT" branch -D "$BRANCH" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

git -C "$REPO_ROOT" worktree add -q -b "$BRANCH" "$WT_DIR" HEAD

set +e
python3 "$SCRIPT_DIR/agy_agent.py" run \
  --role "$ROLE" --allow-write --cwd "$WT_DIR" --prompt "$PROMPT"
RC=$?
set -e

echo "=== WORKTREE DIFF SUMMARY ($WT_DIR / $BRANCH) ===" >&2
git -C "$WT_DIR" status --short >&2
git -C "$WT_DIR" diff --stat >&2

if [[ "$KEEP" == "true" ]]; then
  echo "Kept worktree: $WT_DIR (branch: $BRANCH)" >&2
fi

exit "$RC"

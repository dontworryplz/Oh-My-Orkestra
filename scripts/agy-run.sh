#!/usr/bin/env bash
set -euo pipefail

# Safe wrapper for invoking Antigravity CLI (`agy`) as a specialized agent from OMP.
# Usage:
#   agy-run.sh <role-preset|raw-model> [options] -- "<prompt>"
#
# Role presets:
#   neon-reviewer       -> gemini-4-neon-xhigh (plan / read-only review)
#   hydrogen-debugger   -> gemini-4-hydrogen-xhigh (plan / deep debugging)
#   argon-explorer      -> gemini-4-argon-high (plan / 1M-context exploration)
#   opus-auditor        -> claude-opus-5-5-high (plan / security & integrity audit)
#   sonnet-worker       -> claude-sonnet-5-5-high (auto / bounded implementation)
#   neon-orchestrator   -> gemini-pro-orchestrator-neon (auto / autonomous sub-orchestrator)
#   argon-orchestrator  -> gemini-pro-orchestrator-g1-pro (auto / fast sub-orchestrator)

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <role-or-model> [--mode plan|auto|accept-edits] [--effort low|medium|high|xhigh|max] [--format text|json|stream-json] [--add-dir PATH] -- \"<prompt>\"" >&2
  exit 2
fi

ROLE_OR_MODEL="$1"
shift

MODE=""
EFFORT=""
FORMAT="text"
ADD_DIRS=()
PROMPT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --format)
      FORMAT="$2"
      shift 2
      ;;
    --add-dir)
      ADD_DIRS+=("--add-dir" "$2")
      shift 2
      ;;
    --)
      shift
      PROMPT="$*"
      break
      ;;
    *)
      if [[ -z "$PROMPT" ]]; then
        PROMPT="$1"
      else
        PROMPT="$PROMPT $1"
      fi
      shift
      ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "Error: empty prompt" >&2
  exit 2
fi

case "$ROLE_OR_MODEL" in
  neon-reviewer)
    MODEL="gemini-4-neon-xhigh"
    DEFAULT_MODE="plan"
    ;;
  hydrogen-debugger)
    MODEL="gemini-4-hydrogen-xhigh"
    DEFAULT_MODE="plan"
    ;;
  argon-explorer)
    MODEL="gemini-4-argon-high"
    DEFAULT_MODE="plan"
    ;;
  opus-auditor)
    MODEL="claude-opus-5-5-high"
    DEFAULT_MODE="plan"
    ;;
  sonnet-worker)
    MODEL="claude-sonnet-5-5-high"
    DEFAULT_MODE="auto"
    ;;
  neon-orchestrator)
    MODEL="gemini-pro-orchestrator-neon"
    DEFAULT_MODE="auto"
    ;;
  argon-orchestrator)
    MODEL="gemini-pro-orchestrator-g1-pro"
    DEFAULT_MODE="auto"
    ;;
  *)
    MODEL="$ROLE_OR_MODEL"
    DEFAULT_MODE="plan"
    ;;
esac

FINAL_MODE="${MODE:-$DEFAULT_MODE}"

CMD=(agy --model "$MODEL" --mode "$FINAL_MODE" --output-format "$FORMAT" --dangerously-skip-permissions)
if [[ -n "$EFFORT" ]]; then
  CMD+=(--effort "$EFFORT")
fi
if [[ ${#ADD_DIRS[@]} -gt 0 ]]; then
  CMD+=("${ADD_DIRS[@]}")
fi

# CRITICAL: Attach prompt directly to -p= so agy never misparses another flag as the prompt.
CMD+=("-p=${PROMPT}")

exec "${CMD[@]}"

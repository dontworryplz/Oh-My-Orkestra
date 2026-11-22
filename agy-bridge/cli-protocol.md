# Antigravity CLI (`agy`) Invocation Protocol

OMP agents with the `bash` tool can invoke `agy` directly as an autonomous agent process.

## Critical Flag Rule (`-p=`)

**NEVER** write `agy -p --model ... "prompt"` — `agy` treats the token immediately after `-p` as the prompt string and fails.
**ALWAYS** attach the prompt directly to `-p="..."` (with `=`) and place all other flags before it:

```bash
agy --model gemini-4-neon-xhigh --mode plan --output-format text --dangerously-skip-permissions -p="Review the staged diff in $PWD..."
```

Or use the bundled wrapper script:

```bash
"$HOME/.omp/agent/skills/sol-luna-orchestrator/scripts/agy-run.sh" \
  neon-reviewer -- "Review the staged diff in $PWD..."
```

## Execution Modes

- `--mode plan` — **Read-only / analysis**. Use for `neon-reviewer`, `hydrogen-debugger`, `argon-explorer`, and `opus-auditor`. Prevents accidental file edits.
- `--mode auto` — **Full agentic execution**. Use for `sonnet-worker` and `agy-orchestrator` when the agent is explicitly assigned disjoint file ownership and allowed to edit/run commands or spawn internal subagents.
- `--mode accept-edits` — Auto-approves file edits while keeping stricter command behavior.

## Useful Flags

- `--model <id>`: Exact model from `agy models` (e.g., `gemini-4-neon-xhigh`, `gemini-4-hydrogen-xhigh`, `gemini-4-argon-high`, `gemini-pro-orchestrator-neon`, `claude-opus-5-5-high`, `claude-sonnet-5-5-high`).
- `--effort <level>`: `low | medium | high | xhigh | max`.
- `--output-format <fmt>`: `text` (human/agent readable), `json` (single structured JSON object), `stream-json` (NDJSON events).
- `--json-schema <path-or-json>`: Enforce structured JSON output for automated review gates.
- `--add-dir <path>`: Grant access to an extra directory outside CWD.
- `--dangerously-skip-permissions`: Required for non-interactive headless `agy -p=...` runs inside OMP `bash` so it doesn't hang waiting for interactive TTY confirmation.
- `--print-timeout <duration>`: Optional hard cap (e.g., `180s`, `300s`).

## Role Presets in `scripts/agy-run.sh`

| Preset | Model | Default Mode |
|---|---|---|
| `neon-reviewer` | `gemini-4-neon-xhigh` | `plan` |
| `hydrogen-debugger` | `gemini-4-hydrogen-xhigh` | `plan` |
| `argon-explorer` | `gemini-4-argon-high` | `plan` |
| `opus-auditor` | `claude-opus-5-5-high` | `plan` |
| `sonnet-worker` | `claude-sonnet-5-5-high` | `auto` |
| `neon-orchestrator` | `gemini-pro-orchestrator-neon` | `auto` |
| `argon-orchestrator` | `gemini-pro-orchestrator-g1-pro` | `auto` |

## Failure & Quota Handling

- If `agy` exits non-zero or prints `429 RESOURCE_EXHAUSTED`, **do not fabricate its output**.
- Report the exact exit code/error and switch to the fallback agent defined in [../workflows/fallback-and-recovery.md](../workflows/fallback-and-recovery.md).

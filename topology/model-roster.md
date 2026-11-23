# Verified Model Roster

Only assign models that exist in the active runtime (`omp` models / `agy models`). Never invent an ID. Verify with:

```bash
orchestra doctor        # resolves every role in config/roles.json against live agy models
agy models              # raw list
```

## 1. OpenAI Codex (`openai-codex`) — Conductor, Task Management & Core Engineering

| Model ID | Context | Primary Role | Notes |
|---|---|---|---|
| `openai-codex/gpt-6.2-sol` | 500K | **Root Conductor** (`default`, `advisor`, `slow`, `smol`), infra audit | Best judgment/integration; default fallback for the whole chain |
| `openai-codex/gpt-6.2-astra` | 272K | **Architecture & Contract Analyst** (`designer`), API contract audit | Interfaces, invariants, edge-case matrices; fallback `gpt-6.2-sol` → `claude-opus-5-5` |
| `openai-codex/gpt-6-luna:max` | 272K | **Task Manager & Core Specialist** (`task`, `luna-*`, `terra-analyst`, `release-manager`) | Highest throughput for decomposition, implementation, testing |
| `google-antigravity/gemini-4-argon:high` | 1M | **Vision / Multimodal & 1M explorer** (`vision`, `plan`) | Screenshots, diagrams, UI visual inspection, broad repo map |

## 2. Anthropic (`anthropic`) — Deep Audit & Precision Implementation

| Model ID | Context | Primary Role | Notes |
|---|---|---|---|
| `anthropic/claude-opus-5-5` | 1M | **Security & Integrity Auditor** (`opus-auditor`, `security-reviewer`, `db-migration-auditor`, `threat-modeler`) | Slowest/strongest for auth, tenant isolation, data integrity, migrations |
| `anthropic/claude-sonnet-5-5` | 1M | **Implementation & Refactoring Worker** (`sonnet-worker`) | 1M context, strong code fluency; fallback → `agy claude-sonnet-5-5-high` → `luna-worker` |
| `anthropic/claude-mythos-5-2` | 1M | Optional heavy reasoning | Only when explicitly enabled for long-horizon design synthesis |
| `anthropic/claude-haiku-5-5` | 1M | Fast lightweight checks | Classification/formatting only; never a security or review gate |

## 3. Antigravity CLI (`agy`) & `google-antigravity`

Invocable via `orchestra run --role <role>` / `agy --model <id> -p="..."` / `agy-run.sh`:

| Model ID | Context | Primary Role | Notes |
|---|---|---|---|
| `gemini-4-neon-xhigh` / `high` / `medium` | 1M | **Neon Code Reviewer** (`neon-reviewer`) | Default review engine; `--auto-fallback` walks xhigh → high → medium |
| `gemini-4-hydrogen-xhigh` / `high` | 1M | **Hydrogen Debugger** (`hydrogen-debugger`), perf profiling | Root cause + concurrency/algorithm bottlenecks |
| `gemini-4-argon-high` / `medium` | 1M | **Argon Explorer** (`argon-explorer`) | Repo mapping, log/trace synthesis; `gemini-3.8-flash-high` for cheap triage |
| `gemini-pro-orchestrator-neon` | 1M | **Autonomous Sub-Orchestrator** (`neon-orchestrator`) | Internal `invoke_subagent`/`run_workflow`; depth ≤2 |
| `gemini-pro-orchestrator-g1-pro` | 1M | **Fast Sub-Orchestrator** (`argon-orchestrator`) | Lighter autonomous workflows / fallback for Neon orchestrator |
| `claude-opus-5-5-high` | 1M | **Antigravity Opus Auditor** (`opus-auditor`, `threat-modeler`) | Second opinion when the anthropic slot is unavailable |
| `claude-sonnet-5-5-high` | 1M | **Antigravity Sonnet Worker** (`sonnet-worker`) | Parallel writable implementation via `agy` |
| `gemini-3.8-flash-high` | 1M | Rapid plan / triage | Ultra-fast first pass, log triage, cheap fallback |

## 4. Assignment Rules

1. **One authority per decision.** No two agents own the same judgment (e.g. only `security-reviewer`/`opus-auditor` may pass a security gate).
2. **Cheapest sufficient model.** Default work → Luna; broad mapping → Argon; only gates escalate to Opus/Neon-xhigh.
3. **Reviewer independence.** Never let the model that wrote code be the reviewer that passes it. Prefer a different provider for the gate.
4. **Missing preferred model is not a blocker.** Use the documented fallback and report `fallback_from`.
5. **Do not auto-assign self-hosted/legacy IDs** (older Gemini 2.5/3.x, `tab_*`, image models) unless the task explicitly requires them.

## 5. Reserved / Unassigned

Do **not** auto-assign `gpt-image-2`, `gemini-3-pro-image`, `gemini-3.1-flash-image`, `tab_flash_lite_preview`, `tab_jump_flash_lite_preview`, or legacy `4.5`/`2.5` models — image generation or explicit legacy comparison only.

## 6. Availability & Cost Notes

| Situation | Response |
|---|---|
| Anthropic slot unavailable | `agy claude-opus-5-5-high` (same family, different harness) |
| Gemini 4 unavailable | `luna-reviewer` / `astra-architect` for review; state the degradation |
| Budget pressure | Shift mapping to `gemini-4-argon-medium`/`gemini-3.8-flash-high`; keep xhigh only for the final gate |
| Latency pressure | `gemini-pro-orchestrator-g1-pro`, Luna for execution; avoid stacking two Opus passes on one diff |

Telemetry for real usage lives in `~/.omp/agent/logs/orchestra-ledger.jsonl`; inspect with `orchestra stats`.

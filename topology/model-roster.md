# Verified Model Roster

Only assign models that exist in the active runtime (`omp` `models.db` or `agy models`). Never invent a model ID.

## 1. OpenAI Codex (`openai-codex`) — Conductor, Task Management & Core Engineering

| Model ID | Context | Primary Role in Orchestra |
|---|---|---|
| `openai-codex/gpt-6.2-sol` | 500K | **Root Conductor & Infra Auditor** (`default`, `advisor`, `slow`, `smol`) — decomposition, architecture, integration, final gate |
| `openai-codex/gpt-6.2-astra` | 272K | **Architecture & Contract Analyst** (`designer`) — cross-slice interfaces, invariants, edge cases |
| `openai-codex/gpt-6-luna:max` | 272K | **Task Manager & Core Specialist** (`task`, `luna-*`, `terra-analyst`) — task orchestration, implementation, testing, research, review |
| `google-antigravity/gemini-4-argon:high` | 1M | **Vision / Multimodal & 1M Explorer** (`vision`, `plan`) — screenshots, diagrams, UI visual inspection, broad repo mapping |

## 2. Anthropic (`anthropic`) — Deep Audit & Precision Implementation

| Model ID | Context | Primary Role in Orchestra |
|---|---|---|
| `anthropic/claude-opus-5-5` | 1M | **Security & Integrity Auditor** (`opus-auditor`) — auth, tenant isolation, data integrity, staged-change gate |
| `anthropic/claude-sonnet-5-5` | 1M | **Implementation & Refactoring Worker** (`sonnet-worker`) — bounded coding, UI/API integration, clean refactors |
| `anthropic/claude-mythos-5-2` | 1M | **Optional Heavy Reasoning** — long-horizon design synthesis if explicitly enabled |
| `anthropic/claude-haiku-5-5` | 1M | **Fast Lightweight Checks** — quick formatting/classification if explicitly needed |

## 3. Antigravity CLI (`agy`) & `google-antigravity` — Specialized External Agents

Invocable either via `agy` CLI (`scripts/agy-run.sh` or `agy --model ... -p="..."`) or OMP `antigravity-*` agents:

| `agy` Model ID | Context | Primary Role in Orchestra |
|---|---|---|
| `gemini-4-neon-xhigh` / `high` | 1M | **Neon Code Reviewer** (`neon-code-reviewer`) — deep code review, logic bugs, contract drift |
| `gemini-4-hydrogen-xhigh` / `high` | 1M | **Hydrogen Debugger** (`hydrogen-debugger`) — root-cause debugging, concurrency/race conditions, algorithms |
| `gemini-4-argon-high` / `medium` | 1M | **Argon Explorer** (`argon-explorer`) — broad 1M-context repo mapping, log/trace synthesis |
| `gemini-pro-orchestrator-neon` | 1M | **Autonomous Sub-Orchestrator** (`agy-orchestrator`) — multi-step sub-workflows with internal `agy` subagents |
| `gemini-pro-orchestrator-g1-pro` | 1M | **Fast Sub-Orchestrator** (`argon-orchestrator`) — lighter autonomous sub-workflows |
| `claude-opus-5-5-high` | 1M | **Antigravity Opus Auditor** (`antigravity-opus-reviewer`) — independent second-opinion security/architecture gate |
| `claude-sonnet-5-5-high` | 1M | **Antigravity Sonnet Worker** (`antigravity-sonnet-worker`) — parallel bounded implementation via Antigravity |
| `gemini-3.8-flash-high` | 1M | **Rapid Plan / Triage** (`plan`) — ultra-fast initial planning and log triage |

## Reserved / Unassigned Models

Do **not** auto-assign `gpt-image-2`, `gemini-3-pro-image`, `gemini-3.1-flash-image`, `tab_flash_lite_preview`, `tab_jump_flash_lite_preview`, or legacy `4.5`/`2.5` models unless a task explicitly requires image generation or legacy comparison.

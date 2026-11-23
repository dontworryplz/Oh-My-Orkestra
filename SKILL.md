---
name: sol-luna-orchestrator
description: "Multi-harness full-set orchestra for OMP, Antigravity CLI (`agy`), and Claude Code: GPT-6.2 Sol (Conductor), GPT-6 Luna (Task Manager & Core Specialist), GPT-6.2 Astra (Architecture), Claude Opus 5.5 / Sonnet 5.5 (Security & Implementation), and `agy` CLI specialists (Gemini 4 Neon Code Reviewer, Gemini 4 Hydrogen Debugger, Gemini 4 Argon 1M Explorer, Orchestrator Neon) with nested agent spawning, Grill-Me, Caveman, Trail-Code, GSD-Core, and Active MCP routing."
---

# Sol–Luna Full-Set Orchestra (OMP + Antigravity CLI + Claude Code)

A harness-agnostic, modular multi-model orchestration system working across **OMP**, **Antigravity CLI (`agy`)**, and **Claude Code**—coordinating **OpenAI Codex (GPT-6.2 Sol / GPT-6.2 Astra / GPT-6 Luna)**, **Anthropic (Claude 5.5)**, and **Google Antigravity (`agy` Gemini 4 Neon / Hydrogen / Argon / Orchestrators)** with controlled **nested agent spawning** and integrated **Grill-Me + Caveman + Trail-Code + GSD-Core + Active MCPs**.

## Harness Adaptation

- **In OMP:** Dispatch native `task` agents (`luna-task-manager`, `security-reviewer`, `astra-architect`, `sonnet-worker`, etc.) + `agy_agent.py` / `agy-run.sh` for Gemini 4 Neon/Hydrogen/Argon/Orchestrator.
- **In Antigravity CLI (`agy`):** Use native `invoke_subagent` / `run_workflow` for internal parallelism, and `agy_agent.py` (or `omp -p` when installed) for cross-model specialist passes.
- **In Claude Code:** Use native `Agent` subagents + `agy_agent.py` / `agy-run.sh` for Gemini 4 Neon/Hydrogen/Argon/Orchestrator.

## Modular Directory Map (Progressive Disclosure)

- **Topology & Roles**
  - [topology/model-roster.md](./topology/model-roster.md) — Verified model IDs across `openai-codex`, `anthropic`, `google-antigravity`, and `agy` CLI.
  - [topology/role-matrix.md](./topology/role-matrix.md) — Dedicated mission, authority, and boundaries for every model/agent.
- **Antigravity CLI (`agy`) Bridge & Nested Spawning**
  - [agy-bridge/cli-protocol.md](./agy-bridge/cli-protocol.md) — Exact `agy` CLI flags, `-p=` syntax, modes, JSON/text output, and error handling.
  - [agy-bridge/nested-spawning.md](./agy-bridge/nested-spawning.md) — Rules & guardrails for agents spawning subagents inside themselves (`task` + `agy`, max depth 2).
  - [config/roles.json](./config/roles.json) — Role-to-model routing config for `agy_agent.py`.
  - [config/review-schema.json](./config/review-schema.json) — Strict JSON schema for structured review verdicts (`--schema`).
  - [scripts/agy_agent.py](./scripts/agy_agent.py) — Structured Python adapter (`doctor`, `run`, `stats` telemetry ledger).
  - [scripts/agy-run.sh](./scripts/agy-run.sh) — Fast Bash wrapper for `agy` role presets.
  - [scripts/worktree-run.sh](./scripts/worktree-run.sh) — Isolated `git worktree` runner for parallel writable agents.
  - [scripts/sync-mcps.py](./scripts/sync-mcps.py) — Syncs active MCPs (`graft`, `trail`, `context7`, `TestSprite`, `aws-mcp`) into OMP & AGY.
  - [scripts/orchestra_tools.py](./scripts/orchestra_tools.py) — Ops toolkit: `guard`, `verify`, `redact`, `cost`, `handoff`.
  - [config/pricing.json](./config/pricing.json) — Approximate per-model token prices for `orchestra cost`.
  - [scripts/providers.py](./scripts/providers.py) — Direct OpenAI/Anthropic/Google review without `agy` (`orchestra review --provider`).
  - [hooks/pre-commit](./hooks/pre-commit) — Optional `trail check` + secret + structured `neon-reviewer` gates.
- **Execution Workflows**
  - [workflows/delegation-protocol.md](./workflows/delegation-protocol.md) — Decomposition, disjoint file ownership, task briefs, and parallel batching.
  - [workflows/review-and-qa-gates.md](./workflows/review-and-qa-gates.md) — Multi-model QA pipeline (Luna Tester -> Neon Code Reviewer -> Opus 5.5 Auditor -> Sol Gate).
  - [workflows/security-hardening.md](./workflows/security-hardening.md) — STRIDE threat modeling, OWASP/AuthZ/BOLA/SSRF/secret checks, infra/IAM audit, and dual-model red-team gate.
  - [workflows/session-handoff.md](./workflows/session-handoff.md) — `.orchestra/handoff.md` context-transfer protocol.
  - [workflows/fallback-and-recovery.md](./workflows/fallback-and-recovery.md) — `429 RESOURCE_EXHAUSTED` fallback chains, partial failures, and dirty-worktree preservation.
  - [workflows/ops-toolkit.md](./workflows/ops-toolkit.md) — Enforced guardrails: owned-path `guard`, evidence `verify`, secret `redact`, `cost`, `handoff`.
- **Integrated Sidekick Systems**
  - [integrations/grill-me.md](./integrations/grill-me.md) — Branch-by-branch decision interview before ambiguous/architectural work.
  - [integrations/caveman.md](./integrations/caveman.md) — Ultra-compressed output & inter-agent reporting (`lite` / `full` / `ultra`).
  - [integrations/trail-code.md](./integrations/trail-code.md) — `trail ask` before explore, `trail note` on learnings, `trail check` before commit.
  - [integrations/gsd-core.md](./integrations/gsd-core.md) — GSD phase lifecycle mapped to Orchestra specialists.
  - [integrations/active-mcps.md](./integrations/active-mcps.md) — Routing for `graft`, `codebase-memory-mcp`, `trail`, `context7`, `TestSprite`, `aws-mcp`, `node_repl`, `colab-mcp`.
- **Presets (End-to-End Playbooks)**
  - [presets/feature-build.md](./presets/feature-build.md) — Idea → locked decisions → contracts → parallel slices → multi-model gates → ship.
  - [presets/hard-bug-hunt.md](./presets/hard-bug-hunt.md) — Reproduction → Argon map → Hydrogen root cause → minimal fix → regression proof.
  - [presets/pr-review-gate.md](./presets/pr-review-gate.md) — Staged diff → risk route → Neon review → conditional specialists → verdict.
  - [presets/security-red-team.md](./presets/security-red-team.md) — STRIDE → source-to-sink audit → dual-model red team → fix + negative tests.
- **Examples & Contribution**
  - [examples/orchestra-flows.md](./examples/orchestra-flows.md) — Runnable end-to-end CLI runbooks.
  - [CONTRIBUTING.md](./CONTRIBUTING.md) — Add a role, agent, config mapping, and tests.

## Quick Routing Matrix

| Role / Mission | OMP `task` Agent | Model / Engine | Mode / Authority |
|---|---|---|---|
| **Root Conductor** | *(Active Root Session)* | `openai-codex/gpt-6.2-sol` | Architecture, contracts, integration, final gate |
| **Task Manager** | `luna-task-manager` | `openai-codex/gpt-6-luna:max` | Decomposes phases, spawns OMP/`agy` subagents |
| **Architecture Analyst** | `astra-architect` | `openai-codex/gpt-6.2-astra:high` | Interface design, invariants, edge-case matrix |
| **Research Analyst** | `terra-analyst` | `openai-codex/gpt-6-luna:max` | Primary-source docs (`context7`), spec verification |
| **Core Worker / Tester** | `luna-worker` / `luna-tester` | `openai-codex/gpt-6-luna:max` | Bounded implementation & empirical test execution |
| **Code Reviewer (Neon)** | `neon-code-reviewer` | `agy`: `gemini-4-neon-xhigh` | Deep code review, logic bugs, contract drift |
| **Deep Debugger (Hydrogen)** | `hydrogen-debugger` | `agy`: `gemini-4-hydrogen-xhigh` | Root-cause analysis, race conditions, algorithms |
| **1M Explorer (Argon)** | `argon-explorer` | `agy`: `gemini-4-argon-high` | Broad repo mapping, large logs, cross-file tracing |
| **Security Auditor** | `security-reviewer` / `opus-auditor` | `claude-opus-5-5:high` | Security boundaries, BOLA/SSRF/injection, dual-model red-team |
| **Threat Modeler** | `threat-modeler` | `agy`: `claude-opus-5-5-high` / `gemini-4-neon-xhigh` | Pre-code STRIDE threat model & abuse cases |
| **Infra / DevOps Auditor** | `infra-devops-auditor` | `gpt-6.2-sol:high` + `aws-mcp` | IAM least-privilege, Docker, CI/CD, CORS/CSP/TLS |
| **Perf Profiler** | `perf-profiler` | `agy`: `gemini-4-hydrogen-xhigh` | N+1 queries, memory leaks, lock contention, latency |
| **Visual / UI QA** | `ui-qa-reviewer` | `google-antigravity/gemini-4-argon:high` | Layout/responsive/WCAG/console/TestSprite QA |
| **DB & Migration Auditor** | `db-migration-auditor` | `anthropic/claude-opus-5-5:high` | Zero-downtime SQL/Prisma/Drizzle/Alembic checks |
| **API Contract Auditor** | `api-contract-auditor` | `openai-codex/gpt-6.2-astra:high` | OpenAPI/GraphQL/REST breaking-change & drift checks |
| **Release & PR Manager** | `release-manager` | `openai-codex/gpt-6-luna:max` | PR summary, CHANGELOG, breaking-change & `trail check` |
| **Parallel Worker (Claude)** | `sonnet-worker` / `antigravity-sonnet-worker` | `claude-sonnet-5-5:high` | Independent coding/UI/API slice, clean refactoring |
| **Sub-Orchestrator** | `agy-orchestrator` | `agy`: `gemini-pro-orchestrator-neon` | Autonomous multi-step sub-workflow with nested agents |

## Core Execution Sequence

0. **Tech-Stack & Repo Bootstrap (Mandatory on Session Start):** If `.orchestra/REPO_MAP.md` is missing or stale, run `orchestra init` (`scripts/discover-stack.py`) so every agent immediately knows the project's languages, frameworks, DB/ORM, test runners, scripts, directory layout, and `.orchestra/rules.md`.
1. **Memory & Graph First:** Run `trail ask` and `graft` / `codebase-memory-mcp` before broad file reads.
2. **Grill-Me (if ambiguous):** Resolve design forks branch-by-branch with recommended options before coding.
3. **Contract & Delegate:** Lock interfaces (`astra-architect`), then dispatch disjoint slices (`luna-task-manager`, `luna-worker`, `sonnet-worker`, `agy-orchestrator`).
4. **Verify & Audit:** `luna-tester` (empirical tests) -> `neon-code-reviewer` (`gemini-4-neon-xhigh`) -> `opus-auditor` (if security/data risk) -> `trail check` -> Sol final gate.
5. **Compress:** Use `caveman-lite` for inter-agent reports; preserve exact `file:line`, symbols, commands, and errors verbatim.

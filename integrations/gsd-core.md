# GSD-Core Lifecycle Integration (`open-gsd/gsd-core`)

Maps `gsd-core` project phases (`.planning/STATE.md`, `.planning/ROADMAP.md`, `SPEC.md`, `PLAN.md`, `VERIFICATION.md`) directly to Sol–Luna + AGY specialists.

## Full Phase-to-Orchestra Pipeline

| GSD Phase | Orchestra Lead | Supporting Specialists & Tools | Exit Gate / Artifact |
|---|---|---|---|
| **`gsd-map-codebase`** | `argon-explorer` (`gemini-4-argon-high`) | `orchestra init`, `graft`, `codebase-memory-mcp`, `trail ask` | `.orchestra/REPO_MAP.md` + `.planning/codebase/` |
| **`gsd-discuss-phase`** | Sol (`gpt-6.2-sol`) | **Grill-Me** (`integrations/grill-me.md`) + `trail ask` | Locked decisions & `SPEC.md` |
| **`gsd-plan-phase`** | `astra-architect` (`gpt-6.2-astra`) | `terra-analyst` (`context7` MCP), `threat-modeler` (if auth/DB) | `PLAN.md` with disjoint file slices & contracts |
| **`gsd-execute-phase`** | `luna-task-manager` (`gpt-6-luna:max`) | `luna-worker`, `sonnet-worker`, `agy-orchestrator`, `worktree-run.sh` | Implemented slices (no shared-file collisions) |
| **`gsd-validate-phase`** | `luna-tester` (`gpt-6-luna:max`) | `TestSprite` MCP, Vitest/Pytest/Go test, `ui-qa-reviewer` | Empirical test proof (`VERIFICATION.md`) |
| **`gsd-code-review`** | `neon-code-reviewer` (`gemini-4-neon-xhigh`) | `api-contract-auditor`, `perf-profiler`, `caveman-review` | `PASS` via `review-schema.json` |
| **`gsd-secure-phase`** | `security-reviewer` (`claude-opus-5-5:high`) | `db-migration-auditor`, `infra-devops-auditor`, `trail check` | Zero `P0`/`P1` findings + `STATE.md` updated |

## Execution Rules for GSD Phases

1. Never skip `gsd-plan-phase` contract locking when >1 writer will touch the phase.
2. Update `.planning/STATE.md` only after `luna-tester` + review gates actually pass—never mark a phase complete from model prose alone.
3. Full GSD skills & workflows live in `~/.claude/skills/gsd-*` and `~/.claude/gsd-core/` (or `~/.omp/agent/vendor/gsd-core` when installed via `install.sh`).

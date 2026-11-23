# GSD-Core Lifecycle Integration (`open-gsd/gsd-core`)

Maps `gsd-core` project phases (`.planning/STATE.md`, `.planning/ROADMAP.md`, `SPEC.md`, `PLAN.md`, `VERIFICATION.md`) onto Sol–Luna + AGY specialists. GSD owns the planning state; the orchestra owns execution, review, and evidence.

## Full Phase-to-Orchestra Pipeline

| GSD Phase | Orchestra Lead | Supporting Specialists & Tools | Exit Gate / Artifact |
|---|---|---|---|
| `gsd-map-codebase` | `argon-explorer` (`gemini-4-argon-high`) | `orchestra init`, `graft`, `codebase-memory-mcp`, `trail ask` | `.orchestra/REPO_MAP.md` + `.planning/codebase/` |
| `gsd-discuss-phase` | Sol (`gpt-6.2-sol`) | **Grill-Me** + `trail ask` | Locked Decisions Spec, `SPEC.md` |
| `gsd-plan-phase` | `astra-architect` (`gpt-6.2-astra`) | `terra-analyst` (`context7`), `threat-modeler` if auth/DB | `PLAN.md` with disjoint slices + contracts |
| `gsd-spec-phase` | Sol + `astra-architect` | `terraform`-style ambiguity scoring, `grill-me` | Ambiguity ≤ 3, `SPEC.md` accepted |
| `gsd-execute-phase` | `luna-task-manager` (`gpt-6-luna:max`) | `luna-worker`, `sonnet-worker`, `agy-orchestrator`, `worktree-run.sh` | Implemented slices, no shared-file collisions |
| `gsd-validate-phase` | `luna-tester` (`gpt-6-luna:max`) | `TestSprite`, Vitest/Pytest/Go test, `ui-qa-reviewer` | Empirical proof in `VERIFICATION.md` |
| `gsd-code-review` | `neon-code-reviewer` (`gemini-4-neon-xhigh`) | `api-contract-auditor`, `perf-profiler`, `caveman-review` | `PASS` via `config/review-schema.json` |
| `gsd-secure-phase` | `security-reviewer` (`claude-opus-5-5:high`) | `db-migration-auditor`, `infra-devops-auditor`, `trail check` | Zero `P0`/`P1`, `STATE.md` updated |
| `gsd-ui-phase` | `ui-qa-reviewer` | design tokens, screenshots, `TestSprite` visual diff | `UI-SPEC.md` conformance report |
| `gsd-ship` | `release-manager` | `trail check`, changelog, rollback plan | PR description + release notes |

## Execution Rules

1. **Never skip `gsd-plan-phase` contract locking** when more than one writer touches the phase.
2. **State reflects evidence, not prose.** Update `.planning/STATE.md` only after `luna-tester` and review gates actually pass — a phase is never "complete" because a model said so.
3. **Respect phase boundaries.** Work discovered mid-phase goes to the backlog/capture step, not silently into the current slice.
4. **Reconcile with `.orchestra/handoff.md`** at phase end: decisions, learnings, risks, and next action.
5. **GSD artifacts are the source of truth** for scope; if the code and `PLAN.md` disagree, report the drift and ask before expanding scope.
6. **Trail is shared memory:** learnings from a phase are captured with `trail note` before the phase closes.

## Installation & Layout

- Full GSD skills live in `~/.claude/skills/gsd-*` and `~/.claude/gsd-core/` (or `~/.omp/agent/vendor/gsd-core` when installed through `install.sh`).
- `install.sh` links GSD skills into OMP (`~/.omp/agent/skills/`) and AGY (`~/.gemini/antigravity-cli/skills/`) so the same commands work in every harness.
- `orchestra init` writes `.orchestra/REPO_MAP.md`, `.orchestra/stack-profile.json`, and `.orchestra/rules.md`; GSD phases read these at Step 0 instead of re-discovering the stack.

## Anti-Patterns

- Marking `VERIFICATION.md` from a model summary instead of a command output.
- Running `gsd-execute-phase` without a contract when slices collide on one file.
- Skipping `gsd-secure-phase` because "the diff is small" — small diffs break auth just as well.

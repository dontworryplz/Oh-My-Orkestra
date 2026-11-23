# Preset: Full Feature Build (`feature-build`)

End-to-end runbook for shipping a new feature (or a full GSD phase) through the orchestra. Use for anything touching more than one file or more than one layer (API + DB + UI).

## Phase 0 — Bootstrap (never skip)

```bash
orchestra init                 # writes .orchestra/REPO_MAP.md + .orchestra/stack-profile.json + .orchestra/rules.md
orchestra doctor               # confirms agy CLI, models, role routing
trail ask "<feature keywords>" --source
```

- Confirm from `REPO_MAP.md`: language(s), framework, DB/ORM + migration tool, test runner, package scripts, existing directory layout.
- Read `.orchestra/rules.md` if present — project constitution overrides any generic instinct.
- If `trail ask` returns a previously ruled-out design, reuse that reasoning instead of re-litigating it.

## Phase 1 — Scope & Decisions

1. `argon-explorer` (`agy --role argon-explorer --mode plan`) maps the touched call graph: entrypoint → guards → persistence → response.
2. **Grill-Me** (`integrations/grill-me.md`): resolve every open fork in dependency order — boundary/ownership → data model → failure semantics → compatibility/rollout. One question at a time, recommended option first.
3. Output a **Locked Decisions Spec** (5–10 bullets + explicit non-goals). No implementation before this exists.

## Phase 2 — Contract Locking

`astra-architect` (`gpt-6.2-astra:high`; fallback `gpt-6.2-sol:high` → `claude-opus-5-5:high`) produces:

- Exact interfaces: request/response schemas, DB migration shape, error contract, idempotency keys.
- **Disjoint ownership map** — one file per writer, no overlaps.
- Edge-case matrix: nil/empty, duplicate submit, concurrent update, partial failure, permission-denied.
- Verification plan: exact commands `luna-tester` must run after integration.

## Phase 3 — Parallel Execution

`luna-task-manager` (`gpt-6-luna:max`) dispatches, max 4 concurrent:

| Slice | Owner | Notes |
|---|---|---|
| Backend / domain logic | `luna-worker` | focused unit tests on owned files only |
| Frontend / UI | `sonnet-worker` | existing components + tokens, no second design system |
| Independent module | `agy-orchestrator` | run via `orchestra worktree --role neon-orchestrator` |
| Migration / schema | `luna-worker` + `db-migration-auditor` review before apply | expand → backfill → contract |

Rules: concurrent writers skip repo-wide build/lint/format; never two writers on one file; each brief carries objective, owned paths, non-goals, contract, validation, nesting instruction.

## Phase 4 — Gates (in order, no skipping)

1. `luna-tester` — actually runs tests/typecheck/build; observed output only.
2. `orchestra review --staged --auto-fallback` — structured Neon review via `config/review-schema.json`.
3. `security-reviewer` (`claude-opus-5-5:high`) if auth, permissions, tenant data, payments, uploads, webhooks, shell, or migrations touched.
4. `db-migration-auditor` if any DDL; `api-contract-auditor` if any wire format changed.
5. `ui-qa-reviewer` if frontend changed (loading/empty/error states, responsive, WCAG 2.2 AA, console).
6. `perf-profiler` if hot path, list endpoint, or N+1 risk.
7. `trail check` before commit.
8. **Sol final gate:** read the actual diff, confirm blockers closed, re-run the decisive command after the last edit.

## Abort / Stop Conditions

- Blast radius exceeds the ownership map → stop, return to `astra-architect`.
- Any `P0`/`P1` open at gate time → no delivery.
- Environment/credential blocked → report exact failing command, do not simulate success.

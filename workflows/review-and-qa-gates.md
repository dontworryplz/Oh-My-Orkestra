# Review & QA Gates (Multi-Model Verification)

Substantial changes pass an independent, multi-model pipeline before Sol declares completion. Each gate answers a different question; none substitutes for another.

| Gate | Question answered | Owner |
|---|---|---|
| 1 | Does it actually run? | `luna-tester` |
| 2 | Is the logic correct? | `neon-code-reviewer` |
| 3 | Is it safe and data-consistent? | `security-reviewer` / `opus-auditor` |
| 4 | Did the wire contract survive? | `api-contract-auditor` / `db-migration-auditor` |
| 5 | Did the UI hold up? | `ui-qa-reviewer` |
| 6 | Is the final state coherent? | Sol |

## Gate 1 — Empirical Execution (`luna-tester`)

- Agent: `luna-tester` (`openai-codex/gpt-6-luna:max`), optionally with `TestSprite`.
- Runs focused unit/integration tests, typecheck, lint, build, and real CLI/HTTP checks against the integrated change.
- **Rule:** a model opinion never replaces a command. Quote exact command + observed result (passed/failed counts).
- Tests must be able to fail: reject tautological assertions, mocks replacing the logic under test, snapshots with no invariant.

## Gate 2 — Deep Code Review (`neon-code-reviewer`)

```bash
orchestra review --staged --auto-fallback     # or: orchestra review
```

- Engine: `agy --role neon-reviewer --auto-fallback --mode plan`, structured against `config/review-schema.json`.
- Scope: `git diff` / `git diff --cached` **and touched callers** — a correct line can break a caller.
- Focus order: logic/invariants → contract drift → concurrency/idempotency → security regressions → verification quality.
- Verdict: `PASS` | `CHANGES REQUIRED` | `BLOCKED`, every finding with `file:line` + reachable scenario + smallest fix.
- Fallback: `gemini-4-neon-xhigh` → `-high` → `-medium` → `luna-reviewer`; if all fail, label the review `degraded` and do it read-only, never invent Neon's output.

## Gate 3 — Security & Data Integrity (`security-reviewer` / `opus-auditor`)

- Required when the change touches: auth/session, permissions, tenant isolation, payments, secrets, file uploads, webhooks, shell/exec, SQL, migrations, cloud/IAM config.
- Engine: `anthropic/claude-opus-5-5:high` (or `agy claude-opus-5-5-high`).
- High-risk scopes require **two independent models** (`security-reviewer` + `neon-reviewer`) to agree before merge.
- Every `P0`/`P1` must be fixed and re-verified with a negative regression test.

## Gate 4 — Contract Gates (conditional)

- `db-migration-auditor` — any DDL: lock matrix, expand/contract, irreversible loss, backfill batching.
- `api-contract-auditor` — any wire-format change: spec↔handler↔caller drift, stale generated clients.
- `infra-devops-auditor` — Docker/CI/IAM/CORS/CSP changes.

## Gate 5 — UI QA (conditional)

`ui-qa-reviewer` — state matrix (loading/empty/error/denied), responsive breakpoints, WCAG 2.2 AA, console/hydration hygiene.

## Gate 6 — Root Conductor Final Gate (`gpt-6.2-sol`)

Sol:

1. Reads the actual diff and decisive files — not only the reports.
2. Confirms every blocker is resolved and the fix did not introduce a new one.
3. Re-runs the decisive command **after the last edit** (stale green is not green).
4. Reports only observed results and states residual risks explicitly.

## Gate Arbitration

- Reviewers disagree → reproduce the scenario; evidence wins, not seniority.
- A finding is downgraded only with a cited guard that makes it unreachable; otherwise it stands.
- Missing gate (tool down, `429`) is reported as `NOT RUN`, never as `PASS`.
- P0/P1 open at any point → delivery blocked, no exceptions for deadlines.

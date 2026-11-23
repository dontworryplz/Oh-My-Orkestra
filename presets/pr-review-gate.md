# Preset: PR / Staged Review Gate (`pr-review-gate`)

Use before every commit on risky work, before opening a PR, or on a reviewer request. Goal: multi-model, evidence-backed verdict — not a prose opinion.

## Phase 0 — Know the target

```bash
git status --short
git diff --stat              # working tree
git diff --cached --stat     # staged
git log -n 5 --oneline
trail check                  # repository learnings still satisfied?
```

Decide explicitly whether the review target is committed, staged, or unstaged. Never review a mix silently.

## Phase 1 — Risk routing

```bash
orchestra route --staged     # or: orchestra route
```

`smart-route.py` classifies by diff size and changed paths (`auth`, `sql`/`migrations`, `iam`/`infra`, `openapi`/`graphql`, UI) and recommends the gates below.

## Phase 2 — Structured review

```bash
orchestra review --staged --auto-fallback
```

- Runs `neon-reviewer` (`gemini-4-neon-xhigh`, fallback → `-high` → `-medium`) against `config/review-schema.json`.
- Output is machine-shaped: `verdict` (`PASS` / `CHANGES REQUIRED` / `BLOCKED`), `findings[P0..P3]` with `file`, `line`, `fix`, plus `resolved_checks` and `residual_uncertainty`.
- If `agy` fails across all fallbacks, the reviewer must run the read-only review itself and label the degraded path; never fabricate Neon's verdict.

## Phase 3 — Conditional specialist gates

| Condition | Gate | Why |
|---|---|---|
| auth / permissions / tenant / secrets / shell / uploads / webhooks | `security-reviewer` (`claude-opus-5-5:high`) | Source-to-sink exploitability, BOLA/IDOR, SSRF |
| any DDL / schema change | `db-migration-auditor` | Lock matrix, expand/contract, irreversible loss |
| OpenAPI / GraphQL / tRPC / proto change | `api-contract-auditor` | Breaking vs safe matrix, stale generated clients |
| Dockerfile / CI / IAM / CORS / CSP | `infra-devops-auditor` | Least privilege, pinned SHAs, header policy |
| frontend components/state | `ui-qa-reviewer` | Loading/empty/error, responsive, a11y, console |
| list endpoint / hot loop / latency report | `perf-profiler` | N+1, missing index, unbounded query |

High-risk scopes (auth, billing, multi-tenant DB) require **two independent models** to agree before merge: `security-reviewer` + `neon-code-reviewer`.

## Phase 4 — Evidence and verdict

- Every finding: severity, exact `file:line`, reachable failure scenario, smallest fix, focused validation.
- `P0`/`P1` open → verdict is automatically `CHANGES REQUIRED`; no exceptions for "will fix later".
- Re-run only the gates affected by the fix, then re-check the final diff.

## Phase 5 — Optional automated gate

`hooks/pre-commit` runs `trail check`, and when `ORCHESTRA_REVIEW_GATE=1` also blocks on a non-`PASS` Neon verdict:

```bash
ln -sf "$HOME/.omp/agent/skills/sol-luna-orchestrator/hooks/pre-commit" .git/hooks/pre-commit
ORCHESTRA_REVIEW_GATE=1 git commit
```

## Reject-as-valid reasons

"Tests pass" alone, "small diff" alone, "mostly generated code", "reviewed in the last PR" — none of these replace the gates.

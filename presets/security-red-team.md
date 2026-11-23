# Preset: Security Red-Team Audit (`security-red-team`)

Use for auth/tenant/billing work, pre-release hardening, or an explicit attack-surface review. Model: threat model first, then two independent exploit-hunting passes.

## Phase 0 — Attack surface inventory

```bash
orchestra init --no-write
trail ask "security auth tenant secrets" --source
```

From `REPO_MAP.md` + graph queries establish: authentication mechanism (session/JWT/OAuth), authorization model (RBAC/ABAC/tenant scope), DB/ORM layer, file uploads, outbound HTTP, webhook receivers, shell/exec usage, secret storage, cloud/IAM surface.

Minimum 1M-context pass (`argon-explorer`) on the auth/guards/persistence path — not on the whole repo.

## Phase 1 — STRIDE threat model (pre-code)

`threat-modeler` (`agy --role threat-modeler --auto-fallback`, `claude-opus-5-5-high` / `gemini-4-neon-xhigh`, `--mode plan`):

- **Trust boundaries:** browser → API → service → DB; webhook providers; third-party APIs; LLM/external output; file uploads.
- **Assets:** PII, credentials, payment data, tenant business records, audit trail.
- **Abuse cases per STRIDE** (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, EoP), each tied to a concrete route/symbol.
- **Required pre-code controls + negative tests** that must exist before implementation ships.

## Phase 2 — Dual-model exploit audit (parallel)

```bash
# Gate A — Claude Opus 5.5
python3 "$HOME/.omp/agent/skills/sol-luna-orchestrator/scripts/agy_agent.py" run \
  --role opus-auditor --auto-fallback --cwd "$PWD" \
  --prompt "Audit <scope> for authN/authZ, tenant isolation, injection, SSRF, secrets, races. Read-only."

# Gate B — Gemini 4 Neon (independent)
orchestra run --role neon-reviewer --auto-fallback --cwd "$PWD" \
  --prompt "Independently audit <scope> for authZ bypass, tenant crossover, and unsafe sinks."
```

Checklist both passes must cover:

1. AuthN: hashing, JWT `alg`/`exp`/`iss`/`aud`, rotation, CSRF, rate limiting.
2. AuthZ: server-side `tenant_id`/`owner_id` from session context only; no client-supplied scope; every read/write/delete traced source-to-sink.
3. Injection: parameterized SQL, no shell string interpolation, path canonicalization, SSRF allowlist blocking `169.254.169.254`, `127.0.0.1`, private CIDRs.
4. Secrets & PII: no hardcoded keys, no tokens in logs/errors/prompts, redaction in telemetry.
5. Concurrency/integrity: transactions, idempotency keys, TOCTOU, mass assignment, webhook signature + replay protection.
6. Infra: permissive CORS (`*` + credentials), missing CSP/HSTS, insecure cookie flags, IAM wildcards, `:latest` images, unpinned Actions, `pull_request_target`.

## Phase 3 — Fix and prove

- `luna-worker` fixes `P0`/`P1` on owned files; each fix ships with a negative regression test that failed before.
- Re-run **both** gates after the fix; agreement required.
- `db-migration-auditor` if the fix touched schema; `infra-devops-auditor` if it touched cloud/CI config.

## Phase 4 — Report

`PASS` / `CHANGES REQUIRED` / `BLOCKED`, per finding: severity, `file:line`, reachable exploit, impact, smallest fix, verification. End with `resolved_checks` + `residual_uncertainty` (e.g. unknown prod row counts, unreadable legacy module).

## Non-Negotiables

- No finding without a reachable path (function-name "looks unsafe" is not a finding).
- No fabricated pass when a model was unavailable — state the failed slot.
- No `P0`/`P1` residual at delivery.

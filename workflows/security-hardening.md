# Security Hardening & Red-Team Workflow

Mandatory for changes touching authentication, authorization, multi-tenant data, payments, secrets, file uploads, external webhooks/APIs, SQL/migrations, shell execution, or cloud/IAM configuration. Doctrine: **prove the guard exists at the sink**, never assume it from a function name.

## 1. Security Tier Routing

| Phase | Owner | Engine | Output |
|---|---|---|---|
| Threat modeling (pre-code) | `threat-modeler` | `agy`: `claude-opus-5-5-high` / `gemini-4-neon-xhigh` | Trust boundaries, STRIDE abuse cases, required controls |
| Infra/IAM/CI audit | `infra-devops-auditor` | `gpt-6.2-sol:high` + `aws-mcp` | Least-privilege IAM, container/CI/header findings |
| Primary gate | `security-reviewer` | `anthropic/claude-opus-5-5:high` | Source-to-sink exploitability verdict |
| Independent second opinion | `neon-code-reviewer` | `agy`: `gemini-4-neon-xhigh` | Dual-model agreement on critical paths |
| Schema safety | `db-migration-auditor` | `claude-opus-5-5:high` | Lock matrix, data-loss risk, tenant FK integrity |
| Contract safety | `api-contract-auditor` | `gpt-6.2-astra:high` | Auth/error-envelope/webhook contract drift |

## 2. Mandatory Audit Checklist

1. **AuthN & session:** password/token hashing (bcrypt/argon2 — never md5/sha1), JWT signature + `alg` pinning (reject `none`, reject `HS256` when verification expects `RS256`), `exp`/`nbf`/`iss`/`aud`, session rotation on privilege change, CSRF on cookie-auth mutations, rate limiting + lockout on login/reset, uniform error messages (no user enumeration).
2. **AuthZ & tenant isolation (BOLA/IDOR):** trace every protected route → handler → query; `tenant_id`/`org_id`/`owner_id` must come from session context server-side, never from body/params/headers. Check list endpoints, exports (PDF/Excel), file download, and websocket subscriptions — not only CRUD.
3. **Injection & unsafe sinks:** parameterized SQL/ORM only (no string-interpolated queries, no `ORDER BY ${col}`), no shell concatenation (`exec`/`spawn` with `shell: true`), path canonicalization + prefix check against traversal, SSRF allowlist blocking `169.254.169.254`, `127.0.0.1`, `::1`, private CIDRs, redirect-following and DNS-rebinding, template/deserialization sinks.
4. **Secrets & data exposure:** no hardcoded keys/tokens in code, tests, fixtures, or prompts; `.env` not committed; logs/errors free of tokens, PII, full SQL; stack traces not returned in prod; exported files scoped to the authenticated tenant.
5. **Concurrency & integrity:** DB transactions around multi-write operations, unique constraints as the real idempotency guard, TOCTOU on balance/stock/chosen-slot, mass assignment (filtered DTO, never spreading `req.body` into ORM create/update), webhook signature + timestamp/replay window.
6. **Supply chain & headers:** `npm audit`/`pip-audit`/`govulncheck` on dependency changes; lockfile committed; CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`; CORS explicit origins with credentials (never `*`); cookie `HttpOnly`/`Secure`/`SameSite`.

## 3. Severity Model

| Severity | Meaning | Action |
|---|---|---|
| `P0 Critical` | Reachable exploit: cross-tenant read/write, auth bypass, RCE, secret exposure | Block delivery; fix + negative test now |
| `P1 High` | Exploitable with a plausible precondition, or data-integrity loss | Block delivery |
| `P2 Medium` | Defense-in-depth gap, hardening, unclear exploit path | Fix in same change or file explicitly |
| `P3 Low` | Hygiene, verbose error, minor header | Note with owner |

## 4. Dual-Model Red-Team Gate (high-risk scopes)

Run `security-reviewer` (Claude Opus 5.5) and `neon-code-reviewer` (Gemini 4 Neon) **independently** — do not feed one model the other's findings before it has finished, or you lose the disagreement signal.

- Both `PASS` → gate passes.
- Disagreement → reproduce the scenario; the reachable evidence wins.
- One model unavailable → report `NOT RUN` for that slot; do not claim dual verification.

## 5. Fix Discipline

- Fix the source cause, not the symptom (no `try/catch` masking, no client-side-only checks).
- Each `P0`/`P1` fix ships with a negative regression test that fails before and passes after.
- Re-run both gates after the fix; then `trail note` the vulnerability class and guard so it is not reintroduced.

## 6. Reporting

Per finding: severity, title, exact `file:line`, source→sink path, reachable scenario, impact, smallest fix, verification. End with `resolved_checks` and `residual_uncertainty` (e.g. unreadable infra config, unknown prod data, third-party behavior).

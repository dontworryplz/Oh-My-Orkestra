# Security Hardening & Red-Team Workflow

Mandatory for any change touching authentication, authorization, multi-tenant data, payments, secrets, file uploads, external webhooks/APIs, SQL/migrations, shell execution, or cloud/IAM configs.

## 1. Security Tier Routing

| Phase | Owner | Engine | Output |
|---|---|---|---|
| **Threat Modeling (Pre-Code)** | `threat-modeler` | `agy`: `claude-opus-5-5-high` / `gemini-4-neon-xhigh` | STRIDE matrix, trust boundaries, abuse cases |
| **Infra / IAM / CI-CD Audit** | `infra-devops-auditor` | `gpt-6.2-sol:high` + `aws-mcp` | Least-privilege IAM, container/CI/CORS/CSP findings |
| **Primary Security Gate** | `security-reviewer` | `anthropic/claude-opus-5-5:high` | Source-to-sink exploitability audit (`PASS`/`CHANGES REQUIRED`/`BLOCKED`) |
| **Independent Second Opinion** | `neon-code-reviewer` | `agy`: `gemini-4-neon-xhigh` | Dual-model verification on critical/P0 paths |

## 2. Mandatory Audit Checklist

1. **AuthN & Session Security:** Password/token hashing, JWT `alg`/exp/aud/iss validation, session rotation, CSRF protection, rate limiting on auth endpoints.
2. **AuthZ & Tenant Isolation (BOLA/IDOR):** Every read/write/delete query scopes by authenticated `tenant_id` / `org_id` / `owner_id` server-side—never trust client-supplied IDs or role flags.
3. **Injection & Command Execution:** Parameterized SQL/ORM queries, no raw string interpolation in shell/exec/templates, strict path canonicalization against traversal (`../`), SSRF URL/IP allowlisting (block `169.254.169.254`, `127.0.0.1`, private CIDRs).
4. **Secrets & Data Exposure:** Zero hardcoded API keys, tokens, or `.env` leaks in code, logs, error responses, or model prompts. Redact PII/credentials in telemetry.
5. **Concurrency & Data Integrity:** Atomic transactions, idempotency keys for retries/webhooks, protection against TOCTOU race conditions and mass assignment.
6. **Supply Chain & Runtime Hardening:** Run ecosystem audit (`npm audit`, `pip-audit`, etc.) when dependencies change; verify security headers (`CSP`, `HSTS`, `X-Content-Type-Options`) and strict CORS origins.

## 3. Dual-Model Red-Team Gate (High-Risk Scopes)

For high-risk PRs or security-critical slices:
- Run **both** `security-reviewer` (`Claude Opus 5.5`) and `neon-code-reviewer` (`Gemini 4 Neon`) independently.
- Every `P0 Critical` or `P1 High` finding blocks delivery until fixed and re-verified with focused regression tests (`luna-tester`).

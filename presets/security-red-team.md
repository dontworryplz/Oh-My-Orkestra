# Preset: Security Red-Team Audit (`security-red-team`)

1. `orchestra init --no-write` + `trail ask "security auth tenant"` -> map auth, DB/ORM, and infra layout.
2. `threat-modeler` (`agy`: `claude-opus-5-5-high`) -> STRIDE matrix, trust boundaries, abuse cases.
3. Parallel Dual-Model Audit:
   - `security-reviewer` (`anthropic/claude-opus-5-5:high`) -> AuthN/AuthZ/BOLA, SQLi, SSRF, secrets, races
   - `neon-code-reviewer` (`agy`: `gemini-4-neon-xhigh`) -> independent second opinion
   - `infra-devops-auditor` (`gpt-6.2-sol:high` + `aws-mcp`) -> IAM, Docker, CI/CD, CORS/CSP/TLS
4. Fix all `P0`/`P1` findings (`luna-worker`), add negative regression tests (`luna-tester`), re-run both reviewers until `PASS`.

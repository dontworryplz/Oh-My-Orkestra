# Review & QA Gates (Multi-Model Verification)

Substantial changes pass through an independent, multi-model verification pipeline before Sol declares completion.

## Gate 1: Empirical Execution (`luna-tester`)
- **Agent:** `luna-tester` (`openai-codex/gpt-6-luna:max`)
- **Action:** Runs focused unit/integration tests, typechecks, linters, and real runtime/CLI checks against the integrated change.
- **Rule:** Never substitute a model opinion for actual command execution.

## Gate 2: Deep Code Review (`neon-code-reviewer`)
- **Agent:** `neon-code-reviewer` -> `agy --model gemini-4-neon-xhigh --mode plan`
- **Action:** Reviews `git diff` / `git diff --cached` and touched callers for logic bugs, invariant violations, error paths, edge cases, and contract drift.
- **Verdict:** `PASS`, `CHANGES REQUIRED`, or `BLOCKED` with exact `file:line` evidence.

## Gate 3: Security & Data-Integrity Audit (`opus-auditor` / `antigravity-opus-reviewer`)
- **Agent:** `opus-auditor` (`anthropic/claude-opus-5-5:high`) or `antigravity-opus-reviewer` (`google-antigravity/claude-opus-5-5:high`)
- **When required:** Any change touching auth, permissions, tenant isolation, DB migrations, secrets, external webhooks/APIs, or pre-commit final gate on high-risk work.
- **Verdict:** `PASS`, `CHANGES REQUIRED`, or `BLOCKED`. Every `P0`/`P1` finding must be fixed and re-verified before delivery.

## Gate 4: Root Conductor Final Gate (`gpt-6.2-sol`)
- Sol inspects the actual diff/files, verifies all review blockers are resolved, confirms final test output after the last edit, and reports only directly observed results and residual risks.

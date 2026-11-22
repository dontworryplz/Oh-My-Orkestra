# Preset: PR / Staged Review Gate (`pr-review-gate`)

1. `orchestra route --staged` -> classify diff size and risk (`security`, `infra`, `ui`).
2. `orchestra review --staged --auto-fallback` -> run structured `neon-reviewer` (`config/review-schema.json`).
3. If `flags.security == true`: run `security-reviewer` (`claude-opus-5-5:high`).
4. If `flags.infra == true`: run `infra-devops-auditor`.
5. If `flags.ui == true`: run `ui-qa-reviewer`.
6. Run `trail check` and `luna-tester` focused tests before commit/merge.

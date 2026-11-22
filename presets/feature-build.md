# Preset: Full Feature Build (`feature-build`)

1. `orchestra init` -> generate `.orchestra/REPO_MAP.md` & `.orchestra/stack-profile.json`.
2. `trail ask "<feature>" --source` + `graft` -> inspect existing patterns and ruled-out designs.
3. **Grill-Me** (`integrations/grill-me.md`) -> resolve all open design forks with recommended options.
4. `astra-architect` (fallback: `gpt-6.2-sol` -> `claude-opus-5-5`) -> lock interfaces, DB/API contracts, and disjoint file map.
5. `luna-task-manager` -> dispatch parallel `luna-worker` / `sonnet-worker` / `agy-orchestrator` slices (isolated via `worktree-run.sh` when needed).
6. **Gates:** `luna-tester` -> `neon-code-reviewer` -> `security-reviewer` (if auth/DB/tenant) -> `ui-qa-reviewer` (if UI) -> `trail check` -> Sol final gate.

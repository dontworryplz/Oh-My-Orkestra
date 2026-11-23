# Changelog

All notable changes to Oh-My-Orkestra. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-11-23

### Added
- `orchestra gate` — one command, one verdict: secret scan → detected checks → schema-validated model review, written to `.orchestra/gate.json` (exit 1 on any failing step).
- `orchestra phase start|end|status|list` — phase tracking in `.orchestra/phase.json`; `orchestra cost --by phase` attributes ledger runs to the phase they happened in.
- `orchestra validate --file verdict.json` — dependency-free JSON Schema subset validation of review verdicts (exit 5 when invalid).
- Review schema self-healing: `gate` validates the verdict and retries once with the schema errors appended to the prompt.
- `orchestra redact --history` — scans added lines across git history with commit/path/line attribution; `--allow kind:<name>|<path glob>` suppresses intentional fixtures.
- `orchestra cost --csv` — per-model CSV export for spreadsheets.
- `orchestra doctor --fix` — idempotent re-link/repair via `install.sh --repair`.
- `orchestra uninstall` — removes the symlinks and copied agent files the installer created (keeps config, ledger, `.orchestra/`).
- `scripts/publish.sh` — tests → sync → commit → push in one step, with `--dry-run` and `--no-push`.

### Changed
- `verify` logic extracted into `run_checks()` so `gate` reuses the same detection, timeouts, and evidence file.
- Chrome-level cleanup: agent docs no longer name third-party skills; they point at this repo's workflows.

## [0.4.0] - 2026-11-23

### Added
- `orchestra guard --owned <globs>` — fails (exit 3) when a slice's diff leaves its owned paths; supports `--base`, `--ignore`.
- `orchestra verify` — detects and runs `test`/`typecheck`/`lint` from the stack profile and manifests, writes `.orchestra/evidence.json`.
- `orchestra redact` — masks provider keys, JWTs, DB URLs, private keys and secret assignments; `--check` exits 4 for CI/hooks.
- `orchestra cost` — per-model/per-role token and USD estimate from the ledger with `config/pricing.json`.
- `orchestra handoff` — generates `.orchestra/handoff.md` from git + ledger + verify evidence, preserving hand-written sections.
- `orchestra version` + `VERSION` file.
- `ORCHESTRA_SECRET_GATE` pre-commit gate; `ORCHESTRA_LEDGER` override for tests/CI.
- `workflows/ops-toolkit.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, multi-version CI.

### Changed
- Full playbook rewrites: `presets/*`, `workflows/*`, `integrations/*`, `topology/model-roster.md`, `omp-agents/*`.
- `topology/role-matrix.md` — specialist tier (security, threat-model, infra, perf, UI QA, DB migration, API contract, release) plus sole-authority table.
- `install.sh` links the installed copy and `bin/orchestra` correctly; new scripts are made executable.

### Fixed
- Duplicate/stale skill copy between `~/.omp/agent/skills` and the authoring directory.
- `oran-explorer` → `argon-explorer` typo in `omp-agents/sonnet-worker.md`.
- Owned-path globs no longer let `*` cross `/`; secret spans no longer re-mask each other.

## [0.3.0] - 2026-11-22

### Added
- `db-migration-auditor`, `api-contract-auditor`, `release-manager` roles.
- `orchestra doctor --mcps`, `orchestra stats --budget`.
- Trail-Code, GSD-Core, active-MCP integration docs; `workflows/rules.md`.
- Unit tests for `agy_agent.py` (auto-fallback, stack discovery, smart routing).

### Changed
- Role matrix and roster aligned with live `agy` model IDs (no `5.6` / `6.1`).

## [0.2.0] - 2026-11-21

### Added
- `orchestra init` / `discover-stack.py`, `orchestra route` / `smart-route.py`, `orchestra review`.
- `agy_agent.py` with `doctor`, `run`, `stats`, `--auto-fallback`, JSON schema reviews.
- Nested spawning guardrails (depth 2), isolated `git worktree` runner.

## [0.1.0] - 2026-11-20

### Added
- Initial multi-harness skill: OMP `task` agents, `agy` bridge, Claude Code subagents.
- Model topology, role matrix, install script, pre-commit hook.

# Ops Toolkit: guard, verify, redact, cost, handoff

Five commands that enforce rules the docs otherwise only recommend. All emit JSON (composable with `jq`) and use meaningful exit codes so they work in CI and git hooks.

## 1. `orchestra guard` — owned-path enforcement

Subagents are told "only edit these files"; this proves it.

```bash
orchestra guard --owned "src/api/**,src/ui/**" --ignore ".orchestra/**"
```

- Compares `git diff HEAD` + untracked files (or `--base <ref>` for a branch diff) against owned globs.
- Semantics: `dir/**` = dir and below, `src` = exact file or dir prefix, `docs/*/x.md` = one segment per `*`.
- Exit `3` on violation; payload lists `changed_files` + `violations` so the parent can revert only those paths.
- Typical use: wrap a writable agent, then `orchestra guard --owned "<same globs>"` before accepting its diff.

## 2. `orchestra verify` — empirical evidence, recorded

```bash
orchestra verify --dry-run            # show what would run
orchestra verify --only test          # single kind
orchestra verify --cmd "smoke=node scripts/smoke.mjs" --stop-on-fail
```

- Derives checks from `.orchestra/stack-profile.json` + `package.json` scripts + manifests:
  JS: `typecheck`/`lint`/`test` scripts via npm/pnpm/yarn/bun; Go `go test ./...`; Rust `cargo test`; Python `pytest -q`/`mypy`/`ruff`.
- Writes `.orchestra/evidence.json` (cmd, exit, duration, last 20 output lines, timestamp) — the artifact `orchestra handoff` cites.
- Kinds: `test`, `typecheck`, `lint`. Exit `1` if any check fails, `2` if nothing is detected or a `--cmd` spec is malformed.
- Never fabricate: `luna-tester` reports verify output, not its expectation.

## 3. `orchestra redact` — secrets never reach a model

```bash
orchestra redact --staged --check                # CI / pre-commit: exit 4 on any hit
orchestra redact --staged --output /tmp/diff.txt # masked copy for a prompt
git diff | orchestra redact                      # stdin
```

Detected classes: private keys, AWS access keys, GitHub/OpenAI/Anthropic/Google/Slack/Stripe tokens, JWTs, bearer tokens, credentialed DB URLs, and `*_SECRET|TOKEN|PASSWORD|API_KEY = ...` assignments.

- `--check` never prints the secret; findings carry `kind`, `line`, and a masked preview (`AKIA…REDACTED(20 chars)`).
- Overlap rule: the earliest, most specific pattern owns the span, so a secret is never double-labelled.
- Non-overlapping spans are masked as `REDACTED:<kind>`; the rest of the diff stays readable.
- This is a guardrail, not a guarantee — rotate anything that was already exposed.

## 4. `orchestra cost` — budget reality check

```bash
orchestra cost --days 7
orchestra cost --pricing config/pricing.json --out /tmp/cost.json
```

- Aggregates `~/.omp/agent/logs/orchestra-ledger.jsonl` (override with `ORCHESTRA_LEDGER`).
- Prices come from `config/pricing.json` (per 1M tokens, approximate — verify with the provider).
- Models without pricing appear in `unpriced_models`; runs without `usage` are counted but not priced (`runs_with_token_usage`).
- Shows cost by model **and** by role, so you can see whether the review gate or the workers dominate spend.

## 5. `orchestra handoff` — resumable context

```bash
orchestra handoff                 # print markdown
orchestra handoff --write         # write .orchestra/handoff.md (backs up to handoff.prev.md)
```

- Fills branch, dirty files, diff stat, recent commits, recent ledger runs, stack facts, and `verify` evidence automatically.
- Carries forward the human-authored sections (locked decisions, remaining tasks, open risks) on regeneration; placeholder `<fill: ...>` lines are dropped instead of accumulating.
- Written report is a claim about state — the resuming agent still verifies against `git diff`.

## CI Wiring Example

```yaml
- run: orchestra redact --staged --check   # or: git diff origin/main | orchestra redact
- run: orchestra verify --only test
```

```bash
# .git/hooks/pre-commit
export ORCHESTRA_SECRET_GATE=1
export ORCHESTRA_REVIEW_GATE=1
```

## Exit Code Summary

| Code | Meaning |
|---|---|
| `0` | Clean / passing |
| `1` | Check failed (`verify`), or gate blocked |
| `2` | Bad invocation / nothing to run |
| `3` | Owned-path violation (`guard`) |
| `4` | Secret detected (`redact --check`) |

# Orchestra End-to-End Flows

Concrete runbooks. All paths assume `orchestra` is on `PATH` (`~/.local/bin/orchestra` → skill `bin/orchestra`) and the skill is installed for the active harness.

## 0. First Run In A Repo

```bash
orchestra init                       # .orchestra/REPO_MAP.md, stack-profile.json, rules.md
orchestra doctor                     # agy CLI + models + role routing
orchestra doctor --mcps              # MCP binaries present in PATH?
orchestra sync-mcps                  # mirror Claude/Codex MCPs into OMP + AGY
trail ask "<first task>" --source
```

Read `.orchestra/REPO_MAP.md` and `.orchestra/rules.md` before the first delegation. If `rules.md` is empty, ask the user for the 3–5 non-negotiable project rules and write them.

## 1. Full Feature / GSD Phase

1. `trail ask "<feature>" --source` + `graft`/`argon-explorer` → callers and invariants.
2. **Grill-Me** → Locked Decisions Spec (no coding before this).
3. `astra-architect` → interfaces, ownership map, edge cases, verification plan.
4. `luna-task-manager` dispatches ≤4 slices:
   - `luna-worker` on backend (`src/api/**`)
   - `sonnet-worker` on frontend (`src/ui/**`)
   - `orchestra worktree --role neon-orchestrator` for an independent module
5. Gates: `luna-tester` → `orchestra review --staged` → `security-reviewer` (if auth/tenant/DB) → `ui-qa-reviewer` (if UI) → `trail check`.
6. Sol final gate: read the diff, re-run the decisive command, report in `caveman-lite`.

## 2. Direct `agy` Role Invocation

```bash
# health
python3 ~/.omp/agent/skills/sol-luna-orchestrator/scripts/agy_agent.py doctor

# structured review with fallback
orchestra run --role neon-reviewer --auto-fallback --cwd "$PWD" \
  --schema ~/.omp/agent/skills/sol-luna-orchestrator/config/review-schema.json \
  --prompt "Review git diff for correctness, auth boundaries, and missing edge cases."

# root cause only
orchestra run --role hydrogen-debugger --auto-fallback --cwd "$PWD" --prompt "Bug: <symptom> Reproduce: <cmd>"

# large repo map
orchestra run --role argon-explorer --auto-fallback --cwd "$PWD" --prompt "Trace how a contract payment reaches the ledger."
```

## 3. Staged Review Before Commit

```bash
git add -p
orchestra route --staged
orchestra review --staged --auto-fallback
# conditional gates from the report, then:
trail check
```

With the optional hook: `ORCHESTRA_REVIEW_GATE=1 git commit`.

## 4. Isolated Writable Agent

```bash
orchestra worktree --role sonnet-worker -- "Implement <slice> in src/ui/**. Owned: src/ui/**. Non-goals: shared configs."
# inspect the printed diff stat; --keep to retain the worktree for further review
```

## 5. Hard Bug

```bash
trail ask "<bug area>"            # has this been chased?
# reproduce, capture exact output
orchestra run --role hydrogen-debugger --auto-fallback --cwd "$PWD" --prompt "..."
# fix in a bounded worker, then regression test + review gate
trail note --title "<root cause>"
```

## 6. Security Pass

```bash
orchestra run --role threat-modeler --auto-fallback --cwd "$PWD" --prompt "STRIDE model for <feature>"
orchestra run --role opus-auditor --auto-fallback --cwd "$PWD" --prompt "Audit <scope> source-to-sink"
orchestra review --staged --auto-fallback            # independent second opinion
```

## 7. Telemetry & Cost

```bash
orchestra stats
orchestra stats --budget 200        # daily call budget check
```

Ledger: `~/.omp/agent/logs/orchestra-ledger.jsonl`.

## 8. Resume After Interruption

```bash
cat .orchestra/handoff.md
git status --short && git log -n 5 --oneline
trail ask "<topic>"
```

Verify in-flight slices against the actual diff before dispatching anything new.

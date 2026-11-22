# Orchestra End-to-End Flows

## 1. Full Feature / GSD Phase Flow

1. **Memory & Graph:** `trail ask "<feature>" --source` + `graft` / `argon-explorer` maps callers & invariants.
2. **Grill-Me:** Sol walks unresolved design forks with the user (recommended option first) until zero ambiguity remains.
3. **Contract:** `astra-architect` (`gpt-6.2-astra`) locks types, API boundaries, and disjoint file ownership.
4. **Parallel Execution:** `luna-task-manager` (`gpt-6-luna:max`) dispatches:
   - `luna-worker` on backend slice (`src/api/**`)
   - `sonnet-worker` on frontend slice (`src/ui/**`)
5. **QA & Multi-Model Review:**
   - `luna-tester` runs focused tests (`TestSprite` / `vitest` / `pytest`)
   - `neon-code-reviewer` (`agy: gemini-4-neon-xhigh`) reviews `git diff`
   - `opus-auditor` (`claude-opus-5-5:high`) audits auth/tenant/data boundaries
   - `trail check` verifies repo learnings
6. **Delivery:** Sol inspects final diff + test output and reports in `caveman-lite`.

## 2. Direct `agy_agent.py` CLI Usage

```bash
python3 ~/.omp/agent/managed-skills/sol-luna-orchestrator/scripts/agy_agent.py doctor

python3 ~/.omp/agent/managed-skills/sol-luna-orchestrator/scripts/agy_agent.py run \
  --role neon-reviewer --cwd "$PWD" \
  --prompt "Review git diff for correctness, auth boundaries, and missing edge cases."
```

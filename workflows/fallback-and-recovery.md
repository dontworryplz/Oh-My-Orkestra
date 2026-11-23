# Fallback & Recovery

Behaviour when a provider, model, CLI, or worker fails. Rule zero: **degrade honestly, never fabricate a result.**

## 1. Quota / `429 RESOURCE_EXHAUSTED` / Auth Failure / Timeout

1. Report which slot failed, the exact error, and which fallback answered — never present a fallback verdict as the original model's.
2. Use `--auto-fallback` (or `orchestra run --auto-fallback`) so `agy_agent.py` walks the ordered model list in `config/roles.json` and returns `fallback_from` + `attempts`.
3. Verified chains (each stage only after the previous fails):

| Role | Chain |
|---|---|
| Sol (conductor) | `gpt-6.2-sol` → `gpt-6-luna:max` → `claude-opus-5-5` |
| `astra-architect` | `gpt-6.2-astra` → `gpt-6.2-sol` → `claude-opus-5-5` |
| `luna-*` (worker/tester/manager) | `gpt-6-luna:max` → `claude-sonnet-5-5` |
| `neon-code-reviewer` | `gemini-4-neon-xhigh` → `-high` → `-medium` → `luna-reviewer` |
| `hydrogen-debugger` | `gemini-4-hydrogen-xhigh` → `-high` → `astra-architect` |
| `argon-explorer` | `gemini-4-argon-high` → `-medium` → `gemini-3.8-flash-high` → `luna-explorer` |
| `opus-auditor` | `claude-opus-5-5` (anthropic) → `agy claude-opus-5-5-high` → `neon-code-reviewer` |
| `sonnet-worker` | `claude-sonnet-5-5` (anthropic) → `agy claude-sonnet-5-5-high` → `luna-worker` |
| `agy-orchestrator` | `gemini-pro-orchestrator-neon` → `gemini-pro-orchestrator-g1-pro` |

4. Two different fallbacks failing on the same task → stop looping; reduce scope, split the task, or hand the decision back to the user.

## 2. Budget & Telemetry

```bash
orchestra stats                  # per-role/model success, latency, 429 count
orchestra stats --budget 200     # warn when today's call count approaches the budget
```

- Ledger: `~/.omp/agent/logs/orchestra-ledger.jsonl` (one JSON record per call).
- Approaching budget → shift mapping/triage to cheaper models (`gemini-4-argon-medium`, `gpt-6-luna`), keep the expensive reviewer for the final gate only.

## 3. Partial Worker Failure

- Inspect `git status` / `git diff` on the failed worker's **owned paths** before retrying — partial edits may be half-correct.
- Decide explicitly: keep, complete, or revert **only those paths**. Never `git reset --hard`, `git checkout -- .`, or `git stash` across the repo.
- Reassigning to a different model? Give it the observed diff plus the failure, not the original intent alone.

## 4. `agy` CLI Specifics

| Symptom | Action |
|---|---|
| Hangs / no output | Re-run with `--timeout 180` and a narrower file scope |
| Prompt rejected | Use `-p="..."` (prompt attached to the flag) — see `scripts/agy-run.sh` |
| Model not found | `orchestra doctor` — compare against live `agy models`; never invent an ID |
| `429` on xhigh | Let `--auto-fallback` drop to `-high`/`-medium` |
| Writable agent corrupted a file | Check `git diff` on its owned path first; restore from that file's last good state only |

## 5. MCP / Tool Failure

- Graph MCP down → fall back to targeted `grep` + read, and state "blast radius lower confidence".
- `trail` missing → read `.trail/learnings/` directly.
- `context7` unreachable → use the installed package's own types/source as the primary source, not memory.
- Never fill a missing tool result with plausible prose.

## 6. Environment Blockers

- SSH/network/credential failure: report the exact command and error, plus what was verified locally. Do not claim deployment.
- Deploy verification needs the real health check (`--health/ready` response) quoted, not inferred from a script's exit hint.

## 7. Post-Incident

1. `trail note` the failure class and the guard that now prevents it.
2. If the fallback chain was wrong, fix `config/roles.json` (and `config/config.example.yml` in the repo) so the next run inherits it.
3. If a model is persistently unavailable, mark it in `topology/model-roster.md` rather than silently omitting it.

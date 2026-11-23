# Nested Agent Spawning (Agents Inside Agents)

Agents in this orchestra may spawn subagents inside themselves when a task benefits from parallel or specialized sub-delegation. The permission is bounded; the bounds are not optional.

## 1. Depth Model

| Depth | Who | Can do |
|---|---|---|
| **0** | Root Conductor (GPT-6.2 Sol) | Spawn any OMP `task` agent; invoke `agy` directly; own the final gate |
| **1** | `luna-task-manager`, `astra-architect`, `opus-auditor`, `security-reviewer`, `sonnet-worker`, `luna-worker`, `agy-orchestrator` | Spawn OMP child `task` agents **or** invoke `agy` roles; own a bounded slice |
| **2** | Children of Depth 1 (e.g. `luna-worker` + `neon-reviewer` under `luna-task-manager`) | Execute only; **must not** spawn further agents |

`agy`-native subagents (`invoke_subagent`, `run_workflow`, `research`) count as Depth 2 when launched from a Depth-1 `agy` run.

## 2. Who May Write

| Role | Mode | Write authority |
|---|---|---|
| `neon-reviewer`, `hydrogen-debugger`, `argon-explorer`, `opus-auditor`, `security-reviewer`, `threat-modeler`, `perf-profiler`, `ui-qa-reviewer` | `plan` | None (read-only) |
| `sonnet-worker`, `luna-worker`, `agy-orchestrator`, `luna-task-manager` | `auto` | Only explicitly owned paths |

A parent may delegate write access **only** to paths it already owns. Ownership never expands because a child wants it.

## 3. Mandatory Guardrails

1. **Max depth 2.** Every Depth-2 brief ends with `"Do not spawn further subagents."`
2. **No recursive orchestration.** An `agy` agent never invokes `omp`; `neon-code-reviewer` never spawns another `neon-code-reviewer`; `agy-orchestrator` never spawns `agy-orchestrator`.
3. **Concurrency budget.** ≤4 concurrent OMP `task` calls (`task.maxConcurrency`); ≤2 concurrent `agy` subprocesses per parent turn (avoids `429`).
4. **Disjoint files.** A child never touches a sibling's or a parent's shared file. Shared touchpoints stay with Sol.
5. **Bounded scope in the brief.** Objective, owned paths, non-goals, contract, validation command — same required fields as `workflows/delegation-protocol.md`.
6. **Isolation for risky writes.** Multi-file or concurrent writable work runs via `orchestra worktree --role <role>` so a bad agent cannot damage the main worktree.
7. **No secrets in prompts.** Do not paste credentials/tokens into a subagent prompt; pass env var names.
8. **Timeout.** Set `--timeout`; a hung child is killed and reported, not waited on indefinitely.

## 4. Traceability Contract

Every nested spawn reports back to its parent with:

```
parent: <role>
child: <role> | model: <id> | fallback_from: <id|none>
scope: <owned paths>
observed: <commands run + exact output summary>
result: done | partial | blocked
risk: <residual>
```

Parent then **verifies the diff** on owned paths — a child's summary is a claim; `git diff` is evidence.

## 5. When Nesting Beats Direct Work

- Map + implement + verify inside one bounded area (sub-orchestrator).
- Parallel independent lookups that would otherwise serialize (docs for 3 libraries).
- Investigation while another slice is being written.

## 6. When Nesting Is Wrong

- The task is one file (just edit it).
- The parent has not scoped the work (nesting multiplies ambiguity).
- The child would need to negotiate a contract (do it at Depth 0/1 explicitly).
- The cost/latency of spawning exceeds the work itself.

## 7. Failure Handling

Child fails or `429`s → parent records the failed slot, retries with the fallback chain (`workflows/fallback-and-recovery.md`), and never reports the child's task as complete without observed evidence. Repeated failure of the same child role → reduce scope or escalate to Sol instead of spawning yet another layer.

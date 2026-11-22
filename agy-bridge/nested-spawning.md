# Nested Agent Spawning (Agents Inside Agents)

Agents in this orchestra are explicitly permitted to spawn subagents inside themselves when a task benefits from parallel or specialized sub-delegation.

## Who Can Spawn Whom

1. **Root Conductor (GPT-6.2 Sol)** -> Depth 0
   - Can spawn any OMP `task` agent (`luna-task-manager`, `astra-architect`, `luna-worker`, `neon-code-reviewer`, `opus-auditor`, etc.) AND invoke `agy` CLI directly.
2. **OMP Sub-Coordinators & Specialists** -> Depth 1
   - `luna-task-manager`, `astra-architect`, `opus-auditor`, `sonnet-worker`, `luna-worker`, `agy-orchestrator` have `task` and/or `bash` tools enabled.
   - They MAY:
     - Spawn OMP child `task` agents (e.g., `luna-task-manager` spawning `luna-worker` + `luna-tester` + `neon-code-reviewer`), **OR**
     - Invoke `agy` CLI agents via `scripts/agy-run.sh` (e.g., `luna-worker` calling `agy-run.sh hydrogen-debugger` to isolate a tricky bug).
3. **Antigravity CLI Internal Subagents** -> Depth 2
   - When `agy` runs with `--mode auto --dangerously-skip-permissions` (especially `gemini-pro-orchestrator-neon` or `sonnet-worker`), it has native access to `invoke_subagent`, `run_workflow`, and `research` subagents inside `agy`.

## Mandatory Guardrails (Prevent Chaos & Fork Bombs)

1. **Max Nesting Depth = 2**:
   - Depth 0 (Sol) -> Depth 1 (OMP `task` or `agy` agent) -> Depth 2 (child helper).
   - Depth 2 agents MUST NOT spawn further `task` or `agy` agents. Always include `"Do not spawn further subagents"` in Depth-2 prompts.
2. **Strict Disjoint File Ownership**:
   - A parent agent may only delegate write access to files/directories **it personally owns**.
   - Read-only subagents (`neon-reviewer`, `hydrogen-debugger`, `argon-explorer`, `opus-auditor`) must always run in `--mode plan` (no edits).
3. **Concurrency Budget**:
   - Keep total concurrent OMP `task` calls within `task.maxConcurrency` (4).
   - Avoid launching more than 2 concurrent `agy` subprocesses from a single agent turn to prevent API rate limits (`429`).
4. **No Recursive Self-Calls**:
   - Never have an `agy` agent invoke `omp`, and never have `neon-code-reviewer` spawn another `neon-code-reviewer`.
5. **Traceability**:
   - Every nested spawn must report back to its parent with: agent/model used, exact files inspected/changed, commands run, and observed output.

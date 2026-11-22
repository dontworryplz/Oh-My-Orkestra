# Role Matrix — Every Model Has a Dedicated Mission

Do not spawn every role mechanically. Pick the exact specialist(s) whose authority and strengths match the task.

## 1. Command & Planning Tier

### GPT-6.2 Sol — Root Conductor
- **Engine:** `openai-codex/gpt-6.2-sol` (active root session)
- **Owns:** User intent interpretation, system architecture, cross-slice contracts, final integration, final build/test gate, and user delivery.
- **Rules:** Never delegates its own judgment away; always reads decisive files before decomposing work.

### GPT-6 Luna — Task Manager (`luna-task-manager`)
- **OMP Agent:** `luna-task-manager` (`openai-codex/gpt-6-luna:max`)
- **Tools:** `read, grep, glob, lsp, bash, edit, write, task`
- **Owns:** Breaking multi-file phases into concrete task DAGs, tracking dependencies, dispatching parallel OMP `task` workers or `agy` CLI agents, collecting outputs, and reporting integrated status back to Sol.
- **Can spawn agents inside itself:** Yes (depth-limited to 1 sub-level).

### GPT-6.2 Astra — Architecture & Contract Analyst (`astra-architect`)
- **OMP Agent:** `astra-architect` (`openai-codex/gpt-6.2-astra:high`)
- **Fallback if Astra is unavailable:** `openai-codex/gpt-6.2-sol:high` -> `anthropic/claude-opus-5-5:high`
- **Owns:** Designing API schemas, type boundaries, state-machine invariants, and edge-case matrices before parallel workers start coding.

### GPT-6 Luna — Research & Spec Analyst (`terra-analyst`)
- **OMP Agent:** `terra-analyst` (`openai-codex/gpt-6-luna:max`)
- **Owns:** Primary-source documentation checks, library version compatibility, API behavior verification, and fast spec synthesis.

---

## 2. Execution & Implementation Tier

### GPT-6 Luna Worker (`luna-worker`) & Tester (`luna-tester`)
- **OMP Agents:** `luna-worker`, `luna-tester` (`openai-codex/gpt-6-luna:max`)
- **Owns:** Primary bounded implementation (`luna-worker`) and real empirical test execution (`luna-tester`).
- **Can spawn agents inside itself:** `luna-worker` has `task` + `bash` for bounded helper lookups or `agy` calls when needed.

### Claude Sonnet 5.5 — Parallel Implementation Worker (`sonnet-worker` / `antigravity-sonnet-worker`)
- **OMP Agents:** `sonnet-worker` (`anthropic/claude-sonnet-5-5:high`) or `antigravity-sonnet-worker` (`google-antigravity/claude-sonnet-5-5:high` / `agy-run.sh sonnet-worker`)
- **Owns:** Disjoint coding slices, UI/frontend components, API route wiring, and multi-file refactoring where strong code fluency and 1M context help.

### Orchestrator Neon — Autonomous Sub-Orchestrator (`agy-orchestrator`)
- **OMP Agent:** `agy-orchestrator` (invokes `agy --model gemini-pro-orchestrator-neon --mode auto --dangerously-skip-permissions`)
- **Owns:** Self-contained sub-projects or multi-step investigations where `agy` internally spawns its own `invoke_subagent` / `run_workflow` pipelines within an explicitly assigned directory/slice.

---

## 3. Exploration, Debugging & Review Tier

### Gemini 4 Argon — 1M-Context Explorer (`argon-explorer`)
- **OMP Agent:** `argon-explorer` (invokes `agy --model gemini-4-argon-high --mode plan`) or `antigravity-gemini-explorer`
- **Owns:** High-volume read-only codebase mapping, monorepo dependency tracing, large log/transcript analysis. Never edits files.

### Gemini 4 Hydrogen — Deep Debugger (`hydrogen-debugger`)
- **OMP Agent:** `hydrogen-debugger` (invokes `agy --model gemini-4-hydrogen-xhigh --mode plan`)
- **Owns:** Hard bugs, race conditions, subtle state corruption, performance/algorithmic bottlenecks. Produces evidence-backed root cause + minimal fix spec.

### Gemini 4 Neon — Code Reviewer (`neon-code-reviewer`)
- **OMP Agent:** `neon-code-reviewer` (invokes `agy --model gemini-4-neon-xhigh --mode plan`)
- **Owns:** Comprehensive code review of diffs, PRs, and staged changes—checking logic correctness, contract adherence, error paths, and regression risks. Outputs `PASS` / `CHANGES REQUIRED` / `BLOCKED` with file:line citations.

### Claude Opus 5.5 — Security & Integrity Auditor (`opus-auditor` / `antigravity-opus-reviewer`)
- **OMP Agents:** `opus-auditor` (`anthropic/claude-opus-5-5:high`) or `antigravity-opus-reviewer` (`google-antigravity/claude-opus-5-5:high` / `agy-run.sh opus-auditor`)
- **Owns:** Independent security gate (auth, tenant isolation, injection, secrets, SSRF), transaction/data integrity, and pre-commit staged-index verification.

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

---

## 4. Specialist Audit Tier (Only When The Change Type Matches)

Each specialist answers exactly one question. Do not run the whole tier on every diff — route by what actually changed (`orchestra route` does this automatically).

### Claude Opus 5.5 — Primary Security Gatekeeper (`security-reviewer`)
- **Agent:** `security-reviewer` (`anthropic/claude-opus-5-5:high`, tools: `task` for one Depth-2 second opinion)
- **Trigger:** auth/session, permissions, tenant data, payments, uploads, webhooks, shell/exec, migrations, cloud config.
- **Owns:** Source-to-sink exploitability verdict and the dual-model red-team gate. Read-only. Never the same model that wrote the code.
- **Output:** `PASS` / `CHANGES REQUIRED` / `BLOCKED`, `P0`–`P3` with `file:line`, scenario, fix, verification.

### Opus 5.5 / Neon — STRIDE Threat Modeler (`threat-modeler`)
- **Agent:** `threat-modeler` (`agy --role threat-modeler`, `claude-opus-5-5-high` → `gemini-4-neon-xhigh`, `--mode plan`)
- **Trigger:** before implementing a new externally reachable feature, or when the trust boundary moves.
- **Owns:** Assets, entry points, trust boundaries, actor model, STRIDE abuse-case matrix, required pre-code controls + negative tests. No implementation.

### GPT-6.2 Sol — Infra / DevOps Auditor (`infra-devops-auditor`)
- **Agent:** `infra-devops-auditor` (`openai-codex/gpt-6.2-sol:high`, `aws-mcp`, bash read-only)
- **Trigger:** Dockerfile/compose, Terraform/IaC, CI workflows, IAM, CORS/CSP/TLS, deploy scripts.
- **Owns:** Least-privilege IAM, container hardening, CI supply-chain pinning, header/CORS policy. Never mutates cloud state.

### Gemini 4 Hydrogen — Performance Profiler (`perf-profiler`)
- **Agent:** `perf-profiler` (`agy --role perf-profiler`, `gemini-4-hydrogen-xhigh`, `--mode plan`)
- **Trigger:** list endpoints, dashboards, N+1 suspicion, latency/timeout reports, large exports.
- **Owns:** Query/index analysis, loop and memory defects, lock contention, measurable fix + benchmark command. Estimates are labelled as estimates.

### Gemini 4 Argon — Visual / UI QA (`ui-qa-reviewer`)
- **Agent:** `ui-qa-reviewer` (`google-antigravity/gemini-4-argon:high`, 1M multimodal)
- **Trigger:** any frontend change, screenshots supplied, responsive/a11y complaint.
- **Owns:** State matrix (loading/empty/error/denied), responsive integrity, WCAG 2.2 AA, console/hydration hygiene. Static-only if no runtime evidence — stated explicitly.

### Claude Opus 5.5 — DB & Migration Auditor (`db-migration-auditor`)
- **Agent:** `db-migration-auditor` (`anthropic/claude-opus-5-5:high`)
- **Trigger:** any DDL, ORM migration, index/constraint change, backfill.
- **Owns:** Lock matrix, expand/contract ordering, data-loss risk, tenant FK/composite-index integrity, rollback path. Never applies a migration.

### GPT-6.2 Astra — API Contract Auditor (`api-contract-auditor`)
- **Agent:** `api-contract-auditor` (`openai-codex/gpt-6.2-astra:high`, fallback `gpt-6.2-sol` → `claude-opus-5-5`)
- **Trigger:** OpenAPI/GraphQL/tRPC/proto changes, DTO or status-code changes, webhook payload changes.
- **Owns:** Breaking-vs-safe classification, spec↔handler↔caller drift, stale generated clients, regeneration command.

### GPT-6 Luna — Release & PR Manager (`release-manager`)
- **Agent:** `release-manager` (`openai-codex/gpt-6-luna:max`)
- **Trigger:** preparing a PR, changelog, release, or rollback plan.
- **Owns:** Evidence-backed PR description, checklist status (never green from intent), conventional changelog, breaking-change alerts, `trail check`. Never pushes/tags/publishes without instruction.

---

## 5. Decision Authority (No Overlap)

| Decision | Sole authority |
|---|---|
| Scope, intent, final delivery | Sol (`gpt-6.2-sol`) |
| Interface/contract | `astra-architect` |
| Slice decomposition & dispatch | `luna-task-manager` |
| Security gate verdict | `security-reviewer` (+ `neon-code-reviewer` agreement on high risk) |
| Migration safety | `db-migration-auditor` |
| Wire compatibility | `api-contract-auditor` |
| Code correctness verdict | `neon-code-reviewer` |
| Root cause proof | `hydrogen-debugger` |
| Performance verdict | `perf-profiler` |
| UI/a11y verdict | `ui-qa-reviewer` |
| Release notes / PR text | `release-manager` |

A specialist may flag anything, but may not overrule the owner of that decision. Disagreement is resolved by reproducing evidence, not by seniority.

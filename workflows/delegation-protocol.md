# Delegation Protocol

Rules for turning a plan into parallel work without collisions, duplicated effort, or unverifiable claims.

## 1. Pre-Delegation Scope (Sol / Luna Task Manager)

Before spawning anything:

1. Search and read the target area enough to know exact paths, symbols, and current git state. Delegating a guess produces a guess.
2. If interfaces span slices, get `astra-architect` contracts first — parallel writers cannot negotiate with each other.
3. Confirm there is genuinely independent, substantial work. **Do not delegate** a one-file edit, a question, a status check, or work you have not scoped.
4. Check `git status --short` — never hand a worker a directory full of unrelated dirty changes.

## 2. Task Brief (mandatory fields)

| Field | Content |
|---|---|
| **Objective** | One observable outcome, not a topic |
| **Owned scope** | Exact writable files/dirs; `READ-ONLY: <paths>` for reviewers/explorers |
| **Non-goals** | Files, configs, lockfiles, git history it must not touch |
| **Contract** | Types, signatures, schemas, invariants from `astra-architect` |
| **Edge cases** | nil/empty, duplicate submit, permission-denied, partial failure |
| **Validation** | One focused command, or `skip repo-wide build; Sol runs final gate` |
| **Nesting** | `may spawn one read-only helper` or `standalone` + `Do not spawn further subagents` |
| **Report format** | caveman-lite: behavior, files, command output, residual risk |

Ambiguous brief → the worker will invent scope. That is a coordinator failure, not a worker failure.

## 3. Slicing Rules

- **Dependency order:** schema → domain → API → UI. Parallelize only siblings, never a parent and its child.
- **One writer per file.** Shared touchpoints (router registry, generated clients, `openapi.yaml`, lockfiles, migrations folder) are Sol/Task-Manager-owned and edited serially after slices land.
- **Size:** a slice should be reviewable in one pass. If the diff will exceed ~400 lines of real logic, split it.
- **Blast radius:** write slices that include a schema change also include the migration and the caller updates — otherwise you ship a broken intermediate state.

## 4. Parallel Batching

- Respect `maxConcurrency: 4`; read-only agents do not consume write slots.
- Concurrent writers **skip** repo-wide formatters, linters, full builds, and full test suites — they would race and produce noise.
- Investigations (bug traces, doc research, log synthesis) run in parallel with implementation, not before it, once contracts are locked.
- `agy` subprocesses: at most 2 concurrent per parent turn to stay clear of `429`.

## 5. Integration & Verification

1. After writers finish, Sol inspects the accumulated diff before running anything.
2. Resolve shared touchpoints serially; then run the integration command once.
3. Gates: `luna-tester` → `orchestra review` → conditional specialists → `trail check` → Sol final gate (`workflows/review-and-qa-gates.md`).
4. A slice is `landed` only with observed command output; otherwise it is `dispatched` or `failed`.

## 6. Failure Handling

- Worker fails → inspect `git status`/`git diff` on its owned paths; retry, shrink the slice, or reassign a different model.
- Environment/credential blocked → report the exact failing command; do not simulate a result.
- Scope creep discovered mid-slice → stop, report, re-plan. Never silently expand into another worker's files.
- Never `git reset --hard` / `git checkout -- .` across the repo; user work may be uncommitted.

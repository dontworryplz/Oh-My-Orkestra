# Delegation Protocol

## 1. Pre-Delegation Scope (Sol / Luna Task Manager)

Before spawning any worker:
1. Perform initial search/read on the target area to establish exact paths, symbols, and current git/worktree state.
2. If architecture or cross-slice interfaces are non-trivial, consult `astra-architect` (`gpt-6.2-astra`) first.
3. Only delegate when there are genuinely independent, substantial slices (skip delegation for single-file trivial edits or direct questions).

## 2. Mandatory Task Brief Structure

Every `task` or `agy` delegation prompt MUST specify:
1. **Objective**: Concrete outcome expected.
2. **Owned Scope**: Exact files/directories the agent may read or write (explicitly state `READ-ONLY` for reviewers/explorers/debuggers).
3. **Non-Goals**: What the agent must NOT touch (e.g., unrelated dirty files, shared configs, git commits).
4. **Shared Interface / Contract**: Types, function signatures, API shapes, or invariants it must honor.
5. **Validation**: Focused check to run (or `Skip project-wide build/test; Sol runs final gate` for concurrent writers).
6. **Nesting Instruction**: Whether it may spawn Depth-2 helpers or must work standalone.

## 3. Parallel Batching & Integration

- Dispatch independent slices in a single parallel batch (respecting `maxConcurrency: 4`).
- Never assign two writers to the same file or overlapping module.
- Concurrent writers skip repo-wide formatters, linters, builds, and full test suites.
- After all writers finish, Sol (or `luna-task-manager` under Sol's review) integrates shared touchpoints and triggers the QA/Review gates.

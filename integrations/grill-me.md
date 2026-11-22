# Grill-Me Decision Interview Protocol

Activate before architectural, ambiguous, or multi-slice tasks (or when the user invokes `/grill-me`, asks to plan, or design tradeoffs remain unresolved). Never guess critical requirements and code against assumptions.

## Step 0: Silent Repo Reconnaissance (Before Asking Anything)

1. Read `.orchestra/REPO_MAP.md` (or run `orchestra init --no-write`).
2. Run `trail ask "<topic>"` and `graft` / `codebase-memory-mcp` to inspect existing conventions, schemas, and auth patterns.
3. **Never ask the user a question that the codebase already answers** (e.g., don't ask "which ORM do you use?" if `REPO_MAP.md` shows Prisma/SQLAlchemy).

## Dependency-Ordered Branch Traversal

Walk the decision tree in strict dependency order—resolve upstream architectural forks before downstream implementation details:

1. **Boundary & Ownership:** Which tenants/roles can trigger this? Is it sync HTTP, background job, or CLI?
2. **Data & State Model:** New table vs column, migration expand/contract, idempotency key, retention/soft-delete?
3. **Failure & Edge-Case Semantics:** What happens on partial failure, duplicate webhook/retry, `429`/timeout, or empty state?
4. **Compatibility & Rollout:** Backward compatibility with existing clients/rows, feature flag needed, rollback path?

## Question Format Rules

- Ask **one focused question at a time** (or use `ask_question` for 2–4 independent multi-choice forks).
- For every question, **state your recommended option first** with a 1-line engineering tradeoff reason.
- Challenge weak assumptions (e.g., if a user asks for synchronous processing of a slow external API, flag timeout/retry risk and propose a queue/job alternative).

## Exit Gate & Handoff

Stop grilling immediately once zero unresolved design forks remain. Output a **Locked Decisions Spec**:
- 5–10 crisp bullets of locked choices
- Explicit non-goals
- Handoff directly to `astra-architect` (for interface contracts) or `luna-task-manager` (for parallel execution).

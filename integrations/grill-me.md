# Grill-Me Decision Interview Protocol

Activate before architectural, ambiguous, or multi-slice tasks — or when the user invokes `/grill-me`, asks to plan, or design forks remain unresolved. Never code against assumptions about scope, data model, or compatibility.

## Step 0: Silent Repo Reconnaissance (Before Asking Anything)

1. Read `.orchestra/REPO_MAP.md` + `.orchestra/rules.md` (or `orchestra init --no-write`).
2. `trail ask "<topic>"` and `graft`/`codebase-memory-mcp` to inspect existing conventions, schemas, and auth patterns.
3. Read the relevant handler/service for the area, so questions are about decisions, not discoverable facts.
4. **Never ask what the codebase already answers.** ("Which ORM?" is answered by `REPO_MAP.md`; "is tenant enforced?" is answered by the middleware.)

## Question Generation Rules

Ask only about **decisions that change the code** and cannot be read from the repo:

| Category | Example question |
|---|---|
| Scope boundary | Does this include existing records or only new ones? |
| Data model | New table vs new column on the existing contract table? |
| Backfill | Rewrite historical rows once, or apply the rule going forward only? |
| Failure semantics | On partial failure: roll back the whole operation or leave a retryable state? |
| Idempotency | Can the same request/webhook arrive twice? |
| Compatibility | Must old clients/rows keep working without migration? |
| Rollout | Feature flag, or ship behind the next deploy? |
| Authority | Who is allowed to trigger this — owner, staff, both? |

Do **not** ask about things you can decide with a sane default: naming, formatting, log levels, test framework (already established in the repo).

## Dependency-Ordered Branch Traversal

Resolve upstream forks before downstream details; a later answer often invalidates an earlier question if you go out of order.

1. **Boundary & ownership:** who triggers it, sync HTTP vs job vs CLI, which tenant/role scope.
2. **Data & state model:** schema shape, migration (expand/contract), retention, soft delete, idempotency key.
3. **Failure & edge semantics:** partial failure, duplicate delivery, timeout/`429`, empty state, concurrency.
4. **Compatibility & rollout:** backward compatibility, feature flag, deploy ordering, rollback path.

## Question Format

- **One focused question at a time** (or 2–4 independent multi-choice forks in one call).
- **Recommended option first**, with a one-line engineering tradeoff.
- Give the rejected option's cost plainly (e.g. "sync call → browser timeout on slow provider").
- Challenge weak assumptions: synchronous processing of a slow external API, "we'll add auth later", "no backfill needed" without data evidence.
- Use the user's language and domain vocabulary; no generic framework jargon.

## Exit Gate

Stop as soon as zero unresolved forks remain. Output a **Locked Decisions Spec**:

```
## Locked Decisions
- <decision> — <reason>
## Non-goals
- <explicitly out of scope>
## Open risks accepted
- <risk> — <why accepted>
## Handoff
- astra-architect (contracts) | luna-task-manager (execution)
```

A decision is only locked when the user confirmed it or explicitly accepted the recommended default. Never inflate the spec with assumptions.

## Anti-Patterns

- Asking 10 questions at once (user answers the last one only).
- Asking a question, then ignoring the answer because the model had a preferred design.
- Grilling on trivial work — for a one-line fix, decide and proceed.
- Leaving the interview without a written spec (decisions evaporate at the next context boundary).

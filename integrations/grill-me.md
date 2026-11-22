# Grill-Me Decision Interview Protocol

Activate before architectural, ambiguous, or multi-slice tasks (or when the user invokes `/grill-me` or asks to align on a plan).

## Core Loop

1. **Scout first (silent):** Sol (or `argon-explorer` / `graft`) reads decisive repo files and `.trail/learnings/` so you never ask questions the codebase already answers.
2. **Walk every branch of the design tree:**
   - Ask **one focused question at a time** (or one tight `ask_question` batch for independent choices), resolving dependencies before downstream questions.
   - For every question, **state your recommended option first** with a 1-line tradeoff reason.
3. **Challenge weak assumptions:** Surface hidden edge cases (auth/tenant boundaries, migrations, concurrency, backward compatibility, rollback).
4. **Exit condition:** Stop grilling as soon as all design forks are resolved, summarize the locked decisions in 5–8 bullets, and hand off to `astra-architect` / `luna-task-manager` for execution.

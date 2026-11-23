# Session Handoff Protocol (`.orchestra/handoff.md`)

Use before context compaction, a long pause, a model switch, or conductor change so zero decisions, ownership, or evidence is lost.

## When To Write

- Context window above ~70% and work is unfinished.
- Batch/phase boundary in a multi-phase task.
- Switching conductor model or harness (OMP ↔ `agy` ↔ Claude Code).
- Before any long-running operation whose result arrives in a new context.
- When the user says "continue later" / "devam ederiz".

## Handoff Template

Write to `.orchestra/handoff.md` (commit only if the project tracks planning files):

```markdown
# Orchestra Handoff — <YYYY-MM-DD HH:MM>

## 1. Goal & Locked Decisions (Grill-Me / Astra)
- <decision> — <reason>

## 2. Completed Slices & Evidence
- <path:line> — <change>; verified: `<command>` → <observed result>

## 3. In-Flight Work (state must be recoverable)
- <agent> | owned paths: <paths> | status: dispatched|partial|blocked | last observed output: <...>

## 4. Remaining Tasks (ordered)
- [ ] <task> (owner: <agent>, owned: <paths>, contract: <ref>)

## 5. Open Risks / Blockers
- <risk> — <what would resolve it>

## 6. Learnings Not Yet Captured
- <candidate trail note title>

## 7. Environment Facts
- branch: <name>, dirty files: <list>, ports/services: <...>, credentials needed: <...>
```

## Rules

1. **Evidence over narrative.** Commands and outputs, not "we made good progress".
2. **Ownership is explicit.** A resuming agent must know which files it may touch.
3. **No secrets** in the handoff file — names of required env vars only.
4. **Cap the size.** If it exceeds ~150 lines, compress with `caveman-compress` and keep anchors verbatim.

## Resume Sequence (new session)

```bash
cat .orchestra/handoff.md
git status --short && git log -n 5 --oneline
trail ask "<topic from section 1>"
orchestra init --no-write   # confirm stack if the repo may have changed
```

Then verify the in-flight slices against the actual diff before dispatching anything new — a handoff is a claim, the worktree is the state.

## Anti-Patterns

- Handoff written from memory of *intent* rather than observed output.
- "Continue the work" with no owned paths → the next agent re-explores everything or collides.
- Leaving dirty files unexplained; the next agent cannot tell user work from abandoned agent work.
- Skipping the trail capture; six weeks later nobody knows why the design is the way it is.

# Session Handoff Protocol (`.orchestra/handoff.md`)

Use before context compaction, long-task pause, or switching conductors so zero decisions or file ownership are lost.

## Handoff Template

Write to `.orchestra/handoff.md` (do not commit unless the project tracks planning files):

```markdown
# Orchestra Handoff — <YYYY-MM-DD HH:MM>

## 1. Goal & Locked Decisions (from Grill-Me / Astra)
- ...

## 2. Completed Slices & Verified Evidence
- `<file:line>` — <change> (tested via `<exact command>`)

## 3. Active / Remaining Tasks (for Luna Task Manager)
- [ ] `<task>` (owner: `<agent>`, owned files: `<paths>`)

## 4. Open Risks & Trail Learnings
- ...
```

## Resume Rule

New session reads `.orchestra/handoff.md` + runs `trail ask "<topic>"` + `git status` before dispatching any new worker.

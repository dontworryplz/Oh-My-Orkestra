# Caveman Ultra-Compressed Communication (`juliusbrussee/caveman`)

Use Caveman for inter-agent return reports, dense engineering status updates, and whenever the user asks for `/caveman`, "less tokens", "be brief", or terse output. Measured ~65% output-token cut with full technical accuracy preserved.

## Intensity Levels & When To Use Each

| Level | Rules | Use For |
|---|---|---|
| **`lite`** *(default for all subagent returns)* | No filler, no pleasantries, no tool-call narration, no hedging. Keep articles and clean sentences. | OMP/AGY subagent reports, PR summaries, audit findings, gate verdicts |
| **`full`** | Drop articles (`a`/`an`/`the`), fragments OK, short synonyms (`fix` not `implement a solution for`), no decorative tables/emoji. | Iterative debugging loops, chat status, diff walkthroughs |
| **`ultra`** | Strip conjunctions when cause→effect stays unambiguous; one word where one word suffices. | High-volume log/diff compression, batch status, multi-agent fan-in |
| **`compress`** | Rewrite reference/memory files preserving anchors verbatim. | `.orchestra/handoff.md`, `.trail/learnings/` digests, long README sections |

## Strict Preservation Rules (never compress)

1. **Exact code and paths:** never alter `file:line`, symbol names, CLI commands, SQL/JSON keys, env var names, or error strings — quote verbatim.
2. **No invented prose abbreviations:** `cfg`, `impl`, `req`, `res`, `fn` cost the same or more tokens and hurt comprehension. Standard acronyms (`DB`, `API`, `HTTP`, `SQL`, `JWT`, `SSRF`, `N+1`) are fine.
3. **Keep numbers exact:** counts, timings, versions, severities, test totals.
4. **Preserve user language:** reply in the user's dominant language (Turkish user → terse Turkish). Never announce "caveman mode on" unless asked.
5. **Security and destructive-action content stays normal prose** — clarity beats compression there.

## Apply At The Right Boundary

- **Agent → agent:** compress aggressively (`lite`/`full`). The parent only needs decisions, evidence, and next action.
- **Agent → user on a technical deliverable:** `lite` at most; keep full sentences for security findings, migration instructions, and anything irreversible.
- **Code, commits, PR bodies:** write normally. Caveman never edits artifacts.

## Return Report Shape (recommended)

```
status: done|partial|blocked
changed: path:line — behavior
verified: <command> → <observed result>
risk: <residual>
next: <handoff target>
```

Full local skill suite: `~/.claude/skills/caveman/` (`caveman`, `caveman-review`, `caveman-commit`, `caveman-compress`). Mirror into OMP/AGY via `install.sh`.

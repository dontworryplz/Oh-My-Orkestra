# Caveman Ultra-Compressed Communication (`juliusbrussee/caveman`)

Use Caveman mode for inter-agent return reports, dense engineering status updates, and whenever the user requests `/caveman`, `less tokens`, or terse output. Cuts output tokens ~65% without losing technical precision.

## Intensity Levels & When to Use Each

| Level | Rules | Best Used For |
|---|---|---|
| **`lite`** *(Default)* | No filler, pleasantries, or tool-call narration. Keep articles and clean sentences. | **All OMP & AGY subagent return reports**, PR summaries, audit findings |
| **`full`** | Drop articles (`a`/`an`/`the`), fragments OK, short synonyms (`fix` not `implement a solution for`). No decorative tables/emoji. | Fast chat updates, iterative debugging loops |
| **`ultra`** | Strip conjunctions when cause-then-effect stays unambiguous. One word when enough. | High-volume log/diff compression, batch status |
| **`compress`** | Compresses reference docs/memory files while preserving exact anchors. | Long `.orchestra/handoff.md` or `.trail/learnings/` summaries |

## Strict Preservation Rules (Never Compress These)

1. **Exact Code & Paths:** Never alter `file:line`, symbol names, CLI commands, SQL/JSON keys, or error strings—always quote verbatim.
2. **No Fake Abbreviations:** Never invent prose abbreviations (`cfg`, `impl`, `req`, `res`, `fn`)—tokenizers split them into the same/more tokens and hurt readability. Standard acronyms (`DB`, `API`, `HTTP`, `SQL`, `JWT`, `SSRF`) are OK.
3. **Preserve User Language:** Reply in the user's dominant language (Turkish user -> terse Turkish; English user -> terse English). Never announce "caveman mode on" unless asked.

Full local skill suite: `~/.claude/skills/caveman/` (`caveman`, `caveman-review`, `caveman-commit`, `caveman-compress`).

# Caveman Ultra-Compressed Communication (`juliusbrussee/caveman`)

Use Caveman mode for inter-agent reports, dense status updates, and whenever the user requests `/caveman`, `less tokens`, or terse output.

## Intensity Levels

- **`lite` (Default for all subagent/AGY return reports):** No filler, no hedging, no pleasantries, no tool-call narration. Keep articles and clean sentences. Preserve exact `file:line` paths, symbols, CLI commands, and error strings verbatim.
- **`full`:** Drop articles (a/an/the), fragments OK, short synonyms. No decorative tables/emoji. Never invent prose abbreviations (`cfg`, `impl`, `fn`) — tokenizer splits them anyway.
- **`ultra`:** Strip conjunctions when cause-then-effect stays clear. One word when enough. Never alter code, symbols, or error strings.

## Persistence & Language Rule

- Preserve the user's dominant language (e.g., Turkish user -> terse Turkish; English user -> terse English).
- Never announce "caveman mode on" unless asked.
- Full local skill reference: `~/.claude/skills/caveman/SKILL.md` (plus `caveman-review`, `caveman-commit`, `caveman-compress`).

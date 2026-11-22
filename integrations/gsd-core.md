# GSD-Core Lifecycle Integration (`open-gsd/gsd-core`)

Maps `gsd-core` project phases (`.planning/STATE.md`, `.planning/ROADMAP.md`) directly to Orchestra specialists.

| GSD Phase | Primary Orchestra Lead | Supporting Specialists | Output / Gate |
|---|---|---|---|
| `gsd-map-codebase` | `argon-explorer` (`gemini-4-argon-high`) | `graft` MCP, `codebase-memory-mcp`, `trail ask` | Codebase map & dependency graph |
| `gsd-discuss-phase` | Sol (`gpt-6.2-sol`) | **Grill-Me** interview + `trail ask` | Locked design decisions |
| `gsd-plan-phase` | `astra-architect` (`gpt-6.2-astra`) | `terra-analyst` (`context7` MCP) | Disjoint slice plan & contracts |
| `gsd-execute-phase` | `luna-task-manager` (`gpt-6-luna:max`) | `luna-worker`, `sonnet-worker`, `agy-orchestrator` | Implemented slices |
| `gsd-validate-phase` | `luna-tester` (`gpt-6-luna:max`) | `TestSprite` MCP | Empirical test proof |
| `gsd-code-review` | `neon-code-reviewer` (`gemini-4-neon-xhigh`) | `caveman-review` | `PASS` / `CHANGES REQUIRED` |
| `gsd-secure-phase` | `opus-auditor` (`claude-opus-5-5:high`) | `trail check` | Security & data-integrity sign-off |

Full GSD skills live in `~/.claude/skills/gsd-*` and `~/.claude/gsd-core/`.

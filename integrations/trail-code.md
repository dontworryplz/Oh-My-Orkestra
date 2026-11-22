# Trail-Code Institutional Memory (`trailhq/Trail-Code`)

Integrates `trail` CLI / `trail mcp` / `.trail/learnings/` across the entire orchestra lifecycle.

## 1. Before Exploring (`argon-explorer`, `luna-explorer`, Sol)

- Run `trail ask "<task>" --source` (or query `trail` MCP) **before** grepping or opening source files.
- If `trail` CLI is not installed, grep `.trail/learnings/` directly.
- Honor prior decisions and ruled-out approaches so workers never repeat dead ends.

## 2. During Debugging & Implementation (`hydrogen-debugger`, `luna-worker`, `sonnet-worker`)

- When a test or command fails, run `trail ask` on that area before attempting a speculative fix.
- When the session uncovers non-obvious knowledge (a bug's real cause after failed attempts, an approach dropped and why, a design choice and its reason, or a user correction), record it:
  `trail note --title "<plain decision, no filenames>"` (reason + `In the code:` paths/symbols on stdin).

## 3. Pre-Commit / Review Gate (`neon-code-reviewer`, `opus-auditor`, Sol)

- Run `trail check` before committing, pushing, or opening a PR to validate changes against repository learnings.
- Full reference: `~/.claude/skills/trail/SKILL.md`.

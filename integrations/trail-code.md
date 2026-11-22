# Trail-Code Institutional Memory (`trailhq/Trail-Code`)

Integrates `trail` CLI, `trail mcp`, and `.trail/learnings/` across the entire Orchestra lifecycle so agents stop repeating solved bugs and discarded architectures.

## 1. Pre-Explore Gate (`argon-explorer`, `astra-architect`, `grill-me`, Sol)

Before grepping or opening source files:
```bash
trail ask "<task or module keywords>" --source
```
- If `trail` CLI is absent, grep `.trail/learnings/` directly (match `touches:` and topic keywords).
- Read matching learnings *before* proposing a plan or delegating slices.

## 2. Mid-Session Learning Capture (`hydrogen-debugger`, `luna-worker`, `sonnet-worker`)

When a test or command fails while debugging, run `trail ask "<failing area>"` before trying a speculative fix.
Record a new learning **only** when the session uncovers knowledge that the code diff itself cannot explain to the next engineer:
- Real root cause of a bug after failed attempts
- An approach tried and ruled out (and why)
- An architectural choice between alternatives (and why)
- A user correction on repository conventions

```bash
trail note --title "<plain decision in words, no filenames>" <<'EOF'
## Decided
- <choice and reason>

## Tried and ruled out
- <rejected option and why it failed>

In the code:
- `<path/to/file.ext>:<symbol>`
EOF
```
Never record trivial status updates ("PR opened", "tests passed") or machine-local facts (use `--personal` for those).

## 3. Pre-Commit & Pre-Release Gate (`neon-code-reviewer`, `release-manager`, Sol)

Before committing, pushing, or opening a PR:
```bash
trail check
```
Verify changes do not violate any recorded repository learnings. Full reference: `~/.claude/skills/trail/SKILL.md`.

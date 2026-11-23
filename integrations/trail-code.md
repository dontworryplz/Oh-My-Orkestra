# Trail-Code Institutional Memory (`trailhq/Trail-Code`)

Integrates the `trail` CLI, `trail mcp`, and `.trail/learnings/` across the whole orchestra so agents stop repeating solved bugs and discarded architectures.

## 1. Pre-Explore Gate (`argon-explorer`, `astra-architect`, `grill-me`, Sol)

Before grepping or opening source files:

```bash
trail ask "<task or module keywords>" --source
```

- If the CLI is absent, read `.trail/learnings/` directly and match `touches:` plus topic keywords.
- Read matching learnings *before* proposing a plan or dispatching slices.
- Cite the learning you used — a decision inherited from trail is cheaper to defend than one re-derived.

## 2. What Deserves A Learning

Record only knowledge the diff cannot explain to the next engineer:

| Record | Do not record |
|---|---|
| Real root cause after failed attempts | "PR opened", "tests pass" |
| Approach tried and ruled out, with why | Reversible formatting choices |
| Architectural choice between alternatives | Anything already obvious from the code |
| User correction about repo conventions | Machine-local paths/ports (use `--personal`) |
| Non-obvious external API behavior/limits | Duplicated README content |

## 3. Mid-Session Capture (`hydrogen-debugger`, `luna-worker`, `sonnet-worker`)

When a command/test fails during debugging: `trail ask "<failing area>"` **before** a speculative fix. After the cause is proven, save it:

```bash
trail note --title "<plain decision, no filenames>" <<'EOF'
## Decided
- <choice and reason>

## Tried and ruled out
- <rejected option and why it failed>

In the code:
- `path/to/file.ext:symbol`
EOF
```

Rules:
- Title describes the decision in words a human would search for ("tenant filter enforced in repository layer, not handler").
- Always include the `In the code:` anchor so future agents land on the exact symbol.
- One learning per decision; do not bundle.

## 4. Pre-Commit / Pre-Release Gate (`neon-code-reviewer`, `release-manager`, Sol)

```bash
trail check
```

Verify the change does not violate a recorded learning. If `trail check` reports a conflict, resolve the code **or** the learning explicitly — never delete a learning just to unblock a commit.

`hooks/pre-commit` runs this automatically; when `ORCHESTRA_REVIEW_GATE=1` it also blocks on a non-`PASS` Neon verdict.

## 5. Failure Modes

- `trail` not installed → read `.trail/learnings/` directly, note the degraded path.
- `EACCES` on `npm i -g` → never use `sudo`; offer `npm config set prefix ~/.npm-global` instead.
- Empty `trail ask` → normal on a new repo; do not invent prior context.
- Conflict between a learning and current user instruction → current instruction wins, but flag the divergence so the learning can be updated.

Full reference: `~/.claude/skills/trail/SKILL.md` (mirrored to OMP/AGY by `install.sh`).

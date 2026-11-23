# Active MCP Routing & Tool Discipline

Use the right MCP server in the right order instead of brute-force file reading or guessing external APIs. Every agent's Step 0 runs the mandatory lookup order.

## 1. Mandatory Lookup Order (Before Editing)

1. **Tech stack:** read `.orchestra/REPO_MAP.md` + `.orchestra/rules.md` (or run `orchestra init`).
2. **Institutional memory (`trail`):** `trail ask "<topic>" --source` so ruled-out approaches are not repeated.
3. **Structural graph (`graft` / `codebase-memory-mcp`):** 1–2 targeted symbol/caller queries before opening many files.
4. **Library docs (`context7`):** exact version-specific API before writing integration code.
5. **Runtime proof:** run the actual command (`bash`), not an assumption about what it does.

## 2. Full MCP Routing Table

| MCP Server | Configured In | Primary Owners | Use Cases & Anti-Patterns |
|---|---|---|---|
| `graft` | `~/.claude.json`, OMP, AGY | `argon-explorer`, `astra-architect`, `neon-code-reviewer`, `luna-worker` | **Use:** symbol skeletons, callers, blast radius, dead code. **Avoid:** recursive text search when the graph already knows. |
| `codebase-memory-mcp` | `~/.claude.json`, OMP, AGY | `argon-explorer`, Sol, `astra-architect` | **Use:** cross-module architecture maps, persistent repo memory. **Avoid:** treating stale index results as current truth — verify with a read. |
| `trail` (`trail mcp`) | `~/.codex/config.toml`, OMP, AGY | All agents | **Use:** `trail ask` pre-explore, `trail note` for non-obvious causes/decisions, `trail check` pre-commit. **Avoid:** trivial status notes. |
| `context7` | `~/.claude.json`, OMP, AGY | `terra-analyst`, `sonnet-worker`, `luna-worker` | **Use:** live signatures, breaking changes, migration guides matching lockfile versions. **Avoid:** asking for "latest" when the repo pins an older major. |
| `TestSprite` | `~/.claude.json`, OMP, AGY | `luna-tester`, `ui-qa-reviewer` | **Use:** automated API/UI/E2E generation and execution. **Avoid:** accepting generated tests as proof without running them. |
| `aws-mcp` | `~/.claude.json`, `~/.codex/config.toml`, OMP, AGY | `infra-devops-auditor`, `security-reviewer`, Sol | **Use:** read-only IAM/S3/CloudWatch/ECS/Lambda inspection. **Avoid:** any mutating call without explicit user sign-off. |
| `node_repl` | `~/.codex/config.toml` | `luna-tester`, `hydrogen-debugger` | **Use:** fast JS reproduction, regex/parser edge cases, browser evaluation. **Avoid:** using it as a scratchpad for production logic. |
| `colab-mcp` | `~/.omp/agent/mcp.json` | `terra-analyst`, `luna-worker` | **Use:** GPU/ML notebooks, heavy Python evaluation, dataset checks. **Avoid:** moving repo logic into a notebook. |

## 3. Query Discipline

1. **One good query beats ten greps.** Ask the graph a question shaped like the task ("who calls `UpdateCemetery`", "what writes `contract_balances`").
2. **Graph is a map, not a source of truth.** The final evidence is the file content at `path:line`.
3. **Stale index risk:** after large refactors or branch switches, re-index (`graft`/`index`) or fall back to direct reads.
4. **MCP failure is not permission to guess.** If a server is unreachable, note it and degrade explicitly (e.g. "graph unavailable → targeted grep + read, lower confidence on blast radius").

## 4. Health Check

```bash
orchestra doctor --mcps     # verifies server binaries (trail, graft, uvx, npx, …) are present in PATH
orchestra sync-mcps         # syncs Claude/Codex MCP definitions into OMP + AGY configs
orchestra sync-mcps --dry-run
```

Report the missing binary name rather than silently skipping a tool.

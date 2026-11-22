# Active MCP Routing & Tool Discipline

Use the right MCP server in the right order instead of brute-force file reading or guessing external APIs.

## 1. Mandatory Lookup Order (Before Editing)

1. **Tech Stack:** Read `.orchestra/REPO_MAP.md` & `.orchestra/rules.md` (or run `orchestra init`).
2. **Institutional Memory (`trail`):** Run `trail ask "<topic>" --source` so you don't repeat ruled-out approaches.
3. **Structural Graph (`graft` / `codebase-memory-mcp`):** Run 1–2 targeted graph/caller queries before opening dozens of files.
4. **Library Docs (`context7`):** Fetch exact version-specific docs before writing integration code.

## 2. Full MCP Routing Table

| MCP Server | Configured In | Primary Owners | Exact Use Cases & Anti-Patterns |
|---|---|---|---|
| **`graft`** | `~/.claude.json`, OMP, AGY | `argon-explorer`, `luna-explorer`, `astra-architect`, `neon-code-reviewer` | **Use for:** symbol skeletons, `callers`, blast-radius analysis. **Avoid:** grepping whole `node_modules`/dist when `graft` has the graph. |
| **`codebase-memory-mcp`** | `~/.claude.json`, OMP, AGY | `argon-explorer`, `astra-architect`, Sol | **Use for:** cross-module architecture maps and persistent repo memory. |
| **`trail`** (`trail mcp`) | `~/.codex/config.toml`, OMP, AGY | All agents | **Use for:** `trail ask` (pre-explore), `trail note` (non-obvious root causes/decisions), `trail check` (pre-commit). **Avoid:** saving trivial status notes. |
| **`context7`** | `~/.claude.json`, OMP, AGY | `terra-analyst`, `luna-researcher`, `sonnet-worker` | **Use for:** live API signatures, breaking changes, migration guides matching lockfile versions. |
| **`TestSprite`** | `~/.claude.json`, OMP, AGY | `luna-tester`, `ui-qa-reviewer` | **Use for:** automated API/UI/E2E test generation & execution. |
| **`aws-mcp`** | `~/.claude.json`, `~/.codex/config.toml`, OMP, AGY | `infra-devops-auditor`, `security-reviewer`, Sol | **Use for:** read-only IAM policy, S3, CloudWatch, ECS/Lambda inspection. **Avoid:** mutating prod infra without explicit user sign-off. |
| **`node_repl`** | `~/.codex/config.toml` | `luna-tester`, `hydrogen-debugger` | **Use for:** fast JS/Node reproduction, regex/parser edge-case verification, browser evaluation. |
| **`colab-mcp`** | `~/.omp/agent/mcp.json` | `terra-analyst`, `luna-worker` | **Use for:** GPU/ML notebooks, data-science experiments, heavy Python evaluation. |

## 3. Health Check

Run `orchestra doctor --mcps` at any time to verify which MCP server binaries (`trail`, `graft`, `uvx`, `npx`) are present in `PATH`.

# Active MCP Routing Table

Route specialists to the right active MCP tool instead of brute-force file reading or guessing.

| MCP Server | Configured In | Primary Orchestra Owners | When to Use |
|---|---|---|---|
| **`graft`** | `~/.claude.json` | `argon-explorer`, `luna-explorer`, `astra-architect`, `neon-code-reviewer` | **First call** for symbol lookup, `skeleton`, `callers`, and blast-radius before broad grep/read. |
| **`codebase-memory-mcp`** | `~/.claude.json` | `argon-explorer`, `astra-architect`, Sol | Structural architecture queries, cross-module call graphs, persistent repo memory. |
| **`trail`** (`trail mcp`) | `~/.codex/config.toml` | All agents | `trail ask` before exploring; `trail note` for non-obvious learnings; `trail check` before commit. |
| **`context7`** | `~/.claude.json` | `terra-analyst`, `luna-researcher`, `sonnet-worker` | Live, version-accurate library/framework docs before writing API integrations. |
| **`TestSprite`** | `~/.claude.json` | `luna-tester` | Automated API/UI/E2E test generation and verification. |
| **`aws-mcp`** | `~/.claude.json`, `~/.codex/config.toml` | `terra-analyst`, `opus-auditor`, Sol | AWS resource, IAM, CloudWatch, and deployment verification. |
| **`node_repl`** | `~/.codex/config.toml` | `luna-tester`, `hydrogen-debugger` | Live Node/JS/browser expression evaluation and reproduction. |
| **`colab-mcp`** | `~/.omp/agent/mcp.json` | `terra-analyst`, `luna-worker` | Remote Colab notebook execution, GPU/ML experiments, data inspection. |

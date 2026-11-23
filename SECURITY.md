# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.4.x | ✅ |
| < 0.4 | ❌ |

## Reporting a Vulnerability

Do **not** open a public issue for a vulnerability. Use GitHub's private reporting:

**Security → Advisories → Report a vulnerability** on
<https://github.com/dontworryplz/Oh-My-Orkestra/security/advisories/new>

Include: affected version, harness (OMP / `agy` / Claude Code), a minimal reproduction, and impact. You can expect an acknowledgement within 3 business days and a fix or mitigation plan within 14 days.

## Scope

In scope:

- `scripts/*.py`, `bin/orchestra`, `scripts/*.sh`, `hooks/pre-commit` — command injection, path traversal, unsafe subprocess construction, secret leakage.
- Secret detection gaps in `orchestra_tools.py` (`SECRET_PATTERNS`) that would let a live credential pass `redact --check`.
- `install.sh` — writing outside the intended directories, unsafe `sudo`, downloading unverified code.
- Agent prompts that instruct a model to bypass human approval for destructive actions.

Out of scope:

- The behaviour of third-party models/providers (OpenAI, Anthropic, Google) or third-party MCP servers.
- Vulnerabilities in the repositories the orchestra operates on.
- Requests to weaken the security gates (dual-model requirement, `P0/P1` blocking).

## Handling Secrets

If you discover a credential in this repository's history or docs, report it privately **and rotate it immediately** — removing it from git history is not enough.

`orchestra redact --check` is a guardrail, not a guarantee. Anything exposed must be rotated.

## Safe Defaults

- No command in this project mutates cloud state; `aws-mcp` usage is read-only by policy.
- Destructive actions (force push, `reset --hard`, deploy, migration, publish, external send) require explicit user approval, documented in `skills`/`AGENTS` rules — not agent discretion.

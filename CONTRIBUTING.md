# Contributing to Oh-My-Orkestra

Contributions must keep the orchestra **harness-agnostic** (OMP, Antigravity CLI `agy`, Claude Code) and **evidence-first**. Docs are the product here: a role that exists only in code and not in `topology/` is an undocumented role.

## 1. Repo Layout

```
SKILL.md                 # harness adaptation + directory map + routing matrix
topology/                # model roster (verified IDs) + role matrix (authority)
agy-bridge/              # agy CLI protocol + nested spawning guardrails
config/                  # roles.json, review-schema.json, config.example.yml
scripts/                 # agy_agent.py, smart-route.py, discover-stack.py, sync-mcps.py, *.sh
bin/orchestra            # unified CLI entry point
omp-agents/              # portable agent definitions (mirrored to ~/.omp/agent/agents)
workflows/               # delegation, QA gates, security, fallback, handoff
integrations/            # grill-me, caveman, trail-code, gsd-core, active-mcps
presets/                 # end-to-end playbooks
examples/                # runnable CLI runbooks
hooks/pre-commit         # optional trail check + review gate
tests/                   # unittest suite for the scripts
```

## 2. Adding a New Role

1. **Verify the model exists** — `agy models` / `orchestra doctor`. Never add an ID you have not seen in a live list.
2. `config/roles.json` — add `models` (ordered fallback chain), `mode` (`plan` = read-only, `auto` = writable), `allow_nesting`, and `instructions` (Step 0 + priority order + output contract).
3. `omp-agents/<role>.md` — YAML frontmatter (`name`, `description`, `model`, `tools`), `# Step 0: Repo & Stack Bootstrap`, priority list, evidence discipline, output contract returning in `caveman-lite`.
4. `config/config.example.yml` — register the override/fallback so `orchestra doctor` and `agy_agent.py` agree.
5. `topology/model-roster.md` + `topology/role-matrix.md` — add mission, authority boundaries, and the single decision it owns.
6. If the role is conditional, wire it into `scripts/smart-route.py` triggers and `workflows/review-and-qa-gates.md`.
7. Presets: add the role where the playbook should call it.

### Role Definition Requirements

- **Exactly one owned decision.** Two agents that both "own security" will disagree at the worst moment.
- **Read-only by default.** `mode: plan` unless the role truly must write, and then list owned paths in the prompt.
- **Explicit fallback chain.** Every role must degrade (see `workflows/fallback-and-recovery.md`).
- **No invented model IDs, no invented tool output.** A missing tool is reported as missing.

## 3. Adding an Integration or Workflow Doc

- Frontmatter-free Markdown, H2 sections, tables for matrices.
- Lead with **when to use / when not to**, then the protocol, then anti-patterns.
- Every command must be runnable as written (real paths, real flags). No pseudo-CLI.
- Cross-link with relative paths so the docs work in the GitHub repo and after install.

## 4. Validation Before PR

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
bash -n install.sh bin/orchestra scripts/*.sh hooks/pre-commit
python3 -m py_compile scripts/*.py
./install.sh --dry-run
orchestra doctor
```

All must pass. Add or extend a test in `tests/test_agy_agent.py` for any script behaviour change (routing rules, fallback order, stack detection, schema validation).

## 5. Install / Sync Discipline

The authoring copy and the installed copy are separate paths:

| Path | Role |
|---|---|
| `~/.omp/agent/managed-skills/sol-luna-orchestrator` | authoring source (this repo) |
| `~/.omp/agent/skills/sol-luna-orchestrator` | installed copy used by OMP + Claude/AGY symlinks |
| `~/.omp/agent/agents/*.md` | mirrored `omp-agents/` |
| `/tmp/Oh-My-Orkestra` (or any clone) | git origin for pushing |

After editing, sync both ways:

```bash
SKILL_DIR="$HOME/.omp/agent/managed-skills/sol-luna-orchestrator"
cp "$SKILL_DIR/omp-agents/"*.md "$HOME/.omp/agent/agents/"
(cd "$SKILL_DIR" && ./install.sh)          # refreshes installed copy + symlinks
```

Never hand-edit the installed copy — it will be overwritten.

## 6. Commit Style

Conventional Commits, subject ≤ 72 chars, body only when the *why* is not obvious.

```
docs(presets): expand hard-bug-hunt to full reproduction-to-proof playbook
feat(scripts): add stats --budget for daily call-count checks
fix(config): correct argon-explorer role typo
```

Planning/vault noise (`.orchestra/`, caches, `__pycache__`) stays out of commits.

## 7. Review Checklist for PRs

- [ ] No model ID that is not in the live roster
- [ ] No doc claims a behaviour the scripts do not implement
- [ ] Fallback chain defined and tested for any new role
- [ ] Relative links resolve
- [ ] Tests, `bash -n`, `py_compile`, `install.sh --dry-run` pass
- [ ] README/SKILL.md directory map updated if a file was added

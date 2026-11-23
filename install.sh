#!/usr/bin/env bash
set -euo pipefail

# Self-installing Full-Set Orchestra installer for OMP, Antigravity CLI (agy), and Claude Code.
# Usage:
#   ./install.sh [--all] [--with-config] [--sync-mcps] [--with-hooks] [--skip-sidekicks] [--dry-run]
#   ./install.sh --repair       Re-link skill, agents, and binaries (idempotent fix)
#   ./install.sh --uninstall    Remove links/copies this installer created

WITH_CONFIG=false
SYNC_MCPS=false
WITH_HOOKS=false
SKIP_SIDEKICKS=false
DRY_RUN=false
REPAIR=false
UNINSTALL=false
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --all)
      WITH_CONFIG=true
      SYNC_MCPS=true
      WITH_HOOKS=true
      ;;
    --with-config) WITH_CONFIG=true ;;
    --sync-mcps) SYNC_MCPS=true ;;
    --with-hooks) WITH_HOOKS=true ;;
    --skip-sidekicks) SKIP_SIDEKICKS=true ;;
    --dry-run) DRY_RUN=true ;;
    --repair) REPAIR=true; SKIP_SIDEKICKS=true ;;
    --uninstall) UNINSTALL=true ;;
    --force) FORCE=true ;;
    -h|--help)
      echo "Usage: $0 [--all] [--with-config] [--sync-mcps] [--with-hooks] [--skip-sidekicks] [--dry-run]"
      echo "       $0 --repair | --uninstall [--force]"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 2
      ;;
  esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMP_DIR="${OMP_AGENT_DIR:-$HOME/.omp/agent}"
SKILL_DEST="$OMP_DIR/skills/sol-luna-orchestrator"
AGENTS_DEST="$OMP_DIR/agents"
VENDOR_DIR="$OMP_DIR/vendor"
CLAUDE_SKILLS="$HOME/.claude/skills"
AGY_SKILLS="$HOME/.gemini/antigravity-cli/skills"

run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

LOCAL_BIN="$HOME/.local/bin"

if [[ "$UNINSTALL" == "true" ]]; then
  echo "=== Uninstalling Sol-Luna Full-Set Orchestra ==="
  run_cmd rm -f "$LOCAL_BIN/orchestra"
  for link in "$CLAUDE_SKILLS/sol-luna-orchestrator" "$AGY_SKILLS/sol-luna-orchestrator" "$OMP_DIR/skills/sol-luna-orchestrator"; do
    if [[ -L "$link" ]]; then
      run_cmd rm -f "$link"
    elif [[ -e "$link" ]]; then
      echo "skip (not a symlink): $link"
    fi
  done
  if [[ -d "$REPO_DIR/omp-agents" ]]; then
    for f in "$REPO_DIR/omp-agents/"*.md; do
      [[ -f "$f" ]] || continue
      base="$(basename "$f")"
      if [[ -f "$AGENTS_DEST/$base" ]] && cmp -s "$f" "$AGENTS_DEST/$base"; then
        run_cmd rm -f "$AGENTS_DEST/$base"
      fi
    done
  fi
  if [[ "$REPO_DIR" == "$SKILL_DEST" ]]; then
    echo "authoring copy is the installed copy; leaving files in place"
  else
    run_cmd rm -rf "$SKILL_DEST"
  fi
  echo "Removed links and copied files. Kept: config.yml, ledger, .orchestra/, sidekick skills."
  exit 0
fi

run_cmd mkdir -p "$SKILL_DEST" "$AGENTS_DEST" "$VENDOR_DIR" "$CLAUDE_SKILLS" "$AGY_SKILLS"

# 1. Install skill & portable OMP agents
if [[ "$REPO_DIR" != "$SKILL_DEST" ]]; then
  run_cmd cp -R "$REPO_DIR/"* "$SKILL_DEST/"
fi
if [[ -d "$REPO_DIR/omp-agents" ]]; then
  for f in "$REPO_DIR/omp-agents/"*.md; do
    [[ -f "$f" ]] && run_cmd cp "$f" "$AGENTS_DEST/"
  done
fi
run_cmd chmod +x "$SKILL_DEST/bin/orchestra" "$SKILL_DEST/scripts/agy-run.sh" "$SKILL_DEST/scripts/agy_agent.py" "$SKILL_DEST/scripts/worktree-run.sh" "$SKILL_DEST/scripts/sync-mcps.py" "$SKILL_DEST/scripts/smart-route.py" "$SKILL_DEST/scripts/orchestra_tools.py" "$SKILL_DEST/scripts/discover-stack.py" "$SKILL_DEST/scripts/publish.sh" "$SKILL_DEST/hooks/pre-commit"

run_cmd mkdir -p "$LOCAL_BIN"
run_cmd ln -sfn "$SKILL_DEST/bin/orchestra" "$LOCAL_BIN/orchestra"

run_cmd ln -sfn "$SKILL_DEST" "$CLAUDE_SKILLS/sol-luna-orchestrator"
run_cmd ln -sfn "$SKILL_DEST" "$AGY_SKILLS/sol-luna-orchestrator"

# 2. Configure OMP config.yml
if [[ ! -f "$OMP_DIR/config.yml" ]]; then
  run_cmd cp "$SKILL_DEST/config/config.example.yml" "$OMP_DIR/config.yml"
  echo "Created OMP config -> $OMP_DIR/config.yml"
elif [[ "$WITH_CONFIG" == "true" ]]; then
  run_cmd cp "$OMP_DIR/config.yml" "$OMP_DIR/config.yml.bak.$(date +%Y%m%d%H%M%S)"
  run_cmd cp "$SKILL_DEST/config/config.example.yml" "$OMP_DIR/config.yml"
  echo "Backed up and updated OMP config -> $OMP_DIR/config.yml"
else
  echo "Kept existing $OMP_DIR/config.yml (pass --with-config to overwrite with backup)"
fi

# 3. Install & link sidekick ecosystems (Caveman, Trail-Code, GSD-Core)
link_skill_all() {
  local src="$1"
  local name
  name="$(basename "$src")"
  [[ -d "$src" ]] || return 0
  run_cmd ln -sfn "$src" "$OMP_DIR/skills/$name"
  run_cmd ln -sfn "$src" "$CLAUDE_SKILLS/$name"
  run_cmd ln -sfn "$src" "$AGY_SKILLS/$name"
}

if [[ "$SKIP_SIDEKICKS" == "false" ]]; then
  # 3a. Caveman (https://github.com/juliusbrussee/caveman)
  if [[ ! -d "$CLAUDE_SKILLS/caveman" ]]; then
    if command -v git >/dev/null 2>&1 && [[ "$DRY_RUN" == "false" ]]; then
      if [[ ! -d "$VENDOR_DIR/caveman" ]]; then
        git clone --depth 1 https://github.com/juliusbrussee/caveman.git "$VENDOR_DIR/caveman" || true
      fi
      for d in "$VENDOR_DIR/caveman"/caveman* "$VENDOR_DIR/caveman"/skills/caveman*; do
        [[ -d "$d" ]] && link_skill_all "$d"
      done
    else
      echo "[info] Would install/link caveman from https://github.com/juliusbrussee/caveman"
    fi
  else
    for d in "$CLAUDE_SKILLS"/caveman*; do
      [[ -d "$d" ]] && link_skill_all "$d"
    done
  fi

  # 3b. Trail-Code (https://github.com/trailhq/Trail-Code)
  if ! command -v trail >/dev/null 2>&1; then
    if command -v npm >/dev/null 2>&1; then
      run_cmd npm install -g @trailhq/trail-code || echo "Note: install @trailhq/trail-code manually if npm prefix requires setup."
    fi
  fi
  if [[ -d "$CLAUDE_SKILLS/trail" ]]; then
    link_skill_all "$CLAUDE_SKILLS/trail"
  elif [[ -d "$HOME/.gemini/skills/trail" ]]; then
    link_skill_all "$HOME/.gemini/skills/trail"
  fi

  # 3c. GSD-Core (https://github.com/open-gsd/gsd-core)
  if [[ ! -d "$HOME/.claude/gsd-core" && ! -d "$VENDOR_DIR/gsd-core" ]]; then
    if command -v git >/dev/null 2>&1; then
      run_cmd git clone --depth 1 https://github.com/open-gsd/gsd-core.git "$VENDOR_DIR/gsd-core" || true
    fi
  fi
  for d in "$CLAUDE_SKILLS"/gsd-*; do
    [[ -d "$d" ]] && link_skill_all "$d"
  done
fi

# 4. Sync active MCPs into OMP & AGY
if [[ "$SYNC_MCPS" == "true" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    python3 "$REPO_DIR/scripts/sync-mcps.py" --dry-run || true
  else
    python3 "$SKILL_DEST/scripts/sync-mcps.py" || true
  fi
fi

# 5. Optional Git pre-commit hook in current repository
if [[ "$WITH_HOOKS" == "true" ]] && git rev-parse --git-dir >/dev/null 2>&1; then
  HOOK_DEST="$(git rev-parse --git-dir)/hooks/pre-commit"
  if [[ -f "$HOOK_DEST" ]]; then
    run_cmd cp "$HOOK_DEST" "$HOOK_DEST.bak.$(date +%Y%m%d%H%M%S)"
  fi
  run_cmd cp "$SKILL_DEST/hooks/pre-commit" "$HOOK_DEST"
  run_cmd chmod +x "$HOOK_DEST"
  echo "Installed git pre-commit hook -> $HOOK_DEST"
fi

if [[ "$REPAIR" == "true" ]]; then
  echo ""
  echo "=== Repair complete ==="
fi
echo ""
echo "=== Sol-Luna Full-Set Orchestra Installed ==="
echo "OMP Skill   : $SKILL_DEST"
echo "OMP Agents  : $AGENTS_DEST"
echo "Claude Link : $CLAUDE_SKILLS/sol-luna-orchestrator"
echo "AGY Link    : $AGY_SKILLS/sol-luna-orchestrator"
echo ""
if [[ "$DRY_RUN" == "false" ]]; then
  python3 -m unittest discover -s "$SKILL_DEST/tests" -p "test_*.py" -v || true
  python3 "$SKILL_DEST/scripts/agy_agent.py" doctor || true
fi

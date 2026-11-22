#!/usr/bin/env python3
"""Sync active MCP servers from Claude Code & Codex into OMP and Antigravity CLI configs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tomllib

HOME = Path.home()
CLAUDE_JSON = HOME / ".claude.json"
CODEX_TOML = HOME / ".codex" / "config.toml"
OMP_MCP = HOME / ".omp" / "agent" / "mcp.json"
AGY_MCP = HOME / ".gemini" / "antigravity-cli" / "mcp_config.json"

SAFE_DEFAULT_KEYS = {
    "graft",
    "codebase-memory-mcp",
    "context7",
    "TestSprite",
    "aws-mcp",
    "trail",
    "colab-mcp",
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_sources() -> dict[str, dict]:
    merged: dict[str, dict] = {}
    if CLAUDE_JSON.exists():
        data = load_json(CLAUDE_JSON)
        for name, cfg in data.get("mcpServers", {}).items():
            if name in SAFE_DEFAULT_KEYS and isinstance(cfg, dict):
                merged[name] = cfg
    if CODEX_TOML.exists():
        data = tomllib.loads(CODEX_TOML.read_text(encoding="utf-8"))
        for name, cfg in data.get("mcp_servers", {}).items():
            if name in SAFE_DEFAULT_KEYS and isinstance(cfg, dict) and name not in merged:
                entry = {"command": cfg.get("command"), "args": cfg.get("args", [])}
                if "env" in cfg:
                    entry["env"] = cfg["env"]
                merged[name] = entry
    return merged


def merge_target(path: Path, incoming: dict[str, dict], dry_run: bool) -> list[str]:
    existing = load_json(path)
    servers = existing.setdefault("mcpServers", {})
    added: list[str] = []
    for name, cfg in incoming.items():
        if name not in servers:
            servers[name] = cfg
            added.append(name)
    if not dry_run and added:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return added


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Show what would be synced without writing")
    args = p.parse_args()

    sources = collect_sources()
    omp_added = merge_target(OMP_MCP, sources, args.dry_run)
    agy_added = merge_target(AGY_MCP, sources, args.dry_run)

    print(json.dumps({
        "dry_run": args.dry_run,
        "discovered_sources": sorted(sources.keys()),
        "omp_added": omp_added,
        "agy_added": agy_added,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

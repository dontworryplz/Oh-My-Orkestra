#!/usr/bin/env python3
"""Orchestra ops toolkit: cost, guard, handoff, verify, redact.

Subcommands:
  cost    Aggregate ledger usage into per-model token/cost estimates.
  guard   Fail when the working diff touches files outside the owned paths.
  handoff Generate/maintain .orchestra/handoff.md from real repo + ledger state.
  verify  Run the project's detected test/typecheck/lint commands and record evidence.
  redact  Find and mask secrets in a diff/file/history before sending it to a model.
  phase   Track work phases so the ledger can be priced per phase.
  gate    Run secret scan + verify + structured review as one verdict.
  validate Validate a review verdict (or any JSON) against a config schema.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import providers  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = Path.home() / ".omp" / "agent" / "logs" / "orchestra-ledger.jsonl"
PRICING_PATH = SKILL_ROOT / "config" / "pricing.json"
ORCH_DIR = ".orchestra"


# ---------------------------------------------------------------- shared utils

def ledger_path() -> Path:
    env = os.environ.get("ORCHESTRA_LEDGER")
    return Path(env).expanduser() if env else DEFAULT_LEDGER


def read_ledger(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or ledger_path()
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def emit(payload: dict[str, Any], out: str | None = None) -> None:
    blob = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        dest = Path(out).expanduser().resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(blob + "\n", encoding="utf-8")
    print(blob)


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------- models

def _usage_tokens(usage: Any) -> dict[str, int]:
    """Normalize whatever token fields the provider returned."""
    out = {"input": 0, "output": 0}
    if not isinstance(usage, dict):
        return out
    in_keys = ("input_tokens", "prompt_tokens", "promptTokens", "input")
    out_keys = ("output_tokens", "completion_tokens", "completionTokens", "output")
    for k in in_keys:
        if isinstance(usage.get(k), (int, float)):
            out["input"] = int(usage[k])
            break
    for k in out_keys:
        if isinstance(usage.get(k), (int, float)):
            out["output"] = int(usage[k])
            break
    if not out["input"] and not out["output"]:
        total = usage.get("total_tokens") or usage.get("totalTokens")
        if isinstance(total, (int, float)):
            out["input"] = int(total)  # price conservatively as input
    return out


def _price_for(model: str, pricing: dict[str, Any]) -> dict[str, float] | None:
    models = pricing.get("models", {})
    if not isinstance(models, dict):
        return None
    if model in models:
        return models[model]
    best = None
    for key, value in models.items():
        if model.startswith(key) and (best is None or len(key) > len(best[0])):
            best = (key, value)
    return best[1] if best else None


def cmd_cost(args: argparse.Namespace) -> int:
    pricing = load_json(Path(args.pricing).expanduser()) if args.pricing else load_json(PRICING_PATH)
    rows = read_ledger()
    if args.days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        filtered = []
        for row in rows:
            try:
                ts = datetime.fromisoformat(str(row.get("ts", "")).replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts >= cutoff:
                filtered.append(row)
        rows = filtered

    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "failed": 0, "input_tokens": 0, "output_tokens": 0, "elapsed_seconds": 0.0, "cost_usd": 0.0}
    )
    by_role: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "cost_usd": 0.0})
    unpriced: set[str] = set()
    total_cost = 0.0
    token_runs = 0

    for row in rows:
        model = str(row.get("model") or "unknown")
        role = str(row.get("role") or "unknown")
        entry = by_model[model]
        entry["runs"] += 1
        if not row.get("ok"):
            entry["failed"] += 1
        entry["elapsed_seconds"] += float(row.get("elapsed_seconds") or 0.0)
        tokens = _usage_tokens(row.get("usage"))
        if tokens["input"] or tokens["output"]:
            token_runs += 1
        entry["input_tokens"] += tokens["input"]
        entry["output_tokens"] += tokens["output"]
        price = _price_for(model, pricing)
        cost = 0.0
        if price:
            cost = (tokens["input"] / 1_000_000.0) * float(price.get("input", 0)) + (
                tokens["output"] / 1_000_000.0
            ) * float(price.get("output", 0))
        elif tokens["input"] or tokens["output"]:
            unpriced.add(model)
        entry["cost_usd"] = round(entry["cost_usd"] + cost, 6)
        by_role[role]["runs"] += 1
        by_role[role]["cost_usd"] = round(by_role[role]["cost_usd"] + cost, 6)
        total_cost += cost

    for entry in by_model.values():
        entry["elapsed_seconds"] = round(entry["elapsed_seconds"], 2)
    payload: dict[str, Any] = {
        "ok": True,
        "ledger_path": str(ledger_path()),
        "pricing_path": args.pricing or str(PRICING_PATH),
        "pricing_source": pricing.get("source", "unknown"),
        "window_days": args.days,
        "runs_in_window": len(rows),
        "runs_with_token_usage": token_runs,
        "estimated_total_usd": round(total_cost, 4),
        "by_model": dict(sorted(by_model.items(), key=lambda kv: -kv[1]["cost_usd"])),
        "by_role": dict(sorted(by_role.items(), key=lambda kv: -kv[1]["cost_usd"])),
        "unpriced_models": sorted(unpriced),
        "note": (
            "Cost is an estimate: model prices come from config/pricing.json and are applied to "
            "reported token usage only. Runs without usage are counted but not priced."
        ),
    }
    if getattr(args, "by", None) == "phase":
        payload["by_phase"] = _cost_by_phase(rows, Path(args.cwd).expanduser().resolve())
    if not rows:
        payload["note"] = "No ledger rows in window. Run an agy role first (orchestra run ...)."
    if getattr(args, "csv", False):
        lines = ["model,runs,failed,input_tokens,output_tokens,cost_usd"]
        for model, entry in payload["by_model"].items():
            lines.append(
                f"{model},{entry['runs']},{entry['failed']},{entry['input_tokens']},"
                f"{entry['output_tokens']},{entry['cost_usd']}"
            )
        text = "\n".join(lines)
        if args.out:
            dest = Path(args.out).expanduser().resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    emit(payload, args.out)
    return 0


# ----------------------------------------------------------------------- phase

def phase_path(root: Path) -> Path:
    return root / ORCH_DIR / "phase.json"


def load_phase(root: Path) -> dict[str, Any]:
    state = load_json(phase_path(root))
    if not isinstance(state.get("history"), list):
        state["history"] = []
    return state


def save_phase(root: Path, state: dict[str, Any]) -> Path:
    path = phase_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return path


def _unix(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _close_phase(state: dict[str, Any]) -> dict[str, Any] | None:
    idx = state.get("current_index")
    if idx is None or idx >= len(state.get("history", [])):
        return None
    entry = state["history"][idx]
    if not entry.get("ended_at"):
        entry["ended_at"] = now_iso()
        started = _unix(entry.get("started_at"))
        ended = _unix(entry["ended_at"])
        if started and ended:
            entry["duration_seconds"] = max(0, ended - started)
    state["current_index"] = None
    return entry


def _row_phase(row: dict[str, Any], history: list[dict[str, Any]]) -> str:
    stamped = row.get("phase")
    if stamped:
        return str(stamped)
    ts = _unix(str(row.get("ts") or ""))
    if ts is None:
        return "(unphased)"
    for entry in reversed(history):
        start = _unix(entry.get("started_at"))
        end = _unix(entry.get("ended_at")) or int(time.time())
        if start is not None and start <= ts <= end:
            return str(entry.get("phase") or "(unnamed)")
    return "(unphased)"


def _cost_by_phase(rows: list[dict[str, Any]], root: Path) -> dict[str, dict[str, Any]]:
    history = load_phase(root).get("history", [])
    pricing = load_json(PRICING_PATH)
    by_phase: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "failed": 0, "cost_usd": 0.0})
    for row in rows:
        label = _row_phase(row, history)
        entry = by_phase[label]
        entry["runs"] += 1
        if not row.get("ok"):
            entry["failed"] += 1
        tokens = _usage_tokens(row.get("usage"))
        price = _price_for(str(row.get("model") or "unknown"), pricing)
        if price:
            entry["cost_usd"] = round(
                entry["cost_usd"]
                + (tokens["input"] / 1_000_000.0) * float(price.get("input", 0))
                + (tokens["output"] / 1_000_000.0) * float(price.get("output", 0)),
                6,
            )
    return dict(sorted(by_phase.items(), key=lambda kv: -kv[1]["cost_usd"]))


def cmd_phase(args: argparse.Namespace) -> int:
    root = Path(args.cwd).expanduser().resolve()
    state = load_phase(root)
    action = args.action
    history = state["history"]
    current = history[state["current_index"]] if state.get("current_index") is not None else None

    if action == "start":
        if not args.name:
            emit({"ok": False, "error": "phase start needs a name"}, args.out)
            return 2
        closed = _close_phase(state)
        entry = {"phase": args.name, "started_at": now_iso()}
        history.append(entry)
        state["current_index"] = len(history) - 1
        save_phase(root, state)
        emit(
            {
                "ok": True,
                "action": "start",
                "phase": args.name,
                "started_at": entry["started_at"],
                "closed_previous": closed.get("phase") if closed else None,
                "state_path": str(phase_path(root)),
            },
            args.out,
        )
        return 0

    if action == "end":
        if current is None:
            emit({"ok": False, "error": "no phase is running"}, args.out)
            return 2
        if args.name and args.name != current.get("phase"):
            emit(
                {"ok": False, "error": f"running phase is {current.get('phase')!r}, not {args.name!r}"},
                args.out,
            )
            return 2
        closed = _close_phase(state)
        save_phase(root, state)
        rows = [
            row
            for row in read_ledger()
            if _row_phase(row, history) == closed.get("phase")
        ]
        emit(
            {
                "ok": True,
                "action": "end",
                "phase": closed.get("phase"),
                "started_at": closed.get("started_at"),
                "ended_at": closed.get("ended_at"),
                "duration_seconds": closed.get("duration_seconds"),
                "runs": len(rows),
                "failed_runs": sum(1 for row in rows if not row.get("ok")),
                "state_path": str(phase_path(root)),
            },
            args.out,
        )
        return 0

    if action == "status":
        if current is None:
            emit({"ok": True, "active": None, "history_count": len(history)}, args.out)
            return 0
        started = _unix(current.get("started_at")) or int(time.time())
        rows = [row for row in read_ledger() if _row_phase(row, history) == current.get("phase")]
        emit(
            {
                "ok": True,
                "active": current.get("phase"),
                "started_at": current.get("started_at"),
                "elapsed_seconds": int(time.time()) - started,
                "runs": len(rows),
                "state_path": str(phase_path(root)),
            },
            args.out,
        )
        return 0

    if action == "list":
        items = []
        for entry in history[-20:]:
            rows = [row for row in read_ledger() if _row_phase(row, history) == entry.get("phase")]
            items.append(
                {
                    "phase": entry.get("phase"),
                    "started_at": entry.get("started_at"),
                    "ended_at": entry.get("ended_at"),
                    "duration_seconds": entry.get("duration_seconds"),
                    "runs": len(rows),
                }
            )
        emit({"ok": True, "active": current.get("phase") if current else None, "phases": items}, args.out)
        return 0

    emit({"ok": False, "error": f"unknown action {action!r}"}, args.out)
    return 2


# ----------------------------------------------------------------------- guard

def _match_path(path: str, pattern: str) -> bool:
    path = path.strip().lstrip("./")
    pattern = pattern.strip().lstrip("./").rstrip("/")
    if not pattern:
        return False
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return path == base or path.startswith(base + "/")
    if pattern == "**":
        return True
    if pattern.endswith("*"):
        return _segment_glob(path, pattern)
    return path == pattern or path.startswith(pattern + "/") or _segment_glob(path, pattern)


def _segment_glob(path: str, pattern: str) -> bool:
    """fnmatch per path segment so `*` does not cross `/` (unlike fnmatch.fnmatch)."""
    p_parts = path.split("/")
    g_parts = pattern.split("/")
    if len(p_parts) != len(g_parts):
        return False
    return all(fnmatch.fnmatchcase(p, g) for p, g in zip(p_parts, g_parts))


def changed_files(base: str | None, include_untracked: bool) -> list[str]:
    files: set[str] = set()
    if base:
        files.update(f for f in git("diff", "--name-only", f"{base}...HEAD").splitlines() if f.strip())
        files.update(f for f in git("diff", "--name-only", base).splitlines() if f.strip())
    else:
        files.update(f for f in git("diff", "--name-only", "HEAD").splitlines() if f.strip())
    if include_untracked:
        files.update(f for f in git("ls-files", "--others", "--exclude-standard").splitlines() if f.strip())
    return sorted(files)


def cmd_guard(args: argparse.Namespace) -> int:
    owned = [p for part in args.owned for p in part.split(",") if p.strip()]
    if not owned:
        emit({"ok": False, "error": "--owned requires at least one path/glob"}, args.out)
        return 2
    files = changed_files(args.base, include_untracked=not args.base)
    if args.ignore:
        files = [f for f in files if not any(_match_path(f, p) for p in args.ignore)]
    violations = [f for f in files if not any(_match_path(f, p) for p in owned)]
    payload = {
        "ok": not violations,
        "owned": owned,
        "base": args.base,
        "changed_files": files,
        "violations": violations,
        "note": "Violations are files the agent must not have touched; revert or re-scope before merging.",
    }
    emit(payload, args.out)
    if violations:
        print(f"owned-path violation: {len(violations)} file(s) outside scope", file=sys.stderr)
        return 3
    return 0


# --------------------------------------------------------------------- handoff

def _diff_stat(limit: int = 25) -> list[str]:
    lines = [ln for ln in git("diff", "--stat").splitlines() if ln.strip()]
    return lines[:limit]


def cmd_handoff(args: argparse.Namespace) -> int:
    root = Path(args.cwd).expanduser().resolve()
    dest = root / ORCH_DIR / "handoff.md"
    profile = load_json(root / ORCH_DIR / "stack-profile.json")
    evidence = load_json(root / ORCH_DIR / "evidence.json")

    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip() or "(no git)"
    status = [ln for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    commits = [ln for ln in git("log", "-n", "5", "--oneline").splitlines() if ln.strip()]
    stat = _diff_stat()

    recent_runs = []
    for row in reversed(read_ledger()):
        if len(recent_runs) >= 8:
            break
        recent_runs.append(row)
    recent_runs.reverse()

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    out: list[str] = [f"# Orchestra Handoff — {stamp}", ""]
    out += [f"- Repo: `{root}`", f"- Branch: `{branch}`", f"- Generated by: `orchestra handoff`", ""]

    out += ["## 1. Goal & Locked Decisions (Grill-Me / Astra)", ""]
    if dest.exists():
        prev = dest.read_text(encoding="utf-8")
        section = _extract_section(prev, "1. Goal & Locked Decisions")
        out += section or ["- <fill: decision — reason>"]
    else:
        out += ["- <fill: decision — reason>"]
    out.append("")

    out += ["## 2. Completed Slices & Evidence", ""]
    if evidence:
        for check in evidence.get("checks", []):
            if isinstance(check, dict):
                out.append(
                    f"- `{check.get('cmd', '?')}` → exit {check.get('exit', '?')} "
                    f"({check.get('duration_seconds', 0)}s) at {check.get('ts', '?')}"
                )
    elif stat:
        out += ["- <fill: path:line — change; verified: `cmd` → observed result>"]
    else:
        out += ["- Clean worktree: no uncommitted slice. Confirm with previous commits."]
    out.append("")

    out += ["## 3. In-Flight Work", ""]
    if status:
        out.append("```")
        out += status[:40]
        out.append("```")
        out += ["", f"- Diff stat:", "```"]
        out += stat or ["(no tracked diff)"]
        out.append("```")
    else:
        out.append("- None (clean working tree).")
    out.append("")

    out += ["## 4. Remaining Tasks (ordered)", ""]
    if dest.exists():
        section = _extract_section(dest.read_text(encoding="utf-8"), "4. Remaining Tasks")
        out += section or ["- [ ] <fill>"]
    else:
        out += ["- [ ] <fill> (owner: <agent>, owned: <paths>)"]
    out.append("")

    out += ["## 5. Open Risks / Blockers", ""]
    if dest.exists():
        section = _extract_section(dest.read_text(encoding="utf-8"), "5. Open Risks")
        out += section or ["- <none recorded>"]
    else:
        out += ["- <fill: risk — what resolves it>"]
    out.append("")

    out += ["## 6. Learnings Not Yet Captured", ""]
    out += ["- <candidate `trail note` title>", ""]

    out += ["## 7. Environment Facts", ""]
    out += [f"- Languages: `{', '.join(profile.get('languages', ['unknown']))}`"]
    out += [f"- Test runners: `{', '.join(profile.get('test_runners', ['unknown']))}`"]
    out += [f"- package.json scripts: `{', '.join(sorted(profile.get('scripts', {}).keys()))}`" if profile.get("scripts") else "- package.json scripts: none detected"]
    out += [f"- trail present: `{profile.get('has_trail', False)}` | GSD planning: `{profile.get('has_gsd_planning', False)}`"]
    out.append("")

    out += ["## 8. Recent Orchestra Runs (ledger)", ""]
    if recent_runs:
        out.append("| ts | role | model | ok | elapsed |")
        out.append("|---|---|---|---|---|")
        for row in recent_runs:
            out.append(
                f"| {row.get('ts', '?')} | {row.get('role', '?')} | {row.get('model', '?')} | "
                f"{row.get('ok', '?')} | {row.get('elapsed_seconds', '?')}s |"
            )
    else:
        out.append("- No ledger rows yet.")
    out.append("")
    out += ["## 9. Recent Commits", "", "```"] + (commits or ["(no commits)"]) + ["```", ""]

    body = "\n".join(out)
    if args.write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            backup = dest.with_suffix(".prev.md")
            backup.write_text(dest.read_text(encoding="utf-8"), encoding="utf-8")
        dest.write_text(body, encoding="utf-8")
        if args.out:
            Path(args.out).expanduser().write_text(json.dumps({"ok": True, "written": str(dest)}, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {dest}")
        return 0
    if args.out:
        Path(args.out).expanduser().write_text(body, encoding="utf-8")
    print(body)
    return 0


def _extract_section(markdown: str, heading_prefix: str) -> list[str]:
    """Carry forward a hand-written section so regeneration does not lose intent."""
    lines = markdown.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and heading_prefix in line:
            start = i + 1
            break
    if start is None:
        return []
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    if not body:
        return []
    # Drop placeholder bullets so re-runs do not accumulate noise.
    return [ln for ln in body if not ln.strip().startswith("- <fill")]


# ---------------------------------------------------------------------- verify

def _pm_run(root: Path, profile: dict[str, Any]) -> str | None:
    """Return the package-manager run prefix when a JS project is detected."""
    scripts = profile.get("scripts") or {}
    if not scripts:
        pkg = load_json(root / "package.json")
        scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    if not scripts:
        return None
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        return "bun"
    return "npm"


def derive_checks(root: Path) -> list[dict[str, str]]:
    profile = load_json(root / ORCH_DIR / "stack-profile.json")
    langs = [str(l).lower() for l in profile.get("languages", [])]
    pkg = load_json(root / "package.json")
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else profile.get("scripts") or {}
    pm = _pm_run(root, profile)
    checks: list[dict[str, str]] = []

    def add(name: str, cmd: str) -> None:
        if not any(c["name"] == name for c in checks):
            checks.append({"name": name, "cmd": cmd})

    if pm and scripts:
        for key in ("typecheck", "type-check", "tsc"):
            if key in scripts:
                add("typecheck", f"{pm} run {key}")
                break
        for key in ("lint", "eslint"):
            if key in scripts:
                add("lint", f"{pm} run {key}")
                break
        for key in ("test", "test:unit", "vitest"):
            if key in scripts:
                add("test", f"{pm} run {key}" if key != "test" else f"{pm} test")
                break
    if (root / "tsconfig.json").exists() and not any(c["name"] == "typecheck" for c in checks) and shutil.which("npx"):
        add("typecheck", "npx --no-install tsc --noEmit")

    # Go/Rust manifests are explicit, so they win the single `test` slot over a generic Python guess.
    if (root / "go.mod").exists():
        add("test", "go test ./...")
    if (root / "Cargo.toml").exists():
        add("test", "cargo test")
    has_py = (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or "python" in langs
    if has_py:
        if shutil.which("pytest") and ((root / "pytest.ini").exists() or (root / "tests").exists() or "pytest" in json.dumps(profile).lower()):
            add("test", "pytest -q")
        if (root / "mypy.ini").exists() or (root / ".mypy.ini").exists():
            add("typecheck", "mypy .")
        if shutil.which("ruff") and (root / "ruff.toml").exists():
            add("lint", "ruff check .")
    if not any(c["name"] == "test" for c in checks) and list(root.glob("tests/test_*.py")):
        add("test", "python3 -m unittest discover -s tests -p 'test_*.py'")
    return checks


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.cwd).expanduser().resolve()
    checks = derive_checks(root)
    if args.only:
        wanted = set(args.only)
        checks = [c for c in checks if c["name"] in wanted]
    for spec in args.cmd or []:
        if "=" not in spec:
            emit({"ok": False, "error": f"--cmd must be name=command, got {spec!r}"}, args.out)
            return 2
        name, command = spec.split("=", 1)
        checks.append({"name": name.strip(), "cmd": command.strip()})
    if not checks:
        emit(
            {
                "ok": False,
                "repo": str(root),
                "error": "No runnable checks detected. Run `orchestra init` or pass --cmd 'name=shell command'.",
            },
            args.out,
        )
        return 2
    if args.dry_run:
        emit({"ok": True, "repo": str(root), "checks": checks, "dry_run": True}, args.out)
        return 0

    evidence = run_checks(root, checks, timeout=args.timeout, stop_on_fail=args.stop_on_fail)
    emit(evidence, args.out)
    return 0 if evidence["ok"] else 1


def run_checks(
    root: Path,
    checks: list[dict[str, str]],
    timeout: int = 900,
    stop_on_fail: bool = False,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    worst = 0
    for check in checks:
        started = time.monotonic()
        try:
            proc = subprocess.run(
                check["cmd"],
                shell=True,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-20:]
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            tail = [f"Timed out after {timeout}s"]
            exit_code = 124
        duration = round(time.monotonic() - started, 2)
        results.append(
            {
                "name": check["name"],
                "cmd": check["cmd"],
                "exit": exit_code,
                "duration_seconds": duration,
                "tail": tail,
                "ts": now_iso(),
            }
        )
        worst = worst or exit_code
        if exit_code != 0 and stop_on_fail:
            break

    evidence = {"ok": worst == 0, "repo": str(root), "generated_at": now_iso(), "checks": results}
    ev_path = root / ORCH_DIR / "evidence.json"
    try:
        ev_path.parent.mkdir(parents=True, exist_ok=True)
        ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return dict(evidence, evidence_path=str(ev_path))


# ------------------------------------------------------------------ validation

REVIEW_SCHEMA = SKILL_ROOT / "config" / "review-schema.json"

_PYTYPES: dict[str, Any] = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def validate_payload(data: Any, schema: dict[str, Any], where: str = "$") -> list[str]:
    """Validate a small, practical subset of JSON Schema (no external deps)."""
    errors: list[str] = []
    if not isinstance(schema, dict):
        return [f"{where}: schema is not an object"]

    expected = schema.get("type")
    if isinstance(expected, str) and expected in _PYTYPES and not _PYTYPES[expected](data):
        return [f"{where}: expected {expected}, got {type(data).__name__}"]

    enum = schema.get("enum")
    if isinstance(enum, list) and data not in enum:
        errors.append(f"{where}: {data!r} not in {enum}")

    if "minimum" in schema and isinstance(data, (int, float)) and not isinstance(data, bool):
        if data < schema["minimum"]:
            errors.append(f"{where}: {data} below minimum {schema['minimum']}")

    if isinstance(data, dict):
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        for key in schema.get("required") or []:
            if key not in data:
                errors.append(f"{where}.{key}: required but missing")
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in props:
                    errors.append(f"{where}.{key}: not allowed by schema")
        for key, subschema in props.items():
            if key in data:
                errors.extend(validate_payload(data[key], subschema, f"{where}.{key}"))

    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(data):
            errors.extend(validate_payload(item, schema["items"], f"{where}[{index}]"))
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.file).expanduser()
    if not target.is_file():
        emit({"ok": False, "error": f"not a file: {target}"}, args.out)
        return 2
    schema_path = Path(args.schema).expanduser() if args.schema else REVIEW_SCHEMA
    schema = load_json(schema_path)
    if not schema:
        emit({"ok": False, "error": f"unreadable schema: {schema_path}"}, args.out)
        return 2
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        emit({"ok": False, "error": f"invalid JSON: {exc}"}, args.out)
        return 5
    errors = validate_payload(data, schema)
    emit(
        {
            "ok": not errors,
            "file": str(target.resolve()),
            "schema": str(schema_path),
            "error_count": len(errors),
            "errors": errors[:25],
        },
        args.out,
    )
    return 0 if not errors else 5


# ----------------------------------------------------------------- provider review

def _schema_block(schema: dict[str, Any]) -> str:
    try:
        text = json.dumps(schema, ensure_ascii=False)
    except (TypeError, ValueError):
        text = "{}"
    return text[:4000]


def _review_with_diff_prompt(staged: bool, schema: dict[str, Any], max_chars: int) -> str:
    diff = git("diff", "--cached") if staged else git("diff")
    safe = redact_text(diff)[: max(0, int(max_chars))]
    scope = "staged diff" if staged else "working-tree diff"
    return (
        f"Review the {scope} below for P0-P3 bugs, contract drift, and security issues.\n"
        "Return ONLY a JSON object that matches the schema. No prose, no code fences.\n\n"
        f"Schema:\n{_schema_block(schema)}\n\n"
        f"Diff (secrets already masked):\n```diff\n{safe}\n```"
    )


def _provider_review(
    provider: str,
    model: str,
    prompt: str,
    timeout: int,
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = providers.complete(provider, model, prompt, timeout=timeout, max_tokens=max_tokens)
    verdict = _verdict_from({"response": result.get("text", "")}) if result.get("ok") else {}
    return result, verdict


def cmd_review(args: argparse.Namespace) -> int:
    """Direct-provider review (no agy). Requires --provider and --model."""
    root = Path(args.cwd).expanduser().resolve()
    diff = git("diff", "--cached") if args.staged else git("diff")
    if not diff.strip():
        emit({"ok": True, "skipped": True, "reason": "No diff to review"}, args.out)
        return 0
    schema_path = Path(args.schema).expanduser() if args.schema else REVIEW_SCHEMA
    schema = load_json(schema_path)
    prompt = _review_with_diff_prompt(args.staged, schema, args.max_chars)

    result, verdict = _provider_review(args.provider, args.model, prompt, args.timeout, args.max_tokens)
    errors = validate_payload(verdict, schema) if verdict else ["no verdict returned"]
    retried = False
    if errors and result.get("ok"):
        retried = True
        retry_prompt = (
            prompt
            + "\n\nPrevious answer failed schema validation: "
            + "; ".join(errors[:5])
            + "\nReturn only a valid JSON object."
        )
        result, verdict = _provider_review(args.provider, args.model, retry_prompt, args.timeout, args.max_tokens)
        errors = validate_payload(verdict, schema) if verdict else ["no verdict returned"]

    ok = bool(result.get("ok")) and not errors and verdict.get("verdict") == "PASS"
    emit(
        {
            "ok": ok,
            "repo": str(root),
            "scope": "staged" if args.staged else "working-tree",
            "provider": args.provider,
            "model": args.model,
            "retried": retried,
            "schema_ok": not errors,
            "schema_errors": errors[:10],
            "verdict": verdict or None,
            "usage": result.get("usage"),
            "error": result.get("error"),
            "diff_chars": len(diff),
            "generated_at": now_iso(),
        },
        args.out,
    )
    return 0 if ok else 1


# ------------------------------------------------------------------------ gate

def _kind_allowed(allow: list[str] | None, kind: str) -> bool:
    for item in allow or []:
        name = item[5:] if item.startswith("kind:") else item
        if name.strip() == kind:
            return True
    return False


def _review_prompt(staged: bool) -> str:
    scope = "staged diff (git diff --cached)" if staged else "working-tree diff (git diff)"
    return (
        f"Review the {scope} for P0-P3 bugs, contract drift, and security issues. "
        "Return ONLY a JSON object that matches the provided schema. No prose, no code fences."
    )


def _review_once(root: Path, prompt: str, timeout: int, schema: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    out = root / ORCH_DIR / "review-raw.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    cmd = [
        sys.executable,
        str(SKILL_ROOT / "scripts" / "agy_agent.py"),
        "run",
        "--role",
        "neon-reviewer",
        "--cwd",
        str(root),
        "--schema",
        str(schema),
        "--timeout",
        str(timeout),
        "--out",
        str(out),
        "--prompt",
        prompt,
    ]
    meta: dict[str, Any] = {}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 120, check=False)
        meta = {"returncode": proc.returncode, "stderr_tail": (proc.stderr or "")[-400:]}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": f"review invocation failed: {exc}"}, meta
    try:
        payload = json.loads(out.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("non-object payload")
        return payload, meta
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"unreadable review output: {exc}"}, meta


def _verdict_from(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response")
    if isinstance(response, dict):
        return response
    if isinstance(response, str):
        match = re.search(r"\{[\s\S]*\}", response)
        candidate = match.group(0) if match else response.strip()
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def cmd_gate(args: argparse.Namespace) -> int:
    root = Path(args.cwd).expanduser().resolve()
    schema = Path(args.schema).expanduser() if args.schema else REVIEW_SCHEMA
    steps: list[dict[str, Any]] = []
    ok = True

    diff = git("diff", "--cached") if args.staged else git("diff")
    findings = [hit for hit in find_secrets(diff) if not _kind_allowed(args.allow, hit["kind"])]
    steps.append(
        {
            "name": "secrets",
            "ok": not findings,
            "finding_count": len(findings),
            "findings": findings[:20],
        }
    )
    ok = ok and not findings

    if ok or args.keep_going:
        checks = derive_checks(root)
        if args.only:
            wanted = set(args.only)
            checks = [check for check in checks if check["name"] in wanted]
        for spec in args.cmd or []:
            if "=" not in spec:
                steps.append({"name": "verify", "ok": False, "error": f"--cmd must be name=command, got {spec!r}"})
                ok = False
                checks = []
                break
            name, command = spec.split("=", 1)
            checks.append({"name": name.strip(), "cmd": command.strip()})
        if args.dry_run:
            steps.append({"name": "verify", "ok": True, "dry_run": True, "checks": checks})
        elif not checks:
            steps.append({"name": "verify", "ok": False, "error": "no runnable checks detected"})
            ok = False
        else:
            evidence = run_checks(root, checks, timeout=args.timeout, stop_on_fail=True)
            steps.append(
                {
                    "name": "verify",
                    "ok": evidence["ok"],
                    "checks": [
                        {"name": check["name"], "exit": check["exit"], "duration_seconds": check["duration_seconds"]}
                        for check in evidence["checks"]
                    ],
                    "evidence_path": evidence["evidence_path"],
                }
            )
            ok = ok and evidence["ok"]

    review: dict[str, Any] = {"name": "review", "ok": True, "status": "skipped"}
    if args.no_review:
        review["reason"] = "--no-review"
    elif args.dry_run:
        review["reason"] = "--dry-run"
    elif getattr(args, "provider", None):
        if not ok and not args.keep_going:
            review["reason"] = "earlier step failed"
        else:
            schema_data = load_json(schema)
            prompt = _review_with_diff_prompt(args.staged, schema_data, getattr(args, "max_chars", 12000))
            result, verdict = _provider_review(
                args.provider,
                getattr(args, "model", "") or "",
                prompt,
                args.timeout,
                getattr(args, "max_tokens", 4000),
            )
            errors = validate_payload(verdict, schema_data) if verdict else ["no verdict returned"]
            retried = False
            if errors and result.get("ok"):
                retried = True
                retry_prompt = (
                    prompt
                    + "\n\nPrevious answer failed schema validation: "
                    + "; ".join(errors[:5])
                    + "\nReturn only a valid JSON object."
                )
                result, verdict = _provider_review(
                    args.provider,
                    getattr(args, "model", "") or "",
                    retry_prompt,
                    args.timeout,
                    getattr(args, "max_tokens", 4000),
                )
                errors = validate_payload(verdict, schema_data) if verdict else ["no verdict returned"]
            review.update(
                {
                    "ok": bool(result.get("ok")) and not errors and verdict.get("verdict") == "PASS",
                    "status": verdict.get("verdict", "ERROR" if not result.get("ok") else "INVALID"),
                    "provider": args.provider,
                    "model": getattr(args, "model", None),
                    "schema_ok": not errors,
                    "schema_errors": errors[:10],
                    "retried": retried,
                    "usage": result.get("usage"),
                    "error": result.get("error"),
                }
            )
            ok = ok and review["ok"]
    elif not shutil.which("agy"):
        review["reason"] = "agy CLI not found on PATH"
    elif not ok and not args.keep_going:
        review["reason"] = "earlier step failed"
    else:
        prompt = _review_prompt(args.staged)
        payload, meta = _review_once(root, prompt, args.timeout, schema)
        verdict = _verdict_from(payload)
        errors = validate_payload(verdict, load_json(schema))
        retried = False
        if errors:
            retried = True
            retry_prompt = (
                prompt
                + "\n\nYour previous answer failed schema validation: "
                + "; ".join(errors[:5])
                + "\nReturn only a valid JSON object."
            )
            payload, meta = _review_once(root, retry_prompt, args.timeout, schema)
            verdict = _verdict_from(payload)
            errors = validate_payload(verdict, load_json(schema))
        review.update(
            {
                "ok": not errors and verdict.get("verdict") == "PASS",
                "status": verdict.get("verdict", "INVALID"),
                "schema_ok": not errors,
                "schema_errors": errors[:10],
                "retried": retried,
                "findings": len(verdict.get("findings") or []),
                "model_meta": meta,
            }
        )
        ok = ok and review["ok"]
    steps.append(review)

    verdict_payload = {
        "ok": ok,
        "repo": str(root),
        "scope": "staged" if args.staged else "working-tree",
        "generated_at": now_iso(),
        "steps": steps,
    }
    path = root / ORCH_DIR / "gate.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(verdict_payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    emit(dict(verdict_payload, gate_path=str(path)), args.out)
    return 0 if ok else 1


# ---------------------------------------------------------------------- redact

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----[A-Za-z0-9+/=\s]{64,}-----END (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe-key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("bearer", re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("db-url", re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:@/]+:[^\s@/]+@[^\s\"']+")),
    ("assigned-secret", re.compile(r"\b([A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|ACCESS_KEY)[A-Z0-9_]*)\s*[:=]\s*[\"']?([A-Za-z0-9/+=_.~-]{8,})")),
]


def _secret_spans(text: str) -> list[tuple[int, int, str]]:
    """Non-overlapping spans, earliest pattern in SECRET_PATTERNS wins."""
    spans: list[tuple[int, int, str]] = []
    for kind, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if start == end:
                continue
            line_start = text.rfind("\n", 0, start) + 1
            if "re.compile(" in text[line_start:start]:
                continue  # the detector's own pattern source is not a secret
            if any(start < s_end and s_start < end for s_start, s_end, _ in spans):
                continue
            spans.append((start, end, kind))
    return sorted(spans)


def find_secrets(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for start, end, kind in _secret_spans(text):
        line_no = text.count("\n", 0, start) + 1
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        snippet = text[line_start : line_end if line_end != -1 else len(text)].strip()
        hits.append({"kind": kind, "line": line_no, "preview": _mask_line(snippet)})
    return hits


def _mask_line(line: str) -> str:
    def repl(match: re.Match[str]) -> str:
        value = match.group(0)
        if len(value) <= 8:
            return "REDACTED"
        return f"{value[:4]}…REDACTED({len(value)} chars)"

    masked = line
    for _, pattern in SECRET_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked[:200]


def redact_text(text: str) -> str:
    """Mask non-overlapping secret spans; earlier patterns keep their specific label."""
    out: list[str] = []
    cursor = 0
    for start, end, kind in _secret_spans(text):
        out.append(text[cursor:start])
        out.append(f"REDACTED:<{kind}>")
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def _allowed(allow: list[str] | None, kind: str, path: str | None = None) -> bool:
    for item in allow or []:
        entry = item.strip()
        if entry.startswith("kind:"):
            if entry[5:].strip() == kind:
                return True
        elif path and fnmatch.fnmatch(path, entry.lstrip("./")):
            return True
    return False


def _filter_findings(findings: list[dict[str, Any]], allow: list[str] | None) -> list[dict[str, Any]]:
    return [hit for hit in findings if not _allowed(allow, str(hit.get("kind")), hit.get("path"))]


def _scan_history(limit: int, since: str | None) -> list[dict[str, Any]]:
    """Scan added lines in git history, attributing each hit to commit/path/line."""
    rev_args = ["log", "--no-color", "--unified=0", "-p", f"-n{int(limit)}", "--format=%x00%H%x00%s"]
    if since:
        rev_args.append(f"{since}..HEAD")
    text = git(*rev_args)
    findings: list[dict[str, Any]] = []
    sha = ""
    subject = ""
    path: str | None = None
    new_line = 0
    in_header = True
    for line in text.splitlines():
        if line.startswith("\x00"):
            parts = line.split("\x00")
            sha = parts[1] if len(parts) > 1 else ""
            subject = parts[2] if len(parts) > 2 else ""
            path = None
            new_line = 0
            in_header = True
            continue
        if line.startswith("diff --git "):
            path = None
            in_header = True
            continue
        if line.startswith("+++ "):
            target = line[4:].strip()
            path = None if target == "/dev/null" else (target[2:] if target.startswith("b/") else target)
            in_header = False
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,\d+)?", line)
            if match:
                new_line = int(match.group(1))
            in_header = False
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if path and new_line:
                for hit in find_secrets(line[1:]):
                    findings.append(
                        {
                            "kind": hit["kind"],
                            "preview": hit["preview"],
                            "path": path,
                            "line": new_line,
                            "sha": sha[:12],
                            "subject": subject[:120],
                        }
                    )
            new_line += 1
            continue
        if line.startswith(" ") and path and new_line and not in_header:
            new_line += 1
    return findings


def cmd_redact(args: argparse.Namespace) -> int:
    if getattr(args, "history", False):
        limit = max(1, int(getattr(args, "limit", 200) or 200))
        findings = _filter_findings(_scan_history(limit, getattr(args, "since", None)), args.allow)
        payload: dict[str, Any] = {
            "ok": not findings,
            "source": f"git history (last {limit} commits" + (f" since {args.since}" if args.since else "") + ")",
            "clean": not findings,
            "finding_count": len(findings),
            "findings": findings[:100],
            "truncated": len(findings) > 100,
        }
        if args.check:
            payload["action"] = "blocked" if findings else "allowed"
            emit(payload, args.out)
            return 4 if findings else 0
        emit(payload, args.out)
        return 0

    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            emit({"ok": False, "error": f"not a file: {path}"}, args.out)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
        source = str(path)
        rel_path = str(path)
    elif args.staged:
        text = git("diff", "--cached")
        source = "git diff --cached"
        rel_path = None
    elif args.text:
        text = args.text
        source = "argument"
        rel_path = None
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
        source = "stdin"
        rel_path = None
    else:
        text = git("diff")
        source = "git diff"
        rel_path = None
    if not text.strip():
        emit({"ok": True, "source": source, "clean": True, "findings": [], "note": "No content to scan."}, args.out)
        return 0

    hits = _filter_findings(find_secrets(text), args.allow)
    redacted = redact_text(text)
    payload = {
        "ok": not hits,
        "source": source,
        "clean": not hits,
        "finding_count": len(hits),
        "findings": hits,
    }
    if getattr(args, "allow", None):
        payload["allow"] = args.allow
    if args.check:
        payload["action"] = "blocked" if hits else "allowed"
        emit(payload, args.out)
        return 4 if hits else 0
    if args.output:
        Path(args.output).expanduser().write_text(redacted, encoding="utf-8")
        payload["redacted_written"] = str(Path(args.output).expanduser().resolve())
        emit(payload, args.out)
    else:
        payload["redacted"] = redacted if hits else None
        emit(payload, args.out)
    return 0


# ------------------------------------------------------------------------ main

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command_name", required=True)

    c = sub.add_parser("cost", help="Estimate token usage and USD cost from the ledger")
    c.add_argument("--days", type=int, default=0, help="Only rows newer than N days (0 = all)")
    c.add_argument("--pricing", help="Override pricing table path")
    c.add_argument("--by", choices=["phase"], help="Add a breakdown by phase (reads .orchestra/phase.json)")
    c.add_argument("--cwd", default=".", help="Repo root used to resolve .orchestra/phase.json")
    c.add_argument("--csv", action="store_true", help="Print a per-model CSV instead of JSON")
    c.add_argument("--out", help="Save JSON to path")
    c.set_defaults(func=cmd_cost)

    g = sub.add_parser("guard", help="Fail when the diff leaves the owned paths")
    g.add_argument("--owned", action="append", required=True, help="Owned path/glob (repeatable or comma-separated)")
    g.add_argument("--ignore", action="append", default=[], help="Path/glob to exempt (e.g. .orchestra/**)")
    g.add_argument("--base", help="Compare against this git ref instead of HEAD + untracked")
    g.add_argument("--out", help="Save JSON to path")
    g.set_defaults(func=cmd_guard)

    h = sub.add_parser("handoff", help="Generate .orchestra/handoff.md from repo + ledger state")
    h.add_argument("--cwd", default=".")
    h.add_argument("--write", action="store_true", help="Write .orchestra/handoff.md (backs up previous)")
    h.add_argument("--out", help="Save markdown/JSON to path")
    h.set_defaults(func=cmd_handoff)

    v = sub.add_parser("verify", help="Run detected test/typecheck/lint and record evidence")
    v.add_argument("--cwd", default=".")
    v.add_argument("--only", action="append", choices=["test", "typecheck", "lint"], help="Restrict to check kinds")
    v.add_argument("--cmd", action="append", help="Extra check as name=shell command")
    v.add_argument("--timeout", type=int, default=900)
    v.add_argument("--stop-on-fail", action="store_true")
    v.add_argument("--dry-run", action="store_true", help="Print the checks without running them")
    v.add_argument("--out", help="Save JSON to path")
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("redact", help="Find/mask secrets before sending content to a model")
    r.add_argument("--file")
    r.add_argument("--staged", action="store_true")
    r.add_argument("--text")
    r.add_argument("--check", action="store_true", help="Exit 4 if any secret is found (CI/pre-commit use)")
    r.add_argument("--history", action="store_true", help="Scan added lines across git history")
    r.add_argument("--limit", type=int, default=200, help="Commits to scan with --history (default 200)")
    r.add_argument("--since", help="Only scan commits after this ref (with --history)")
    r.add_argument("--allow", action="append", default=[], help="Allow entry: kind:<name> or a path glob")
    r.add_argument("--output", help="Write redacted content to this file")
    r.add_argument("--out", help="Save JSON report to path")
    r.set_defaults(func=cmd_redact)

    ph = sub.add_parser("phase", help="Track work phases so cost can be attributed per phase")
    ph.add_argument("action", choices=["start", "end", "status", "list"])
    ph.add_argument("name", nargs="?", help="Phase name (start) or expected name (end)")
    ph.add_argument("--cwd", default=".")
    ph.add_argument("--out", help="Save JSON to path")
    ph.set_defaults(func=cmd_phase)

    ga = sub.add_parser("gate", help="Secret scan + verify + structured review as one verdict")
    ga.add_argument("--cwd", default=".")
    ga.add_argument("--staged", action="store_true", help="Gate the staged diff instead of the working tree")
    ga.add_argument("--only", action="append", choices=["test", "typecheck", "lint"])
    ga.add_argument("--cmd", action="append", help="Extra check as name=shell command")
    ga.add_argument("--timeout", type=int, default=900)
    ga.add_argument("--schema", help="Override review schema path")
    ga.add_argument("--allow", action="append", default=[], help="Allow entry: kind:<name> (secret kinds to ignore)")
    ga.add_argument("--no-review", action="store_true", help="Skip the model review step")
    ga.add_argument("--provider", choices=list(providers.PROVIDERS), help="Review via a direct provider API instead of agy")
    ga.add_argument("--model", help="Provider model id (required with --provider)")
    ga.add_argument("--max-tokens", type=int, default=4000, help="Max output tokens for provider review")
    ga.add_argument("--max-chars", type=int, default=12000, help="Max diff characters sent to the provider")
    ga.add_argument("--keep-going", action="store_true", help="Run every step even after an earlier failure")
    ga.add_argument("--dry-run", action="store_true", help="Print the plan without running checks or review")
    ga.add_argument("--out", help="Save JSON verdict to path")
    ga.set_defaults(func=cmd_gate)

    rv = sub.add_parser("review", help="Direct-provider structured review (no agy)")
    rv.add_argument("--provider", required=True, choices=list(providers.PROVIDERS))
    rv.add_argument("--model", required=True)
    rv.add_argument("--cwd", default=".")
    rv.add_argument("--staged", action="store_true")
    rv.add_argument("--schema")
    rv.add_argument("--timeout", type=int, default=180)
    rv.add_argument("--max-tokens", type=int, default=4000)
    rv.add_argument("--max-chars", type=int, default=12000)
    rv.add_argument("--out", help="Save JSON report to path")
    rv.set_defaults(func=cmd_review)

    va = sub.add_parser("validate", help="Validate a JSON file against a schema (review verdict by default)")
    va.add_argument("--file", required=True)
    va.add_argument("--schema", help="Schema path (default: config/review-schema.json)")
    va.add_argument("--out", help="Save JSON report to path")
    va.set_defaults(func=cmd_validate)

    args = p.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

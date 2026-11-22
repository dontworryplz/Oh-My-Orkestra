#!/usr/bin/env python3
"""Antigravity CLI (`agy`) subprocess adapter for the Sol-Luna Orchestra (stdlib only).

Supports:
  - `doctor`: Verifies `agy` installation, live `agy models`, and role routing.
  - `run`: Executes a real headless `agy` agent with role preset or explicit model,
    handling `-p=...` safely, optional `--allow-write`, `--allow-nesting`, `--schema`,
    and logs telemetry to `ORCHESTRA_LEDGER_PATH` (default `~/.omp/agent/logs/orchestra-ledger.jsonl`).
  - `stats`: Summarizes orchestra ledger telemetry (calls, success/429 rates, latency).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
ROLES_PATH = SKILL_ROOT / "config" / "roles.json"
DEFAULT_LEDGER = Path.home() / ".omp" / "agent" / "logs" / "orchestra-ledger.jsonl"
MODEL_SLUG = re.compile(r"^[a-z][a-z0-9_.-]+$")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def ledger_path() -> Path:
    env = os.environ.get("ORCHESTRA_LEDGER_PATH")
    return Path(env).expanduser() if env else DEFAULT_LEDGER


def record_ledger(entry: dict[str, Any]) -> None:
    try:
        path = ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def emit(payload: dict[str, Any], out: str | None = None) -> None:
    blob = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        path = Path(out).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(blob + "\n", encoding="utf-8")
    print(blob)


def command(args: list[str], timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def get_available_models() -> tuple[list[str], str | None]:
    if not shutil.which("agy"):
        return [], "agy executable not found in PATH"
    try:
        proc = command(["agy", "models"], timeout=25)
    except subprocess.TimeoutExpired:
        return [], "agy models timed out"
    if proc.returncode != 0:
        return [], f"agy models failed ({proc.returncode}): {(proc.stderr or proc.stdout)[-800:]}"
    discovered: list[str] = []
    for raw_line in ANSI.sub("", proc.stdout).splitlines():
        slug = raw_line.strip().split(maxsplit=1)[0] if raw_line.strip() else ""
        if MODEL_SLUG.fullmatch(slug) and (
            slug.startswith("gemini-") or slug.startswith("claude-") or slug.startswith("gpt-")
        ):
            discovered.append(slug)
    if not discovered:
        return [], "agy models returned no recognizable model IDs"
    return sorted(set(discovered)), None


def load_roles() -> dict[str, Any]:
    with ROLES_PATH.open(encoding="utf-8") as fp:
        return json.load(fp)


def make_prompt(role: str, cfg: dict[str, Any], user_prompt: str, writable: bool, nesting: bool) -> str:
    boundary = (
        "Writable mode authorized ONLY for explicitly owned files/directories in this task."
        if writable
        else "READ-ONLY MODE. Do not edit, create, delete, stage, or commit any files."
    )
    nest_rule = (
        "Nesting permitted: you may use internal subagents/workflows (Depth 2 max). Do NOT invoke `omp`."
        if nesting
        else "Do not spawn further subagents or invoke other AI CLIs."
    )
    return (
        f"Role: {role}\n"
        f"Instructions: {cfg['instructions']}\n"
        f"Boundary: {boundary}\n"
        f"Nesting: {nest_rule}\n"
        "Use caveman-lite compression for prose while preserving exact file:line citations, symbols, commands, and errors verbatim.\n"
        "--- BEGIN TASK ---\n"
        f"{user_prompt}\n"
        "--- END TASK ---\n"
    )


def doctor(out: str | None) -> int:
    exe = shutil.which("agy")
    models, error = get_available_models()
    roles = load_roles()
    routes = {
        role: next((m for m in cfg["models"] if m in models), None)
        for role, cfg in roles.items()
    }
    emit(
        {
            "ok": error is None,
            "agy_path": exe,
            "model_list_error": error,
            "models_available": models,
            "resolved_roles": routes,
            "ledger_path": str(ledger_path()),
        },
        out,
    )
    return 0 if error is None else 1


def stats(out: str | None) -> int:
    path = ledger_path()
    if not path.exists():
        emit({"ok": True, "ledger_path": str(path), "total_runs": 0, "by_role": {}, "by_model": {}}, out)
        return 0
    total = 0
    ok_count = 0
    quota_count = 0
    total_elapsed = 0.0
    by_role: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "ok": 0, "failed": 0})
    by_model: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "ok": 0, "failed": 0})
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        is_ok = bool(row.get("ok"))
        ok_count += int(is_ok)
        if "429" in str(row.get("error", "")):
            quota_count += 1
        total_elapsed += float(row.get("elapsed_seconds", 0.0))
        role = str(row.get("role", "unknown"))
        model = str(row.get("model", "unknown"))
        by_role[role]["runs"] += 1
        by_role[role]["ok" if is_ok else "failed"] += 1
        by_model[model]["runs"] += 1
        by_model[model]["ok" if is_ok else "failed"] += 1
    emit(
        {
            "ok": True,
            "ledger_path": str(path),
            "total_runs": total,
            "success_runs": ok_count,
            "quota_429_runs": quota_count,
            "avg_elapsed_seconds": round(total_elapsed / total, 2) if total else 0.0,
            "by_role": dict(by_role),
            "by_model": dict(by_model),
        },
        out,
    )
    return 0


def run_task(args: argparse.Namespace) -> int:
    roles = load_roles()
    if args.role not in roles:
        emit({"ok": False, "error": f"Unknown role {args.role!r}", "valid_roles": sorted(roles)}, args.out)
        return 2
    cfg = roles[args.role]
    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        emit({"ok": False, "error": f"CWD not a directory: {cwd}"}, args.out)
        return 2
    user_prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8") if args.prompt_file else args.prompt
    if not user_prompt or not user_prompt.strip():
        emit({"ok": False, "error": "Prompt is empty"}, args.out)
        return 2

    models, error = get_available_models()
    if error:
        emit({"ok": False, "error": error}, args.out)
        return 2

    requested = args.model or next((m for m in cfg["models"] if m in models), None)
    if not requested or requested not in models:
        emit(
            {
                "ok": False,
                "role": args.role,
                "error": "No configured model for this role is available in `agy models`",
                "suggested": cfg["models"],
                "models_available": models,
            },
            args.out,
        )
        return 2

    writable = args.allow_write or cfg.get("mode") == "auto"
    if cfg.get("mode") == "plan" and not args.allow_write:
        writable = False
    mode = "auto" if writable else "plan"
    nesting = bool(args.allow_nesting or cfg.get("allow_nesting", False))
    prompt = make_prompt(args.role, cfg, user_prompt, writable, nesting)

    cmd = [
        "agy",
        "--model",
        requested,
        "--mode",
        mode,
        "--output-format",
        "json",
        "--print-timeout",
        f"{args.timeout}s",
        "--dangerously-skip-permissions",
    ]
    if args.effort:
        cmd.extend(["--effort", args.effort])
    if args.schema:
        cmd.extend(["--json-schema", str(Path(args.schema).expanduser().resolve())])
    for extra_dir in args.add_dir or []:
        cmd.extend(["--add-dir", extra_dir])
    # CRITICAL: attach prompt to -p= so agy never misparses a flag as the prompt
    cmd.append(f"-p={prompt}")

    started = time.monotonic()
    try:
        proc = command(cmd, timeout=args.timeout + 20, cwd=cwd)
    except subprocess.TimeoutExpired:
        elapsed = round(time.monotonic() - started, 2)
        err = f"Timed out after {args.timeout + 20}s"
        record_ledger({
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": args.role,
            "model": requested,
            "mode": mode,
            "ok": False,
            "status": "TIMEOUT",
            "elapsed_seconds": elapsed,
            "error": err,
        })
        emit({"ok": False, "role": args.role, "model_requested": requested, "error": err}, args.out)
        return 124

    elapsed = round(time.monotonic() - started, 2)
    try:
        result = json.loads(proc.stdout)
        if not isinstance(result, dict):
            raise ValueError("AGY returned non-object JSON")
    except (ValueError, json.JSONDecodeError) as exc:
        err = f"Invalid AGY JSON: {exc}"
        record_ledger({
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": args.role,
            "model": requested,
            "mode": mode,
            "ok": False,
            "status": "PARSE_ERROR",
            "elapsed_seconds": elapsed,
            "error": err,
        })
        emit(
            {
                "ok": False,
                "role": args.role,
                "model_requested": requested,
                "returncode": proc.returncode,
                "error": err,
                "stdout_tail": proc.stdout[-1500:],
                "stderr_tail": proc.stderr[-1500:],
                "elapsed_seconds": elapsed,
            },
            args.out,
        )
        return 1

    status = result.get("status", "UNKNOWN")
    success = status == "SUCCESS" and proc.returncode == 0
    err_msg = result.get("error", "") if not success else ""
    usage = result.get("usage", {})
    record_ledger({
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": args.role,
        "model": requested,
        "mode": mode,
        "ok": success,
        "status": status,
        "elapsed_seconds": elapsed,
        "usage": usage,
        "error": err_msg,
    })
    emit(
        {
            "ok": success,
            "role": args.role,
            "model_requested": requested,
            "mode": mode,
            "status": status,
            "response": result.get("response", "") if success else "",
            "error": err_msg,
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "usage": usage,
            "stderr_tail": proc.stderr[-1000:] if proc.stderr else "",
        },
        args.out,
    )
    return 0 if success else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command_name", required=True)
    dr = sub.add_parser("doctor", help="Verify agy CLI, models, and role routing")
    dr.add_argument("--out", help="Save JSON output to path")

    st = sub.add_parser("stats", help="Summarize orchestra telemetry ledger")
    st.add_argument("--out", help="Save JSON output to path")

    run = sub.add_parser("run", help="Run a headless agy agent and emit normalized JSON")
    run.add_argument("--role", required=True)
    pg = run.add_mutually_exclusive_group(required=True)
    pg.add_argument("--prompt", help="Inline prompt text")
    pg.add_argument("--prompt-file", help="Path to prompt file")
    run.add_argument("--cwd", default=".", help="Workspace directory")
    run.add_argument("--model", help="Override agy model slug")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    run.add_argument("--schema", help="Path to JSON schema file for structured output")
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--allow-write", action="store_true", help="Enable --mode auto for writable tasks")
    run.add_argument("--allow-nesting", action="store_true", help="Permit Depth-2 subagent spawning inside agy")
    run.add_argument("--add-dir", action="append", help="Extra directory to expose to agy")
    run.add_argument("--out", help="Save JSON output to path")

    args = p.parse_args()
    if args.command_name == "doctor":
        return doctor(args.out)
    if args.command_name == "stats":
        return stats(args.out)
    if not 30 <= args.timeout <= 3600:
        emit({"ok": False, "error": "--timeout must be 30..3600"}, args.out)
        return 2
    return run_task(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Orchestra ops toolkit: cost, guard, handoff, verify, redact.

Subcommands:
  cost    Aggregate ledger usage into per-model token/cost estimates.
  guard   Fail when the working diff touches files outside the owned paths.
  handoff Generate/maintain .orchestra/handoff.md from real repo + ledger state.
  verify  Run the project's detected test/typecheck/lint commands and record evidence.
  redact  Find and mask secrets in a diff/file before sending it to a model.
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
    payload = {
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
    if not rows:
        payload["note"] = "No ledger rows in window. Run an agy role first (orchestra run ...)."
    emit(payload, args.out)
    return 0


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

    results: list[dict[str, Any]] = []
    worst = 0
    for check in checks:
        started = time.monotonic()
        proc = subprocess.run(
            check["cmd"],
            shell=True,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
        duration = round(time.monotonic() - started, 2)
        tail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()[-20:]
        results.append(
            {
                "name": check["name"],
                "cmd": check["cmd"],
                "exit": proc.returncode,
                "duration_seconds": duration,
                "tail": tail,
                "ts": now_iso(),
            }
        )
        worst = worst or proc.returncode
        if proc.returncode != 0 and args.stop_on_fail:
            break

    evidence = {"ok": worst == 0, "repo": str(root), "generated_at": now_iso(), "checks": results}
    ev_path = root / ORCH_DIR / "evidence.json"
    try:
        ev_path.parent.mkdir(parents=True, exist_ok=True)
        ev_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    payload = dict(evidence, evidence_path=str(ev_path))
    emit(payload, args.out)
    return 0 if worst == 0 else 1


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


def cmd_redact(args: argparse.Namespace) -> int:
    if args.file:
        path = Path(args.file).expanduser()
        if not path.is_file():
            emit({"ok": False, "error": f"not a file: {path}"}, args.out)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
        source = str(path)
    elif args.staged:
        text = git("diff", "--cached")
        source = "git diff --cached"
    elif args.text:
        text = args.text
        source = "argument"
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
        source = "stdin"
    else:
        text = git("diff")
        source = "git diff"
    if not text.strip():
        emit({"ok": True, "source": source, "clean": True, "findings": [], "note": "No content to scan."}, args.out)
        return 0

    hits = find_secrets(text)
    redacted = redact_text(text)
    payload: dict[str, Any] = {
        "ok": not hits,
        "source": source,
        "clean": not hits,
        "finding_count": len(hits),
        "findings": hits,
    }
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
    r.add_argument("--output", help="Write redacted content to this file")
    r.add_argument("--out", help="Save JSON report to path")
    r.set_defaults(func=cmd_redact)

    args = p.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

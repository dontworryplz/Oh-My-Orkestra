#!/usr/bin/env python3
"""Smart diff & risk router for Sol-Luna Full-Set Orchestra."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

SECURITY_PATTERNS = re.compile(
    r"(auth|login|session|token|jwt|oauth|rbac|acl|permission|tenant|billing|payment|webhook|secret|crypto|sql|migration|prisma|drizzle|schema)",
    re.IGNORECASE,
)
INFRA_PATTERNS = re.compile(
    r"(dockerfile|docker-compose|\.github/workflows|terraform|\.tf$|iam|nginx|cors|csp|helm|k8s)",
    re.IGNORECASE,
)
UI_PATTERNS = re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|html)$", re.IGNORECASE)
DB_MIGRATION_PATTERNS = re.compile(r"(migrations?/|prisma/schema|drizzle|\.sql$|alembic)", re.IGNORECASE)
API_CONTRACT_PATTERNS = re.compile(r"(openapi|swagger|\.graphql$|\.proto$|/api/.*\.(ts|go|py)$)", re.IGNORECASE)


def git_output(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def analyze(staged: bool) -> dict:
    diff_flag = ["--cached"] if staged else []
    files = [f for f in git_output(["diff", *diff_flag, "--name-only"]).splitlines() if f.strip()]
    numstat = git_output(["diff", *diff_flag, "--numstat"]).splitlines()

    added = 0
    deleted = 0
    for line in numstat:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            deleted += int(parts[1])
    total_lines = added + deleted

    has_security = any(SECURITY_PATTERNS.search(f) for f in files)
    has_infra = any(INFRA_PATTERNS.search(f) for f in files)
    has_ui = any(UI_PATTERNS.search(f) for f in files)
    has_db = any(DB_MIGRATION_PATTERNS.search(f) for f in files)
    has_api = any(API_CONTRACT_PATTERNS.search(f) for f in files)

    recommended: list[dict[str, str]] = []
    if not files:
        return {
            "ok": True,
            "scope": "staged" if staged else "working",
            "files_changed": 0,
            "lines_changed": 0,
            "risk": "none",
            "recommended_agents": [],
            "note": "No changed files detected.",
        }

    if total_lines > 300 or len(files) >= 5:
        recommended.append({
            "role": "astra-architect",
            "reason": "Large multi-file change (>300 lines or >=5 files); lock contracts first (fallback: gpt-6.2-sol -> claude-opus-5-5).",
        })
        recommended.append({
            "role": "luna-task-manager",
            "reason": "Decompose into disjoint parallel slices.",
        })

    if has_security:
        risk = "high"
        recommended.append({"role": "threat-modeler", "reason": "Security/auth/DB/tenant paths touched."})
        recommended.append({"role": "security-reviewer", "reason": "Mandatory Opus 5.5 security gate."})
        recommended.append({"role": "neon-code-reviewer", "reason": "Dual-model independent code review."})
    elif total_lines > 120 or len(files) >= 3:
        risk = "medium"
        recommended.append({"role": "neon-code-reviewer", "reason": "Substantial diff; verify logic & contracts."})
    else:
        risk = "low"
        recommended.append({"role": "luna-reviewer", "reason": "Small bounded diff; fast review sufficient."})

    if has_infra:
        recommended.append({"role": "infra-devops-auditor", "reason": "Infra/CI/Docker/IAM files modified."})
    if has_ui:
        recommended.append({"role": "ui-qa-reviewer", "reason": "Frontend/UI files modified."})
    if has_db:
        recommended.append({"role": "db-migration-auditor", "reason": "Database/migration/schema files modified."})
    if has_api:
        recommended.append({"role": "api-contract-auditor", "reason": "API/OpenAPI/GraphQL contract files modified."})

    recommended.append({"role": "luna-tester", "reason": "Run focused empirical tests before final gate."})

    return {
        "ok": True,
        "scope": "staged" if staged else "working",
        "files_changed": len(files),
        "lines_changed": total_lines,
        "risk": risk,
        "flags": {"security": has_security, "infra": has_infra, "ui": has_ui},
        "files": files[:30],
        "recommended_agents": recommended,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--staged", action="store_true", help="Inspect staged diff instead of working tree")
    args = p.parse_args()
    print(json.dumps(analyze(args.staged), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

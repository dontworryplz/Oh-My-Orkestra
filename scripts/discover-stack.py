#!/usr/bin/env python3
"""Auto-discover a repository's tech stack, directory layout, test commands, and orchestra readiness."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any

KEY_DIRS = [
    "src", "app", "apps", "packages", "pages", "api", "server", "backend",
    "frontend", "web", "db", "prisma", "drizzle", "migrations", "tests",
    "test", "e2e", "scripts", "infra", "terraform", ".github/workflows",
    ".planning", ".trail",
]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def detect_stack(root: Path) -> dict[str, Any]:
    languages: list[str] = []
    frameworks: list[str] = []
    databases: list[str] = []
    test_runners: list[str] = []
    package_managers: list[str] = []
    scripts: dict[str, str] = {}

    def add_unique(lst: list[str], item: str) -> None:
        if item not in lst:
            lst.append(item)

    # Scan root + 1-level service/app/package directories for monorepos (e.g. backend/, frontend/, apps/*)
    scan_dirs: list[Path] = [root]
    for sub_name in ("backend", "frontend", "api", "server", "web", "app"):
        sub = root / sub_name
        if sub.is_dir():
            scan_dirs.append(sub)
    for group in ("apps", "packages"):
        gdir = root / group
        if gdir.is_dir():
            scan_dirs.extend(p for p in sorted(gdir.iterdir())[:10] if p.is_dir())

    for base in scan_dirs:
        rel = "." if base == root else str(base.relative_to(root))
        pkg_path = base / "package.json"
        if pkg_path.exists():
            add_unique(languages, "JavaScript/TypeScript" if (base / "tsconfig.json").exists() else "JavaScript")
            pkg = read_json(pkg_path)
            for k, v in pkg.get("scripts", {}).items():
                key = k if rel == "." else f"{rel}:{k}"
                scripts[key] = str(v)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            for pm_file, pm_name in [
                ("pnpm-lock.yaml", "pnpm"),
                ("yarn.lock", "yarn"),
                ("bun.lockb", "bun"),
                ("bun.lock", "bun"),
                ("package-lock.json", "npm"),
            ]:
                if (base / pm_file).exists():
                    add_unique(package_managers, pm_name)

            fw_map = {
                "next": "Next.js",
                "react": "React",
                "vue": "Vue",
                "svelte": "Svelte",
                "astro": "Astro",
                "@nestjs/core": "NestJS",
                "express": "Express",
                "fastify": "Fastify",
                "hono": "Hono",
                "tailwindcss": "Tailwind CSS",
            }
            for dep, label in fw_map.items():
                if dep in deps:
                    add_unique(frameworks, label)

            db_map = {
                "prisma": "Prisma",
                "@prisma/client": "Prisma",
                "drizzle-orm": "Drizzle ORM",
                "mongoose": "MongoDB (Mongoose)",
                "pg": "PostgreSQL",
                "mysql2": "MySQL",
                "better-sqlite3": "SQLite",
                "redis": "Redis",
                "ioredis": "Redis",
                "@supabase/supabase-js": "Supabase",
            }
            for dep, label in db_map.items():
                if dep in deps:
                    add_unique(databases, label)

            test_map = {
                "vitest": "Vitest",
                "jest": "Jest",
                "@playwright/test": "Playwright",
                "playwright": "Playwright",
                "cypress": "Cypress",
            }
            for dep, label in test_map.items():
                if dep in deps:
                    add_unique(test_runners, label)

        if (base / "pyproject.toml").exists() or (base / "requirements.txt").exists():
            add_unique(languages, "Python")
            py_text = ""
            for p in ("pyproject.toml", "requirements.txt"):
                if (base / p).exists():
                    py_text += (base / p).read_text(encoding="utf-8", errors="ignore").lower()
            for key, label in [("fastapi", "FastAPI"), ("django", "Django"), ("flask", "Flask")]:
                if key in py_text:
                    add_unique(frameworks, label)
            for key, label in [("sqlalchemy", "SQLAlchemy"), ("psycopg", "PostgreSQL"), ("pymongo", "MongoDB"), ("redis", "Redis")]:
                if key in py_text:
                    add_unique(databases, label)
            if "pytest" in py_text:
                add_unique(test_runners, "Pytest")

        if (base / "go.mod").exists():
            add_unique(languages, "Go")
            add_unique(test_runners, "go test")
        if (base / "Cargo.toml").exists():
            add_unique(languages, "Rust")
            add_unique(test_runners, "cargo test")

    infra: list[str] = []
    if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists() or (root / "compose.yml").exists():
        infra.append("Docker")
    if (root / ".github" / "workflows").exists():
        infra.append("GitHub Actions")
    if list(root.glob("*.tf")) or (root / "terraform").exists():
        infra.append("Terraform")

    present_dirs = [d for d in KEY_DIRS if (root / d).exists()]
    top_files = sorted(p.name for p in root.iterdir() if p.is_file() and not p.name.startswith(".DS_Store"))[:35]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "languages": languages or ["Unknown"],
        "package_managers": package_managers,
        "frameworks": frameworks,
        "databases": databases,
        "test_runners": test_runners,
        "infra": infra,
        "scripts": scripts,
        "present_dirs": present_dirs,
        "top_level_files": top_files,
        "has_trail": (root / ".trail").exists(),
        "trail_cli": shutil.which("trail") is not None,
        "has_gsd_planning": (root / ".planning").exists(),
    }


def render_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# Repository Tech-Stack & Map (`.orchestra/REPO_MAP.md`)",
        "",
        f"- **Root:** `{profile['repo_root']}`",
        f"- **Generated:** `{profile['generated_at']}`",
        f"- **Languages:** {', '.join(profile['languages'])}",
        f"- **Package Managers:** {', '.join(profile['package_managers']) or 'None detected'}",
        f"- **Frameworks:** {', '.join(profile['frameworks']) or 'None detected'}",
        f"- **Databases / ORMs:** {', '.join(profile['databases']) or 'None detected'}",
        f"- **Test Runners:** {', '.join(profile['test_runners']) or 'None detected'}",
        f"- **Infra / CI:** {', '.join(profile['infra']) or 'None detected'}",
        f"- **Trail-Code (`.trail/`):** {'Present' if profile['has_trail'] else 'Not initialized'}",
        f"- **GSD Planning (`.planning/`):** {'Present' if profile['has_gsd_planning'] else 'Not initialized'}",
        "",
        "## Key Directories Present",
        "",
    ]
    for d in profile["present_dirs"]:
        lines.append(f"- `{d}/`")
    if not profile["present_dirs"]:
        lines.append("- *(No standard subdirectories detected at root)*")

    if profile["scripts"]:
        lines.extend(["", "## Package Scripts", ""])
        for k, v in list(profile["scripts"].items())[:20]:
            lines.append(f"- `{k}`: `{v}`")

    lines.extend(["", "## Top-Level Files", ""])
    lines.append(", ".join(f"`{f}`" for f in profile["top_level_files"]) or "*(none)*")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cwd", default=".", help="Repository root to inspect")
    p.add_argument("--no-write", action="store_true", help="Print JSON only without writing .orchestra/")
    args = p.parse_args()

    root = Path(args.cwd).expanduser().resolve()
    profile = detect_stack(root)

    if not args.no_write:
        out_dir = root / ".orchestra"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stack-profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        (out_dir / "REPO_MAP.md").write_text(render_markdown(profile), encoding="utf-8")
        rules_path = out_dir / "rules.md"
        if not rules_path.exists():
            rules_path.write_text(
                "# Project Orchestra Rules (`.orchestra/rules.md`)\n\n"
                "Add repository-specific invariants here. Every Orchestra agent reads this in Step 0.\n\n"
                "- Never bypass tenant/auth checks or alter DB schemas without a safe migration.\n"
                "- Run project-specific test/typecheck commands listed in `.orchestra/REPO_MAP.md` before delivery.\n",
                encoding="utf-8",
            )

    print(json.dumps(profile, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

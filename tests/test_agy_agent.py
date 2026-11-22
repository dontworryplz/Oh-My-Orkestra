#!/usr/bin/env python3
"""Unit tests for agy_agent.py using a mocked `agy` executable."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "agy_agent.py"

FAKE_AGY = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if args == ["models"]:
    print("gemini-4-neon-xhigh           Gemini 4 Neon (XHigh)")
    print("gemini-4-neon-high            Gemini 4 Neon (High)")
    print("gemini-4-hydrogen-xhigh       Gemini 4 Hydrogen (XHigh)")
    print("gemini-4-hydrogen-xhigh       Gemini 4 Hydrogen (XHigh)")
    print("gemini-4-argon-high           Gemini 4 Argon (High)")
    print("claude-opus-5-5-high          Claude Opus 5.5 (High)")
    print("claude-sonnet-5-5-high        Claude Sonnet 5.5 (High)")
    print("gemini-pro-orchestrator-neon  Orchestrator (Neon)")
    sys.exit(0)

if "--model" not in args or "--mode" not in args or "--output-format" not in args:
    print("missing required flags", file=sys.stderr)
    sys.exit(4)

if not any(a.startswith("-p=") for a in args):
    print("prompt must be attached via -p=", file=sys.stderr)
    sys.exit(5)

model = args[args.index("--model") + 1]
mode = args[args.index("--mode") + 1]

if os.getenv("MOCK_AGY_SCENARIO") == "quota":
    print(json.dumps({"status": "ERROR", "error": "429 RESOURCE_EXHAUSTED", "response": ""}))
    sys.exit(1)

if os.getenv("MOCK_AGY_SCENARIO") == "quota_xhigh_only" and model == "gemini-4-neon-xhigh":
    print(json.dumps({"status": "ERROR", "error": "429 RESOURCE_EXHAUSTED", "response": ""}))
    sys.exit(1)

print(json.dumps({"status": "SUCCESS", "response": f"ok:{model}:{mode}", "usage": {"total": 10}}))
'''


class TestAgyAgent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        exe = self.base / "agy"
        exe.write_text(FAKE_AGY, encoding="utf-8")
        exe.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.base) + os.pathsep + self.env.get("PATH", "")
        self.env["ORCHESTRA_LEDGER_PATH"] = str(self.base / "ledger.jsonl")

    def run_cli(self, *argv, env=None):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, argv)],
            capture_output=True,
            text=True,
            env=env or self.env,
        )
        return proc.returncode, json.loads(proc.stdout)

    def test_doctor_resolves_all_roles(self):
        rc, data = self.run_cli("doctor")
        self.assertEqual(rc, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["resolved_roles"]["neon-reviewer"], "gemini-4-neon-xhigh")
        self.assertEqual(data["resolved_roles"]["hydrogen-debugger"], "gemini-4-hydrogen-xhigh")
        self.assertEqual(data["resolved_roles"]["argon-explorer"], "gemini-4-argon-high")
        self.assertEqual(data["resolved_roles"]["neon-orchestrator"], "gemini-pro-orchestrator-neon")

    def test_neon_reviewer_runs_plan_mode(self):
        rc, data = self.run_cli("run", "--role", "neon-reviewer", "--cwd", self.base, "--prompt", "Review diff")
        self.assertEqual(rc, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["mode"], "plan")
        self.assertEqual(data["response"], "ok:gemini-4-neon-xhigh:plan")

    def test_neon_orchestrator_runs_auto_mode(self):
        rc, data = self.run_cli("run", "--role", "neon-orchestrator", "--cwd", self.base, "--prompt", "Run slice")
        self.assertEqual(rc, 0)
        self.assertEqual(data["mode"], "auto")
        self.assertEqual(data["response"], "ok:gemini-pro-orchestrator-neon:auto")

    def test_quota_failure_not_fabricated(self):
        env = self.env.copy()
        env["MOCK_AGY_SCENARIO"] = "quota"
        rc, data = self.run_cli("run", "--role", "neon-reviewer", "--cwd", self.base, "--prompt", "Review", env=env)
        self.assertNotEqual(rc, 0)
        self.assertFalse(data["ok"])
        self.assertIn("429", data["error"])

    def test_unknown_model_fails_closed(self):
        rc, data = self.run_cli(
            "run", "--role", "neon-reviewer", "--cwd", self.base, "--model", "nonexistent-model", "--prompt", "Hi"
        )
        self.assertEqual(rc, 2)
        self.assertFalse(data["ok"])

    def test_schema_and_stats_ledger(self):
        schema = Path(__file__).resolve().parents[1] / "config" / "review-schema.json"
        rc, data = self.run_cli(
            "run", "--role", "neon-reviewer", "--cwd", self.base, "--schema", schema, "--prompt", "Review"
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["ok"])
        rc_s, st = self.run_cli("stats", "--budget", "5")
        self.assertEqual(rc_s, 0)
        self.assertEqual(st["total_runs"], 1)
        self.assertEqual(st["success_runs"], 1)
        self.assertEqual(st["by_role"]["neon-reviewer"]["ok"], 1)
        self.assertEqual(st["budget"]["remaining"], 4)
        self.assertFalse(st["budget"]["exceeded"])

    def test_doctor_with_mcps_flag(self):
        rc, data = self.run_cli("doctor", "--mcps")
        self.assertEqual(rc, 0)
        self.assertIn("mcps", data)

    def test_auto_fallback_on_429(self):
        env = self.env.copy()
        env["MOCK_AGY_SCENARIO"] = "quota_xhigh_only"
        rc, data = self.run_cli(
            "run", "--role", "neon-reviewer", "--auto-fallback", "--cwd", self.base, "--prompt", "Review", env=env
        )
        self.assertEqual(rc, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["model_requested"], "gemini-4-neon-high")
        self.assertEqual(data["fallback_from"], "gemini-4-neon-xhigh")
        self.assertEqual(len(data["attempts"]), 2)

    def test_discover_stack_monorepo(self):
        root = self.base / "monorepo"
        (root / "backend").mkdir(parents=True)
        (root / "frontend").mkdir(parents=True)
        (root / "backend" / "go.mod").write_text("module example.com/app\n", encoding="utf-8")
        (root / "frontend" / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^19.0.0"}, "devDependencies": {"vitest": "^2.0.0"}}),
            encoding="utf-8",
        )
        discover = Path(__file__).resolve().parents[1] / "scripts" / "discover-stack.py"
        proc = subprocess.run([sys.executable, str(discover), "--cwd", str(root)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        profile = json.loads(proc.stdout)
        self.assertIn("Go", profile["languages"])
        self.assertIn("JavaScript", profile["languages"])
        self.assertIn("React", profile["frameworks"])
        self.assertIn("Vitest", profile["test_runners"])
        self.assertTrue((root / ".orchestra" / "REPO_MAP.md").exists())
        self.assertTrue((root / ".orchestra" / "rules.md").exists())

    def test_smart_route_detects_security_and_ui(self):
        repo = self.base / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=repo, check=True)
        (repo / "auth.ts").write_text("export const x = 1;\n", encoding="utf-8")
        (repo / "Button.tsx").write_text("export const B = () => null;\n", encoding="utf-8")
        (repo / "migrations").mkdir()
        (repo / "migrations" / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
        (repo / "openapi.yaml").write_text("openapi: 3.1.0\n", encoding="utf-8")
        subprocess.run(["git", "add", "auth.ts", "Button.tsx", "migrations/001.sql", "openapi.yaml"], cwd=repo, check=True)
        router = Path(__file__).resolve().parents[1] / "scripts" / "smart-route.py"
        proc = subprocess.run([sys.executable, str(router), "--staged"], cwd=repo, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        res = json.loads(proc.stdout)
        self.assertEqual(res["risk"], "high")
        roles = {r["role"] for r in res["recommended_agents"]}
        self.assertIn("security-reviewer", roles)
        self.assertIn("ui-qa-reviewer", roles)
        self.assertIn("db-migration-auditor", roles)
        self.assertIn("api-contract-auditor", roles)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for orchestra_tools.py (cost, guard, handoff, verify, redact)."""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import orchestra_tools as ot  # noqa: E402


def ns(**kwargs) -> argparse.Namespace:
    defaults = {
        "out": None,
        "days": 0,
        "pricing": None,
        "owned": [],
        "ignore": [],
        "base": None,
        "cwd": ".",
        "write": False,
        "only": None,
        "cmd": None,
        "timeout": 30,
        "stop_on_fail": False,
        "dry_run": False,
        "file": None,
        "staged": False,
        "text": None,
        "check": False,
        "output": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def run_quiet(fn, args):
    buf = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = fn(args)
    return rc, buf.getvalue(), err.getvalue()


class MatchPathTests(unittest.TestCase):
    def test_glob_dir_prefix(self):
        self.assertTrue(ot._match_path("src/api/handlers/x.ts", "src/api/**"))
        self.assertTrue(ot._match_path("src/api", "src/api/**"))
        self.assertFalse(ot._match_path("src/apiary/x.ts", "src/api/**"))

    def test_exact_and_dir_prefix(self):
        self.assertTrue(ot._match_path("src/a.ts", "src/a.ts"))
        self.assertTrue(ot._match_path("src/a.ts", "src"))
        self.assertFalse(ot._match_path("src/b.ts", "src/a.ts"))

    def test_glob_star(self):
        self.assertTrue(ot._match_path("docs/x/readme.md", "docs/*/readme.md"))
        self.assertFalse(ot._match_path("docs/x/y/readme.md", "docs/*/readme.md"))

    def test_leading_dot_slash_normalized(self):
        self.assertTrue(ot._match_path("./src/a.ts", "src/a.ts"))


class GuardTests(unittest.TestCase):
    def test_violation_exit_and_payload(self):
        with mock.patch.object(ot, "changed_files", return_value=["src/a.ts", "secrets/env"]):
            code, out, err = run_quiet(ot.cmd_guard, ns(owned=["src/**"]))
        payload = json.loads(out)
        self.assertEqual(code, 3)
        self.assertEqual(payload["violations"], ["secrets/env"])
        self.assertIn("outside scope", err)

    def test_clean_exit_zero(self):
        with mock.patch.object(ot, "changed_files", return_value=["src/a.ts"]):
            code, out, _ = run_quiet(ot.cmd_guard, ns(owned=["src/**"]))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])

    def test_ignore_exempts_paths(self):
        with mock.patch.object(ot, "changed_files", return_value=[".orchestra/handoff.md", "src/a.ts"]):
            code, out, _ = run_quiet(
                ot.cmd_guard, ns(owned=["src/**"], ignore=[".orchestra/**"])
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["changed_files"], ["src/a.ts"])

    def test_requires_owned(self):
        code, out, _ = run_quiet(ot.cmd_guard, ns(owned=[]))
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)["ok"])


class RedactTests(unittest.TestCase):
    def test_detects_provider_keys_without_leaking(self):
        text = "\n".join([
            "AWS_KEY=AKIAABCDEFGHIJKLMNOP",
            "gh: ghp_" + "a" * 36,
            "sk-proj-" + "b" * 30,
        ])
        hits = ot.find_secrets(text)
        kinds = {h["kind"] for h in hits}
        self.assertIn("aws-access-key", kinds)
        self.assertIn("github-token", kinds)
        self.assertIn("openai-key", kinds)
        for hit in hits:
            self.assertNotIn("AKIAABCDEFGHIJKLMNOP", hit["preview"])
            self.assertNotIn("b" * 30, hit["preview"])

    def test_redact_text_masks_all(self):
        text = "token=AKIAABCDEFGHIJKLMNOP, db postgres://user:pass@host:5432/db"
        masked = ot.redact_text(text)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", masked)
        self.assertNotIn("user:pass@", masked)
        self.assertIn("REDACTED:<aws-access-key>", masked)

    def test_check_mode_exit_4_and_clean_exit_0(self):
        code, out, _ = run_quiet(ot.cmd_redact, ns(text="AKIAABCDEFGHIJKLMNOP", check=True))
        self.assertEqual(code, 4)
        self.assertFalse(json.loads(out)["clean"])

        code, out, _ = run_quiet(ot.cmd_redact, ns(text="nothing secret here", check=True))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["clean"])

    def test_private_key_block_masked(self):
        pem = "-----BEGIN PRIVATE KEY-----\nMIIEvQ\n-----END PRIVATE KEY-----"
        self.assertNotIn("MIIEvQ", ot.redact_text(pem))

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "redacted.diff"
            code, out, _ = run_quiet(
                ot.cmd_redact, ns(text="AWS_KEY=AKIAABCDEFGHIJKLMNOP", output=str(dest))
            )
            self.assertEqual(code, 0)
            self.assertNotIn("AKIAABCDEFGHIJKLMNOP", dest.read_text())
            self.assertEqual(json.loads(out)["redacted_written"], str(dest.resolve()))


class CostTests(unittest.TestCase):
    def _ledger(self, tmp: str, rows: list[dict]) -> Path:
        path = Path(tmp) / "ledger.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def test_aggregates_tokens_and_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            pricing = Path(tmp) / "pricing.json"
            pricing.write_text(json.dumps({"models": {"gemini-4-neon": {"input": 2.0, "output": 10.0}}}))
            ledger = self._ledger(tmp, [
                {"ts": ot.now_iso(), "role": "neon-reviewer", "model": "gemini-4-neon-xhigh",
                 "ok": True, "elapsed_seconds": 3.0, "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 100_000}},
                {"ts": ot.now_iso(), "role": "neon-reviewer", "model": "gemini-4-neon-xhigh",
                 "ok": False, "elapsed_seconds": 1.0, "usage": {"total_tokens": 500_000}},
            ])
            with mock.patch.dict(os.environ, {"ORCHESTRA_LEDGER": str(ledger)}):
                code, out, _ = run_quiet(ot.cmd_cost, ns(pricing=str(pricing)))
            payload = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(payload["runs_in_window"], 2)
            self.assertEqual(payload["runs_with_token_usage"], 2)
            entry = payload["by_model"]["gemini-4-neon-xhigh"]
            self.assertEqual(entry["failed"], 1)
            self.assertEqual(entry["input_tokens"], 1_500_000)
            self.assertAlmostEqual(entry["cost_usd"], 4.0, places=4)

    def test_unpriced_model_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            pricing = Path(tmp) / "pricing.json"
            pricing.write_text(json.dumps({"models": {}}))
            ledger = self._ledger(tmp, [
                {"ts": ot.now_iso(), "role": "x", "model": "mystery-model", "ok": True,
                 "usage": {"input_tokens": 10, "output_tokens": 5}},
            ])
            with mock.patch.dict(os.environ, {"ORCHESTRA_LEDGER": str(ledger)}):
                _, out, _ = run_quiet(ot.cmd_cost, ns(pricing=str(pricing)))
            payload = json.loads(out)
            self.assertEqual(payload["unpriced_models"], ["mystery-model"])
            self.assertEqual(payload["estimated_total_usd"], 0)

    def test_missing_ledger_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"ORCHESTRA_LEDGER": str(Path(tmp) / "none.jsonl")}):
                code, out, _ = run_quiet(ot.cmd_cost, ns())
            payload = json.loads(out)
            self.assertEqual(code, 0)
            self.assertEqual(payload["runs_in_window"], 0)


class VerifyTests(unittest.TestCase):
    def test_derive_checks_from_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({
                "scripts": {"test": "vitest run", "lint": "eslint .", "typecheck": "tsc --noEmit"},
            }))
            (root / "pnpm-lock.yaml").write_text("")
            checks = ot.derive_checks(root)
            cmds = {c["name"]: c["cmd"] for c in checks}
            self.assertEqual(cmds["test"], "pnpm test")
            self.assertEqual(cmds["lint"], "pnpm run lint")
            self.assertEqual(cmds["typecheck"], "pnpm run typecheck")

    def test_derive_checks_go_and_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module x\n")
            (root / "requirements.txt").write_text("pytest\n")
            (root / "tests").mkdir()
            checks = {c["name"]: c["cmd"] for c in ot.derive_checks(root)}
            self.assertEqual(checks["test"], "go test ./...")

    def test_detects_unittest_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "test_x.py").write_text("import unittest\n")
            checks = {c["name"]: c["cmd"] for c in ot.derive_checks(root)}
            self.assertIn("unittest", checks["test"])

    def test_dry_run_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module x\n")
            with mock.patch.object(ot.subprocess, "run") as fake:
                code, out, _ = run_quiet(ot.cmd_verify, ns(cwd=str(root), dry_run=True))
            fake.assert_not_called()
            payload = json.loads(out)
            self.assertEqual(code, 0)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["checks"][0]["cmd"], "go test ./...")

    def test_extra_cmd_and_failure_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, _ = run_quiet(
                ot.cmd_verify,
                ns(cwd=str(root), cmd=["smoke=exit 7"], stop_on_fail=True, timeout=30),
            )
            payload = json.loads(out)
            names = [c["name"] for c in payload["checks"]]
            self.assertEqual(names, ["smoke"])
            self.assertEqual(payload["checks"][-1]["exit"], 7)
            self.assertEqual(code, 1)
            self.assertTrue((root / ".orchestra" / "evidence.json").exists())


class HandoffTests(unittest.TestCase):
    def test_generate_contains_core_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".orchestra").mkdir()
            (root / ".orchestra" / "stack-profile.json").write_text(json.dumps({
                "languages": ["TypeScript"], "test_runners": ["Vitest"], "scripts": {"test": "vitest"},
            }))
            code, out, _ = run_quiet(ot.cmd_handoff, ns(cwd=str(root)))
            self.assertEqual(code, 0)
            for heading in ("Goal & Locked Decisions", "Completed Slices", "In-Flight Work",
                            "Remaining Tasks", "Open Risks", "Environment Facts", "Recent Commits"):
                self.assertIn(heading, out)
            self.assertIn("TypeScript", out)

    def test_write_preserves_handwritten_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orch = root / ".orchestra"
            orch.mkdir()
            (orch / "handoff.md").write_text(
                "# Old\n\n## 1. Goal & Locked Decisions (Grill-Me / Astra)\n\n"
                "- use expand/contract migration — avoids table lock\n\n"
                "## 5. Open Risks / Blockers\n\n- Stripe sandbox key missing\n"
            )
            code, out, _ = run_quiet(ot.cmd_handoff, ns(cwd=str(root), write=True))
            self.assertEqual(code, 0)
            body = (orch / "handoff.md").read_text()
            self.assertIn("expand/contract migration", body)
            self.assertIn("Stripe sandbox key missing", body)
            self.assertTrue((orch / "handoff.prev.md").exists())
            self.assertIn("wrote", out)

    def test_extract_section_ignores_placeholders(self):
        md = "## 4. Remaining Tasks (ordered)\n\n- <fill: task>\n- real task\n\n## 5. Open Risks\n"
        self.assertEqual(ot._extract_section(md, "4. Remaining Tasks"), ["- real task"])


if __name__ == "__main__":
    unittest.main()

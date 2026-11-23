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
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"  # split so secret scanners do not flag fixtures
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
        "schema": None,
        "action": None,
        "name": None,
        "history": False,
        "limit": 200,
        "since": None,
        "allow": [],
        "by": None,
        "csv": False,
        "keep_going": False,
        "no_review": False,
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
            "AWS_KEY=" + FAKE_AWS,
            "gh: ghp_" + "a" * 36,
            "sk-proj-" + "b" * 30,
        ])
        hits = ot.find_secrets(text)
        kinds = {h["kind"] for h in hits}
        self.assertIn("aws-access-key", kinds)
        self.assertIn("github-token", kinds)
        self.assertIn("openai-key", kinds)
        for hit in hits:
            self.assertNotIn(FAKE_AWS, hit["preview"])
            self.assertNotIn("b" * 30, hit["preview"])

    def test_redact_text_masks_all(self):
        text = "token=" + FAKE_AWS + ", db postgres://user" + ":pass@host:5432/db"
        masked = ot.redact_text(text)
        self.assertNotIn(FAKE_AWS, masked)
        self.assertNotIn("user:pass@", masked)
        self.assertIn("REDACTED:<aws-access-key>", masked)

    def test_check_mode_exit_4_and_clean_exit_0(self):
        code, out, _ = run_quiet(ot.cmd_redact, ns(text=FAKE_AWS, check=True))
        self.assertEqual(code, 4)
        self.assertFalse(json.loads(out)["clean"])

        code, out, _ = run_quiet(ot.cmd_redact, ns(text="nothing secret here", check=True))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["clean"])

    def test_private_key_block_masked(self):
        pem = "-----BEGIN PRIVATE KEY-----\n" + ("A" * 80) + "\n-----END PRIVATE KEY-----"
        self.assertNotIn("A" * 80, ot.redact_text(pem))

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "redacted.diff"
            code, out, _ = run_quiet(
                ot.cmd_redact, ns(text="AWS_KEY=" + FAKE_AWS, output=str(dest))
            )
            self.assertEqual(code, 0)
            self.assertNotIn(FAKE_AWS, dest.read_text())
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


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ledger = self.root / "ledger.jsonl"
        patch = mock.patch.dict(os.environ, {"ORCHESTRA_LEDGER": str(self.ledger)})
        patch.start()
        self.addCleanup(patch.stop)

    def test_start_status_end_cycle(self):
        code, out, _ = run_quiet(ot.cmd_phase, ns(action="start", name="p2-auth", cwd=str(self.root)))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["phase"], "p2-auth")

        code, out, _ = run_quiet(ot.cmd_phase, ns(action="status", cwd=str(self.root)))
        status = json.loads(out)
        self.assertEqual(status["active"], "p2-auth")
        self.assertGreaterEqual(status["elapsed_seconds"], 0)

        code, out, _ = run_quiet(ot.cmd_phase, ns(action="end", name="p2-auth", cwd=str(self.root)))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["phase"], "p2-auth")

        code, out, _ = run_quiet(ot.cmd_phase, ns(action="status", cwd=str(self.root)))
        self.assertIsNone(json.loads(out)["active"])

    def test_end_without_start_fails(self):
        code, out, _ = run_quiet(ot.cmd_phase, ns(action="end", cwd=str(self.root)))
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)["ok"])

    def test_end_name_mismatch_fails(self):
        run_quiet(ot.cmd_phase, ns(action="start", name="one", cwd=str(self.root)))
        code, out, _ = run_quiet(ot.cmd_phase, ns(action="end", name="two", cwd=str(self.root)))
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)["ok"])

    def test_start_auto_closes_previous(self):
        run_quiet(ot.cmd_phase, ns(action="start", name="one", cwd=str(self.root)))
        code, out, _ = run_quiet(ot.cmd_phase, ns(action="start", name="two", cwd=str(self.root)))
        self.assertEqual(json.loads(out)["closed_previous"], "one")

    def test_cost_attributes_rows_to_phase(self):
        run_quiet(ot.cmd_phase, ns(action="start", name="p1", cwd=str(self.root)))
        self.ledger.write_text(
            json.dumps({"ts": ot.now_iso(), "model": "claude-opus-5-5-high", "role": "reviewer",
                        "ok": True, "usage": {"input_tokens": 1000, "output_tokens": 500}}) + "\n",
            encoding="utf-8",
        )
        run_quiet(ot.cmd_phase, ns(action="end", cwd=str(self.root)))
        with mock.patch.object(ot, "PRICING_PATH", self.root / "missing.json"):
            code, out, _ = run_quiet(ot.cmd_cost, ns(by="phase", cwd=str(self.root)))
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertIn("p1", payload["by_phase"])
        self.assertEqual(payload["by_phase"]["p1"]["runs"], 1)

    def test_cost_csv(self):
        self.ledger.write_text(
            json.dumps({"ts": ot.now_iso(), "model": "m1", "role": "r", "ok": True,
                        "usage": {"input_tokens": 10, "output_tokens": 5}}) + "\n",
            encoding="utf-8",
        )
        code, out, _ = run_quiet(ot.cmd_cost, ns(csv=True))
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().splitlines()[0], "model,runs,failed,input_tokens,output_tokens,cost_usd")
        self.assertIn("m1,1,0,10,5", out)


class RedactHistoryTests(unittest.TestCase):
    def test_history_finds_secret_and_check_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess = __import__("subprocess")
            def git(*a):
                return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True,
                                      env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                                           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
            git("init", "-q", "-b", "main")
            (repo / "app.env").write_text("AWS_KEY=" + FAKE_AWS + "\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-q", "-m", "add config")
            (repo / "app.env").write_text("clean\n", encoding="utf-8")
            git("commit", "-q", "-am", "remove config")

            with mock.patch.object(ot, "git", side_effect=lambda *a: subprocess.run(
                ["git", *a], cwd=repo, capture_output=True, text=True).stdout):
                code, out, _ = run_quiet(ot.cmd_redact, ns(history=True, check=True, limit=50, allow=[]))
            payload = json.loads(out)
            self.assertEqual(code, 4)
            self.assertEqual(payload["finding_count"], 1)
            self.assertEqual(payload["findings"][0]["path"], "app.env")
            self.assertNotIn(FAKE_AWS, json.dumps(payload))

    def test_allow_kind_suppresses(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess = __import__("subprocess")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            (repo / "a.env").write_text("AWS_KEY=" + FAKE_AWS + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                            "commit", "-q", "-m", "add"], cwd=repo, check=True)
            with mock.patch.object(ot, "git", side_effect=lambda *a: subprocess.run(
                ["git", *a], cwd=repo, capture_output=True, text=True).stdout):
                code, out, _ = run_quiet(ot.cmd_redact,
                                         ns(history=True, check=True, limit=50, allow=["kind:aws-access-key"]))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["finding_count"], 0)


class ValidateTests(unittest.TestCase):
    def _verdict(self, **over):
        data = {
            "verdict": "PASS",
            "findings": [],
            "resolved_checks": ["tests"],
            "residual_uncertainty": [],
        }
        data.update(over)
        return data

    def test_valid_verdict_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.json"
            path.write_text(json.dumps(self._verdict()), encoding="utf-8")
            code, out, _ = run_quiet(ot.cmd_validate, ns(file=str(path)))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["ok"])

    def test_missing_field_fails_with_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.json"
            data = self._verdict()
            del data["residual_uncertainty"]
            path.write_text(json.dumps(data), encoding="utf-8")
            code, out, _ = run_quiet(ot.cmd_validate, ns(file=str(path)))
        payload = json.loads(out)
        self.assertEqual(code, 5)
        self.assertTrue(any("residual_uncertainty" in e for e in payload["errors"]))

    def test_bad_enum_and_extra_key_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.json"
            path.write_text(json.dumps(self._verdict(verdict="MAYBE", extra=1)), encoding="utf-8")
            code, out, _ = run_quiet(ot.cmd_validate, ns(file=str(path)))
        errors = json.loads(out)["errors"]
        self.assertEqual(code, 5)
        self.assertTrue(any("not in" in e for e in errors))
        self.assertTrue(any("not allowed" in e for e in errors))

    def test_invalid_json_returns_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.json"
            path.write_text("{not json", encoding="utf-8")
            code, _, _ = run_quiet(ot.cmd_validate, ns(file=str(path)))
        self.assertEqual(code, 5)

    def test_finding_item_schema(self):
        bad = self._verdict(findings=[{"severity": "P9", "title": "x", "file": "a.py",
                                       "line": 0, "scenario": "s", "fix": "f"}])
        errors = ot.validate_payload(bad, ot.load_json(ot.REVIEW_SCHEMA))
        self.assertTrue(any("severity" in e for e in errors))
        self.assertTrue(any("line" in e for e in errors))


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_x.py").write_text("import unittest\n", encoding="utf-8")

    def test_dry_run_reports_plan(self):
        code, out, _ = run_quiet(ot.cmd_gate, ns(cwd=str(self.root), dry_run=True))
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([s["name"] for s in payload["steps"]], ["secrets", "verify", "review"])
        self.assertEqual(payload["steps"][2]["reason"], "--dry-run")

    def test_failing_check_fails_gate(self):
        code, out, _ = run_quiet(
            ot.cmd_gate,
            ns(cwd=str(self.root), cmd=["boom=false"], dry_run=False, no_review=False, keep_going=False),
        )
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        review = [s for s in payload["steps"] if s["name"] == "review"][0]
        self.assertEqual(review["status"], "skipped")

    def test_passing_check_without_agy_skips_review(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ot.shutil, "which", return_value=None):
            code, out, _ = run_quiet(
                ot.cmd_gate, ns(cwd=tmp, cmd=["ok=true"], dry_run=False, no_review=False)
            )
        payload = json.loads(out)
        review = [s for s in payload["steps"] if s["name"] == "review"][0]
        self.assertEqual(review["status"], "skipped")
        self.assertIn("agy", review["reason"])
        self.assertTrue(payload["ok"])
        self.assertEqual(code, 0)

    def test_gate_writes_verdict_file(self):
        with mock.patch.object(ot.shutil, "which", return_value=None):
            run_quiet(ot.cmd_gate, ns(cwd=str(self.root), cmd=["ok=true"], no_review=False))
        self.assertTrue((self.root / ".orchestra" / "gate.json").is_file())

    def test_verdict_parse_handles_fences(self):
        payload = {"response": "```json\n{\"verdict\": \"PASS\"}\n```"}
        self.assertEqual(ot._verdict_from(payload), {"verdict": "PASS"})


class ProviderTests(unittest.TestCase):
    def test_build_request_shapes(self):
        openai = ot.providers.build_request("openai", "gpt-x", "hi", 100)
        self.assertEqual(openai["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(openai["body"]["messages"][0]["content"], "hi")
        anth = ot.providers.build_request("anthropic", "claude-x", "hi", 100)
        self.assertEqual(anth["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(anth["body"]["max_tokens"], 100)
        goog = ot.providers.build_request("google", "gemini-x", "hi", 100)
        self.assertTrue(goog["url"].endswith("/gemini-x:generateContent"))

    def test_build_request_requires_model(self):
        with self.assertRaises(ValueError):
            ot.providers.build_request("openai", "", "hi")
        with self.assertRaises(ValueError):
            ot.providers.build_request("nope", "m", "hi")

    def test_parse_response_shapes(self):
        oa = ot.providers.parse_response("openai", {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        })
        self.assertEqual(oa["text"], "ok")
        self.assertEqual(oa["usage"], {"input_tokens": 3, "output_tokens": 4})
        an = ot.providers.parse_response("anthropic", {
            "content": [{"text": "a"}, {"text": "b"}],
            "usage": {"input_tokens": 1, "output_tokens": 2},
        })
        self.assertEqual(an["text"], "ab")
        go = ot.providers.parse_response("google", {
            "candidates": [{"content": {"parts": [{"text": "g"}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 6},
        })
        self.assertEqual(go["text"], "g")
        self.assertEqual(go["usage"], {"input_tokens": 5, "output_tokens": 6})

    def test_complete_requires_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            result = ot.providers.complete("openai", "m", "hi")
        self.assertFalse(result["ok"])
        self.assertIn("missing API key", result["error"])

    def test_complete_parses_http_response(self):
        class FakeResponse:
            status = 200
            def read(self):
                return b'{"choices":[{"message":{"content":"hello"}}],"usage":{"prompt_tokens":1,"completion_tokens":2}}'
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "k"}, clear=False), \
             mock.patch.object(ot.providers.urllib.request, "urlopen", return_value=FakeResponse()):
            result = ot.providers.complete("openai", "m", "hi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "hello")


class ProviderReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _verdict_text(self, verdict="PASS"):
        return json.dumps({
            "verdict": verdict,
            "findings": [],
            "resolved_checks": ["tests"],
            "residual_uncertainty": [],
        })

    def test_review_skips_without_diff(self):
        with mock.patch.object(ot, "git", return_value=""):
            code, out, _ = run_quiet(
                ot.cmd_review,
                ns(provider="openai", model="m", staged=False, cwd=str(self.root), max_chars=100, max_tokens=10),
            )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["skipped"])

    def test_review_passes_with_valid_verdict(self):
        with mock.patch.object(ot, "git", return_value="diff --git a/x b/x\n+line\n"), \
             mock.patch.object(ot.providers, "complete",
                               return_value={"ok": True, "text": self._verdict_text(), "usage": {}}):
            code, out, _ = run_quiet(
                ot.cmd_review,
                ns(provider="openai", model="m", staged=False, cwd=str(self.root),
                   max_chars=1000, max_tokens=10, timeout=30),
            )
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["verdict"]["verdict"], "PASS")
        self.assertTrue(payload["schema_ok"])

    def test_review_retries_once_on_schema_error(self):
        bad = self._verdict_text("MAYBE")
        good = self._verdict_text("PASS")
        with mock.patch.object(ot, "git", return_value="+x\n"), \
             mock.patch.object(ot.providers, "complete", side_effect=[
                 {"ok": True, "text": bad, "usage": {}},
                 {"ok": True, "text": good, "usage": {}},
             ]) as complete:
            code, out, _ = run_quiet(
                ot.cmd_review,
                ns(provider="anthropic", model="m", staged=False, cwd=str(self.root),
                   max_chars=1000, max_tokens=10, timeout=30),
            )
        payload = json.loads(out)
        self.assertEqual(complete.call_count, 2)
        self.assertTrue(payload["retried"])
        self.assertEqual(code, 0)

    def test_review_reports_provider_error(self):
        with mock.patch.object(ot, "git", return_value="+x\n"), \
             mock.patch.object(ot.providers, "complete",
                               return_value={"ok": False, "error": "HTTP 401: bad key"}):
            code, out, _ = run_quiet(
                ot.cmd_review,
                ns(provider="google", model="m", staged=False, cwd=str(self.root),
                   max_chars=1000, max_tokens=10, timeout=30),
            )
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertIn("401", payload["error"])

    def test_gate_provider_review_failure_blocks(self):
        with mock.patch.object(ot, "git", return_value="+x\n"), \
             mock.patch.object(ot.providers, "complete",
                               return_value={"ok": False, "error": "missing API key"}):
            code, out, _ = run_quiet(
                ot.cmd_gate,
                ns(cwd=str(self.root), cmd=["ok=true"], provider="openai", model="m",
                   max_chars=500, max_tokens=10),
            )
        payload = json.loads(out)
        review = [s for s in payload["steps"] if s["name"] == "review"][0]
        self.assertEqual(review["provider"], "openai")
        self.assertFalse(review["ok"])
        self.assertEqual(code, 1)

    def test_gate_provider_review_pass(self):
        with mock.patch.object(ot, "git", return_value="+x\n"), \
             mock.patch.object(ot.providers, "complete",
                               return_value={"ok": True, "text": self._verdict_text(), "usage": {}}):
            code, out, _ = run_quiet(
                ot.cmd_gate,
                ns(cwd=str(self.root), cmd=["ok=true"], provider="openai", model="m",
                   max_chars=500, max_tokens=10),
            )
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for workflow healer classify / budget / propose path."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import healer


class HealerClassifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run_dir = self.root / "run-a"
        self.run_dir.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def _state(self, **fields: object) -> dict:
        data = {"status": "running", "updated_at": "2026-11-09T00:00:00+00:00"}
        data.update(fields)
        (self.run_dir / "state.json").write_text(json.dumps(data) + "\n", encoding="utf-8")
        return data

    def test_flake_vs_orch_bug(self) -> None:
        flake = self._state(status="aborted_agent_failure", error="cursor agent timed out after 480s")
        self.assertEqual(
            healer.classify(flake, stale_running_sec=3600, run_dir=self.run_dir),
            "flake",
        )
        bug = self._state(
            status="aborted_agent_failure",
            error='Traceback (most recent call last):\n  File "/x/scripts/gh_collab.py", line 1\nAttributeError: boom',
        )
        self.assertEqual(
            healer.classify(bug, stale_running_sec=3600, run_dir=self.run_dir),
            "orch_bug",
        )

    def test_max_rounds_never_auto_resumed(self) -> None:
        state = self._state(status="aborted_max_rounds", error="max rounds")
        self.assertEqual(
            healer.classify(state, stale_running_sec=3600, run_dir=self.run_dir),
            "escalate",
        )

    def test_publish_retry(self) -> None:
        state = self._state(status="publish_failed", error="push failed")
        self.assertEqual(
            healer.classify(state, stale_running_sec=3600, run_dir=self.run_dir),
            "publish_retry",
        )

    def test_ignore_after_terminal(self) -> None:
        state = self._state(status="aborted_agent_failure", error="timeout")
        healer.mark_healer(self.run_dir, terminal="escalated")
        self.assertEqual(
            healer.classify(state, stale_running_sec=3600, run_dir=self.run_dir),
            "ignore",
        )

    def test_stuck_when_pid_dead(self) -> None:
        state = self._state(status="s1_started", server_pid=0)
        (self.run_dir / "job.pid").write_text("99999999\n", encoding="utf-8")
        with mock.patch.object(healer, "age_seconds", return_value=120.0):
            self.assertEqual(
                healer.classify(state, stale_running_sec=3600, run_dir=self.run_dir),
                "stuck",
            )


class HealerHandleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run_id = "demo-issue-1"
        self.run_dir = self.root / self.run_id
        self.run_dir.mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = healer.HealerConfig(
            enabled=True,
            poll_sec=90,
            max_auto_resume_per_run=1,
            stale_running_sec=3600,
            orch_fix="propose",
            model="composer-2.5",
        )

    def test_propose_orch_bug_writes_diagnosis_not_product(self) -> None:
        state = {
            "status": "aborted_agent_failure",
            "stage": "spec",
            "error": 'File "/repo/scripts/workflow_server.py", line 1\nTypeError: bad',
            "updated_at": "2026-11-09T00:00:00+00:00",
        }
        (self.run_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
        docs = self.root / "docs"
        docs.mkdir()
        product = docs / "spec.md"
        product.write_text("do not touch\n", encoding="utf-8")

        with mock.patch.object(healer, "run_dir_for", return_value=self.run_dir), mock.patch.object(
            healer, "notify_human"
        ), mock.patch.object(healer, "ROOT", self.root), mock.patch.object(
            healer, "write_state", wraps=healer.write_state
        ):
            # write_state uses aac_common.ROOT; patch path via writing ourselves after handle
            with mock.patch("healer.write_state") as ws, mock.patch.object(healer, "append_decision"):
                result = healer.handle_run(self.run_dir, self.cfg)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result["action"], "diagnose")
                self.assertTrue((self.run_dir / "healer" / "diagnosis.md").is_file())
                self.assertEqual(product.read_text(encoding="utf-8"), "do not touch\n")
                ws.assert_called()
                kwargs = ws.call_args.kwargs
                self.assertEqual(kwargs.get("status"), "needs_human")

    def test_resume_budget_blocks_second_flake(self) -> None:
        state = {
            "status": "aborted_agent_failure",
            "error": "cursor agent timed out",
            "updated_at": "2026-11-09T00:00:00+00:00",
        }
        (self.run_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
        healer.mark_healer(self.run_dir, auto_resume_count=1)
        with mock.patch.object(healer, "notify_human"), mock.patch.object(
            healer, "write_state"
        ) as ws, mock.patch.object(healer, "run_resume_spec") as resume:
            result = healer.handle_run(self.run_dir, self.cfg)
            resume.assert_not_called()
            assert result is not None
            self.assertEqual(result["action"], "escalate")
            self.assertEqual(ws.call_args.kwargs.get("status"), "needs_human")


if __name__ == "__main__":
    unittest.main()

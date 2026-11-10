#!/usr/bin/env python3
"""Unit tests for workflow server helpers (no live gh / orca)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage_labels import tech_lead_note, waiting_labels
import workflow_server as server


class WorkflowServerHelpersTest(unittest.TestCase):
    def test_job_registry_respects_max_jobs(self) -> None:
        registry = server.JobRegistry(max_jobs=1)

        class FakeProc:
            def __init__(self, code: int | None) -> None:
                self._code = code
                self.pid = 1

            def poll(self) -> int | None:
                return self._code

        registry.add("a", FakeProc(None))  # type: ignore[arg-type]
        self.assertFalse(registry.can_start())
        registry.add("b-done", FakeProc(0))  # type: ignore[arg-type]
        # living() drops finished jobs
        self.assertEqual(registry.living(), 1)
        self.assertFalse(registry.can_start())

    def test_waiting_labels_are_the_pr_queue(self) -> None:
        self.assertEqual(waiting_labels(), ("Spec", "Plan", "Acceptance", "Implement", "Gate"))

    def test_tech_lead_note_contract(self) -> None:
        note = tech_lead_note(stage="Gate", delivered="Merging into dev", next_step="No further human gate")
        self.assertTrue(note.startswith("**Gate done.**"))
        self.assertEqual(len(note.splitlines()), 3)

    def test_list_ready_issues_uses_ready_label(self) -> None:
        with mock.patch.object(server, "gh_run") as gh_run:
            gh_run.return_value = mock.Mock(
                stdout=json.dumps([{"number": 7, "title": "x", "labels": [{"name": "Ready"}]}])
            )
            issues = server.list_ready_issues("Ready")
            self.assertEqual(issues[0]["number"], 7)
            args = gh_run.call_args[0][0]
            self.assertIn("--label", args)
            self.assertIn("Ready", args)


if __name__ == "__main__":
    unittest.main()

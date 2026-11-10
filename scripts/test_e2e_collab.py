#!/usr/bin/env python3
"""Walk S1–S6 by feeding GitHub-shaped comments through the watcher handler.

Agent calls are skipped (AAC_E2E_SKIP). One feedback comment is applied at the
plan stage; every other comment is /approve. The last /approve merges (e2e stub).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["AAC_E2E_SKIP"] = "1"

from aac_common import ROOT
from gh_collab import apply_comments, classify_body
from pipeline import decide, load_state

RUN_ID = "TsengMJ-orca-agentic-coding-orch-pr-99"


class EndToEndCollabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = ROOT / "aac" / "docs" / RUN_ID
        self.run = ROOT / "aac" / ".run" / RUN_ID
        shutil.rmtree(self.docs, ignore_errors=True)
        shutil.rmtree(self.run, ignore_errors=True)
        self.docs.mkdir(parents=True)
        self.run.mkdir(parents=True)
        (self.docs / "spec.md").write_text("# e2e spec\n", encoding="utf-8")
        (self.run / "state.json").write_text(
            json.dumps({"run_id": RUN_ID, "status": "awaiting_human_gate", "request": "e2e"}) + "\n",
            encoding="utf-8",
        )
        (self.run / "github.json").write_text(
            json.dumps(
                {
                    "issue": 99,
                    "pr": 99,
                    "branch": "feature/e2e-collab",
                    "run_id": RUN_ID,
                    "url": "https://example.test/pr/99",
                    "label": "Spec",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.stub = ROOT / "fixtures" / "dogfood" / "tests" / "acceptance" / RUN_ID / "test_s3_stub.py"

    def tearDown(self) -> None:
        shutil.rmtree(self.docs, ignore_errors=True)
        shutil.rmtree(self.run, ignore_errors=True)
        evidence = ROOT / "artifacts" / "runs"
        for name in ("s4", "s5", "s6"):
            path = evidence / f"{RUN_ID}-{name}.md"
            if path.exists():
                path.unlink()
        if self.stub.parent.exists():
            shutil.rmtree(self.stub.parent)

    def test_comments_drive_every_stage(self) -> None:
        self.assertIsNone(classify_body("<!-- aac-orchestrator -->\n/approve"))
        self.assertEqual(classify_body("/approve\n"), "/approve")
        self.assertEqual(classify_body("Please split the first task."), "feedback")

        comments = [
            {"id": "c1", "body": "/approve"},
            {"id": "c2", "body": "Please keep ping() covered in the plan."},
            {"id": "c3", "body": "/approve"},
            {"id": "c4", "body": "/approve"},
            {"id": "c5", "body": "/approve"},
            {"id": "c6", "body": "/approve"},
        ]
        seen: set[str] = set()
        messages = apply_comments(RUN_ID, comments, seen, pr=99)
        self.assertEqual(len(messages), 6, messages)
        self.assertFalse(any(item.startswith("failed") for item in messages), messages)
        self.assertIn("recorded revise_plan", messages)
        self.assertTrue(any("merged PR #99" in item for item in messages), messages)
        self.assertEqual(load_state(RUN_ID).get("status"), "merged")
        self.assertTrue((self.docs / "pr-body.md").is_file())
        self.assertIn("revise_plan", (self.run / "feedback-actions.log").read_text(encoding="utf-8"))
        self.assertIn("Please keep ping()", (self.run / "FEEDBACK.md").read_text(encoding="utf-8"))
        plan = (self.docs / "plan.md").read_text(encoding="utf-8")
        self.assertIn("- [x]", plan)
        self.assertNotIn("- [ ]", plan)
        if self.stub.parent.exists():
            shutil.rmtree(self.stub.parent)

        again = apply_comments(RUN_ID, comments, seen, pr=99)
        self.assertEqual(again, [])
        self.assertEqual(decide("final_accepted", "feedback"), "revise_final")
        self.assertEqual(decide("final_accepted", "approve"), "merge")


if __name__ == "__main__":
    unittest.main()

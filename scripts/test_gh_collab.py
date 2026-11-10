#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gh_collab import latest_human_command, ORCH_MARKER, report_stage, repo
from ids import branch_name, issue_run_id, parse_run_id, pr_run_id, task_id
from stage_labels import approved_label, next_waiting, tech_lead_note, waiting_labels


class CommentParseTest(unittest.TestCase):
    def test_ignores_orchestrator_and_keeps_latest_human(self) -> None:
        comments = [
            {"body": f"**Spec done.**\n\n{ORCH_MARKER}"},
            {"body": "/abort"},
            {"body": "looks good\n/approve"},
            {"body": "/approve"},
        ]
        self.assertEqual(latest_human_command(comments), "/approve")

    def test_approve_with_trailing_orch_marker_counts(self) -> None:
        """Self-drive used to append the orch marker and stall the gate."""
        from gh_collab import classify_body

        body = f"/approve\n\n{ORCH_MARKER}"
        self.assertEqual(classify_body(body), "/approve")
        self.assertEqual(latest_human_command([{"body": body}]), "/approve")

    def test_orch_note_with_marker_first_is_ignored(self) -> None:
        from gh_collab import classify_body

        body = f"{ORCH_MARKER}\n/approve"
        self.assertIsNone(classify_body(body))
        self.assertIsNone(latest_human_command([{"body": body}]))

    def test_abort_wins_when_latest(self) -> None:
        comments = [{"body": "/approve"}, {"body": "/abort\nstop"}]
        self.assertEqual(latest_human_command(comments), "/abort")

    def test_empty(self) -> None:
        self.assertIsNone(latest_human_command([{"body": "not a command"}]))


class IdSchemeTest(unittest.TestCase):
    def test_ids_use_repo_and_numbers(self) -> None:
        branch = branch_name("feature", "Add Counter to dogfood")
        self.assertEqual(branch, "feature/add-counter-to-dogfood")
        repo = "TsengMJ/orca-agentic-coding-orch"
        self.assertEqual(issue_run_id(repo, 12), "TsengMJ-orca-agentic-coding-orch-issue-12")
        run = pr_run_id(repo, 34)
        self.assertEqual(run, "TsengMJ-orca-agentic-coding-orch-pr-34")
        self.assertEqual(task_id(run, 1), "TsengMJ-orca-agentic-coding-orch-pr-34-T01")
        self.assertEqual(parse_run_id(run), ("pr", 34))
        self.assertEqual(parse_run_id(issue_run_id(repo, 12)), ("issue", 12))


class StageLabelTest(unittest.TestCase):
    def test_waiting_and_approved_chain(self) -> None:
        self.assertEqual(waiting_labels()[0], "Spec")
        self.assertEqual(approved_label("Spec"), "Spec_Approved")
        self.assertEqual(next_waiting("Spec_Approved"), "Plan")
        self.assertEqual(next_waiting("Implement_Approved"), "Gate")
        self.assertIsNone(next_waiting("Gate_Approved"))

    def test_tech_lead_note_is_short(self) -> None:
        note = tech_lead_note(
            stage="Plan",
            delivered="Plan reviewed and ready",
            next_step="`/approve` to write acceptance tests",
        )
        self.assertIn("**Plan done.**", note)
        self.assertIn("Plan reviewed and ready", note)
        self.assertIn("Next:", note)
        self.assertNotIn("please", note.lower())
        self.assertNotIn("thank", note.lower())
        self.assertLessEqual(len(note.splitlines()), 3)

    def test_tech_lead_note_failure_outcome(self) -> None:
        note = tech_lead_note(
            stage="Spec",
            delivered="agent timeout",
            next_step="resume",
            outcome="failed",
        )
        self.assertTrue(note.startswith("**Spec failed.**"))


class ProductRepoTest(unittest.TestCase):
    def test_repo_prefers_run_meta_over_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "other-project-pr-1"
            (root / "aac" / ".run" / run_id).mkdir(parents=True)
            (root / "aac" / ".run" / run_id / "github.json").write_text(
                json.dumps({"repo": "Acme/widget", "pr": 1}) + "\n",
                encoding="utf-8",
            )
            with mock.patch("gh_collab.ROOT", root), mock.patch.dict(
                "os.environ", {"AAC_GITHUB_REPO": "TsengMJ/orca-agentic-coding-orch"}
            ):
                self.assertEqual(repo(run_id), "Acme/widget")

    def test_repo_env_overrides_config(self) -> None:
        with mock.patch.dict("os.environ", {"AAC_GITHUB_REPO": "Acme/other"}):
            self.assertEqual(repo(), "Acme/other")

    def test_report_stage_failure_comments_issue_when_no_pr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "Acme-other-issue-9"
            (root / "aac" / ".run" / run_id).mkdir(parents=True)
            (root / "aac" / ".run" / run_id / "github.json").write_text(
                json.dumps({"repo": "Acme/other", "issue": 9, "pr": None}) + "\n",
                encoding="utf-8",
            )
            with mock.patch("gh_collab.ROOT", root), mock.patch(
                "gh_collab.post_issue_comment"
            ) as post_issue, mock.patch("gh_collab.post_pr_comment") as post_pr, mock.patch.dict(
                "os.environ", {"AAC_E2E_SKIP": ""}
            ):
                report_stage(
                    run_id,
                    stage="Spec",
                    delivered="S1 exited 1",
                    next_step="resume",
                    outcome="failed",
                )
            post_issue.assert_called_once()
            post_pr.assert_not_called()
            body = post_issue.call_args[0][1]
            self.assertIn("**Spec failed.**", body)


if __name__ == "__main__":
    unittest.main()

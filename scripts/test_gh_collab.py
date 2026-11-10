#!/usr/bin/env python3
import unittest

from gh_collab import latest_human_command, ORCH_MARKER
from ids import branch_name, issue_run_id, parse_run_id, pr_run_id, task_id
from stage_labels import approved_label, next_waiting, tech_lead_note, waiting_labels


class CommentParseTest(unittest.TestCase):
    def test_ignores_orchestrator_and_keeps_latest_human(self) -> None:
        comments = [
            {"body": f"/approve\n\n{ORCH_MARKER}"},
            {"body": "/abort"},
            {"body": "looks good\n/approve"},
            {"body": "/approve"},
        ]
        self.assertEqual(latest_human_command(comments), "/approve")

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


if __name__ == "__main__":
    unittest.main()

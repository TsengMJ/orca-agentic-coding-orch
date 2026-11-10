#!/usr/bin/env python3
"""S3 must collect and land acceptance files on the feature branch."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from s3_acceptance_loop import acceptance_commit_paths, land_acceptance_on_branch


class S3CommitPathsTest(unittest.TestCase):
    def test_collects_tests_and_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "pr-99"
            test_dir = root / "fixtures" / "dogfood" / "tests" / "acceptance" / run_id
            test = test_dir / "test_a.py"
            helper = test_dir / "helpers.py"
            matrix = root / "aac" / "docs" / run_id / "acceptance-matrix.md"
            test_dir.mkdir(parents=True)
            test.write_text("def test_a():\n    assert True\n", encoding="utf-8")
            helper.write_text("X=1\n", encoding="utf-8")
            matrix.parent.mkdir(parents=True)
            matrix.write_text("# matrix\n", encoding="utf-8")
            paths = acceptance_commit_paths(root, test_dir, matrix)
            self.assertEqual(
                paths,
                [
                    f"fixtures/dogfood/tests/acceptance/{run_id}/helpers.py",
                    f"fixtures/dogfood/tests/acceptance/{run_id}/test_a.py",
                    f"aac/docs/{run_id}/acceptance-matrix.md",
                ],
            )

    def test_land_calls_worktree_commit(self) -> None:
        paths = ["fixtures/dogfood/tests/acceptance/r1/test_a.py"]
        with mock.patch.dict("os.environ", {"AAC_E2E_SKIP": ""}), mock.patch(
            "worktree_commit.commit_paths"
        ) as commit:
            landed = land_acceptance_on_branch("run-1", paths)
        commit.assert_called_once_with(
            "run-1",
            paths,
            "Add acceptance tests for run-1.",
        )
        self.assertEqual(landed, paths)

    def test_land_skips_empty(self) -> None:
        with mock.patch("worktree_commit.commit_paths") as commit:
            landed = land_acceptance_on_branch("run-1", [])
        commit.assert_not_called()
        self.assertEqual(landed, [])

    def test_land_skips_under_e2e(self) -> None:
        paths = ["fixtures/dogfood/tests/acceptance/r1/test_a.py"]
        with mock.patch.dict("os.environ", {"AAC_E2E_SKIP": "1"}), mock.patch(
            "worktree_commit.commit_paths"
        ) as commit:
            landed = land_acceptance_on_branch("run-1", paths)
        commit.assert_not_called()
        self.assertEqual(landed, paths)


if __name__ == "__main__":
    unittest.main()

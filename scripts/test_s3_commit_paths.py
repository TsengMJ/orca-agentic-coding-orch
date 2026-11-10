#!/usr/bin/env python3
"""S3 should collect acceptance files + matrix for worktree commit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from s3_acceptance_loop import acceptance_commit_paths


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


if __name__ == "__main__":
    unittest.main()

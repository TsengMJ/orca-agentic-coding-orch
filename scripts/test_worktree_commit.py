#!/usr/bin/env python3
"""Local dogfood commits must work without github.json / remote branch."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import worktree_commit


class LocalCommitTest(unittest.TestCase):
    def test_ensure_local_meta_writes_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "local-run-1"
            (root / "aac" / ".run" / run_id).mkdir(parents=True)

            def fake_git(args: list[str], cwd: Path | None = None) -> None:
                if args[:2] == ["worktree", "add"]:
                    Path(args[3]).mkdir(parents=True, exist_ok=True)
                    return
                raise AssertionError(args)

            with mock.patch.object(worktree_commit, "ROOT", root), mock.patch.object(
                worktree_commit, "git", side_effect=fake_git
            ):
                meta = worktree_commit.ensure_local_meta(run_id)
            self.assertTrue(meta["local"])
            self.assertEqual(meta["branch"], f"local/{run_id}")
            written = json.loads((root / "aac" / ".run" / run_id / "github.json").read_text())
            self.assertEqual(written["branch"], f"local/{run_id}")

    def test_commit_paths_local_skips_push(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "local-run-2"
            (root / "aac" / ".run" / run_id).mkdir(parents=True)
            src = root / "fixtures" / "dogfood" / "src" / "dogfood" / "__init__.py"
            src.parent.mkdir(parents=True)
            src.write_text("x=1\n", encoding="utf-8")
            work = root / "aac" / ".worktrees" / run_id
            work.mkdir(parents=True)
            (root / "aac" / ".run" / run_id / "github.json").write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "branch": f"local/{run_id}",
                        "worktree": str(work),
                        "local": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            calls: list[list[str]] = []

            def fake_git(args: list[str], cwd: Path | None = None) -> None:
                calls.append(list(args))

            porcelain = mock.Mock(stdout=" M file\n", returncode=0)
            with mock.patch.object(worktree_commit, "ROOT", root), mock.patch.object(
                worktree_commit, "git", side_effect=fake_git
            ), mock.patch("worktree_commit.subprocess.run", return_value=porcelain):
                worktree_commit.commit_paths(
                    run_id,
                    ["fixtures/dogfood/src/dogfood/__init__.py"],
                    "Implement T02.",
                )

            self.assertTrue(any(c[:1] == ["add"] for c in calls))
            self.assertTrue(any(c[:1] == ["commit"] for c in calls))
            self.assertFalse(any(c and c[0] == "push" for c in calls))

    def test_require_github_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "local-run-3"
            (root / "aac" / ".run" / run_id).mkdir(parents=True)
            with mock.patch.object(worktree_commit, "ROOT", root), mock.patch.dict(
                "os.environ", {"AAC_REQUIRE_GITHUB": "1"}
            ):
                with self.assertRaises(SystemExit) as ctx:
                    worktree_commit.commit_paths(run_id, ["x.py"], "msg")
            self.assertIn("missing github.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

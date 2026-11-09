#!/usr/bin/env python3
"""Offline checks for review_loop bounds (no Cursor calls)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aac_common import ROOT
from review_loop import LoopConfig, LoopPaths, run_review_fix_loop


class ReviewLoopBoundsTest(unittest.TestCase):
    def test_max_rounds_aborts_without_approve(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            archive = run_dir / "archive"
            reviews = run_dir / "reviews" / "spec"
            docs = base / "docs"
            for p in (run_dir, archive, reviews, docs):
                p.mkdir(parents=True)
            spec = docs / "spec.md"
            spec.write_text("# spec\n", encoding="utf-8")

            def review(round_n: int, review_path: Path, verdict_path: Path) -> str:
                # skip_agents path writes approved stub — override by writing after? 
                # We use skip_agents False but mock via custom: actually skip writes approved.
                # So drive without skip and inject via build that writes files... 
                # Simpler: monkey by not skip and empty model calls — use skip then overwrite.
                return "prompt"

            # Directly simulate: call loop with skip_agents True always approves.
            # Instead test abort when start_round > max.
            cfg = LoopConfig(stage="spec", max_rounds=3, skip_agents=True)
            paths = LoopPaths(
                run_dir=run_dir,
                archive=archive,
                reviews_root=reviews,
                artifact_path=spec,
                run_id="unit",
            )
            result = run_review_fix_loop(
                paths=paths,
                cfg=cfg,
                model_owner="x",
                model_reviewer="y",
                build_review_prompt=review,
                build_fix_prompt=review,
                resume_hint="echo resume",
                start_round=4,
            )
            self.assertFalse(result.approved)
            self.assertEqual(result.status, "aborted_max_rounds")
            self.assertTrue((run_dir / "REVIEW_ABORTED_MAX_ROUNDS.md").exists())

    def test_skip_agents_approves_within_cap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            archive = run_dir / "archive"
            reviews = run_dir / "reviews" / "spec"
            docs = base / "docs"
            for p in (run_dir, archive, reviews, docs):
                p.mkdir(parents=True)
            spec = docs / "spec.md"
            spec.write_text("# spec\n", encoding="utf-8")

            cfg = LoopConfig(stage="spec", max_rounds=3, skip_agents=True)
            paths = LoopPaths(
                run_dir=run_dir,
                archive=archive,
                reviews_root=reviews,
                artifact_path=spec,
                run_id="unit",
            )

            def review(round_n: int, review_path: Path, verdict_path: Path) -> str:
                return f"round {round_n}"

            result = run_review_fix_loop(
                paths=paths,
                cfg=cfg,
                model_owner="x",
                model_reviewer="y",
                build_review_prompt=review,
                build_fix_prompt=review,
                resume_hint="echo resume",
                start_round=1,
            )
            self.assertTrue(result.approved)
            self.assertEqual(result.rounds_used, 1)


if __name__ == "__main__":
    unittest.main()

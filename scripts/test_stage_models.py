#!/usr/bin/env python3
"""stage_models resolution for free-plan A/B pairings."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aac_common import load_workflow, slot_model


class StageModelsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_workflow()

    def test_same_stage_a_and_b_differ(self) -> None:
        for stage in ("spec", "plan", "acceptance", "gate", "final"):
            a = slot_model(self.cfg, "A" if stage != "gate" else "I", stage=stage)
            b = slot_model(self.cfg, "B", stage=stage)
            self.assertNotEqual(a, b, msg=f"stage={stage} A/I={a} B={b}")

    def test_recommended_matrix(self) -> None:
        self.assertEqual(slot_model(self.cfg, "A", stage="spec"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "B", stage="spec"), "grok-4.6")
        self.assertEqual(slot_model(self.cfg, "A", stage="plan"), "grok-4.6")
        self.assertEqual(slot_model(self.cfg, "B", stage="plan"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "B", stage="acceptance"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "A", stage="acceptance"), "grok-4.6")
        self.assertEqual(slot_model(self.cfg, "I", stage="implement"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "I", stage="gate"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "B", stage="gate"), "grok-4.6")
        self.assertEqual(slot_model(self.cfg, "A", stage="final"), "composer-2.5")
        self.assertEqual(slot_model(self.cfg, "B", stage="final"), "grok-4.5")


if __name__ == "__main__":
    unittest.main()

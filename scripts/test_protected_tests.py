#!/usr/bin/env python3
"""Arm a file, prove a one-byte edit fails closed, then restore it."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import protected_tests as pt


class ProtectedTests(unittest.TestCase):
    def test_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = "fixtures/dogfood/tests/acceptance/test_s3_stub.py"
            path = root / rel
            path.parent.mkdir(parents=True)
            path.write_text("def test_s3_stub_is_red():\n    assert False\n", encoding="utf-8")
            run = root / "aac" / ".run" / "s3-unit"
            run.mkdir(parents=True)
            original_root = pt.ROOT
            pt.ROOT = root
            try:
                payload = pt.arm("s3-unit", [rel])
                self.assertEqual(list(payload["files"]), [rel])
                self.assertEqual(pt.check("s3-unit"), [])
                path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                self.assertEqual(pt.check("s3-unit"), [f"hash changed {rel}"])
                self.assertEqual(pt.check("missing-run"), ["protected-tests.json missing"])
            finally:
                pt.ROOT = original_root


if __name__ == "__main__":
    unittest.main()

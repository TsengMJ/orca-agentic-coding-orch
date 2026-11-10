#!/usr/bin/env python3
"""Stage handoffs must spawn via uv run, not ephemeral sys.executable."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aac_common


class SpawnUvScriptTest(unittest.TestCase):
    def test_command_uses_uv_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "stage.log"
            fake = mock.Mock(pid=4242)
            with mock.patch.object(aac_common.subprocess, "Popen", return_value=fake) as popen:
                proc = aac_common.spawn_uv_script(
                    "s3_acceptance_loop.py",
                    ["--run-id", "r1", "--stream"],
                    log=log,
                    cwd=Path(td),
                )
            self.assertIs(proc, fake)
            cmd = popen.call_args.args[0]
            self.assertEqual(cmd[0], "uv")
            self.assertEqual(cmd[1:3], ["run", "--with"])
            self.assertIn("pyyaml", cmd)
            self.assertTrue(str(cmd[4]).endswith("s3_acceptance_loop.py"))
            self.assertEqual(cmd[5:], ["--run-id", "r1", "--stream"])
            self.assertTrue(log.is_file())


if __name__ == "__main__":
    unittest.main()

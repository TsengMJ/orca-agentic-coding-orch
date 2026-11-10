#!/usr/bin/env python3
"""Stage handoffs must spawn via uv run, not ephemeral sys.executable."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aac_common

SCRIPTS = Path(__file__).resolve().parent
HANDOFF_SCRIPTS = (
    "s1_human_gate.py",
    "s2_human_gate.py",
    "s2_plan_loop.py",
    "workflow_server.py",
)


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

    def test_handoff_scripts_call_spawn_uv_script(self) -> None:
        for name in HANDOFF_SCRIPTS:
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertIn(
                "spawn_uv_script",
                source,
                msg=f"{name} must hand off via spawn_uv_script",
            )
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "Popen":
                    # Only aac_common.spawn_uv_script (or other helpers) should Popen stages.
                    # Direct subprocess.Popen of sys.executable for stage scripts is forbidden.
                    joined = ast.dump(node)
                    self.assertNotIn(
                        "sys.executable",
                        joined,
                        msg=f"{name} still Popen(sys.executable …)",
                    )


if __name__ == "__main__":
    unittest.main()

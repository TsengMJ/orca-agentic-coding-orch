#!/usr/bin/env python3
"""Agent completion must use protocol end signals, not prompt-printed sentinels."""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from aac_common import DONE_SENTINEL, _tool_call_label, run_command_reaping_done, run_cursor


class AgentEndSignalTest(unittest.TestCase):
    def test_tool_call_label_exposes_progress(self) -> None:
        label = _tool_call_label(
            {
                "readToolCall": {"args": {"path": "/tmp/spec.md"}},
                "toolCallId": "x",
            }
        )
        self.assertIn("read", label)
        self.assertIn("/tmp/spec.md", label)
    def _script(self, body: str) -> list[str]:
        return ["python3", "-c", textwrap.dedent(body)]

    def test_reaps_after_stream_json_result_without_process_exit(self) -> None:
        cmd = self._script(
            """
            import sys, time
            print('{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"done-work"}]}}', flush=True)
            print('{"type":"result","subtype":"success","is_error":false,"result":"done-work"}', flush=True)
            time.sleep(30)
            """
        )
        started = __import__("time").monotonic()
        result = run_command_reaping_done(
            cmd,
            timeout_sec=20,
            grace_sec=1,
            stream=False,
            cwd=Path.cwd(),
        )
        elapsed = __import__("time").monotonic() - started
        self.assertEqual(result.returncode, 0)
        self.assertLess(elapsed, 8, f"should reap soon after result, took {elapsed:.1f}s")
        self.assertIn('"type":"result"', result.stdout)
        self.assertIn("reaped agent", result.stdout)

    def test_wall_timeout_without_result_is_failure(self) -> None:
        cmd = self._script(
            """
            import time
            print('still working', flush=True)
            time.sleep(30)
            """
        )
        started = __import__("time").monotonic()
        result = run_command_reaping_done(
            cmd,
            timeout_sec=2,
            grace_sec=1,
            stream=False,
            cwd=Path.cwd(),
        )
        elapsed = __import__("time").monotonic() - started
        self.assertEqual(result.returncode, 124)
        self.assertLess(elapsed, 6)
        self.assertIn("timed out", result.stdout)

    def test_clean_exit_without_result_still_ok(self) -> None:
        cmd = self._script("print('plain text done', flush=True)")
        result = run_command_reaping_done(
            cmd,
            timeout_sec=10,
            grace_sec=1,
            stream=False,
            cwd=Path.cwd(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("plain text done", result.stdout)

    def test_error_result_reaps_as_failure(self) -> None:
        cmd = self._script(
            """
            import time
            print('{"type":"result","subtype":"error","is_error":true,"result":"boom"}', flush=True)
            time.sleep(30)
            """
        )
        result = run_command_reaping_done(
            cmd,
            timeout_sec=20,
            grace_sec=1,
            stream=False,
            cwd=Path.cwd(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.returncode, 124)

    def test_run_cursor_does_not_inject_done_sentinel(self) -> None:
        """Prompt contract must not require AAC_AGENT_DONE."""
        captured: dict[str, object] = {}

        def fake_reap(cmd, **kwargs):  # type: ignore[no-untyped-def]
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, "ok", "")

        import aac_common as mod

        original = mod.run_command_reaping_done
        mod.run_command_reaping_done = fake_reap  # type: ignore[assignment]
        try:
            prompt = "Write a file and stop."
            run_cursor("composer-2", prompt, timeout_sec=30, stream=False)
        finally:
            mod.run_command_reaping_done = original  # type: ignore[assignment]

        cmd = captured["cmd"]
        assert isinstance(cmd, list)
        self.assertIn("--output-format", cmd)
        fmt_idx = cmd.index("--output-format")
        self.assertEqual(cmd[fmt_idx + 1], "stream-json")
        agent_prompt = cmd[-1]
        self.assertIsInstance(agent_prompt, str)
        self.assertNotIn(DONE_SENTINEL, agent_prompt)
        self.assertEqual(agent_prompt, prompt)

    def test_legacy_sentinel_still_reaps_if_emitted(self) -> None:
        cmd = self._script(
            f"""
            import time
            print('{DONE_SENTINEL}', flush=True)
            time.sleep(30)
            """
        )
        started = __import__("time").monotonic()
        result = run_command_reaping_done(
            cmd,
            timeout_sec=20,
            grace_sec=1,
            stream=False,
            cwd=Path.cwd(),
        )
        elapsed = __import__("time").monotonic() - started
        self.assertEqual(result.returncode, 0)
        self.assertLess(elapsed, 8)


if __name__ == "__main__":
    unittest.main()

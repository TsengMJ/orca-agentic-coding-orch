"""AC-04: echo_id preserves empty string."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from echo_test_helpers import require_echo_id  # noqa: E402


def test_ac04_empty_string() -> None:
    echo_id = require_echo_id()
    assert echo_id("") == ""

"""AC-03: echo_id returns non-empty strings unchanged."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from echo_test_helpers import require_echo_id  # noqa: E402


def test_ac03_non_empty_identity_abc() -> None:
    echo_id = require_echo_id()
    assert echo_id("abc") == "abc"


def test_ac03_unicode_identity_preserved() -> None:
    echo_id = require_echo_id()
    value = "café-🐶-日本語"
    assert echo_id(value) == value

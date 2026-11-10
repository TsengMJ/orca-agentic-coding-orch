"""AC-05: bool is valid int input."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def test_ac05_bool_construction() -> None:
    Counter = require_counter()
    assert Counter(True).value() == 1
    assert Counter(False).value() == 0
    assert Counter(start=True).value() == 1
    assert Counter(start=False).value() == 0
    for v in (Counter(True).value(), Counter(False).value()):
        assert type(v) is int


def test_ac05_bool_inc() -> None:
    Counter = require_counter()
    assert Counter(True).inc() == 2
    assert type(Counter(True).inc()) is int
    assert Counter(0).inc(True) == 1
    assert Counter(0).inc(False) == 0
    assert Counter(5).inc(True) == 6
    assert Counter(5).inc(by=False) == 5


def test_ac05_bool_reset_cycle() -> None:
    Counter = require_counter()
    c = Counter(True)
    c.inc(True)
    assert c.reset() is None
    assert c.value() == 1
    assert type(c.value()) is int

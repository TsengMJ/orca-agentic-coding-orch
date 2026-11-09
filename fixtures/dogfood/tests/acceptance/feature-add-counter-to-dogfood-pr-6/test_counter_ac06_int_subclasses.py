"""AC-06: int subclasses including hostile __add__."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import _E, _Odd, _Plain, require_counter  # noqa: E402


def test_ac06_plain_subclass() -> None:
    Counter = require_counter()
    assert Counter(_Plain(2)).value() == 2
    assert type(Counter(_Plain(2)).value()) is int
    assert Counter(_Plain(2)).inc(_Plain(3)) == 5
    assert Counter(_Plain(2)).inc(3) == 5
    assert Counter(3).inc(_Plain(2)) == 5
    c = Counter(_Plain(2))
    c.inc(3)
    assert c.reset() is None
    assert c.value() == 2


def test_ac06_odd_hostile_subclass() -> None:
    Counter = require_counter()
    assert Counter(_Odd(2)).value() == 2
    assert type(Counter(_Odd(2)).value()) is int
    assert Counter(_Odd(2)).inc(_Odd(3)) == 5
    assert Counter(_Odd(2)).inc(3) == 5
    assert Counter(10).inc(_Odd(1)) == 11
    assert Counter(_Odd(-4)).inc(1) == -3
    c = Counter(_Odd(2))
    c.inc(_Odd(3))
    assert c.reset() is None
    assert c.value() == 2
    assert type(c.value()) is int


def test_ac06_int_enum() -> None:
    Counter = require_counter()
    assert Counter(_E.A).value() == 1
    assert Counter(_E.A).inc(_E.B) == 3
    assert Counter(5).inc(_E.B) == 7
    c = Counter(_E.A)
    c.inc(_E.B)
    assert c.reset() is None
    assert c.value() == 1
    assert type(c.value()) is int

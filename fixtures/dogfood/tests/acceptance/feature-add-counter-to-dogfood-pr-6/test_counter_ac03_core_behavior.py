"""AC-03: construction, value, inc, reset."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("default", 0),
        ("positional_zero", 0),
        ("keyword_zero", 0),
        ("positional_five", 5),
        ("keyword_five", 5),
        ("negative_three", -3),
        ("keyword_negative_seven", -7),
    ],
)
def test_ac03_initial_value(mode: str, expected: int) -> None:
    Counter = require_counter()
    if mode == "default":
        got = Counter().value()
    elif mode == "positional_zero":
        got = Counter(0).value()
    elif mode == "keyword_zero":
        got = Counter(start=0).value()
    elif mode == "positional_five":
        got = Counter(5).value()
    elif mode == "keyword_five":
        got = Counter(start=5).value()
    elif mode == "negative_three":
        got = Counter(-3).value()
    else:
        got = Counter(start=-7).value()
    assert got == expected
    assert type(got) is int


def test_ac03_value_is_stable_across_calls() -> None:
    Counter = require_counter()
    c = Counter(4)
    assert c.value() == 4
    assert c.value() == 4
    assert c.value() == 4


def test_ac03_inc_updates_and_returns_current() -> None:
    Counter = require_counter()
    c = Counter(1)
    v = c.value()
    got = c.inc(4)
    assert got == 5
    assert type(got) is int
    assert c.value() == 5
    assert v == 1


def test_ac03_inc_default_and_keyword_one() -> None:
    Counter = require_counter()
    c = Counter(5)
    assert c.inc() == 6 and c.value() == 6
    c = Counter(5)
    assert c.inc(1) == 6 and c.value() == 6
    c = Counter(5)
    assert c.inc(by=1) == 6 and c.value() == 6


def test_ac03_inc_negative_start_and_by() -> None:
    Counter = require_counter()
    c = Counter(-2)
    assert c.inc() == -1 and c.value() == -1
    c = Counter(5)
    assert c.inc(3) == 8 and c.value() == 8
    c = Counter(5)
    assert c.inc(by=3) == 8 and c.value() == 8
    c = Counter(5)
    assert c.inc(0) == 5 and c.value() == 5
    c = Counter(5)
    assert c.inc(by=0) == 5 and c.value() == 5
    c = Counter(5)
    assert c.inc(-2) == 3 and c.value() == 3
    c = Counter(5)
    assert c.inc(-5) == 0 and c.value() == 0
    c = Counter(5)
    assert c.inc(-8) == -3 and c.value() == -3


def test_ac03_inc_large_delta() -> None:
    Counter = require_counter()
    c = Counter(10**6)
    assert c.inc(10**6) == 2_000_000
    assert c.value() == 2_000_000


def test_ac03_repeated_default_inc() -> None:
    Counter = require_counter()
    c = Counter()
    assert c.inc() == 1
    assert c.inc() == 2
    assert c.inc() == 3
    assert c.value() == 3


def test_ac03_inc_return_is_int_not_instance() -> None:
    Counter = require_counter()
    c = Counter(1)
    r = c.inc(1)
    assert r == 2
    assert r is not c
    assert c.inc(1) == 3
    assert c.value() == 3


def test_ac03_reset_restores_construction_baseline() -> None:
    Counter = require_counter()
    c = Counter(6)
    assert c.reset() is None
    assert c.value() == 6

    c = Counter(10)
    assert c.inc(5) == 15
    assert c.reset() is None
    assert c.value() == 10

    c = Counter(10)
    c.inc(5)
    c.reset()
    c.reset()
    assert c.value() == 10

    c = Counter(10)
    c.inc(5)
    c.reset()
    assert c.inc(1) == 11
    c.reset()
    assert c.value() == 10

    c = Counter(0)
    c.inc(4)
    c.reset()
    assert c.value() == 0


def test_ac03_independent_instances() -> None:
    Counter = require_counter()
    a = Counter(3)
    b = Counter(9)
    assert a.inc(1) == 4
    assert a.value() == 4
    assert b.value() == 9
    a.reset()
    assert a.value() == 3
    assert b.value() == 9

    Counter(1).inc(4)
    assert Counter(1).value() == 1

    c = Counter(2)
    c.inc(9)
    assert Counter().value() == 0
    assert c.value() == 11

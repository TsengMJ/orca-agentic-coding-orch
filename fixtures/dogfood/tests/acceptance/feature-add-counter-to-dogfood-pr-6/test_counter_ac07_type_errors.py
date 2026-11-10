"""AC-07: non-int start and by raise TypeError."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import _Box, require_counter  # noqa: E402


@pytest.mark.parametrize(
    "bad_start",
    [1.0, "1", None, b"1", [1], 1 + 0j, object()],
    ids=["float", "str", "none", "bytes", "list", "complex", "object"],
)
def test_ac07_constructor_rejects_non_int(bad_start) -> None:
    Counter = require_counter()
    seen: list[object] = []
    with pytest.raises(TypeError):
        seen.append(Counter(bad_start))
    assert seen == []


def test_ac07_constructor_rejects_float_keyword() -> None:
    Counter = require_counter()
    seen: list[object] = []
    with pytest.raises(TypeError):
        seen.append(Counter(start=1.0))
    assert seen == []


def test_ac07_constructor_rejects_box() -> None:
    Counter = require_counter()
    seen: list[object] = []
    with pytest.raises(TypeError):
        seen.append(Counter(_Box()))
    assert seen == []


def test_ac07_still_constructs_after_bad_start() -> None:
    Counter = require_counter()
    for bad in (1.0, "1", None):
        with pytest.raises(TypeError):
            Counter(bad)
    v = Counter(4).value()
    assert v == 4
    assert type(v) is int


def test_ac07_inc_rejects_box_leaves_state() -> None:
    Counter = require_counter()
    c = Counter(5)
    with pytest.raises(TypeError):
        c.inc(_Box())
    assert c.value() == 5
    assert c.reset() is None
    assert c.value() == 5


@pytest.mark.parametrize(
    "bad_by",
    [1.0, "1", None, b"1", [1], 1 + 0j, object()],
    ids=["float", "str", "none", "bytes", "list", "complex", "object"],
)
def test_ac07_inc_rejects_non_int_by(bad_by) -> None:
    Counter = require_counter()
    c = Counter(5)
    c.inc(2)
    assert c.value() == 7
    with pytest.raises(TypeError):
        c.inc(bad_by)
    assert c.value() == 7


def test_ac07_inc_rejects_by_kw_float() -> None:
    Counter = require_counter()
    c = Counter(5)
    c.inc(2)
    with pytest.raises(TypeError):
        c.inc(by=1.0)
    assert c.value() == 7


def test_ac07_valid_inc_after_type_errors_then_reset() -> None:
    Counter = require_counter()
    c = Counter(5)
    c.inc(2)
    for bad in (1.0, "1", None, b"1", [1], 1 + 0j, object()):
        with pytest.raises(TypeError):
            c.inc(bad)
    with pytest.raises(TypeError):
        c.inc(by=1.0)
    assert c.inc(2) == 9
    assert c.value() == 9
    assert c.reset() is None
    assert c.value() == 5

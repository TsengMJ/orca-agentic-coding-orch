"""AC-08: wrong argument counts raise TypeError."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def test_ac08_method_arity_on_instance() -> None:
    Counter = require_counter()
    c = Counter(5)
    c.inc(2)
    assert c.value() == 7
    for bad_call in (
        lambda: c.value(1),
        lambda: c.value(x=1),
        lambda: c.inc(1, 2),
        lambda: c.inc(1, by=2),
        lambda: c.inc(by=1, extra=2),
        lambda: c.reset(0),
        lambda: c.reset(to=0),
    ):
        with pytest.raises(TypeError):
            bad_call()
        assert c.value() == 7
    assert c.reset() is None
    assert c.value() == 5


@pytest.mark.parametrize(
    "bad_ctor",
    [
        lambda C: C(1, 2),
        lambda C: C(1, start=2),
        lambda C: C(start=1, by=2),
    ],
    ids=["two_positional", "pos_and_kw_start", "start_and_by"],
)
def test_ac08_constructor_arity(bad_ctor) -> None:
    Counter = require_counter()
    with pytest.raises(TypeError):
        bad_ctor(Counter)


def test_ac08_unbound_method_calls() -> None:
    Counter = require_counter()
    with pytest.raises(TypeError):
        Counter.value()
    with pytest.raises(TypeError):
        Counter.inc()
    with pytest.raises(TypeError):
        Counter.reset()
    with pytest.raises(TypeError):
        Counter.value(1, 2)

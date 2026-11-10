"""AC-04: non-int rejection and arity errors."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twice_test_helpers import require_twice  # noqa: E402


@pytest.mark.parametrize(
    "bad",
    [1.0, "3", None],
    ids=["float", "str", "none"],
)
def test_ac04_non_int_raises_type_error(bad: object) -> None:
    twice = require_twice()
    seen: list[object] = []
    with pytest.raises(TypeError):
        seen.append(twice(bad))
    assert seen == []


def test_ac04_not_poisoned_after_type_errors() -> None:
    twice = require_twice()
    for bad in (1.0, "3", None):
        with pytest.raises(TypeError):
            twice(bad)
    assert twice(2) == 4
    assert type(twice(2)) is int


@pytest.mark.parametrize(
    "bad_call",
    [
        lambda fn: fn(),
        lambda fn: fn(1, 2),
        lambda fn: fn(n=1, extra=2),
        lambda fn: fn(1, n=1),
    ],
    ids=["no_args", "two_pos", "extra_kw", "dup_n"],
)
def test_ac04_arity_raises_type_error(bad_call) -> None:
    twice = require_twice()
    with pytest.raises(TypeError):
        bad_call(twice)

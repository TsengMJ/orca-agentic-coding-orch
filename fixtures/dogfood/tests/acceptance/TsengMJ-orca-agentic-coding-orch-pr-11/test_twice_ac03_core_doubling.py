"""AC-03: core doubling returns builtin int."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twice_test_helpers import require_twice  # noqa: E402


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, 0),
        (3, 6),
        (-4, -8),
        (10**6, 2_000_000),
    ],
    ids=["zero", "three", "negative", "million"],
)
def test_ac03_core_doubling(n: int, expected: int) -> None:
    twice = require_twice()
    got = twice(n)
    assert got == expected
    assert type(got) is int


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (False, 0),
        (True, 2),
    ],
    ids=["false", "true"],
)
def test_ac03_bool_doubling(n, expected: int) -> None:
    twice = require_twice()
    got = twice(n)
    assert got == expected
    assert type(got) is int

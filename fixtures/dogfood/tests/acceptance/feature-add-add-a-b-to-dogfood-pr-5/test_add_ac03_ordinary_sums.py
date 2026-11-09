"""AC-03: ordinary integer sums."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        ((0, 0), 0),
        ((1, 2), 3),
        ((2, 1), 3),
        ((-3, -5), -8),
        ((-3, 5), 2),
        ((3, -5), -2),
        ((41, 0), 41),
        ((0, -7), -7),
        ((10**6, 10**6), 2_000_000),
    ],
    ids=[
        "zero",
        "one_two",
        "two_one",
        "neg_both",
        "neg_pos",
        "pos_neg",
        "n_and_zero",
        "zero_neg",
        "million",
    ],
)
def test_ac03_ordinary_sums(call: tuple[int, int], expected: int) -> None:
    add = require_add()
    a, b = call
    got = add(a, b)
    assert got == expected
    assert type(got) is int
    assert got == int.__add__(a, b)


def test_ac03_keyword_a_b() -> None:
    add = require_add()
    assert add(a=4, b=6) == 10
    assert type(add(a=4, b=6)) is int


def test_ac03_keyword_b_a() -> None:
    add = require_add()
    assert add(b=6, a=4) == 10
    assert type(add(b=6, a=4)) is int


def test_ac03_mixed_positional_keyword() -> None:
    add = require_add()
    assert add(1, b=2) == 3
    assert type(add(1, b=2)) is int

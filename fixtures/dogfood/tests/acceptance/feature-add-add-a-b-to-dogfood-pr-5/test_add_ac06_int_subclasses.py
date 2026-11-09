"""AC-06: int subclasses including hostile __add__."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import _E, _Odd, _Plain, require_add  # noqa: E402


def test_ac06_plain_subclass() -> None:
    add = require_add()
    for a, b, expected in (
        (_Plain(2), _Plain(3), 5),
        (_Plain(2), 3, 5),
        (3, _Plain(2), 5),
    ):
        got = add(a, b)
        assert got == expected
        assert type(got) is int
        assert got == int.__add__(a, b)


def test_ac06_odd_hostile_subclass() -> None:
    add = require_add()
    for a, b, expected in (
        (_Odd(2), _Odd(3), 5),
        (_Odd(2), 3, 5),
        (3, _Odd(2), 5),
        (_Odd(-4), 1, -3),
    ):
        got = add(a, b)
        assert got == expected
        assert type(got) is int
        assert got == int.__add__(a, b)


def test_ac06_int_enum() -> None:
    add = require_add()
    for a, b, expected in (
        (_E.A, _E.B, 3),
        (_E.A, 5, 6),
        (5, _E.B, 7),
    ):
        got = add(a, b)
        assert got == expected
        assert type(got) is int
        assert got == int.__add__(a, b)

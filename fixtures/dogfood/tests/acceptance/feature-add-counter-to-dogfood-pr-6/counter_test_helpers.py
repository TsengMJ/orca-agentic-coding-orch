"""Test-only types and lazy Counter access (not part of dogfood)."""

from __future__ import annotations

from enum import IntEnum
from typing import Any


def require_counter() -> Any:
    import dogfood

    if not hasattr(dogfood, "Counter"):
        raise AssertionError("dogfood.Counter is not implemented yet")
    from dogfood import Counter

    return Counter


class _Plain(int):
    pass


class _Odd(int):
    def __add__(self, other: object) -> str:
        return "nope"

    def __radd__(self, other: object) -> str:
        return "nope"

    def __int__(self) -> int:
        raise RuntimeError("no")


class _E(IntEnum):
    A = 1
    B = 2


class _Box:
    def __int__(self) -> int:
        return 7

    def __index__(self) -> int:
        return 7

    def __add__(self, other: object) -> int:
        return 0

"""Test-only types and lazy add access (not part of dogfood)."""

from __future__ import annotations

from enum import IntEnum
from typing import Callable


def require_add() -> Callable[..., int]:
    import dogfood

    if not hasattr(dogfood, "add"):
        raise AssertionError("dogfood.add is not implemented yet")
    from dogfood import add

    return add


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
    def __add__(self, other: object) -> int:
        return 0

    def __radd__(self, other: object) -> int:
        return 0

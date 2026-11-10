"""Test-only helpers for lazy twice access (not part of dogfood)."""

from __future__ import annotations

from typing import Callable


def require_twice() -> Callable[[int], int]:
    import dogfood

    if not hasattr(dogfood, "twice"):
        raise AssertionError("dogfood.twice is not implemented yet")
    from dogfood import twice

    return twice

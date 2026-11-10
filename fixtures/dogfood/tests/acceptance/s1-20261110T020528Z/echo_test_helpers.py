"""Test-only lazy echo_id access (not part of dogfood)."""

from __future__ import annotations

from typing import Callable


def require_echo_id() -> Callable[..., str]:
    import dogfood

    if not hasattr(dogfood, "echo_id"):
        raise AssertionError("dogfood.echo_id is not implemented yet")
    from dogfood import echo_id

    return echo_id

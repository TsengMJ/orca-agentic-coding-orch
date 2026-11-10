"""AC-10: ping unchanged."""

from __future__ import annotations

import inspect

from dogfood import ping


def test_ac10_ping_returns_pong() -> None:
    assert ping() == "pong"


def test_ac10_ping_signature() -> None:
    sig = inspect.signature(ping)
    assert list(sig.parameters) == []
    assert sig.return_annotation is str


def test_ac10_ping_source_unchanged() -> None:
    assert inspect.getsource(ping) == 'def ping() -> str:\n    return "pong"\n'

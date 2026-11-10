"""AC-05: ping, add, echo_id, and Counter unchanged."""

from __future__ import annotations

from dogfood import Counter, add, echo_id, ping


def test_ac05_ping_unchanged() -> None:
    assert ping() == "pong"


def test_ac05_add_unchanged() -> None:
    assert add(1, 2) == 3


def test_ac05_echo_id_unchanged() -> None:
    assert echo_id("x") == "x"


def test_ac05_counter_unchanged() -> None:
    assert Counter(2).inc(1) == 3
    assert Counter(2).value() == 2

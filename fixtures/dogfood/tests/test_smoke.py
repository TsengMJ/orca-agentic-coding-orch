import inspect

from dogfood import Counter, add, echo_id, ping


def test_ping() -> None:
    assert ping() == "pong"
    sig = inspect.signature(ping)
    assert list(sig.parameters) == []
    assert sig.return_annotation is str


def test_add_smoke() -> None:
    assert add(1, 2) == 3


def test_echo_id_smoke() -> None:
    assert echo_id("x") == "x"


def test_counter_smoke() -> None:
    assert Counter(2).inc(1) == 3
    assert Counter(2).value() == 2

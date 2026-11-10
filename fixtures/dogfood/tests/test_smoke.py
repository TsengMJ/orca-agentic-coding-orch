import inspect

from dogfood import ping


def test_ping() -> None:
    assert ping() == "pong"
    sig = inspect.signature(ping)
    assert list(sig.parameters) == []
    assert sig.return_annotation is str

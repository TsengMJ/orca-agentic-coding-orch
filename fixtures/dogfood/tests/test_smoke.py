from dogfood import ping


def test_ping() -> None:
    assert ping() == "pong"

"""Dogfood package — intentional stub for AAC GATE_CMD practice."""

__version__ = "0.1.0"


def ping() -> str:
    return "pong"


def add(a: int, b: int) -> int:
    return int.__add__(a, b)


class Counter:
    def __init__(self, start: int = 0) -> None:
        self._baseline = int.__add__(start, 0)
        self._current = self._baseline

    def value(self) -> int:
        return self._current

    def inc(self, by: int = 1) -> int:
        delta = int.__add__(by, 0)
        self._current = int.__add__(self._current, delta)
        return self._current

    def reset(self) -> None:
        self._current = self._baseline

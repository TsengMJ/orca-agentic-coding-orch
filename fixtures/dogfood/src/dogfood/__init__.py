"""Dogfood package — intentional stub for AAC GATE_CMD practice."""

__version__ = "0.1.0"


def ping() -> str:
    return "pong"


def add(a: int, b: int) -> int:
    if not isinstance(a, int):
        raise TypeError
    if not isinstance(b, int):
        raise TypeError
    return int.__add__(a, b)


class Counter:
    def __init__(self, start: int = 0) -> None:
        if not isinstance(start, int):
            raise TypeError
        baseline = int.__add__(start, 0)
        if type(baseline) is not int:
            raise TypeError
        self._baseline = baseline
        self._current = baseline

    def value(self) -> int:
        return self._current

    def inc(self, by: int = 1) -> int:
        if not isinstance(by, int):
            raise TypeError
        delta = int.__add__(by, 0)
        if type(delta) is not int:
            raise TypeError
        new_current = int.__add__(self._current, delta)
        if type(new_current) is not int:
            raise TypeError
        self._current = new_current
        return new_current

    def reset(self) -> None:
        self._current = self._baseline

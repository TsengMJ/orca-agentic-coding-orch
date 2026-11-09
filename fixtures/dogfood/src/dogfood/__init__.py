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

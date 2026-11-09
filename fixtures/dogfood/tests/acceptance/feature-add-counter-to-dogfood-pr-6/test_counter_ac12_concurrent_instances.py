"""AC-12: distinct instances updated concurrently."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import dogfood
from dogfood import ping

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def test_ac12_two_threads_distinct_counters() -> None:
    Counter = require_counter()
    a = Counter(0)
    b = Counter(50)
    a_returns: list[int] = []
    b_returns: list[int] = []
    errors: list[BaseException] = []

    def run_a() -> None:
        try:
            for _ in range(20):
                a_returns.append(a.inc())
        except BaseException as e:
            errors.append(e)

    def run_b() -> None:
        try:
            for _ in range(20):
                b_returns.append(b.inc(2))
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=run_a)
    t2 = threading.Thread(target=run_b)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
    assert a_returns == list(range(1, 21))
    assert b_returns == list(range(52, 91, 2))
    for v in a_returns + b_returns:
        assert type(v) is int
    assert a.value() == 20
    assert b.value() == 90
    assert type(a.value()) is int
    assert type(b.value()) is int
    assert dogfood.__version__ == "0.1.0"
    assert ping() == "pong"

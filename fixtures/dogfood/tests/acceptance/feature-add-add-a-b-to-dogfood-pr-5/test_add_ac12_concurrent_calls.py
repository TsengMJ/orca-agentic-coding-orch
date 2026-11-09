"""AC-12: concurrent add calls."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import dogfood
from dogfood import ping

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


def test_ac12_two_threads_repeated_add() -> None:
    add = require_add()
    expected = 2**50 + 3
    returns_a: list[int] = []
    returns_b: list[int] = []
    errors: list[BaseException] = []

    def run_many(store: list[int]) -> None:
        try:
            for _ in range(20):
                store.append(add(2**50, 3))
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=run_many, args=(returns_a,))
    t2 = threading.Thread(target=run_many, args=(returns_b,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == []
    assert returns_a == [expected] * 20
    assert returns_b == [expected] * 20
    for v in returns_a + returns_b:
        assert type(v) is int
    assert dogfood.__version__ == "0.1.0"
    assert ping() == "pong"

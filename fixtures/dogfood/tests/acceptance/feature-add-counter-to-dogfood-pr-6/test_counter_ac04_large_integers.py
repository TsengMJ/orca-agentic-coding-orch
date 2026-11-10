"""AC-04: unbounded integer arithmetic."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def _assert_under_one_second(fn) -> None:
    t0 = time.monotonic()
    fn()
    assert time.monotonic() - t0 < 1.0


def test_ac04_inc_past_63_bit() -> None:
    Counter = require_counter()

    def run() -> None:
        assert Counter(2**63 - 1).inc() == 2**63
        assert type(Counter(2**63 - 1).inc()) is int

    _assert_under_one_second(run)


def test_ac04_double_63_bit_inc() -> None:
    Counter = require_counter()

    def run() -> None:
        got = Counter(2**63).inc(2**63)
        assert got == 2**64
        assert type(got) is int

    _assert_under_one_second(run)


def test_ac04_negative_63_bit_boundary() -> None:
    Counter = require_counter()

    def run() -> None:
        got = Counter(-(2**63)).inc(-1)
        assert got == -(2**63) - 1
        assert type(got) is int

    _assert_under_one_second(run)


def test_ac04_power_of_two_100() -> None:
    Counter = require_counter()

    def run() -> None:
        assert Counter(2**100).inc(2**100) == 2**101
        assert Counter(-(2**100)).inc(-(2**100)) == -(2**101)

    _assert_under_one_second(run)


def test_ac04_sys_maxsize_edges() -> None:
    import sys

    Counter = require_counter()

    def run() -> None:
        assert Counter(sys.maxsize).inc(1) == sys.maxsize + 1
        assert Counter(-sys.maxsize - 1).inc(-1) == -sys.maxsize - 2

    _assert_under_one_second(run)


def test_ac04_large_value_and_reset() -> None:
    Counter = require_counter()

    def run() -> None:
        assert Counter(2**100).value() == 2**100
        assert Counter(2**80).inc(0) == 2**80
        c = Counter(2**80)
        c.inc(5)
        assert c.reset() is None
        assert c.value() == 2**80

    _assert_under_one_second(run)

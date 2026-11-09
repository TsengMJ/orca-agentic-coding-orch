"""AC-04: unbounded integer arithmetic."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


def _assert_under_one_second(fn) -> None:
    t0 = time.monotonic()
    fn()
    assert time.monotonic() - t0 < 1.0


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (2**63 - 1, 1, 2**63),
        (2**63, 2**63, 2**64),
        (-(2**63), -1, -(2**63) - 1),
        (2**100, 2**100, 2**101),
        (-(2**100), -(2**100), -(2**101)),
    ],
    ids=["63bit_plus_one", "double_63", "neg_63", "pow100", "neg_pow100"],
)
def test_ac04_large_exact_sums(a: int, b: int, expected: int) -> None:
    add = require_add()

    def run() -> None:
        got = add(a, b)
        assert got == expected
        assert type(got) is int

    _assert_under_one_second(run)


def test_ac04_sys_maxsize_edges() -> None:
    add = require_add()

    def run() -> None:
        assert add(sys.maxsize, 1) == sys.maxsize + 1
        assert type(add(sys.maxsize, 1)) is int
        assert add(-sys.maxsize - 1, -1) == -sys.maxsize - 2
        assert type(add(-sys.maxsize - 1, -1)) is int

    _assert_under_one_second(run)

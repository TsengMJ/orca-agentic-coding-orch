"""AC-05: bool is valid int input."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (True, True, 2),
        (True, False, 1),
        (False, False, 0),
        (True, 5, 6),
        (4, False, 4),
    ],
    ids=["true_true", "true_false", "false_false", "true_five", "four_false"],
)
def test_ac05_bool_inputs(a, b, expected: int) -> None:
    add = require_add()
    got = add(a, b)
    assert got == expected
    assert type(got) is int

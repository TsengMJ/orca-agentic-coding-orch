"""AC-08: wrong argument counts raise TypeError."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


@pytest.mark.parametrize(
    "bad_call",
    [
        lambda add: add(),
        lambda add: add(1),
        lambda add: add(1, 2, 3),
        lambda add: add(a=1),
        lambda add: add(a=1, b=2, c=3),
        lambda add: add(1, 2, b=3),
    ],
    ids=["no_args", "one_arg", "three_pos", "only_a", "extra_kw", "pos_and_dup_kw"],
)
def test_ac08_arity_raises_type_error(bad_call) -> None:
    add = require_add()
    with pytest.raises(TypeError):
        bad_call(add)

"""AC-07: non-int operands raise TypeError."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import _Box, require_add  # noqa: E402


@pytest.mark.parametrize(
    "bad_pair",
    [
        (1, 1.0),
        (1.0, 1),
        (1.0, 1.0),
        (1, "1"),
        ("1", 2),
        (1, None),
        (None, None),
        (1, b"1"),
        (1, [1]),
        (1 + 0j, 1),
        (True, 1.0),
        (object(), 1),
    ],
    ids=[
        "int_float",
        "float_int",
        "float_float",
        "int_str",
        "str_int",
        "int_none",
        "none_none",
        "int_bytes",
        "int_list",
        "complex_int",
        "bool_float",
        "object_int",
    ],
)
def test_ac07_non_int_raises_type_error(bad_pair: tuple[object, object]) -> None:
    add = require_add()
    a, b = bad_pair
    seen: list[object] = []
    with pytest.raises(TypeError):
        seen.append(add(a, b))
    assert seen == []


def test_ac07_box_operand_raises() -> None:
    add = require_add()
    for pair in ((_Box(), 1), (1, _Box())):
        with pytest.raises(TypeError):
            add(*pair)

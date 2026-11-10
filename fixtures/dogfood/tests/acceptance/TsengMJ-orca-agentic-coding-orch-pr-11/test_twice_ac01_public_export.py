"""AC-01: public twice on dogfood."""

from __future__ import annotations

import sys
from pathlib import Path

import dogfood

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twice_test_helpers import require_twice  # noqa: E402


def test_ac01_twice_on_package() -> None:
    twice = require_twice()
    assert twice is dogfood.twice


def test_ac01_twice_is_callable() -> None:
    twice = require_twice()
    assert callable(twice)


def test_ac01_twice_module_is_dogfood() -> None:
    twice = require_twice()
    assert twice.__module__ == "dogfood"


def test_ac01_from_dogfood_import_twice() -> None:
    from dogfood import twice  # noqa: F401

    assert twice is dogfood.twice

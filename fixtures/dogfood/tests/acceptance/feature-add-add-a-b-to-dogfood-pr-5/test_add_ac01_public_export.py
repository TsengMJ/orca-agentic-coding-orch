"""AC-01: public add on dogfood."""

from __future__ import annotations

import sys
from pathlib import Path

import dogfood

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


def test_ac01_import_add_succeeds() -> None:
    add = require_add()
    assert add is dogfood.add


def test_ac01_add_is_callable() -> None:
    add = require_add()
    assert callable(add)


def test_ac01_add_module_is_dogfood() -> None:
    add = require_add()
    assert add.__module__ == "dogfood"

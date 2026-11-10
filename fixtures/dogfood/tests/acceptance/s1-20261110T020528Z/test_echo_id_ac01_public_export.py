"""AC-01: public echo_id on dogfood."""

from __future__ import annotations

import sys
from pathlib import Path

import dogfood

sys.path.insert(0, str(Path(__file__).resolve().parent))
from echo_test_helpers import require_echo_id  # noqa: E402


def test_ac01_echo_id_is_package_attribute() -> None:
    assert hasattr(dogfood, "echo_id"), "dogfood must expose echo_id on the package"


def test_ac01_import_echo_id_succeeds() -> None:
    echo_id = require_echo_id()
    assert echo_id is dogfood.echo_id


def test_ac01_echo_id_is_callable() -> None:
    echo_id = require_echo_id()
    assert callable(echo_id)


def test_ac01_echo_id_module_is_dogfood() -> None:
    echo_id = require_echo_id()
    assert echo_id.__module__ == "dogfood"

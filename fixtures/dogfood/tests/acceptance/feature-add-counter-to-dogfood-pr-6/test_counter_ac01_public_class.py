"""AC-01: public Counter class on dogfood."""

from __future__ import annotations

import collections
import inspect
import sys
from pathlib import Path

import dogfood

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def test_ac01_import_counter_succeeds() -> None:
    Counter = require_counter()
    assert Counter is dogfood.Counter


def test_ac01_counter_is_class() -> None:
    Counter = require_counter()
    assert inspect.isclass(Counter)


def test_ac01_counter_module_is_dogfood() -> None:
    Counter = require_counter()
    assert Counter.__module__ == "dogfood"


def test_ac01_instance_type_is_counter() -> None:
    Counter = require_counter()
    c = Counter(0)
    assert isinstance(c, Counter)
    assert type(c) is Counter


def test_ac01_mro_excludes_collections_dict_int() -> None:
    Counter = require_counter()
    assert collections.Counter not in Counter.__mro__
    assert dict not in Counter.__mro__
    assert int not in Counter.__mro__


def test_ac01_methods_are_callable_not_int_property() -> None:
    Counter = require_counter()
    c = Counter()
    assert callable(c.value)
    assert callable(c.inc)
    assert callable(c.reset)
    assert isinstance(c.value, int) is False


def test_ac01_public_names_counter_and_ping() -> None:
    require_counter()
    names = {n for n in dir(dogfood) if not n.startswith("_")}
    assert {"Counter", "ping"}.issubset(names)

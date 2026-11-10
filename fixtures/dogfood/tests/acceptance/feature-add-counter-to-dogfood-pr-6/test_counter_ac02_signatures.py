"""AC-02: Counter constructor and method signatures."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counter_test_helpers import require_counter  # noqa: E402


def test_ac02_signature_counter_init_param() -> None:
    Counter = require_counter()
    sig = inspect.signature(Counter)
    params = list(sig.parameters.values())
    assert len(params) == 1
    p = params[0]
    assert p.name == "start"
    assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert type(p.default) is int
    assert p.default == 0
    assert p.annotation is int


def test_ac02_signature_init_method() -> None:
    Counter = require_counter()
    sig = inspect.signature(Counter.__init__)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["self", "start"]
    for p in params:
        assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[0].default is inspect.Parameter.empty
    start = params[1]
    assert start.annotation is int
    assert type(start.default) is int
    assert start.default == 0
    assert sig.return_annotation is None


def test_ac02_signature_value() -> None:
    Counter = require_counter()
    sig = inspect.signature(Counter.value)
    params = list(sig.parameters.values())
    assert len(params) == 1 and params[0].name == "self"
    assert params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[0].default is inspect.Parameter.empty
    assert sig.return_annotation is int


def test_ac02_signature_inc() -> None:
    Counter = require_counter()
    sig = inspect.signature(Counter.inc)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["self", "by"]
    for p in params:
        assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[0].default is inspect.Parameter.empty
    by = params[1]
    assert by.annotation is int
    assert type(by.default) is int
    assert by.default == 1
    assert sig.return_annotation is int


def test_ac02_signature_reset() -> None:
    Counter = require_counter()
    sig = inspect.signature(Counter.reset)
    params = list(sig.parameters.values())
    assert len(params) == 1 and params[0].name == "self"
    assert params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[0].default is inspect.Parameter.empty
    assert sig.return_annotation is None

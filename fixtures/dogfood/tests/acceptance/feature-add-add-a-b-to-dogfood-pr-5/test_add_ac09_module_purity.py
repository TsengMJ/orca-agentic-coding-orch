"""AC-09: no I/O, logging, or module __dict__ side effects from add."""

from __future__ import annotations

import importlib
import io
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import dogfood

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


def test_ac09_purity_module_dict_unchanged() -> None:
    importlib.reload(dogfood)
    baseline_keys = set(dogfood.__dict__)
    baseline_values = {k: dogfood.__dict__[k] for k in baseline_keys}
    add = require_add()

    records: list[logging.LogRecord] = []

    class _Catch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    root = logging.getLogger()
    handler = _Catch()
    root.addHandler(handler)
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            r1 = add(6, 7)
            assert r1 == 13
            assert type(r1) is int
            r2 = add(6, 7)
            assert r2 == 13
            assert type(r2) is int
            big = add(2**80, 3)
            assert big == 2**80 + 3
            assert type(big) is int
        assert out.getvalue() == ""
        assert err.getvalue() == ""
        assert records == []
    finally:
        root.removeHandler(handler)

    def fail_open(*_a, **_k):
        raise AssertionError("open called")

    def fail_socket(*_a, **_k):
        raise AssertionError("socket called")

    with patch("builtins.open", fail_open):
        assert add(1, 2) == 3
    with patch("socket.socket", fail_socket):
        assert add(1, 2) == 3

    assert dogfood.__version__ == "0.1.0"
    assert dogfood.ping() == "pong"
    assert set(dogfood.__dict__) == baseline_keys
    for key in baseline_keys:
        assert dogfood.__dict__[key] is baseline_values[key]
    assert "__all__" not in dogfood.__dict__

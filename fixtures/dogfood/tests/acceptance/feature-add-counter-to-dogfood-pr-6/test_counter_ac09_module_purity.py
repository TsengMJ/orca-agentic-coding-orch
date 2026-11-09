"""AC-09: no I/O, logging, or module __dict__ side effects."""

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
from counter_test_helpers import require_counter  # noqa: E402


def test_ac09_module_dict_unchanged_after_use() -> None:
    importlib.reload(dogfood)
    baseline_keys = set(dogfood.__dict__)
    baseline_values = {k: dogfood.__dict__[k] for k in baseline_keys}
    C = require_counter()

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
            c = C(6)
            got = c.inc(7)
            assert got == 13
            assert type(got) is int
            assert c.value() == 13
            assert type(c.value()) is int
            assert c.reset() is None
            assert c.value() == 6
            assert type(c.value()) is int
            big = C(2**80).inc(3)
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
        assert C(1).inc(2) == 3
    with patch("socket.socket", fail_socket):
        assert C(1).inc(2) == 3

    assert dogfood.__version__ == "0.1.0"
    assert dogfood.ping() == "pong"
    assert set(dogfood.__dict__) == baseline_keys
    for key in baseline_keys:
        assert dogfood.__dict__[key] is baseline_values[key]
    assert "__all__" not in dogfood.__dict__

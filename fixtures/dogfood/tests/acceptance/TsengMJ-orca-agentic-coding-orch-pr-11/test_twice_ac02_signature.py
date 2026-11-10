"""AC-02: twice signature and annotations."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from twice_test_helpers import require_twice  # noqa: E402


def test_ac02_signature_single_n_param() -> None:
    twice = require_twice()
    sig = inspect.signature(twice)
    params = list(sig.parameters.values())
    assert len(params) == 1
    n = params[0]
    assert n.name == "n"
    assert n.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert n.default is inspect.Parameter.empty
    assert n.annotation is int
    assert sig.return_annotation is int

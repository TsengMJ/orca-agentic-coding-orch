"""AC-02: add signature and annotations."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_test_helpers import require_add  # noqa: E402


def test_ac02_signature_add_params() -> None:
    add = require_add()
    sig = inspect.signature(add)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["a", "b"]
    for p in params:
        assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert p.default is inspect.Parameter.empty
        assert p.annotation is int
    assert sig.return_annotation is int

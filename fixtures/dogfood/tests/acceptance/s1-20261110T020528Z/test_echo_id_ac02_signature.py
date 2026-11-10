"""AC-02: echo_id signature and annotations."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from echo_test_helpers import require_echo_id  # noqa: E402


def test_ac02_signature_echo_id_param() -> None:
    echo_id = require_echo_id()
    sig = inspect.signature(echo_id)
    params = list(sig.parameters.values())
    assert len(params) == 1
    s = params[0]
    assert s.name == "s"
    assert s.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert s.default is inspect.Parameter.empty
    assert s.annotation is str
    assert sig.return_annotation is str

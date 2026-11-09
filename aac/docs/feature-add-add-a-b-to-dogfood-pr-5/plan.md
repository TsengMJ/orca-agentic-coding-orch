# Plan: `dogfood.add`

Spec: `aac/docs/s1-20261109T081826Z/spec.md` (approved; do not edit it).
Scope: product edits only in `fixtures/dogfood/src/dogfood/__init__.py`. Do not edit `ping`, `__version__`, `fixtures/dogfood/pyproject.toml`, or `fixtures/dogfood/tests/test_smoke.py`. Do not add a module, dependency, `__all__`, or `from __future__ import annotations`. These tasks do not write acceptance tests.
Gate after every task: `uv run --project fixtures/dogfood --group dev pytest -q` (existing `test_ping` stays green). Acceptance tests stay out of these commits; until they exist, check new behavior against the spec oracle (`result == int.__add__(a, b)` and `type(result) is int`) before committing.
Both tasks write the same file, so they run in order. No parallel task.
Rollback: delete `add` from `__init__.py` and re-run the gate; expect exit 0. No schema or stored data.

## Phase 1
Acceptance: existing ping stays green; valid-int `add` matches `int.__add__`
- [ ] T-01 Run the gate before editing; add `add(a: int, b: int) -> int` with runtime annotations of builtin `int` (no `from __future__ import annotations`), returning `int.__add__(a, b)` and not `a + b` or `int()`; do not add non-int `TypeError` guards in this commit; AC-01,AC-02,AC-03,AC-04,AC-05,AC-06,AC-08,AC-09,AC-10,AC-11,AC-12; files=fixtures/dogfood/src/dogfood/__init__.py; deps=[]; DoD=`from dogfood import add` is `dogfood.add` with AC-02's signature, valid int/bool/subclass/unbounded sums equal `int.__add__` with `type is int` and no `OverflowError`, wrong arity raises `TypeError`, calls do no I/O and do not change `dogfood.__dict__` identities, two threads each get the full sum, `ping` source and package metadata stay as specified, and the pytest gate exits 0

Risk: `return a + b` or `int(a) + int(b)` honors `__add__` / `__int__` and breaks AC-06. Call `int.__add__`. This commit does not type-filter, so `bool` and `int` subclasses stay valid.

## Phase 2
Acceptance: non-int inputs raise `TypeError` and `add` does not return `NotImplemented`
- [ ] T-02 Raise `TypeError` when `isinstance(a, int)` or `isinstance(b, int)` is false, before any sum, and do not return `NotImplemented`; keep the T-01 signature so arity errors stay `TypeError` and are not caught; AC-01,AC-02,AC-03,AC-04,AC-05,AC-06,AC-07,AC-08,AC-09,AC-10,AC-11,AC-12; files=fixtures/dogfood/src/dogfood/__init__.py; deps=[T-01]; DoD=every AC-07 call raises `TypeError` with no returned value, `bool` and `int` subclasses still sum via `int.__add__`, ordinary and unbounded rows stay exact builtin `int`s, arity `TypeError` is unchanged, purity and concurrent calls still hold, `ping` source and version stay as specified, and the pytest gate exits 0

Risk: `type(arg) is not int` rejects `bool`, `_Plain`, and `IntEnum` (AC-05, AC-06). Check `isinstance(..., int)` only. Do not catch `TypeError`.

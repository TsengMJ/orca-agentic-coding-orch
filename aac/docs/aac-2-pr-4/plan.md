# Plan: `dogfood.Counter`

Spec: `aac/docs/s1-20261109T090223Z/spec.md` (approved; do not edit it).
Scope: product edits only in `fixtures/dogfood/src/dogfood/__init__.py`. Do not edit `ping`, `__version__`, `fixtures/dogfood/pyproject.toml`, or `fixtures/dogfood/tests/test_smoke.py`. Do not add a module, dependency, `__all__`, or `from __future__ import annotations`. These tasks do not write acceptance tests.
Gate after every task: `uv run --project fixtures/dogfood --group dev pytest -q` (existing `test_ping` stays green). New acceptance tests may stay red until T-02.
Both tasks write the same file, so they run in order. No parallel task.
Rollback: delete `Counter` from `__init__.py` and re-run the gate; expect exit 0. No schema or stored data.

## Phase 1
Acceptance: existing ping stays green; valid-int `Counter` matches the oracle
- [ ] T-01 Run the gate before editing; add `Counter` with the spec signatures and per-instance baseline/current using `int.__add__` (not `+` or `int()`), including `reset` back to that baseline; do not add non-int `TypeError` guards in this commit; AC-01,AC-02,AC-03,AC-04,AC-05,AC-06,AC-09,AC-10,AC-11,AC-12; files=fixtures/dogfood/src/dogfood/__init__.py; deps=[]; DoD=valid-int value/inc/reset match the spec oracle, instances do not share state, no I/O or `__dict__` identity changes, `ping` source and package metadata stay as specified, and the existing pytest gate exits 0

Risk: a class-level current, `+`, or `int()` breaks AC-03, AC-06, and AC-12. Store `int.__add__(start, 0)` on the instance once.

## Phase 2
Acceptance: non-int and arity errors raise `TypeError` and leave current and baseline unchanged
- [ ] T-02 Raise `TypeError` for a non-int `start` or `by` and for calls that do not match the signatures, before any current or baseline write, and do not return `NotImplemented`; AC-07,AC-08,AC-09,AC-10,AC-11; files=fixtures/dogfood/src/dogfood/__init__.py; deps=[T-01]; DoD=AC-07 and AC-08 observations hold, a later `reset()` restores the construction baseline, and the pytest gate exits 0 with `ping` unchanged

Risk: validating after assignment lets a failed `inc` replace the baseline (AC-07, AC-08). Check `isinstance` first and do not catch arity `TypeError`.

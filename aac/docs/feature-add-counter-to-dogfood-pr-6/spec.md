# Spec: `dogfood.Counter` in-memory counter

Run: `s1-20261109T090223Z`
Target: `fixtures/dogfood` (Python package `dogfood`, requires-python `>=3.11`)
Status: normative contract for implementation and later acceptance tests

This document does not implement `Counter` and does not add tests.

Existing module `fixtures/dogfood/src/dogfood/__init__.py`:

- `__version__ == "0.1.0"`
- `ping() -> str` returns the string `"pong"`
- `inspect.getsource(ping)` is exactly `def ping() -> str:\n    return "pong"\n`
- `fixtures/dogfood/tests/test_smoke.py` asserts `ping() == "pong"`
- Package metadata in `fixtures/dogfood/pyproject.toml`: `name = "dogfood"`, `version = "0.1.0"`, `requires-python = ">=3.11"`, `dependencies = []`
- The only product source file under `fixtures/dogfood/src` is `dogfood/__init__.py`
- The only non-underscore import name today is `ping`

## Context / Problem / Goals

`dogfood` is a minimal practice package. Its only callable is `ping`. Callers have no in-memory counter.

**User story:** As a caller of `dogfood`, I construct `Counter(start)` and then read, increment, and restore that instance's integer, while `ping()` still returns `"pong"`.

**Goals**

- Publish a class `Counter` on package `dogfood` with independent instances.
- `Counter(start: int = 0)`, `value() -> int`, `inc(by: int = 1) -> int`, `reset() -> None`.
- Integer results are builtin `int` values, including magnitudes past 64-bit and `sys.maxsize`.
- Reject values for which `isinstance(x, int)` is false with `TypeError`.
- Leave `ping` and the package version unchanged.

**Impact:** the only current importer is `fixtures/dogfood/tests/test_smoke.py` (`from dogfood import ping`). No stored data and no other package depends on `dogfood`.

## Scope / Out of Scope

**In scope**

- One public class, `Counter`, defined in `fixtures/dogfood/src/dogfood/__init__.py` and importable as `from dogfood import Counter` and `dogfood.Counter`.
- Independent instances. Each instance has its own baseline and current value.
- Constructor parameter `start`, positional or keyword, default `0`.
- Methods `value`, `inc`, and `reset` on each instance. `inc` parameter `by`, positional or keyword, default `1`.
- Exact integer arithmetic for every `isinstance(x, int)` value, including negatives, zero, `bool`, and `int` subclasses.
- `TypeError` for a non-int `start` or `by`, and for calls that do not match the signatures below.
- A failed `inc`, `value`, or `reset` leaves that instance's current value and construction baseline unchanged.
- Preserving `ping`, `__version__`, project metadata listed above, and `tests/test_smoke.py`.

**Out of scope**

- A module-level singleton counter, or module functions `value` / `inc` / `reset` that share one global current value.
- `collections.Counter` and any subclass of `dict`, `collections.Counter`, or `int`.
- Any new module, CLI, script, dependency, or persistence (disk, network, process restart).
- Changing `ping`, `__version__`, `pyproject.toml` name / version / `requires-python` / `dependencies`, or `tests/test_smoke.py`.
- Introducing `__all__`, `from __future__ import annotations`, or a required docstring.
- A required exception message.
- Requiring or forbidding extra methods on the class. Callers use only the constructor and the three methods. Tests must not depend on any other attribute.
- Instance attribute names, `__slots__`, `__eq__`, ordering, hashing, `repr`, `str`, `format`, pickle, copy, iteration, mapping, context-manager, or calling the instance.
- `float`, `Decimal`, `Fraction`, complex, numeric strings, and third-party numeric types (including NumPy). No AC imports a third-party numeric library.
- Wrapping, saturating, or fixed-width modes.
- Changing an instance's baseline after construction. `reset` takes no new start.
- Fluent chaining. `inc` returns an `int`, so the return value has no `inc` method.
- Timeout, retry, cancel, metrics, authentication, or authorization parameters.
- Same-instance concurrent `inc` / `reset`. A lock is not required. Lost updates on one shared instance are not a defect for this dogfood.
- `MemoryError` on pathological magnitudes (guidance only, not an AC).
- Argument caching on the instance or function, child loggers with `propagate=False`, and in-place mutation of a mutable object that already lived in `dogfood.__dict__` before the call.
- Writing the acceptance tests themselves (this document is the contract only).

## Interfaces and Behaviors

```python
class Counter:
    def __init__(self, start: int = 0) -> None: ...
    def value(self) -> int: ...
    def inc(self, by: int = 1) -> int: ...
    def reset(self) -> None: ...
```

| Item | Contract |
|---|---|
| Location | Class in `fixtures/dogfood/src/dogfood/__init__.py` |
| Import | `from dogfood import Counter` and `dogfood.Counter` are the same object |
| Kind | `inspect.isclass(Counter)` is true. `type(Counter(0)) is Counter` |
| MRO | `collections.Counter`, `dict`, and `int` are not in `Counter.__mro__` |
| Constructor | `start`, positional-or-keyword, default builtin `int` `0`. User-facing parameter list is exactly `(start: int = 0)` |
| `value` | No parameters beyond the instance. Returns the current builtin `int`. Does not change current or baseline |
| `inc` | `by`, positional-or-keyword, default builtin `int` `1`. Adds `by` to current and returns the new current builtin `int` |
| `reset` | No parameters beyond the instance. Sets current back to that instance's baseline and returns `None` |
| Baseline | Fixed at successful construction. Later `inc` and `reset` calls do not replace it |
| Valid input | `isinstance(start, int)` and `isinstance(by, int)`. This includes builtin `bool` and every subclass of `int` |
| Invalid input | `isinstance(..., int)` is false. Raise `TypeError` and return no value. On an existing instance, current and baseline stay as they were |
| Arity | A call that does not match the signature raises `TypeError`. On an existing instance, current and baseline stay as they were |
| Annotations | Runtime annotations are real objects (`int` or `None`), which requires the module not to use `from __future__ import annotations` |
| `ping` | Behavior, signature, and source text stay as they are today |

**State oracle.** `int.__add__` is the observable oracle, not a required implementation. For a value `n` with `isinstance(n, int)`, the builtin integer is `int.__add__(n, 0)`. That call does not invoke the operand's `__add__`, `__radd__`, `__int__`, or `__index__`.

On a successful `Counter(start)`:

- `baseline = int.__add__(start, 0)` and `current = baseline`
- both are builtin `int` (`type(...) is int`)

Then, for that instance only:

- `value()` returns `current` and leaves `current` and `baseline` unchanged
- `inc(by)` sets `current = int.__add__(current, int.__add__(by, 0))` and returns that builtin `int`
- `reset()` sets `current = baseline` and returns `None`
- A `TypeError` from `inc`, `value`, or `reset` leaves both `current` and `baseline` unchanged. After one or more such failures on an instance, `reset()` returns `None` and `value()` equals the construction baseline (AC-07 for a non-int `by`; AC-08 for arity errors on `value`, `inc`, and `reset`)

A bare `+` is non-conforming when the other operand's `__add__` or `__radd__` can run. `int(n)` is non-conforming when it can call `n.__int__`. `value` and `inc` must not return `NotImplemented`.

Reference values the oracle matches:

- `int.__add__(True, 0) == 1` and the type is `int` (`False` yields `0`)
- `int.__add__(1, 1.0)` is `NotImplemented`, so a `float` argument raises `TypeError`
- A subclass that overrides `__add__` / `__radd__` to return `"nope"` and `__int__` to raise `RuntimeError` still contributes its numeric value through `int.__add__(n, 0)`

**Closed behavior choices** (restated as assumptions; ACs use only these):

1. `reset()` restores the construction-time baseline. It does not ignore `start` and force `0` unless that baseline is `0`.
2. `inc` returns the updated current value.
3. Each `Counter(...)` call has its own baseline and current value.

**Concurrency, timeout, retry, cancel**

- Calls are synchronous. There is no timeout, retry, or cancel parameter.
- Two instances do not share current or baseline. Overlapping calls on distinct instances do not interfere (AC-12).
- Overlapping `inc` / `reset` on the **same** instance is out of scope. No lock is required.
- `value()` is repeatable: two calls with no `inc` or `reset` between them return equal builtin ints and leave the instance unchanged.
- `reset()` is repeatable: a second `reset()` with no `inc` between them returns `None` and leaves current equal to baseline.
- `inc` is not repeatable unless `by` is `0`. A second `inc(1)` adds `1` again.
- The methods do not catch `MemoryError`. Default acceptance magnitudes stay within AC-04 and must not raise it.

## Acceptance Criteria

Each AC is PASS only when every listed observation holds. Any miss, extra exception, or wrong type is FAIL.

Import the package with `fixtures/dogfood/src` on `sys.path` (the same path `fixtures/dogfood/pyproject.toml` gives pytest).

### AC-01 Public class

PASS when:

- `from dogfood import Counter` succeeds
- `Counter` is `dogfood.Counter`
- `inspect.isclass(Counter)` is true
- `Counter.__module__ == "dogfood"`
- `isinstance(Counter(0), Counter)` and `type(Counter(0)) is Counter`
- `collections.Counter`, `dict`, and `int` are not in `Counter.__mro__`
- For `c = Counter()`, `callable(c.value)`, `callable(c.inc)`, and `callable(c.reset)` are true, and `isinstance(c.value, int)` is false (`value` is a method, not a property that already holds the int)
- `sorted(n for n in dir(dogfood) if not n.startswith("_")) == ["Counter", "ping"]`

### AC-02 Signatures and annotations

PASS when all of the following hold.

`inspect.signature(Counter)`:

- Parameter names, in order: `start` only
- Kind is `POSITIONAL_OR_KEYWORD`
- `type(default) is int` and `default == 0` (`False == 0` is true in Python, so the `type is int` check is required)
- Annotation is the builtin `int` (`annotation is int`)

`inspect.signature(Counter.__init__)`:

- Parameter names, in order: `self`, `start`
- Both kinds are `POSITIONAL_OR_KEYWORD`
- `self` default is `Parameter.empty`
- `start` matches the constructor bullet above (`annotation is int`, `type(default) is int`, `default == 0`)
- `return_annotation is None`

Do not read `inspect.signature(Counter).return_annotation`. A custom `__new__` beside `__init__` can drop it; that return annotation is not part of the contract.

`inspect.signature(Counter.value)`:

- Parameter names, in order: `self` only
- Kind is `POSITIONAL_OR_KEYWORD` and default is `Parameter.empty`
- `return_annotation is int`

`inspect.signature(Counter.inc)`:

- Parameter names, in order: `self`, `by`
- Both kinds are `POSITIONAL_OR_KEYWORD`
- `self` default is `Parameter.empty`
- `by`: `annotation is int`, `type(default) is int`, and `default == 1`
- `return_annotation is int`

`inspect.signature(Counter.reset)`:

- Parameter names, in order: `self` only
- Kind is `POSITIONAL_OR_KEYWORD` and default is `Parameter.empty`
- `return_annotation is None`

### AC-03 Ordinary construction, value, inc, and reset

Each row uses a fresh instance except where the steps name `a` and `b` or reuse `c`. Every `value()` and `inc(...)` result has `type is int`. Every `reset()` result `is None`.

| Steps | Required observation |
|---|---|
| `Counter().value()` | `0` |
| `Counter(0).value()` | `0` |
| `Counter(start=0).value()` | `0` |
| `Counter(5).value()` | `5` |
| `Counter(start=5).value()` | `5` |
| `Counter(-3).value()` | `-3` |
| `Counter(start=-7).value()` | `-7` |
| `c = Counter(4)`; `c.value()`; `c.value()` | both calls return `4`; current stays `4` |
| `c = Counter(1)`; `v = c.value()`; `c.inc(4)` | `inc` returns `5`; `c.value() == 5`; `v == 1` |
| `c = Counter(5)`; `c.inc()` | returns `6`; `value()` is `6` |
| `c = Counter(5)`; `c.inc(1)` | returns `6`; `value()` is `6` |
| `c = Counter(5)`; `c.inc(by=1)` | returns `6`; `value()` is `6` |
| `c = Counter(-2)`; `c.inc()` | returns `-1`; `value()` is `-1` |
| `c = Counter(5)`; `c.inc(3)` | returns `8`; `value()` is `8` |
| `c = Counter(5)`; `c.inc(by=3)` | returns `8`; `value()` is `8` |
| `c = Counter(5)`; `c.inc(0)` | returns `5`; `value()` is `5` |
| `c = Counter(5)`; `c.inc(by=0)` | returns `5`; `value()` is `5` |
| `c = Counter(5)`; `c.inc(-2)` | returns `3`; `value()` is `3` |
| `c = Counter(5)`; `c.inc(-5)` | returns `0`; `value()` is `0` |
| `c = Counter(5)`; `c.inc(-8)` | returns `-3`; `value()` is `-3` |
| `c = Counter(10**6)`; `c.inc(10**6)` | returns `2000000`; `value()` is `2000000` |
| `c = Counter()`; `c.inc()`; `c.inc()`; `c.inc()` | returns are `1`, then `2`, then `3`; `value()` is `3` |
| `c = Counter(1)`; `r = c.inc(1)`; `c.inc(1)` | `r == 2` and `r` is not `c`; `value()` is `3` |
| `c = Counter(6)`; `c.reset()` | returns `None`; `value()` is `6` |
| `c = Counter(10)`; `c.inc(5)`; `c.reset()` | `inc` returns `15`; `reset()` is `None`; `value()` is `10` |
| `c = Counter(10)`; `c.inc(5)`; `c.reset()`; `c.reset()` | `value()` is `10` |
| `c = Counter(10)`; `c.inc(5)`; `c.reset()`; `c.inc(1)`; `c.reset()` | the `inc(1)` returns `11`; final `value()` is `10` |
| `c = Counter(0)`; `c.inc(4)`; `c.reset()` | `value()` is `0` |
| `a = Counter(3)`; `b = Counter(9)`; `a.inc(1)` | `a.inc` returns `4`; `a.value() == 4`; `b.value() == 9` |
| continuing `a` and `b`: `a.reset()` | `a.value() == 3`; `b.value() == 9` |
| `Counter(1).inc(4)`; then a new `Counter(1).value()` | the new call returns `1` |
| `c = Counter(2)`; `c.inc(9)`; then a new `Counter().value()` | the new call returns `0`; `c.value() == 11` |

`reset()` on `Counter(10)` leaving `0` is FAIL. `inc` returning the delta `by`, the previous current, or the instance is FAIL.

### AC-04 Unbounded integers (no overflow)

PASS when each call returns the expected builtin `int` (`type is int`), raises no exception, and finishes in under 1.0 second wall time. `c.reset()` results `is None`.

The 1.0s bound is one wall-clock sample per listed call on the gate host: the pytest process started by `uv run --project fixtures/dogfood --group dev pytest` (the same invocation as AC-11). It is not a separate idle-machine benchmark. There is no retry; a single sample at or above 1.0s is FAIL. The numeric bound is unchanged.

| Steps | Expected current |
|---|---|
| `Counter(2**63 - 1).inc()` | `2**63` |
| `Counter(2**63).inc(2**63)` | `2**64` |
| `Counter(-(2**63)).inc(-1)` | `-(2**63) - 1` |
| `Counter(2**100).inc(2**100)` | `2**101` |
| `Counter(-(2**100)).inc(-(2**100))` | `-(2**101)` |
| `Counter(sys.maxsize).inc(1)` | `sys.maxsize + 1` |
| `Counter(-sys.maxsize - 1).inc(-1)` | `-sys.maxsize - 2` |
| `Counter(2**100).value()` | `2**100` |
| `Counter(2**80).inc(0)` | `2**80` |
| `c = Counter(2**80)`; `c.inc(5)`; `c.reset()`; `c.value()` | `2**80` |

`OverflowError`, a wrapped low-width result, or a non-`int` is FAIL.

### AC-05 `bool` inputs

`bool` is a subclass of `int`, so it is valid. PASS when each numeric result equals `expected` and `type(result) is int` (the result is not `bool`). `reset()` `is None`.

| Steps | Expected |
|---|---|
| `Counter(True).value()` | `1` |
| `Counter(False).value()` | `0` |
| `Counter(start=True).value()` | `1` |
| `Counter(start=False).value()` | `0` |
| `Counter(True).inc()` | `2` |
| `Counter(0).inc(True)` | `1` |
| `Counter(0).inc(False)` | `0` |
| `Counter(5).inc(True)` | `6` |
| `Counter(5).inc(by=False)` | `5` |
| `c = Counter(True)`; `c.inc(True)`; `c.reset()`; `c.value()` | `1` |

A `TypeError` for `True` or `False` is FAIL.

### AC-06 `int` subclasses

Valid input is any `isinstance(arg, int)`, not an allowlist of builtin `int` and `bool`. This AC observes three shapes defined only in the test, not in `dogfood`. A `TypeError` or `RuntimeError` for `_Plain`, `_Odd`, or `_E` is FAIL. Rejecting an argument because `type(arg) is not int` fails the `_Plain` rows.

**Benign subclass.** Overrides nothing:

```python
class _Plain(int):
    pass
```

PASS when each result equals `expected`, `type(result) is int`, and `reset()` `is None`:

| Steps | Expected |
|---|---|
| `Counter(_Plain(2)).value()` | `2` |
| `Counter(_Plain(2)).inc(_Plain(3))` | `5` |
| `Counter(_Plain(2)).inc(3)` | `5` |
| `Counter(3).inc(_Plain(2))` | `5` |
| `c = Counter(_Plain(2))`; `c.inc(3)`; `c.reset()`; `c.value()` | `2` |

`type(_Plain(2)) is int` is false and `isinstance(_Plain(2), int)` is true.

**Hostile subclass.** Overrides arithmetic and conversion:

```python
class _Odd(int):
    def __add__(self, other: object) -> str:
        return "nope"

    def __radd__(self, other: object) -> str:
        return "nope"

    def __int__(self) -> int:
        raise RuntimeError("no")
```

PASS when:

- `Counter(_Odd(2)).value() == 2` and `type is int`
- `Counter(_Odd(2)).inc(_Odd(3)) == 5` and `type is int`
- `Counter(_Odd(2)).inc(3) == 5` and `type is int`
- `Counter(10).inc(_Odd(1)) == 11` and `type is int`
- `Counter(_Odd(-4)).inc(1) == -3` and `type is int`
- `c = Counter(_Odd(2))`; `c.inc(_Odd(3))`; `c.reset()`; `c.value() == 2` and `type is int`
- No `RuntimeError` and no result equal to `"nope"`
- Each numeric result equals `int.__add__` of the construction baseline and the `inc` deltas above

**Stdlib `IntEnum`:**

```python
from enum import IntEnum

class _E(IntEnum):
    A = 1
    B = 2
```

PASS when:

- `Counter(_E.A).value() == 1` and `type is int`
- `Counter(_E.A).inc(_E.B) == 3` and `type is int`
- `Counter(5).inc(_E.B) == 7` and `type is int`
- `c = Counter(_E.A)`; `c.inc(_E.B)`; `c.reset()`; `c.value() == 1` and `type is int`

### AC-07 Non-int inputs raise `TypeError`

PASS when each call raises `TypeError` and does not return (including not returning `NotImplemented` or a coerced `int`). Exception text is not part of the contract. A different exception type is FAIL. On an existing instance, current and the construction baseline are unchanged. Baseline is observed by `reset()` returning `None` and the following `value()` equaling the `start` passed to `Counter`.

Constructor calls, including this keyword call: `Counter(start=1.0)`.

- `Counter(1.0)`
- `Counter("1")`
- `Counter(None)`
- `Counter(b"1")`
- `Counter([1])`
- `Counter(1 + 0j)`
- `Counter(object())`

For each constructor call, the caller receives no instance:

```python
seen = []
try:
    seen.append(Counter(1.0))
except TypeError:
    pass
assert seen == []
```

The same `seen == []` observation holds for every constructor call in the list above. After those failures, `Counter(4).value() == 4` and `type is int` (the class still constructs).

Also define this type only in the test:

```python
class _Box:
    def __int__(self) -> int:
        return 7

    def __index__(self) -> int:
        return 7

    def __add__(self, other: object) -> int:
        return 0
```

- `Counter(_Box())` raises `TypeError` and appends nothing to `seen`
- `c = Counter(5)`; `c.inc(_Box())` raises `TypeError`; `c.value() == 5`; then `c.reset() is None` and `c.value() == 5` (construction baseline unchanged)

On `c = Counter(5)`; `c.inc(2)` so current is `7` and the construction baseline is `5`, each following call raises `TypeError` and leaves `c.value() == 7`:

- `c.inc(1.0)`
- `c.inc("1")`
- `c.inc(None)`
- `c.inc(b"1")`
- `c.inc([1])`
- `c.inc(1 + 0j)`
- `c.inc(object())`
- `c.inc(by=1.0)`

After that series, `c.inc(2) == 9` and `c.value() == 9` (the instance is not poisoned). Then `c.reset() is None` and `c.value() == 5`. That `5` is the baseline stored by `Counter(5)`. FAIL if `reset()` restores any other integer, including `7` or `9`.

### AC-08 Argument count

PASS when each call raises `TypeError`. On an existing instance, current and the construction baseline are unchanged. Baseline is observed after the instance calls below: `reset()` returns `None` and `value()` equals the `start` passed to `Counter`.

Fresh `c = Counter(5)`; `c.inc(2)` so `c.value() == 7` and the construction baseline is `5`. Then each of these raises `TypeError` and `c.value()` stays `7`:

- `c.value(1)`
- `c.value(x=1)`
- `c.inc(1, 2)`
- `c.inc(1, by=2)`
- `c.inc(by=1, extra=2)`
- `c.reset(0)`
- `c.reset(to=0)`

After that series, `c.reset() is None` and `c.value() == 5`. That `5` is the baseline stored by `Counter(5)`. The series includes failing `value`, `inc`, and `reset` calls. FAIL if `reset()` restores any other integer, including `7`.

These constructor and unbound calls also raise `TypeError`:

- `Counter(1, 2)`
- `Counter(1, start=2)`
- `Counter(start=1, by=2)`
- `Counter.value()`
- `Counter.inc()`
- `Counter.reset()`
- `Counter.value(1, 2)` with two positional arguments after an implicit missing instance (call `Counter.value(1, 2)`)

`Counter()`, `Counter(1)`, `c.inc()`, `c.value()`, and `c.reset()` are valid and are covered by AC-03, not by this AC.

### AC-09 Purity and determinism

Perform this AC on a fresh `import dogfood`. Do not reuse a module object on which `Counter` has already been instantiated, and do not share this snapshot with AC-12.

Immediately after that import completes, and before the first `Counter` call in this AC, capture the only baseline:

- `baseline_keys = set(dogfood.__dict__)`
- `baseline_values = {key: dogfood.__dict__[key] for key in baseline_keys}`

Do not compare against a pre-feature module that lacks `Counter`. Do not recapture the baseline after any `Counter` call.

PASS when every observation holds:

- `c = Counter(6)`; `c.inc(7) == 13` and `type is int`; `c.value() == 13` and `type is int`
- `c.reset() is None`; `c.value() == 6` and `type is int`
- `Counter(2**80).inc(3) == 2**80 + 3` and `type is int`
- Captured stdout and stderr around those calls are empty
- A list handler attached to the root logger receives no `LogRecord` from those calls
- While `builtins.open` is replaced with a function that raises `AssertionError`, `Counter(1).inc(2)` still returns `3`
- While `socket.socket` is replaced with a function that raises `AssertionError`, `Counter(1).inc(2)` still returns `3`
- After the calls listed above, `dogfood.__version__ == "0.1.0"` and `dogfood.ping() == "pong"`
- After the calls listed above, `set(dogfood.__dict__) == baseline_keys`. A key those calls insert is FAIL. For every `key` in `baseline_keys`, `dogfood.__dict__[key] is baseline_values[key]`. A value object those calls insert or replace is FAIL. In-place mutation of a mutable object that keeps the same identity is outside this check
- `"__all__" not in dogfood.__dict__`

Instance state is supposed to change. This AC does not freeze `c.value()`.

### AC-10 `ping` unchanged

PASS when:

- `ping() == "pong"`
- `inspect.signature(ping)` has no parameters
- `inspect.signature(ping).return_annotation is str`
- `inspect.getsource(ping)` equals this Python string (newline escapes, four-space indent, LF):

```python
'def ping() -> str:\n    return "pong"\n'
```

### AC-11 Version, package surface, and existing suite

PASS when:

- `dogfood.__version__ == "0.1.0"`
- `fixtures/dogfood/pyproject.toml` still has `name = "dogfood"`, `version = "0.1.0"`, `requires-python = ">=3.11"`, and `dependencies = []`
- The only `*.py` file under `fixtures/dogfood/src` is `dogfood/__init__.py`
- `fixtures/dogfood/tests/test_smoke.py` still contains `assert ping() == "pong"`
- `uv run --project fixtures/dogfood --group dev pytest -q` exits 0, including `test_ping`

### AC-12 Distinct instances used concurrently

PASS when two threads run with no other synchronization, and they do not touch each other's instances:

- Thread A: `a = Counter(0)`, then `a.inc()` twenty times
- Thread B: `b = Counter(50)`, then `b.inc(2)` twenty times

Required observations:

- Every return from thread A is the successive totals `1` through `20`, each `type is int`
- Every return from thread B is `52, 54, ... , 90`, each `type is int`
- No exception leaves either thread
- After both threads join, `a.value() == 20`, `b.value() == 90`, both types are `int`
- `dogfood.__version__ == "0.1.0"` and `ping() == "pong"`

Same-instance overlap is not part of this AC.

## Failure / Edge Cases

| Situation | Required observation | AC |
|---|---|---|
| Non-int `start`, including `1.0`, `"1"`, `None`, `bytes`, `complex`, `list`, `object`, or `_Box` | `TypeError`. No instance for the caller. Class still accepts `Counter(4)` afterward | AC-07 |
| Non-int `by`, including `by=1.0` and `_Box` | `TypeError`. Current unchanged. A later valid `inc` still works. `reset()` then returns `None` and `value()` equals the construction baseline | AC-07 |
| Fewer, more, or unexpected keywords on the constructor or methods | `TypeError`. Existing current unchanged. On an instance, `reset()` then returns `None` and `value()` equals the construction baseline | AC-08 |
| `bool` | Accepted. Results are builtin `int`, using `True == 1` and `False == 0` | AC-05 |
| Benign `int` subclass `_Plain` | Builtin `int` equal to the numeric value. `TypeError` is FAIL | AC-06 |
| Hostile `__add__` / `__radd__` / `__int__` | Numeric builtin `int`. Those methods are not the source of the result and `__int__` does not run | AC-06 |
| `enum.IntEnum` | Accepted. Result and later `reset` baseline are builtin `int` | AC-06 |
| `by == 0` | Returns the unchanged current builtin `int` | AC-03 |
| Negative `start` or negative `by` | Exact builtin `int`, including crossing zero | AC-03 |
| `reset()` before any `inc` | Current stays at the baseline | AC-03 |
| `reset()` after `inc`, including a second cycle of `inc` then `reset` | Current returns to the original baseline, including when that baseline is not `0` | AC-03 |
| `value()` twice | Same numeric result, current unchanged | AC-03 |
| Two live instances, or a discarded instance plus a new `Counter` | Currents stay independent | AC-03 |
| Magnitude past signed 64-bit or `sys.maxsize` | Exact builtin `int`. No `OverflowError`. Each covered call returns within 1 second on the pytest gate host; one sample; no retry | AC-04 |
| Second `inc(1)` | Adds again. `inc` is not an idempotent cache | AC-03 |
| Module `__dict__` after the AC-09 calls | Key set and value identities match the post-import baseline | AC-09 |
| Overlapping calls on two distinct instances | Each instance reaches its own total | AC-12 |
| Overlapping `inc` / `reset` on one shared instance | Out of scope. Not an AC. No lock is required | — |
| Interpreter cannot allocate a pathological int | Guidance only (not an AC): `MemoryError` propagates. Default ACs use only AC-04 magnitudes | — |
| Timeout, retry, cancel, metrics | No such parameters and no such behavior | AC-04 |
| Process kill mid-call | No external state is written, so there is no partial result outside the process | AC-09 |

## Backward Compatibility / Regression Targets

Current public behavior that must remain true after `Counter` exists:

- `ping()` returns `"pong"` with signature `() -> str` and the source text in AC-10.
- `dogfood.__version__` remains `"0.1.0"`.
- Project `name` remains `"dogfood"`, version remains `0.1.0`, `requires-python` remains `>=3.11`, and `dependencies` remains `[]`.
- `tests/test_smoke.py` keeps `assert ping() == "pong"`, and `uv run --project fixtures/dogfood --group dev pytest -q` exits 0 (AC-11).
- No `__all__` is added (AC-09). Existing `from dogfood import ping` keeps working.
- The only new non-underscore import name is `Counter` (AC-01).

There is no data migration. `Counter` is a new symbol. Instances exist only in the caller's process.

## Security / Reliability Requirements

- I/O, logging, and module-dict constraints are **exactly** AC-09: empty stdout/stderr around those calls; no root-logger `LogRecord`; `open` / `socket` stubs still succeed; `__dict__` key set and value **identities** unchanged versus the post-import baseline. In-place mutation of an existing mutable value (same identity), argument caching, and child loggers are **out of scope**.
- `eval` / `exec` of `start` or `by` is guidance only (not an AC).
- Non-ints are rejected rather than coerced with `int()` (AC-07).
- Successful `inc` and `value` results are the entire builtin `int` (AC-03, AC-04). There is no truncated or wrapped integer on those rows.
- A `TypeError` from `inc` with a non-int `by` leaves that instance's current value unchanged and does not replace its construction baseline (AC-07). AC-07 does not call `value()`.
- A `TypeError` from `value()`, or from an `inc` or `reset` call that does not match the signature, leaves that instance's current value unchanged and does not replace its construction baseline (AC-08). `value()` failures are AC-08 only.
- No internal timeout and no retry loop inside `Counter`. AC-04 measures one wall-clock sample per listed call on the pytest gate host named in AC-04. A sample at or above 1.0s is FAIL. There is no test retry.
- `MemoryError` on pathological allocations is **guidance only** (not an AC).
- Distinct-instance concurrency is AC-12. Same-instance concurrency is **out of scope**.
- No metrics endpoint, authentication, authorization, secret, or permission model. Any caller who can import `dogfood` can construct a `Counter`. Risk level: **low**.

## Assumptions and Open Questions

Normative assumptions (they fix the contract; acceptance tests can implement them directly):

1. **`Counter` is a class of independent instances.** A module-global current value cannot represent two `Counter(start)` objects. `collections.Counter` is a different type and is not this API.
2. **`reset()` restores the construction-time baseline.** Baseline is `int.__add__(start, 0)` for that instance. `Counter(10).reset()` leaves `10` when no `inc` has stuck. The alternative "always set current to `0`" is rejected: it would drop a non-zero `start` on the first `reset`. This is a closed spec decision so AC-03 has one PASS/FAIL result.
3. **`inc` returns the updated current value.** Returning the delta, the previous value, or the instance is non-conforming. The instance is not an `int`.
4. **`value()` does not change current or baseline.**
5. **`bool` is valid input.** `isinstance(True, int)` is true, and PEP 484 treats `bool` as a subtype of `int`. Results use the numeric values `1` and `0` and have `type is int`.
6. **Other `int` subclasses are valid input.** That includes `_Plain`, `_Odd`, and `enum.IntEnum` in AC-06. Overrides of `__add__`, `__radd__`, `__int__`, and `__index__` do not affect the result.
7. **Non-instances of `int` are rejected**, even when `int()`, `__index__`, or `+` could produce a number. `1.0` is not an `int`.
8. **Exception text is unconstrained.** Tests assert the exception type only.
9. **No magnitude cap for AC-04 sizes.** Those rows must succeed. Larger pathological sizes and `MemoryError` are guidance only (not an AC).
10. **`Counter` lives in the existing `__init__.py`.** No new module, no `__all__`, no version bump, no `from __future__ import annotations`. The instance parameter is named `self`.
11. **A docstring is optional** and has no required wording. Module docstring wording is out of scope.
12. **Runtime is CPython compatible with `requires-python >= 3.11`**, the interpreter already used by this package.
13. **Failed `inc` / `value` / `reset` are non-mutating** with respect to current and baseline. After one or more such `TypeError`s on an instance built with non-zero `start`, `reset()` returns `None` and `value()` equals that construction baseline: AC-07 for a non-int `by` (including the `_Box` row and the series that ends at current `9`), and AC-08 for arity errors on `value`, `inc`, and `reset` (the series that leaves current at `7`). A failed constructor yields no instance to the caller (AC-07).
14. **Same-instance threads are out of scope.** Distinct instances are AC-12.

### Open questions

None. No item is `Requires Human Decision`.

## Risks / Rollback

| Risk | Impact | Mitigation |
|---|---|---|
| `reset()` always stores `0` | `Counter(10)` cannot be restored to `10` | AC-03 rows whose baseline is not `0` |
| `return current + by` or `int(start)` | `float` leaks through, or `_Odd` returns `"nope"` / raises `RuntimeError` | AC-06 and AC-07; oracle is `int.__add__` |
| One class attribute shared as current | A second `Counter(1)` observes the first instance's `inc` | AC-03 discarded-instance row and AC-12 |
| Edit to `ping` or `__version__` while adding `Counter` | Breaks the existing smoke test | AC-10 and AC-11 |
| Treating `2**63` as overflow | Wrong current value on ordinary Python ints | AC-04 |
| Failed `inc` / `value` / `reset` replaces baseline | A later `reset()` restores the wrong integer while `value()` still looks right before that `reset()` | AC-07 and AC-08: `reset()` then `value()` equals the non-zero construction baseline |

**Rollback:** delete the `Counter` class from `fixtures/dogfood/src/dogfood/__init__.py`. No schema, config, or stored data changes. `ping`, `__version__`, and `test_ping` remain sufficient for the package to behave as it did before this feature. Re-run `uv run --project fixtures/dogfood --group dev pytest -q` and expect exit 0.

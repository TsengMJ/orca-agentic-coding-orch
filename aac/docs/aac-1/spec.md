# Spec: `dogfood.add` exact integer sum

Run: `s1-20261109T081826Z`
Target: `fixtures/dogfood` (Python package `dogfood`, requires-python `>=3.11`)
Status: normative contract for implementation and later acceptance tests

Existing module `fixtures/dogfood/src/dogfood/__init__.py`:

- `__version__ == "0.1.0"`
- `ping() -> str` returns the string `"pong"`
- `inspect.getsource(ping)` is exactly `def ping() -> str:\n    return "pong"\n`
- `fixtures/dogfood/tests/test_smoke.py` asserts `ping() == "pong"`
- Package metadata version in `fixtures/dogfood/pyproject.toml` is `0.1.0`

## Context / Problem / Goals

`dogfood` is a minimal practice package. Its only callable is `ping`. Callers have no package function that adds two integers.

Python `int` is arbitrary precision. A sum that is correct for this runtime returns the mathematical sum as a builtin `int`, including values outside the signed 64-bit range and outside `sys.maxsize`. It does not wrap, saturate, or raise `OverflowError`. The annotation `-> int` is a real return type: inputs that would make the `+` operator return a non-int (for example `float`) are rejected.

**User story:** As a caller of `dogfood`, I pass two integers and receive their exact sum as a builtin `int`, while `ping()` still returns `"pong"`.

**Goals**

- Publish a pure `add(a: int, b: int) -> int` on package `dogfood`.
- The result equals the mathematical sum of the two integer values.
- State overflow and type behavior that matches Python `int` (unbounded value; `bool` accepted as an `int` subclass; non-ints rejected).
- Leave `ping` and the package version unchanged.

## Scope / Out of Scope

**In scope**

- One public function, `add`, defined in `fixtures/dogfood/src/dogfood/__init__.py` and importable as `from dogfood import add` and `dogfood.add`.
- Positional and keyword calls using the parameter names `a` and `b`.
- Exact sums, including negatives, zero, `bool`, `int` subclasses (a benign subclass that defines no methods, a subclass that overrides arithmetic, and `enum.IntEnum`), and magnitudes beyond 64-bit and `sys.maxsize`.
- `TypeError` for values that are not instances of `int`, and for calls that do not pass exactly two arguments.
- Preserving `ping`, `__version__`, and the project version.

**Out of scope**

- Any new module, CLI, script, or dependency.
- Changing `ping`, `__version__`, `pyproject.toml` version, or `tests/test_smoke.py`.
- Introducing `__all__`.
- A required docstring or a required exception message string.
- `float`, `Decimal`, `Fraction`, complex, or string-numeric APIs, including coercing those types with `int(...)`.
- Wrapping, saturating, or fixed-width modes.
- A maximum magnitude, timeout parameter, retry, or cancellation API.
- NumPy or other third-party numeric types as supported inputs.
- Writing the acceptance tests themselves (this document is the contract only).

## Interfaces and Behaviors

```python
def add(a: int, b: int) -> int:
    ...
```

| Item | Contract |
|---|---|
| Location | Module-level function in `fixtures/dogfood/src/dogfood/__init__.py` |
| Import | `from dogfood import add` and `dogfood.add` are the same callable |
| Parameters | `a`, then `b`. Both positional-or-keyword. No defaults. No extra parameters. |
| Annotations | Runtime annotations are the builtin type `int` for `a`, `b`, and the return. The module does not switch on `from __future__ import annotations`. |
| Valid input | `isinstance(a, int)` and `isinstance(b, int)`. This includes builtin `bool` and every subclass of `int`, including a subclass that defines no methods. AC-06 observes that case as `_Plain`. Rejecting an argument because `type(arg) is not int` is non-conforming. |
| Result | A builtin `int` (`type(result) is int`) equal to the mathematical sum. Oracle for every valid pair: `result == int.__add__(a, b)`. |
| Invalid input | Any argument for which `isinstance(arg, int)` is false. `add` raises `TypeError` and returns no value. |
| Arity | Not exactly two arguments: raise `TypeError` (Python's call machinery is sufficient). |
| Purity | Limited to what AC-09 observes: empty stdout/stderr around the listed calls; no `LogRecord` on the **root** logger; fs/network stubs in AC-09 still succeed; `dogfood.__dict__` key set and value identities unchanged vs the post-import baseline; same inputs yield the same `int` result. Claims not covered by AC-09 (argument caching on the function object/closure, child loggers with `propagate=False`) are **out of scope** and must not be treated as requirements. |
| Overflow | No `OverflowError`, no wrap at `2**63`, `2**64`, or `sys.maxsize`. |
| `ping` | Behavior, signature, and source text stay as they are today. |

`int.__add__` is the observable oracle, not a required implementation. Operand `__add__`, `__radd__`, and `__int__` must not change the result. `int.__add__` on a non-int returns `NotImplemented`; `add` must not return `NotImplemented`.

Reference values that the oracle matches:

- `int.__add__(True, True) == 2` and the type is `int`
- `int.__add__(1, 1.0)` is `NotImplemented`, so `add(1, 1.0)` raises `TypeError`
- A subclass that overrides `__add__` to return `"nope"` still sums to the numeric value via `int.__add__`

**Concurrency, timeout, retry, cancel**

- Calls are synchronous. There is no timeout, retry, or cancel parameter.
- There is no shared mutable state, so overlapping calls do not interfere and cannot leave a partial sum.
- Duplicate calls with the same arguments succeed and return the same `int`.
- The function does not catch `MemoryError`. If CPython cannot allocate the sum, `MemoryError` propagates. The default acceptance cases below stay within tiny magnitudes and must not raise it.

## Acceptance Criteria

Each AC is PASS only when every listed observation holds. Any miss, extra exception, or wrong type is FAIL.

### AC-01 Public export

PASS when, with `fixtures/dogfood` importable (`pythonpath` includes `fixtures/dogfood/src`):

- `from dogfood import add` succeeds
- `add` is `dogfood.add`
- `callable(add)` is true
- `add.__module__ == "dogfood"`

### AC-02 Signature and annotations

PASS when `inspect.signature(add)` reports:

- Parameter names, in order: `a`, `b`
- Each kind is `POSITIONAL_OR_KEYWORD`
- Each default is `Parameter.empty`
- Each annotation is the builtin `int` (`annotation is int`)
- `return_annotation is int`

### AC-03 Ordinary sums

PASS when every row returns `expected` and `type(add(...)) is int`:

| Call | Expected |
|---|---|
| `add(0, 0)` | `0` |
| `add(1, 2)` | `3` |
| `add(2, 1)` | `3` |
| `add(-3, -5)` | `-8` |
| `add(-3, 5)` | `2` |
| `add(3, -5)` | `-2` |
| `add(41, 0)` | `41` |
| `add(0, -7)` | `-7` |
| `add(10**6, 10**6)` | `2000000` |
| `add(a=4, b=6)` | `10` |
| `add(b=6, a=4)` | `10` |
| `add(1, b=2)` | `3` |

### AC-04 Unbounded integers (no overflow)

PASS when each call returns `expected`, `type(result) is int`, raises no exception, and finishes in under 1.0 second wall time:

| Call | Expected |
|---|---|
| `add(2**63 - 1, 1)` | `2**63` |
| `add(2**63, 2**63)` | `2**64` |
| `add(-(2**63), -1)` | `-(2**63) - 1` |
| `add(2**100, 2**100)` | `2**101` |
| `add(-(2**100), -(2**100))` | `-(2**101)` |
| `add(sys.maxsize, 1)` | `sys.maxsize + 1` |
| `add(-sys.maxsize - 1, -1)` | `-sys.maxsize - 2` |

`OverflowError`, a wrapped low-width result, or a non-`int` is FAIL.

### AC-05 `bool` inputs

`bool` is a subclass of `int`, so it is valid input. PASS when each result equals `expected` and `type(result) is int` (the result is not `bool`):

| Call | Expected |
|---|---|
| `add(True, True)` | `2` |
| `add(True, False)` | `1` |
| `add(False, False)` | `0` |
| `add(True, 5)` | `6` |
| `add(4, False)` | `4` |

### AC-06 `int` subclasses

Valid input is any `isinstance(arg, int)`, not an allowlist of builtin `int` and `bool`. This AC observes three shapes defined only in the test, not in `dogfood`. A call that raises `TypeError` for `_Plain`, `_Odd`, or `_E` is FAIL. An implementation that rejects a subclass solely because `type(arg) is not int` (for example `type(arg) not in (int, bool)`) fails the `_Plain` rows below.

**Benign subclass.** Overrides nothing:

```python
class _Plain(int):
    pass
```

PASS when:

- `add(_Plain(2), _Plain(3)) == 5` and `type(result) is int`
- `add(_Plain(2), 3) == 5` and `type(result) is int`
- `add(3, _Plain(2)) == 5` and `type(result) is int`
- Each of those equals `int.__add__` of the same arguments

`type(_Plain(2)) is int` is false and `isinstance(_Plain(2), int)` is true. Those rows are the observation that a benign user-defined subclass is valid.

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

- `add(_Odd(2), _Odd(3)) == 5` and `type(result) is int`
- `add(_Odd(2), 3) == 5` and `type(result) is int`
- `add(3, _Odd(2)) == 5` and `type(result) is int`
- `add(_Odd(-4), 1) == -3` and `type(result) is int`
- Each result equals `int.__add__` of the same arguments
- No `RuntimeError` and no return value of `"nope"`

**Stdlib `IntEnum`.** Covers a subclass that is neither a bare `int` nor the test-local `_Plain` / `_Odd` types:

```python
from enum import IntEnum

class _E(IntEnum):
    A = 1
    B = 2
```

PASS when:

- `add(_E.A, _E.B) == 3` and `type(result) is int`
- `add(_E.A, 5) == 6` and `type(result) is int`
- `add(5, _E.B) == 7` and `type(result) is int`
- Each of those equals `int.__add__` of the same arguments

### AC-07 Non-int inputs raise `TypeError`

PASS when each call raises `TypeError` and does not return (including not returning `NotImplemented`, a coerced `int`, or a `float`):

- `add(1, 1.0)`
- `add(1.0, 1)`
- `add(1.0, 1.0)`
- `add(1, "1")`
- `add("1", 2)`
- `add(1, None)`
- `add(None, None)`
- `add(1, b"1")`
- `add(1, [1])`
- `add(1 + 0j, 1)`
- `add(True, 1.0)`
- `add(object(), 1)`

Also define this type only in the test:

```python
class _Box:
    def __add__(self, other: object) -> int:
        return 0

    def __radd__(self, other: object) -> int:
        return 0
```

- `add(_Box(), 1)` raises `TypeError`
- `add(1, _Box())` raises `TypeError`

Exception text is not part of the contract. A different exception type is FAIL.

### AC-08 Argument count

PASS when each call raises `TypeError`:

- `add()`
- `add(1)`
- `add(1, 2, 3)`
- `add(a=1)`
- `add(a=1, b=2, c=3)`
- `add(1, 2, b=3)`

### AC-09 Purity and determinism

Perform this AC on a fresh `import dogfood`. Do not reuse a module object on which `add` has already been called, and do not share this snapshot with AC-12.

Immediately after that import completes, and before the first `add` invocation in this AC, capture the only baseline:

- `baseline_keys = set(dogfood.__dict__)`
- `baseline_values = {key: dogfood.__dict__[key] for key in baseline_keys}`

Do not compare against a pre-feature module that lacks `add`. Do not recapture the baseline after any `add` call, and do not recapture it between the calls below.

PASS when every observation holds:

- Two calls `add(6, 7)` both return `13` and `type is int`
- `add(2**80, 3) == 2**80 + 3` and `type is int`
- Captured stdout and stderr around those three calls are empty
- A list handler attached to the root logger receives no `LogRecord` from those three calls
- While `builtins.open` is replaced with a function that raises `AssertionError`, `add(1, 2)` still returns `3`
- While `socket.socket` is replaced with a function that raises `AssertionError`, `add(1, 2)` still returns `3`
- After the calls listed above, `dogfood.__version__ == "0.1.0"` and `dogfood.ping() == "pong"`
- After the calls listed above, `set(dogfood.__dict__) == baseline_keys`. A key those `add` calls insert (any key absent from `baseline_keys`) is FAIL. For every `key` in `baseline_keys`, `dogfood.__dict__[key] is baseline_values[key]`. A value object those `add` calls insert or replace under any key is FAIL. In-place mutation of a mutable object that keeps the same identity is outside this check.
- `"__all__" not in dogfood.__dict__`

### AC-10 `ping` unchanged

PASS when:

- `ping() == "pong"`
- `inspect.signature(ping)` has no parameters
- `inspect.signature(ping).return_annotation is str`
- `inspect.getsource(ping)` equals this Python string (newline escapes, four-space indent, LF):

```python
'def ping() -> str:\n    return "pong"\n'
```

### AC-11 Version and existing suite

PASS when:

- `dogfood.__version__ == "0.1.0"`
- `fixtures/dogfood/pyproject.toml` still has project `version = "0.1.0"` and `requires-python = ">=3.11"`
- `fixtures/dogfood/tests/test_smoke.py` still contains `assert ping() == "pong"`
- `uv run --project fixtures/dogfood --group dev pytest -q` exits 0, including `test_ping`

### AC-12 Concurrent calls

PASS when two threads each call `add(2**50, 3)` twenty times, with no other synchronization:

- Every return value is `2**50 + 3`
- Every return type is `int`
- No exception leaves either thread
- After both threads join, `dogfood.__version__ == "0.1.0"` and `ping() == "pong"`

## Failure / Edge Cases

| Situation | Required observation | AC |
|---|---|---|
| Non-int argument, including an integral `float` such as `1.0`, a numeric string, `None`, `bytes`, `complex`, or a non-int with `__add__` | `TypeError`. No coercion via `int()`. No returned value. | AC-07 |
| Fewer or more than two arguments, or an unexpected keyword | `TypeError` | AC-08 |
| `bool` | Accepted. Result is builtin `int` `0` or `1` combined with the other operand. | AC-05 |
| Benign `int` subclass with no overrides (`class _Plain(int): pass`), including `_Plain` mixed with builtin `int` | Builtin `int` equal to `int.__add__` of the same arguments. `TypeError` is FAIL. | AC-06 |
| `int` subclass with hostile `__add__` / `__radd__` / `__int__` | Numeric sum as builtin `int`. Those methods are not the source of the result. | AC-06 |
| Module `__dict__` after the AC-09 `add` calls | Key set equals `baseline_keys` captured immediately after that AC's fresh import and before its first `add`. No key or value object inserted or replaced by those calls. | AC-09 |
| Magnitude past signed 64-bit or `sys.maxsize`, including both-negative | Exact builtin `int`. No `OverflowError`. | AC-04 |
| Zero and mixed signs | Exact sum. `add(n, 0)` and `add(0, n)` equal `n` for the rows in AC-03. | AC-03 |
| Same call repeated | Same builtin `int` again. | AC-09 |
| Overlapping calls on two threads | Each call returns the full sum. No shared-state corruption of `__version__` or `ping`. | AC-12 |
| Interpreter cannot allocate a pathological sum | Guidance only (not an AC): prefer letting `MemoryError` propagate. Default ACs use only AC-04 magnitudes and must not raise `MemoryError`. | Out of scope for acceptance |
| Timeout, retry, cancel | No such parameters and no such behavior. A call either returns the full sum or raises. Bounded AC-04 inputs return within 1 second. | AC-04 |
| Process kill mid-call | No external state is written, so there is no partial result to observe. | AC-09 |

## Backward Compatibility / Regression Targets

Current public behavior that must remain true after `add` exists:

- `ping()` returns `"pong"` with signature `() -> str` and the source text in AC-10.
- `dogfood.__version__` remains `"0.1.0"`.
- Project version remains `0.1.0` and `requires-python` remains `>=3.11`.
- `tests/test_smoke.py` keeps `assert ping() == "pong"`, and `uv run --project fixtures/dogfood --group dev pytest -q` exits 0 (AC-11).
- No `__all__` is added (AC-09). Existing `from dogfood import ping` keeps working.

There is no data migration. `add` is a new symbol.

## Security / Reliability Requirements

- I/O / logging / module-dict constraints are **exactly** AC-09: empty stdout/stderr around those calls; no root-logger `LogRecord`; `open`/`socket` stubs still succeed; `__dict__` key set and value **identities** unchanged vs the post-import baseline. In-place mutation of an existing mutable value (same identity) and argument caching on the function object/closure are **out of scope**.
- `eval` / `exec` of arguments is guidance only for this dogfood (not an AC).
- The return value is the entire sum or an exception for the AC-covered cases (AC-03, AC-04). There is no truncated or wrapped integer on those rows.
- No internal timeout and no retry loop for AC-04 inputs (return within 1 second on the gate host).
- `MemoryError` behavior for pathological allocations is **guidance only** (not an AC).
- Concurrent callers: see AC-12 if present; otherwise out of scope for this dogfood.
- No secrets, permissions, or authentication apply. Risk level: **low**.

## Assumptions and Open Questions

Normative assumptions (they fix the contract; acceptance tests can implement them directly):

1. **`bool` is valid input.** `isinstance(True, int)` is true, and PEP 484 treats `bool` as a subtype of `int`. `add(True, True)` is `2` with `type is int`.
2. **Other `int` subclasses are valid input.** That includes a benign subclass with no overrides (`_Plain`), a hostile subclass (`_Odd`), and `enum.IntEnum` (`_E`), all in AC-06. The result follows `int.__add__(a, b)`, so overrides of `__add__`, `__radd__`, and `__int__` do not affect it.
3. **Non-instances of `int` are rejected**, even when `+` or `int()` could produce a number. `1.0` is not an `int`.
4. **Exception text is unconstrained.** Tests assert the exception type only.
5. **No magnitude cap for AC-04 sizes.** Those rows must succeed. Larger pathological sizes / `MemoryError` are guidance only (not an AC).
6. **`add` lives in the existing `__init__.py`.** No new module, no `__all__`, no version bump, no `from __future__ import annotations`.
7. **A docstring is optional** and has no required wording.
8. **Runtime is CPython compatible with `requires-python >= 3.11`**, the interpreter already used by this package.

### Open questions

None. No item is `Requires Human Decision`.

## Risks / Rollback

| Risk | Impact | Mitigation |
|---|---|---|
| A bare `return a + b` accepts `float` and returns `float`, or honors a subclass `__add__` and returns a non-int | Breaks `-> int` (AC-06, AC-07) | Domain check plus a sum that matches `int.__add__` |
| Edit to `ping` or `__version__` while adding `add` | Breaks the existing smoke test | AC-10 and AC-11 |
| Treating `2**63` as overflow | Wrong sum on ordinary Python ints | AC-04 |

**Rollback:** delete the `add` function from `fixtures/dogfood/src/dogfood/__init__.py`. No schema, config, or stored data changes. `ping`, `__version__`, and `test_ping` remain sufficient for the package to behave as it did before this feature. Re-run `uv run --project fixtures/dogfood --group dev pytest -q` and expect exit 0.

# Spec: `twice` on `fixtures/dogfood`

## Context / Goals

The `fixtures/dogfood` package is a minimal Python stub used to exercise AAC on small, verifiable API changes. This issue adds `twice(n: int) -> int`, which returns double the input, using the same strict-integer input rules as existing `add`.

Goal: publish `twice` on the public `dogfood` surface without altering behavior of `ping`, `add`, `Counter`, or `echo_id`.

## Scope / Out of Scope

**In scope**

- Add `twice` to `dogfood` with signature `twice(n: int) -> int`.
- For arguments where `isinstance(n, int)` is true, return `n * 2` as a builtin `int`.
- For arguments where `isinstance(n, int)` is false, raise `TypeError` (message text not constrained), matching the spirit of `add`.
- Confirm existing symbols `ping`, `add`, `Counter`, and `echo_id` keep their current behavior.

**Out of scope**

- Changes to orchestration, review workflow, or non-dogfood product code.
- New dependencies, CLI, persistence, or concurrency requirements.
- Writing acceptance tests or implementation in this stage (spec only).

## Interfaces and Behaviors

| Symbol | Signature | Behavior |
| --- | --- | --- |
| `twice` | `(n: int) -> int` | If `isinstance(n, int)`, return `n * 2`. Otherwise raise `TypeError`. |
| `ping` | `() -> str` | Unchanged: returns `"pong"`. |
| `add` | `(a: int, b: int) -> int` | Unchanged. |
| `echo_id` | `(s: str) -> str` | Unchanged. |
| `Counter` | (class) | Unchanged. |

- `twice` is defined on the `dogfood` module and importable as `from dogfood import twice` (same export pattern as `ping` and `add`).
- Valid input includes builtin `bool` values (`isinstance(True, int)` is true).
- No required logging, I/O, or module-level side effects beyond defining the function.

## Acceptance Criteria

**AC-01 (public export)**  
`twice` is an attribute of the `dogfood` package, is callable, and `twice.__module__ == "dogfood"`.

**AC-02 (signature)**  
`inspect.signature(twice)` has exactly one parameter named `n`, positional-or-keyword, no default; `n` and the return annotation are both the builtin `int`.

**AC-03 (core doubling)**  
Each call returns the listed value and `type(result) is int`:

| Call | Expected |
| --- | --- |
| `twice(0)` | `0` |
| `twice(3)` | `6` |
| `twice(-4)` | `-8` |
| `twice(10**6)` | `2000000` |

**AC-04 (non-int rejection)**  
Each call raises `TypeError` and does not return a value: `twice(1.0)`, `twice("3")`, `twice(None)`. After these failures, `twice(2) == 4` still holds (function is not poisoned).

**AC-05 (existing API regression)**  
`ping() == "pong"`; `add(1, 2) == 3`; `echo_id("x") == "x"`; `Counter(2).inc(1) == 3` and `Counter(2).value() == 2`.

## Failure / Edge Cases

- **Non-int `n`:** `TypeError` before any result is returned. Exception message is not part of the contract.
- **Wrong arity:** Extra positional or keyword arguments raise `TypeError` (same expectation as `add` for bad calls).
- **`bool` input:** Accepted via `isinstance`; e.g. `twice(False) == 0`, `twice(True) == 2`, with a builtin `int` result.
- **Large magnitudes:** Exact integer arithmetic; no overflow wrapping for ordinary Python `int` sizes used in AC-03.

## Assumptions and Open Questions

- **Assumption:** `twice` is implemented in `fixtures/dogfood/src/dogfood/__init__.py` alongside existing public symbols.
- **Assumption:** Multiplication follows normal Python `int` semantics for valid inputs; no custom numeric types are required.
- No open questions requiring human decision.

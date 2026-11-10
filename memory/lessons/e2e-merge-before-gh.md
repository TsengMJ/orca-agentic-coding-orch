# E2E merge must not call `gh` (2026-11-10)

## Failure

`test_e2e_collab` failed with `FileNotFoundError: gh` on hosts without the GitHub CLI. `merge_pr` labeled/commented via `gh` **before** checking `AAC_E2E_SKIP`.

## Fix

Short-circuit the e2e stub at the top of `merge_pr` before any `gh` invocation.

## Why

Protocol stubs that still touch the real CLI are not stubs. Ask: does this path require the binary, or only the state transition?
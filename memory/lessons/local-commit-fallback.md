# Local commit fallback (2026-11-10)

## Failure

Self-iteration / local dogfood runs often have no Issue→PR `publish`, so `github.json` is missing. S4 then died with `missing github.json` and could not exercise the commit path.

## Fix

`scripts/worktree_commit.py`:

- If `github.json` is missing and `AAC_REQUIRE_GITHUB` is unset, create `local/<run_id>` worktree from `HEAD`, write `github.json` with `local: true`, commit there, **do not push**.
- Remote collab still uses published meta and pushes.
- Set `AAC_REQUIRE_GITHUB=1` to keep fail-closed for production-shaped runs.

## Regression

`scripts/test_worktree_commit.py`

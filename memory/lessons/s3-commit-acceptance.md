# S3 must commit acceptance tests onto the PR branch (2026-11-10)

## Failure

Issue #10 / PR #11 (`twice`) completed S3 with protected acceptance tests under
`fixtures/dogfood/tests/acceptance/TsengMJ-orca-agentic-coding-orch-pr-11/`, then
implemented and merged to `dev`. After merge, those acceptance files were **only
local/untracked** — never on `origin/dev`.

Root cause: `s3_acceptance_loop.py` armed `protected-tests.json` and posted the
Acceptance stage note, but never called `worktree_commit.commit_paths`. S4 only
commits task files from the plan, so the RED suite stayed off the feature branch.

## Fix

After protection succeeds, S3 calls `land_acceptance_on_branch` →
`worktree_commit.commit_paths` for the acceptance test tree plus
`aac/docs/{run_id}/acceptance-matrix.md`.

`aac/docs/*` is gitignored, so `commit_paths` must `git add -f` for explicit
path lists (otherwise the matrix never lands). Live-proved on
`local/local-s3-land-dogfood`.

Regression: `scripts/test_s3_commit_paths.py`, `scripts/test_worktree_commit.py`.

## Related spawn flake

When S2 auto-continued into S3 via `sys.executable` from a temporary `uv` build
env, that path was gone by the time S3 should start (`FileNotFoundError` on the
uv `.tmp…/bin/python`). Stage handoffs (S1 gate → S2, S2 → S3, plan gate → S3,
workflow_server → S1) use `aac_common.spawn_uv_script` (`uv run --with pyyaml …`).

Regression: `scripts/test_spawn_uv_script.py` (command shape + handoff scripts
must call `spawn_uv_script`, no `Popen(sys.executable …)`).

## `/approve` with orch marker

Self-drive posted `/approve\n\n<!-- aac-orchestrator -->`, and
`classify_body` / `latest_human_command` ignored **any** body containing the
marker — gates stalled until a bare `/approve` appeared.

Fix: first-line `/approve` or `/abort` always counts; other orch-marked notes
(still without that first line) stay ignored.

Regression: `scripts/test_gh_collab.py` + `scripts/test_e2e_collab.py`.

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

After protection succeeds, S3 commits the acceptance test tree plus
`aac/docs/{run_id}/acceptance-matrix.md` onto the run’s feature/fix branch
(same `worktree_commit` path as S4).

## Related spawn flake

When S2 auto-continued into S3 via `sys.executable` from a temporary `uv` build
env, that path was gone by the time S3 should start (`FileNotFoundError` on the
uv `.tmp…/bin/python`). Stage handoffs now use `aac_common.spawn_uv_script`
(`uv run --with pyyaml …`) so children do not depend on ephemeral interpreters.

## Acting as human on GitHub

`/approve` comments that include `<!-- aac-orchestrator -->` are ignored by
`classify_body`. When self-driving gates, post a bare `/approve` with no orch
marker.

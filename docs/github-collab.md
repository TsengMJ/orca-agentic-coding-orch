# GitHub collaboration (1 Issue = 1 draft PR)

Default only. Several issues in one PR is not implemented.

## Shape

- Issue `#N` is the request. Label it `Ready` to enqueue S1.
- Branch is `feature/<slug>` or `fix/<slug>` (bug label or a `fix:` title selects `fix`).
- The draft PR targets `dev`. Merge is into `dev`, not `master`.
- **Product repo** is `github.repo` / `AAC_GITHUB_REPO` / per-run `github.json.repo`. Issues and PRs open there — not automatically on the orch tooling checkout when you are developing another project.
- **Every stage end** (success or failure) posts a Tech Lead note on the PR (or the Issue before publish). Cron reads `Ready` on issues and waiting labels + `/approve`/`/abort`/feedback on PRs to advance.
- Before the PR exists, `run_id` is `{repo}-issue-{N}` (repo slash → `-`).
- After `publish`, `run_id` is `{repo}-pr-{pr}`. Task ids append `-T01`, `-T02`, and so on.
- Branch is stored in `aac/.run/<run_id>/github.json`, not in the run id.
- You decide on the PR with a comment whose first line is `/approve` or `/abort`.
- A comment whose first line is `/approve` continues from the current stage.
- Any other human comment is feedback. The current stage is revised and reviewed again.
- `/abort` stops the run, labels `Abort`, and closes the PR.
- `watch` applies new comments on open PRs that carry a waiting stage label (`Spec` … `Gate`).
- `Gate` + `/approve` → `Gate_Approved` and the service merges into `dev`.

## Stage labels

One workflow label at a time:

| Label | Where | Meaning |
| --- | --- | --- |
| `Ready` | issue | Cron picks it up for S1, then removes it |
| `Spec` | draft PR | Spec ready; wait for `/approve` |
| `Spec_Approved` | draft PR | Spec approved; plan running |
| `Plan` | draft PR | Plan ready; wait for `/approve` |
| `Plan_Approved` | draft PR | Plan approved; acceptance running |
| `Acceptance` | draft PR | Tests protected; wait for `/approve` |
| `Acceptance_Approved` | draft PR | Acceptance approved; implement running |
| `Implement` | draft PR | Task committed; wait for `/approve` |
| `Implement_Approved` | draft PR | Implement approved; gate + final running |
| `Gate` | ready PR | S6 accepted; draft converted to ready-for-review; wait for `/approve` to merge |
| `Gate_Approved` | ready PR | Merging into `dev` |
| `Abort` | PR | Stopped |

Each stage completion posts a short Tech Lead note on the PR (conclusion, delivery, next step).

## Commands

```bash
# long-running server (issue cron + PR cron + healer cron + /health)
uv run --with pyyaml scripts/workflow_server.py
# healer alone: uv run --with pyyaml scripts/healer.py --once

# after S1 review has written aac/docs/<run-id>/spec.md
uv run --with pyyaml scripts/gh_collab.py publish --issue N --run-id <run-id>
uv run --with pyyaml scripts/gh_collab.py check --issue N
uv run --with pyyaml scripts/gh_collab.py apply --issue N --run-id <run-id>
uv run --with pyyaml scripts/gh_collab.py watch
uv run --with pyyaml scripts/gh_collab.py ensure-labels
```

`publish` checks out `feature/<slug>` or `fix/<slug>` from `origin/dev`, force-adds the spec, pushes, opens the draft PR into `dev` if needed, and sets label `Spec`.

Config: `github` and `healer` in [`config/workflow.yaml`](../config/workflow.yaml). Healer role: [`memory/roles/roles/10-workflow-healer.md`](../memory/roles/roles/10-workflow-healer.md).

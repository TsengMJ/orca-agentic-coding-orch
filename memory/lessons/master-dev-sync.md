# master / dev sync

- Feature PRs merge into `dev` only (`docs/github-collab.md`).
- Workflow/infra lands on `master`; when they diverge, **merge `master` → `dev`**, do not reset either side.
- Expected end state: `master` is an ancestor of `dev`; `dev` may be ahead with dogfood feature commits.
- Sole typical conflict: `fixtures/dogfood/src/dogfood/__init__.py` — keep feature APIs from `dev` and hardening from `master` (e.g. `add` type checks + `Counter`).

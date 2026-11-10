# Collaboration invariants (2026-11-10)

Three known requirements for bulk use of this orch against real projects. Re-verify when touching cron, `gh_collab`, or stage abort paths.

## 1. Cron advances from Issue/PR signals

- Issue cron: open issues with `Ready` → claim → S1 → `publish` → PR labeled `Spec`.
- PR cron: open PRs with waiting labels (`Spec`…`Gate`) → read new human comments → `/approve` continues, `/abort` stops, other text is feedback.
- Regression: `scripts/test_workflow_server.py`, `scripts/test_e2e_collab.py`, `scripts/test_gh_collab.py`.

## 2. Every stage end updates the product PR (including failure)

- Success: `stage_complete` → next waiting label + Tech Lead note.
- Failure/abort: `stage_failed` / `report_stage(..., outcome="failed")` — still comment (PR if present, else Issue).
- Silent local-only aborts are a regression.

## 3. PRs open in the product project, not silently on orch

- Resolve repo: run `github.json.repo` → `AAC_GITHUB_REPO` → `config.workflow.yaml` `github.repo`.
- When driving project X, point that setting at X. Orch checkout is tooling; the PR host is the product under development.
- `publish` / labels / comments must use `repo(run_id)`.

## Dogfood checklist

1. `gh auth status` ok.
2. Label a Ready issue on the **product** repo; server claims and publishes a draft PR **there**.
3. Force an agent abort; confirm the PR (or Issue) gets a `**… failed.**` note.
4. `/approve` on Spec advances to Plan.

## Live proof (2026-11-10)

- Issue [#8](https://github.com/TsengMJ/orca-agentic-coding-orch/issues/8) `Ready` listed by `list_ready_issues`.
- Draft PR [#9](https://github.com/TsengMJ/orca-agentic-coding-orch/pull/9) on product repo `TsengMJ/orca-agentic-coding-orch` with `Spec`.
- `stage_failed` posted `**Spec failed.**` on the PR.
- Human `/approve` + `gh_collab watch` → `Spec_Approved` → S2 → `Plan` label / `plan_approved`.
- Extra fix: `publish` / remote commits push via `git@github.com:…` because HTTPS `origin` prompts fail in agents.
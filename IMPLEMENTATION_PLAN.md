# Implementation Plan — AAC × Orca

## Stage 0: Foundation + config
**Goal**: Repo is a configurable AAC practice surface; A/B Cursor models smoke-ok.  
**Success Criteria**:
- [x] `config/workflow.yaml` exists (A=`grok-4.7-high`, B=`composer-2.5`)
- [x] `fixtures/dogfood` pytest green via `gate_cmd`
- [x] `scripts/resolve_slot.py` prints runtime+model for A/B/I
- [x] Cursor A/B smoke returns `PONG-A` / `PONG-B`
- [x] `orca agent hooks status` shows cursor installed
- [x] `prompts/coordinator_brief.md` + stage prompt stubs present
- [x] `aac/`, `artifacts/runs/` placeholders present
**Tests**: commands in README Quick smoke; evidence [`artifacts/runs/s0-smoke.md`](artifacts/runs/s0-smoke.md)  
**Status**: Complete

## Stage 1: Spec loop + human gate
**Goal**: A writes spec, B reviews via `verdict.json`, human approves.  
**Success Criteria**:
- [x] dogfood request produces `aac/docs/.../spec.md` + review artifacts
- [x] review loop with `verdict.json`
- [x] human gate: add run aborted then re-approved；Counter approved
**Tests**: both runs exercised the gate  
**Status**: Complete  
**Commands**:
```bash
uv run --with pyyaml scripts/s1_spec_loop.py --request "…"
uv run --with pyyaml scripts/s1_human_gate.py --run-id <id> --approve   # or --abort
```
**Postmortem**: dogfood exceeded AAC `MAX_ROUNDS` via manual resume to r7; owner hang was hand-patched. Fixed by [`scripts/review_loop.py`](scripts/review_loop.py) + [`docs/review-loop.md`](docs/review-loop.md) (hard cap, agent-call repair retries, abort+resume).

## Stage 2: Plan loop
**Goal**: Checkbox `plan.md` with A/B review; optional `human_gate_plan`.  
**Success Criteria**: ≥2 checkboxes; review approved.  
**Tests**: both dogfood runs reached `plan_approved` (task ids now `<run>-T01` / `<run>-T02`)  
**Status**: Complete  
**Dogfood**: `feature-add-add-a-b-to-dogfood-pr-5`（PR #5）and `feature-add-counter-to-dogfood-pr-6`（PR #6）are here. S3 has not started. Plan spec paths point at these run ids.

## Stage 3: Acceptance tests (roles swapped)
**Goal**: B writes tests, A reviews; arm protected-tests.  
**Success Criteria**: protected list non-empty; tamper check fails closed; red OK.  
**Tests**: `scripts/test_protected_tests.py`. S3 runs `gate_cmd` (same pytest as S5). Each run writes tests under `fixtures/dogfood/tests/acceptance/<run_id>/`.  
**Status**: Implemented. Live dogfood not started.  
**Commands**:
```bash
uv run --with pyyaml scripts/s3_acceptance_loop.py --run-id <id> --stream
uv run --with pyyaml scripts/protected_tests.py --run-id <id> --check
```

## Stage 4: One-task implement
**Goal**: First checkbox → I/A implement → build gate → protected check → commit.  
**Success Criteria**: one commit; protected unchanged; red AT still allowed.  
**Tests**: covered by `scripts/test_e2e_collab.py` with `--skip-commit` (no live implement commit)  
**Status**: Implemented. Live dogfood not started.
**Commands**: `scripts/s4_implement_task.py` (protected check, one commit, `--skip-commit` in the e2e)

## Stage 5: Full gate + branch review
**Goal**: Remaining tasks; workflow-run `gate_cmd`; B branch review loop.  
**Success Criteria**: pytest exit 0 from coordinator; B `approved` with empty blockers.  
**Tests**: e2e reaches this stage with `--skip-gate` (live `gate_cmd` not run on the dogfood)  
**Status**: Implemented. Live dogfood not started.
**Commands**: `scripts/s5_gate_review.py`

## Stage 6: Final + ship
**Goal**: Self-review, final acceptance, `pr-body.md` / optional PR; human merge.  
**Success Criteria**: end-to-end S1–S6 with only spec gate + merge human.  
**Status**: Implemented. Live dogfood not started. Merge stays manual.
**Tests**: `scripts/test_e2e_collab.py` drives S1–S6 from GitHub-shaped comments, including one plan feedback. The e2e skips live agents, git commit, and `gate_cmd`. Feedback on `final_accepted` revises `pr-body.md` and stays there; `/approve` after that asks for a manual merge into `dev`.
**Commands**: `scripts/s6_final.py`

## Stage 7: Modes + retune
**Goal**: Dual Spec / Phased / `human_gate: false` experiments; model swap via YAML only.  
**Success Criteria**: change B model, S1 smoke still works.  
**Tests**: config swap regression  
**Status**: Not Started

## Stage 8: Workflow healer (sidecar)
**Goal**: Permanent healer cron beside issue/PR crons; classify failed/stuck runs; auto-resume flakes; diagnose and optionally auto-fix orch bugs without touching product artifacts.  
**Success Criteria**:
- [x] `config/workflow.yaml` has `healer.*`; server starts healer thread when enabled
- [x] Role `10-workflow-healer.md` + `prompts/healer-orch-fix.md`
- [x] Flake → resume within `max_auto_resume_per_run`; MAX_ROUNDS abort never auto-extended
- [x] Orch bug → diagnosis (+ optional draft fix PR when `orch_fix: auto`)
- [x] Unit tests for classify / budget / forbidden product edits policy
**Tests**: `uv run --with pyyaml scripts/test_healer.py`  
**Status**: Complete  
**Commands**:
```bash
uv run --with pyyaml scripts/healer.py --once
# or via workflow_server (healer cron when healer.enabled)
```

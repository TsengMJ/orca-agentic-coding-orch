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
- [x] human gate: `s1-20261109T081826Z` abort；`s1-20261109T090223Z`（Counter）approve
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
**Tests**: Counter run `s1-20261109T090223Z` — T-01/T-02, review r1 approved. Evidence [`artifacts/runs/s1-20261109T090223Z-s2.md`](artifacts/runs/s1-20261109T090223Z-s2.md)  
**Status**: Complete

## Stage 3: Acceptance tests (roles swapped)
**Goal**: B writes tests, A reviews; arm protected-tests.  
**Success Criteria**: protected list non-empty; tamper check fails closed; red OK.  
**Tests**: integrity check script  
**Status**: Not Started

## Stage 4: One-task implement
**Goal**: First checkbox → I/A implement → build gate → protected check → commit.  
**Success Criteria**: one commit; protected unchanged; red AT still allowed.  
**Tests**: single-task dogfood  
**Status**: Not Started

## Stage 5: Full gate + branch review
**Goal**: Remaining tasks; workflow-run `gate_cmd`; B branch review loop.  
**Success Criteria**: pytest exit 0 from coordinator; B `approved` with empty blockers.  
**Tests**: full remaining plan  
**Status**: Not Started

## Stage 6: Final + ship
**Goal**: Self-review, final acceptance, `pr-body.md` / optional PR; human merge.  
**Success Criteria**: end-to-end S1–S6 with only spec gate + merge human.  
**Tests**: full dogfood request  
**Status**: Not Started

## Stage 7: Modes + retune
**Goal**: Dual Spec / Phased / `human_gate: false` experiments; model swap via YAML only.  
**Success Criteria**: change B model, S1 smoke still works.  
**Tests**: config swap regression  
**Status**: Not Started

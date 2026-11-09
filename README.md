# orca-agentic-coding-orch

Orca-native practice repo for the [adversarial-ai-coding](https://github.com/yhchiu/adversarial-ai-coding) pipeline: A/B slots, structured `verdict.json`, protected acceptance tests, deterministic gates, human checkpoints.

## Defaults (change in config)

Global fallbacks plus per-stage overrides in [`config/workflow.yaml`](config/workflow.yaml) `stage_models` (Free Cursor pool). Same stage never uses one model on both sides.

| Stage | A / I | B |
| --- | --- | --- |
| Spec | `composer-2.5` | `grok-4.6` |
| Plan | `grok-4.6` | `composer-2.5` |
| Acceptance | `grok-4.6` (review) | `composer-2.5` (write tests) |
| Implement | `composer-2.5` (I) | — |
| Gate | `composer-2.5` (I) | `grok-4.7` |
| Final | `composer-2.5` | `grok-4.5` |

```bash
uv run --with pyyaml scripts/resolve_slot.py A --stage spec
uv run --with pyyaml scripts/resolve_slot.py B --stage gate
```

Human gates (AAC-aligned):

- Spec approval on (`human_gate: true`)
- Plan approval off by default (`human_gate_plan: false`)
- Merge stays human (`open_pr` only opens a PR)

Role pack: [`memory/roles/`](memory/roles/README.md) (`agent_team_roles_v1`).

## Stages

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md). **S0 must pass its smoke checklist before S1.**

## Quick smoke (S0)

```bash
# hooks (worker_done wakes)
orca agent hooks status   # cursor: installed

# resolve A/B from config
uv run --with pyyaml scripts/resolve_slot.py A
uv run --with pyyaml scripts/resolve_slot.py B

# dogfood GATE_CMD
uv run --project fixtures/dogfood --group dev pytest -q

# Cursor model smoke (needs network + auth)
./scripts/smoke_slots.sh
```

## GitHub (1 issue = 1 draft PR)

See [`docs/github-collab.md`](docs/github-collab.md). Label an issue `Ready` to enqueue it. Waiting PR labels are `Spec` → `Plan` → `Acceptance` → `Implement` → `Gate`; `/approve` becomes `*_Approved`. `Gate_Approved` merges into `dev`.

```bash
# start once: issue cron + PR cron + healer cron + GET /health
uv run --with pyyaml scripts/workflow_server.py
# healer alone: uv run --with pyyaml scripts/healer.py --once

uv run --with pyyaml scripts/gh_collab.py publish --issue N --run-id <run-id>
uv run --with pyyaml scripts/gh_collab.py check --issue N
uv run --with pyyaml scripts/gh_collab.py apply --issue N --run-id <run-id>
uv run --with pyyaml scripts/gh_collab.py watch
```

`/approve` on the PR advances the stage. `/abort` stops and closes the PR.

## S1 — Spec loop

```bash
# Live observe agent text (--stream). Full guide: docs/dogfood-observe.md
uv run --with pyyaml scripts/s1_spec_loop.py --stream --request "Add a Counter to fixtures/dogfood…"
# after B approved:
uv run --with pyyaml scripts/s1_human_gate.py --run-id <run_id> --approve   # or --abort
```

## S3 — Acceptance tests

B writes tests, A reviews, then the workflow freezes hashes. A failing pytest is allowed.

```bash
uv run --with pyyaml scripts/s3_acceptance_loop.py --stream --run-id <run_id>
uv run --with pyyaml scripts/protected_tests.py --run-id <run_id> --check
```

Review/repair contract: [`docs/review-loop.md`](docs/review-loop.md) (AAC `MAX_ROUNDS`, same-call agent retries, abort+resume — **no unbounded review**).

```bash
# Resume within the same max_rounds budget after agent abort:
uv run --with pyyaml scripts/s1_resume_review.py --run-id <id>
# Intentionally raise cap (rare):
AAC_MAX_ROUNDS=5 uv run --with pyyaml scripts/s1_resume_review.py --run-id <id> --allow-raise-max-rounds
```

## References

- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/how-it-works.md
- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/artifact-contract.md
- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/gates.md

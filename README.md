# orca-agentic-coding-orch

Orca-native practice repo for the [adversarial-ai-coding](https://github.com/yhchiu/adversarial-ai-coding) pipeline: A/B slots, structured `verdict.json`, protected acceptance tests, deterministic gates, human checkpoints.

## Defaults (change in config)

| Slot | Role | Runtime | Model |
| --- | --- | --- | --- |
| A | owner | Cursor | `grok-4.7-high` |
| B | reviewer | Cursor | `composer-2.5` |
| I | implementer | inherits A | — |

Source of truth: [`config/workflow.yaml`](config/workflow.yaml) (created in S0). Swap models/gates there; do not hardcode in prompts.

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

## S1 — Spec loop

```bash
# Live observe agent text (--stream). Full guide: docs/dogfood-observe.md
uv run --with pyyaml scripts/s1_spec_loop.py --stream --request "Add a Counter to fixtures/dogfood…"
# after B approved:
uv run --with pyyaml scripts/s1_human_gate.py --run-id <run_id> --approve   # or --abort
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

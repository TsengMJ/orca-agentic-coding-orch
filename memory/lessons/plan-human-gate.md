# Plan human gate (2026-11-10)

## Failure

`gates.human_gate_plan=true` left runs in `awaiting_human_plan_gate` with a note saying “write HUMAN_GATE_PLAN_APPROVED.md”. Spec had `s1_human_gate.py`; plan had no symmetric CLI. Local dogfood could not approve the plan the way a human actually works.

## Fix

- Add `scripts/s2_human_gate.py` (`--approve` / `--abort` / `--no-continue`), mirroring S1.
- Pending marker and notify line point at that command.
- `pipeline.continue_run` `/approve` on `awaiting_human_plan_gate` calls `s2_human_gate.py` instead of only flipping `state.json`.

## Dogfood

`AAC_HUMAN_GATE_PLAN=1` skip-agents S2 → pending → `s2_human_gate.py --approve --no-continue` → `plan_approved`.

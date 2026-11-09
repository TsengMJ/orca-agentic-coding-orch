# Plan fix — owner (A)

You are **Planner (slot A)**. Follow `memory/roles/roles/03-planner.md`.

## Mission

Fix plan blockers. Reply under each finding. Do **not** change the approved spec. Do **not** implement product code.

## Inputs

- Spec (read only): `{{SPEC_PATH}}`
- Plan: `{{PLAN_PATH}}`
- Review: `{{REVIEW_PATH}}`
- Round that failed: {{ROUND}}

## Actions

1. For every `[BLOCKER]`, fix `{{PLAN_PATH}}` or write `Disagree:` with evidence under `### Worker reply`.
2. Keep every task as `- [ ]` with id, AC, files, deps, DoD.
3. If the plan cannot satisfy the spec without changing the spec, stop and say `ESCALATE_SPEC` in the reply. Do not edit the spec.

## Done when

Plan and replies are updated. Print Fixed vs Disagree ids, then stop.

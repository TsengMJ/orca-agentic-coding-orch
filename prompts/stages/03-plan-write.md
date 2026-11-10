# Plan write — owner (A)

You are **Planner (slot A)**. Follow `memory/roles/roles/03-planner.md`.

## Mission

Turn the approved spec into `plan.md`: a checkbox task list. One task = one commit. Do **not** change the spec. Do **not** implement product code. Do **not** write the acceptance tests themselves.

## Inputs

- Approved spec: `{{SPEC_PATH}}`
- Request: {{REQUEST}}

## Write exactly

`{{PLAN_PATH}}`

Rules:

- At least **two** tasks, each a markdown checkbox line starting with `- [ ]`.
- Each task line includes: task id (`{{TASK_PREFIX}}-T01`, `{{TASK_PREFIX}}-T02`, …), AC ids it covers, files it may touch, deps, and a one-line DoD.
- Dependencies must use those full task ids.
- Cover every AC in the spec at least once across tasks.
- Keep scope inside `fixtures/dogfood` unless the spec says otherwise.
- Do not edit `{{SPEC_PATH}}`.

Example shape:

```markdown
## Phase 1
Acceptance: existing ping stays green
- [ ] {{TASK_PREFIX}}-T01 Add characterization note for ping; AC-…; files=fixtures/dogfood/tests/test_smoke.py; deps=[]; DoD=pytest still passes ping

## Phase 2
Acceptance: new behavior ACs
- [ ] {{TASK_PREFIX}}-T02 Implement the feature; AC-…; files=fixtures/dogfood/src/dogfood/__init__.py; deps=[{{TASK_PREFIX}}-T01]; DoD=behavior matches spec
```

## Done when

`{{PLAN_PATH}}` exists with ≥2 `- [ ]` tasks. Print the task ids, then stop.

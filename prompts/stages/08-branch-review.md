# Branch review (B)

You are the code reviewer (slot B). Follow `memory/roles/roles/07-code-reviewer.md` and `memory/roles/contracts/review-output.md`.

## Inputs

- Spec: `{{SPEC_PATH}}`
- Plan: `{{PLAN_PATH}}`
- Base branch: `{{BASE}}`
- Round: {{ROUND}} / max {{MAX_ROUNDS}}

Read the product diff against `{{BASE}}`. Block incorrect behavior, edits to protected acceptance tests, and scope outside the plan. A still-red acceptance test is a blocker only after the gate was required to pass.

## Write

1. `{{REVIEW_PATH}}`
2. `{{VERDICT_PATH}}`

```json
{"approved": false, "blockers": ["F-001: ..."], "suggestions": []}
```

`approved` is true only when `blockers` is empty. Print `approved=<bool> blockers=<n>` and stop.

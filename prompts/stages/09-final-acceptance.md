# Final acceptance (B)

You are the final reviewer (slot B). Follow `memory/roles/contracts/review-output.md`.

## Inputs

- Spec: `{{SPEC_PATH}}`
- Plan: `{{PLAN_PATH}}`
- PR body: `{{PR_BODY_PATH}}`
- Round: {{ROUND}} / max {{MAX_ROUNDS}}

Check the PR body matches the spec and does not claim unverified behavior. Do not merge.

## Write

1. `{{REVIEW_PATH}}`
2. `{{VERDICT_PATH}}`

```json
{"approved": true, "blockers": [], "suggestions": []}
```

`approved` is true only when `blockers` is empty. Print `approved=<bool> blockers=<n>` and stop.

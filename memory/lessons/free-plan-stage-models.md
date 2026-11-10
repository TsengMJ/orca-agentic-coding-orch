# Free-plan stage models (2026-03-22)

Cursor Free only has Grok 4.7 / 4.6 / 4.5 and Composer 2.5.

- Same stage: A/B must differ; prefer `composer` ↔ `grok-*`.
- Save `grok-4.7` for S5 branch review (B). Do not burn it on S1 owner.
- Spec owner: `composer-2.5` (shorter contracts). Spec reviewer: `grok-4.6`.
- Implement / write tests: Composer. Review contracts/tests: Grok.
- Config: `config/workflow.yaml` → `stage_models`; resolve with `scripts/resolve_slot.py A --stage spec`.

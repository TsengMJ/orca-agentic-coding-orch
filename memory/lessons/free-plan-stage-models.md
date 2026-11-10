# Free-plan stage models

Cursor Free only has Grok 4.7 / 4.6 / 4.5 and Composer 2.5.

- Same stage: A/B must differ; prefer `composer` ↔ `grok-*`.
- Implement / write tests: Composer. Review / contract sides: Grok.
- Config: `config/workflow.yaml` → `stage_models`; resolve with `scripts/resolve_slot.py A --stage spec`.

## 2026-11-10 trial

After the agent end-signal fix, try **`grok-4.7` for every grok slot** (spec B, plan A, acceptance A, gate B, final B; default slot B). Revert per-stage if a role misbehaves; do not paper over with longer timeouts.

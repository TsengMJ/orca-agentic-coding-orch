# Workflow healer (2026-11-09)

- `workflow_server` alone is not a coordinator: it only polls issues/PRs. Failures used to sit in `aborted_agent_failure` / `publish_failed` until a human noticed.
- Healer is a **sidecar cron** (`scripts/healer.py`), not a replacement for Role 00. It may resume flakes and propose orch fixes; it must not edit product artifacts or raise `max_rounds`.
- Dogfood lesson still stands: hand-editing `spec.md` after an owner hang violates AAC. Healer must resume or escalate, never patch the spec itself.

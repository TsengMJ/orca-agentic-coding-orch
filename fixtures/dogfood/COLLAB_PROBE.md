# Collab invariants dogfood probe

Live verification that AAC orchestrator cron and stage-end GitHub collaboration notes behave as expected on this run.

## AC-01 — Orchestrator progress notes on Issue #8

**Acceptance criterion:** Issue #8 receives orchestrator progress notes before and/or after draft PR publish.

For this dogfood run, Issue #8 is the live tracking issue. The orchestrator posts progress notes to that issue (and linked draft PR conversation) on the scheduled collab cron and at stage boundaries. Notes may appear immediately before draft PR publish, after publish, or in both windows—the invariant is that progress is visible around draft PR publish, not silence across that event.

This file is documentary only; it does not change the dogfood product API (`ping`, `add`, `echo_id`, `Counter`, `__version__`).

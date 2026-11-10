# Collab invariants dogfood probe

Live verification that AAC orchestrator cron and stage-end GitHub collaboration notes behave as expected on this run.

## AC-01 — Orchestrator progress notes on Issue #8

**Acceptance criterion:** Issue #8 receives orchestrator progress notes before and/or after draft PR publish.

For this dogfood run, Issue #8 is the live tracking issue. The orchestrator posts progress notes to that issue (and linked draft PR conversation) on the scheduled collab cron and at stage boundaries. Notes may appear immediately before draft PR publish, after publish, or in both windows—the invariant is that progress is visible around draft PR publish, not silence across that event.

## AC-02 — Draft PR on the configured product repo

**Acceptance criterion:** Draft PR opens on `TsengMJ/orca-agentic-coding-orch` (the product repo configured for this run), not a wrong host.

For this dogfood run, the product repository is `TsengMJ/orca-agentic-coding-orch`—the same checkout as the orch self-dogfood probe, not a stray tooling fork or alternate GitHub host. When the run publishes a draft pull request, that draft PR must target this product repo. Opening the draft PR on any other owner or repository would violate AC-02.

## AC-03 — Stage failure and Tech Lead `failed` note

**Acceptance criterion:** Stage failure path can post a Tech Lead `failed` note to the PR/Issue.

If a pipeline stage fails after a draft PR is in play, the failure handling path may post a Tech Lead `failed` note to the draft pull request and/or Issue #8 (the live tracking issue). The note signals that the stage did not complete successfully; the invariant is that collaboration can surface failure on the same PR or Issue thread where progress was already being posted, rather than leaving the run silent on failure.

This file is documentary only; it does not change the dogfood product API (`ping`, `add`, `echo_id`, `Counter`, `__version__`).

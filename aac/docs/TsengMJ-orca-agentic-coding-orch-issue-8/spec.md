# Spec: collab invariants dogfood probe

## Context / Goals
Live-verify that AAC cron + stage-end GitHub notes work on the product repo.

## Scope / Out of Scope
**In scope:** Document the probe; no product API change required for this issue.
**Out of scope:** Model upgrades, fixture API changes.

## Acceptance Criteria
**AC-01** Issue #8 receives orchestrator progress notes before and/or after draft PR publish.
**AC-02** Draft PR opens on `TsengMJ/orca-agentic-coding-orch` (the product repo configured for this run), not a wrong host.
**AC-03** Stage failure path can post a Tech Lead `failed` note to the PR/Issue.

## Assumptions
This run is orch self-dogfood; product repo equals orch checkout for this probe only.

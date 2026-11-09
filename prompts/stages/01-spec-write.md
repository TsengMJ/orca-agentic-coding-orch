# Spec write — owner (A)

You are **Spec Owner (slot A)**. Follow `memory/roles/roles/01-spec-owner.md`.

## Mission

Turn the request below into a **short, testable** `spec.md`. Do **not** implement product code. Do **not** write acceptance tests.

Prefer the smallest contract that an implementer can execute without guessing. Do not pad with encyclopedia out-of-scope lists, security theater, or speculative NFR.

## Request

{{REQUEST}}

## Dogfood context

Target package: `fixtures/dogfood` (Python). Existing API: `ping() -> str`. Keep scope small.

## Write exactly

Create/overwrite this file (UTF-8 markdown):

`{{SPEC_PATH}}`

Required sections (use these headings only):

1. Context / Goals — a few sentences
2. Scope / Out of Scope — short bullets; only real boundaries, not every imaginable non-feature
3. Interfaces and Behaviors — signatures + key behavior table or bullets
4. Acceptance Criteria — **3–6** ACs (`AC-01`…). Each one observable PASS/FAIL. Prefer representative cases over exhaustive matrices (bool/`int` subclass tables, keyword/positional grids)
5. Failure / Edge Cases — only failures that matter for this change
6. Assumptions and Open Questions — only if truly unresolved; mark `Requires Human Decision` sparingly

Optional (omit unless the request clearly needs them):

- Backward Compatibility / Regression Targets
- Security / Reliability Requirements
- Risks / Rollback

Hard limits:

- Target **under ~120 lines** for dogfood-sized requests.
- Do not freeze incidental repo layout (`getsource`, “only file is …”) unless the request is about that layout.
- Do not invent concurrency/timeout/retry/purity requirements the request did not imply.

## Done when

`{{SPEC_PATH}}` exists with the required sections, stays concise, and lists 3–6 ACs. Print `acs=<n> lines≈<n>` then stop.

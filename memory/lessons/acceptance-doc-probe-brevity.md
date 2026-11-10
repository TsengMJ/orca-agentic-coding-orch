# Acceptance tests for doc probes (2026-11-10)

## Failure

Collab-invariants dogfood (PR #9) burned S3 `MAX_ROUNDS=3` under `grok-4.7` review on a **documentation probe**. Blockers chased optional-regex holes (`failed comment` vs `failed note`) instead of product behavior.

## Guidance

- Doc-only ACs: prefer a few substring / presence checks, not multi-alternative destination regexes.
- Reviewer (especially Grok 4.7): one blocker theme; do not invent new regex attack surface each round.
- After `aborted_max_rounds`, human/self-iter may patch the cited test and **resume review-only** (do not rewrite the whole suite from S3 write).

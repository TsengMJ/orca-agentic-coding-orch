# Self-iteration dogfood (2026-11-10)

Goal mode for this repo: harden the orchestrator until bulk development of *other* projects is boringly reliable.

## Branch sync (part of the goal)

Work may happen on the `goal` branch, but **landing is always remote `dev`**:

1. Orchestrator fixes found while self-iterating → merge/push to **`origin/dev`**.
2. Dogfood product changes (e.g. `fixtures/dogfood`) from the same loop → also merge/push to **`origin/dev`**.
3. Keep the `goal` branch **continuously based on the latest `origin/dev`** (merge or rebase from `dev` before/after landing) so orch fixes and dogfood stay one timeline.
4. Do not leave lasting fixes only on `goal` / local worktrees; `local/<run_id>` is a temporary commit path, not the sync source of truth.

This keeps self-iteration and dogfood synchronized for the next run.

## Operating loop

1. When something fails (timeout, hung gate, wrong approve path), ask **why** before patching symptoms.
2. Prefer protocol/OS end conditions over model-cooperative fields.
3. Prove the fix with a unit test *and* a live dogfood pass through the same stage.
4. While dogfooding, **act as the human**: read the artifact, run `s1_human_gate.py --approve` / `--abort`, and check `state.json` + evidence files.
5. Record each recurrence-class failure under `memory/lessons/` with root cause + regression pointer.
6. After a batch of fixes/dogfood, land on `origin/dev` and refresh `goal` from that `dev`.

## First pass this session

- Fixed agent completion: `stream-json` `result` instead of `AAC_AGENT_DONE` prompt field (`agent-end-signal.md`).
- Live run `s1-20261110T020528Z` exercised end-of-call `result` through S1→S4 (no 480s hangs):
  - S1 ~114s → human gate → I approved with `s1_human_gate.py --approve --no-continue`
  - S2 ~115s, S3 ~139s (RED acceptance allowed), S4 T01+T02 ~20s each with `--skip-commit`
  - Acceptance suite: 11 passed after implement
- Also dogfooded: human `--abort` then re-`--approve` (`reopened_after_abort=true`); healer classifies `timed out after 480s` as `flake` and resumes within budget.
- Fixed stream silence during tools (`stream-tool-progress.md`).
- Local commit fallback without `github.json` (`local-commit-fallback.md`); live commit on `local/s1-20261110T020528Z`.
- Plan human gate CLI (`plan-human-gate.md` / `s2_human_gate.py`); dogfooded approve.
- E2E merge no longer calls `gh` before stub (`e2e-merge-before-gh.md`).
- Landed orch+dogfood batch on `origin/dev` at `4f94278`; `goal` fast-forwarded to match.
- Collaboration invariants locked in: cron signals, stage-end PR updates (incl. failure), product-repo PRs (`collab-invariants.md`).
- Open follow-ups: `gh auth login` then live Issue→PR `/approve` dogfood; workflow_server cron against a real draft. Keep landing batches on `origin/dev`.
- **Queued (do not start yet):** after current collab/`gh` blockers are cleared, try `grok-4.7` for every stage that currently uses grok (end-signal fix already landed).

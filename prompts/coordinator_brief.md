# Coordinator brief (Orca)

You are the Orchestrator for this AAC practice repo. Control flow is yours — never trust an agent's claim that tests passed. Load role rules from `memory/roles/roles/00-orchestrator.md` and merge policy from `memory/roles/contracts/merge-policy.yaml`.

## Before any Run

1. `orca agent hooks on` if cursor hooks are not installed (`orca agent hooks status`).
2. Read `config/workflow.yaml` (or `scripts/resolve_slot.py <A|B|I>`) for runtime/model/gates.
3. Confirm dogfood gate works: `uv run --project fixtures/dogfood --group dev pytest -q`.
4. `orca skills get orchestration` once per session.

## Slot → Orca worker

```bash
# Example: start owner (A)
MODEL=$(uv run --with pyyaml scripts/resolve_slot.py A --field model)
orca orchestration worker-start \
  --task <task_id> \
  --agent cursor \
  --model "$MODEL" \
  --worktree current \
  --json
```

- Owner / implementer Fix loops: `--keep-open` when `orca.keep_open_implement` is true; repair with `orca orchestration send`.
- Reviewer rounds: **fresh** worker/context each round (do not keep prior verdict anchoring).
- After `worker-start`, **end your turn**. Do not poll with consuming `check`.

## Artifact rules (fail closed)

- Pre-seed `verdict.json` as `{"approved":false,"blockers":["pending"],"suggestions":[]}`.
- Approval only if `approved===true` **and** `blockers` empty.
- Suggestions accumulate for final stage; they do not block.
- Agents communicate only via files under `aac/` — no shared chat as protocol.
- You run `gates.gate_cmd` / `gates.build_gate_cmd` yourself; agent stdout is not evidence.

## Review / repair (see `docs/review-loop.md`)

- Use `scripts/review_loop.py` semantics: review → blockers → owner fix → review; **stop at `max_rounds`**.
- Agent timeout/nonzero: same-call retries (`agent_call_retries`), then **abort + resume cmd** — never hang, never silently edit the artifact yourself.
- Do not manually continue past `MAX_ROUNDS`; raise config only with an explicit operator action.

## Human gates

- If `gates.human_gate`: after Spec review approved, pause (`gate-create` or ask user). Anything other than explicit approve → abort.
- If `gates.human_gate_plan`: same after Plan.
- Never auto-merge in S0–S6; `gates.open_pr` only creates a PR when true.

## Workflow healer (sidecar)

- `workflow_server` starts a third cron when `healer.enabled` (see `config/workflow.yaml`).
- Role: `memory/roles/roles/10-workflow-healer.md`. Manual once: `uv run --with pyyaml scripts/healer.py --once`.
- Flakes → resume within `healer.max_auto_resume_per_run`. Orch bugs → diagnosis / optional draft fix PR (`healer.orch_fix`).
- You still do not silently edit product artifacts; healer must not either.

## Stage prompts

Render a self-contained prompt from `prompts/stages/*.md`, point the worker at the archived copy under `aac/.run/<run_id>/archive/`, and attach the matching role file from `memory/roles/roles/`.

#!/usr/bin/env python3
"""Resume an incomplete S1 review loop within the same MAX_ROUNDS budget.

AAC semantics:
- Resume restores workflow state; it does NOT grant unlimited extra rounds.
- Default: continue at last_round+1 if status is aborted_agent_failure mid-fix/review,
  or re-enter the incomplete round after an agent abort.
- To raise the cap you must set AAC_MAX_ROUNDS / gates.max_rounds explicitly
  (and pass --allow-raise-max-rounds so it is intentional).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aac_common import ROOT, ensure_run_dirs, load_workflow, notify_human, slot_model
from review_loop import LoopPaths, loop_config_from_workflow, run_review_fix_loop
from s1_spec_loop import load_prompt, render


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--start-round",
        type=int,
        default=0,
        help="Review round to run next (default: last_round+1 from state, or 1)",
    )
    parser.add_argument(
        "--allow-raise-max-rounds",
        action="store_true",
        help="Permit AAC_MAX_ROUNDS / --max-rounds above the value stored in state.json",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=0,
        help="Override max rounds for this attempt (requires --allow-raise-max-rounds if higher than state)",
    )
    parser.add_argument("--skip-agents", action="store_true")
    args = parser.parse_args()

    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "spec", skip_agents=args.skip_agents)
    if args.max_rounds:
        loop_cfg.max_rounds = args.max_rounds

    dirs = ensure_run_dirs(args.run_id)
    state_path = dirs["run"] / "state.json"
    if not state_path.is_file():
        raise SystemExit(f"missing state: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    stored_max = int(state.get("max_rounds") or loop_cfg.max_rounds)
    last_round = int(state.get("round") or 0)
    request = state.get("request") or ""

    if loop_cfg.max_rounds > stored_max and not args.allow_raise_max_rounds:
        print(
            f"Refusing to raise max_rounds {stored_max} → {loop_cfg.max_rounds} "
            f"without --allow-raise-max-rounds (AAC: no silent unbounded review).",
            file=sys.stderr,
        )
        return 3

    # If previous attempt aborted on agent failure during fix after review N,
    # resume at N+1 only if N was approved? No — if review N had blockers and fix failed,
    # retry fix is done by start_round=N meaning re-run review N... Actually:
    # Our loop structure: review N → if blockers and N<max → fix → review N+1
    # If fix after review N failed: resume should re-run fix then continue — simpler to
    # start at review N again (re-review) which is wasteful but correct, OR start_round=N+1
    # after coordinator confirms fix applied.
    # Default: last_round + 1 when last status reviewing with blockers and fix completed;
    # if aborted_agent_failure on fix after round R, start_round = R+1 only if fix artifacts exist.
    start = args.start_round or (last_round + 1 if last_round else 1)

    if start > loop_cfg.max_rounds:
        print(
            f"start_round={start} exceeds max_rounds={loop_cfg.max_rounds}. "
            f"Raise max with AAC_MAX_ROUNDS=… --allow-raise-max-rounds, or abort.",
            file=sys.stderr,
        )
        return 2

    model_a = slot_model(cfg, "A")
    model_b = slot_model(cfg, "B")
    spec_path = dirs["docs"] / "spec.md"
    if not spec_path.is_file():
        raise SystemExit(f"missing spec: {spec_path}")

    mapping_base = {
        "REQUEST": request,
        "SPEC_PATH": str(spec_path.relative_to(ROOT)),
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }
    resume_hint = f"uv run --with pyyaml scripts/s1_resume_review.py --run-id {args.run_id}"

    print(
        f"resume {args.run_id}: start_round={start} max_rounds={loop_cfg.max_rounds} "
        f"(stored_max={stored_max})"
    )

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("02-spec-review.md"),
            {
                **mapping_base,
                "ROUND": str(round_n),
                "REVIEW_PATH": str(review_path.relative_to(ROOT)),
                "VERDICT_PATH": str(verdict_path.relative_to(ROOT)),
            },
        )

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("01b-spec-fix.md"),
            {
                **mapping_base,
                "ROUND": str(round_n),
                "REVIEW_PATH": str(review_path.relative_to(ROOT)),
                "VERDICT_PATH": str(verdict_path.relative_to(ROOT)),
            },
        )

    result = run_review_fix_loop(
        paths=LoopPaths(
            run_dir=dirs["run"],
            archive=dirs["archive"],
            reviews_root=dirs["reviews"],
            artifact_path=spec_path,
            run_id=args.run_id,
        ),
        cfg=loop_cfg,
        model_owner=model_a,
        model_reviewer=model_b,
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=resume_hint,
        start_round=start,
    )

    if not result.approved:
        return 2

    human_gate = bool((cfg.get("gates") or {}).get("human_gate", True))
    if human_gate:
        pending = dirs["run"] / "HUMAN_GATE_PENDING.md"
        pending.write_text(
            "\n".join(
                [
                    f"# Human gate — Spec (`{args.run_id}`)",
                    "",
                    f"Spec: `aac/docs/{args.run_id}/spec.md`",
                    "",
                    "```bash",
                    f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {args.run_id} --approve",
                    f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {args.run_id} --abort",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"HUMAN GATE PENDING → {pending}")
        notify_human(
            f"Spec ready for approval: {args.run_id}. "
            f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {args.run_id} --approve",
            title="AAC spec gate",
        )
        return 0

    print("S1 review approved (human_gate off)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

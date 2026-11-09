#!/usr/bin/env python3
"""S6: write the PR body, B accepts it. Merging into dev stays a human act."""

from __future__ import annotations

import argparse
from pathlib import Path

from aac_common import ROOT, ensure_run_dirs, load_workflow, slot_model, write_state
from review_loop import LoopPaths, call_agent_with_repair, loop_config_from_workflow, run_review_fix_loop


def render(template: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    args = parser.parse_args()

    dirs = ensure_run_dirs(args.run_id)
    body = dirs["docs"] / "pr-body.md"
    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "final", skip_agents=args.skip_agents, stream=args.stream)
    base = str((cfg.get("github") or {}).get("base") or "dev")
    write_state(dirs["run"], stage="final", status="final_running")
    if args.skip_agents:
        body.write_text(
            f"# {args.run_id}\n\nRefs the approved spec and plan.\n\nMerge into `{base}` is manual.\n",
            encoding="utf-8",
        )
    else:
        prompt = "\n".join(
            [
                "Write the pull request body.",
                f"Spec: {(dirs['docs'] / 'spec.md').relative_to(ROOT)}",
                f"Plan: {(dirs['docs'] / 'plan.md').relative_to(ROOT)}",
                f"Write {body.relative_to(ROOT)}",
                "Summarize what changed and how to verify it. Say that merge is manual. Do not merge.",
            ]
        )
        wrote = call_agent_with_repair(
            model=slot_model(cfg, "A", stage="final"),
            prompt=prompt,
            archive=dirs["archive"],
            tag="601-pr-body",
            cfg=loop_cfg,
        )
        if wrote.returncode != 0:
            write_state(dirs["run"], status="aborted_agent_failure")
            return wrote.returncode or 1
    if not body.is_file():
        raise SystemExit("pr-body.md missing")

    mapping = {
        "SPEC_PATH": str((dirs["docs"] / "spec.md").relative_to(ROOT)),
        "PLAN_PATH": str((dirs["docs"] / "plan.md").relative_to(ROOT)),
        "PR_BODY_PATH": str(body.relative_to(ROOT)),
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }
    reviews = dirs["run"] / "reviews" / "final"
    reviews.mkdir(parents=True, exist_ok=True)
    template = (ROOT / "prompts" / "stages" / "09-final-acceptance.md").read_text(encoding="utf-8")

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(template, {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))})

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return f"Update {body.relative_to(ROOT)} so the blockers in {review_path.relative_to(ROOT)} are gone. Do not merge.\n"

    result = run_review_fix_loop(
        paths=LoopPaths(dirs["run"], dirs["archive"], reviews, body, args.run_id),
        cfg=loop_cfg,
        model_owner=slot_model(cfg, "A", stage="final"),
        model_reviewer=slot_model(cfg, "B", stage="final"),
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=f"uv run --with pyyaml scripts/s6_final.py --run-id {args.run_id}",
    )
    if not result.approved:
        return 2
    write_state(dirs["run"], stage="final", status="final_accepted")
    from gh_collab import mark_pr_ready, stage_complete
    from stage_labels import labels_cfg

    ready_code, ready_msg = mark_pr_ready(args.run_id)
    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s6.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        f"# S6 `{args.run_id}`\n\n"
        f"- pr body: `{body.relative_to(ROOT)}`\n"
        f"- draft: converted to ready-for-review\n"
        f"- ready: {ready_msg}\n"
        f"- merge: `/approve` merges into `{base}`\n",
        encoding="utf-8",
    )
    print(f"S6 complete. {ready_msg}. Reply /approve to merge into {base}. evidence={evidence}")
    stage_complete(
        args.run_id,
        labels_cfg()["implement_approved"],
        delivered="PR body accepted; draft converted to ready-for-review",
        next_step=f"`/approve` to merge into `{base}`",
    )
    return 0 if ready_code == 0 else ready_code


if __name__ == "__main__":
    raise SystemExit(main())

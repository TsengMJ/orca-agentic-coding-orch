#!/usr/bin/env python3
"""S5: finish remaining tasks, run gate_cmd, then B reviews the branch."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from aac_common import ROOT, ensure_run_dirs, load_workflow, slot_model, write_state
from protected_tests import check
from review_loop import LoopPaths, call_agent_with_repair, loop_config_from_workflow, run_review_fix_loop
from tasks import mark_done, parse_tasks
from worktree_commit import commit_paths


def render(template: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    parser.add_argument("--skip-commit", action="store_true")
    parser.add_argument("--skip-gate", action="store_true")
    args = parser.parse_args()

    dirs = ensure_run_dirs(args.run_id)
    plan_path = dirs["docs"] / "plan.md"
    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "branch", skip_agents=args.skip_agents, stream=args.stream)
    base = str((cfg.get("github") or {}).get("base") or "dev")
    prompt_template = (ROOT / "prompts" / "stages" / "07-implement-task.md").read_text(encoding="utf-8")

    while True:
        open_tasks = [task for task in parse_tasks(plan_path.read_text(encoding="utf-8"), args.run_id) if not task["done"]]
        if not open_tasks:
            break
        task = open_tasks[0]
        print(f"S5 task {task['id']}")
        write_state(dirs["run"], stage="implement", status="implementing", current_task=task["id"])
        if not args.skip_agents:
            prompt = render(
                prompt_template,
                {
                    "TASK_ID": task["id"],
                    "TASK_LINE": task["line"],
                    "SPEC_PATH": str((dirs["docs"] / "spec.md").relative_to(ROOT)),
                    "PLAN_PATH": str(plan_path.relative_to(ROOT)),
                },
            )
            result = call_agent_with_repair(
                model=slot_model(cfg, "I", stage="gate"),
                prompt=prompt,
                archive=dirs["archive"],
                tag=f"501-implement-{task['id']}",
                cfg=loop_cfg,
            )
            if result.returncode != 0:
                write_state(dirs["run"], status="aborted_agent_failure")
                return result.returncode or 1
        problems = check(args.run_id)
        if problems:
            print(f"FAIL protected tests: {problems}", file=sys.stderr)
            write_state(dirs["run"], status="failed", error="protected-tests-changed")
            return 2
        plan_path.write_text(mark_done(plan_path.read_text(encoding="utf-8"), args.run_id, task["id"]), encoding="utf-8")
        if not args.skip_commit:
            commit_paths(args.run_id, task["files"] or ["fixtures/dogfood/src/dogfood/__init__.py"], f"Implement {task['id']}.")

    if not args.skip_gate:
        gate = str((cfg.get("gates") or {}).get("gate_cmd") or "").strip()
        if not gate:
            raise SystemExit("gate_cmd is empty")
        env = {**__import__("os").environ, "AAC_RUN_ID": args.run_id}
        ran = subprocess.run(["sh", "-c", gate], cwd=ROOT, check=False, env=env)
        if ran.returncode != 0:
            write_state(dirs["run"], status="failed", error="gate-cmd")
            print("FAIL gate_cmd", file=sys.stderr)
            return ran.returncode or 1
        print("gate_cmd passed")

    mapping = {
        "SPEC_PATH": str((dirs["docs"] / "spec.md").relative_to(ROOT)),
        "PLAN_PATH": str(plan_path.relative_to(ROOT)),
        "BASE": base,
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }
    reviews = dirs["run"] / "reviews" / "branch"
    reviews.mkdir(parents=True, exist_ok=True)

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            (ROOT / "prompts" / "stages" / "08-branch-review.md").read_text(encoding="utf-8"),
            {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))},
        )

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            prompt_template,
            {
                "TASK_ID": f"review-fix-r{round_n}",
                "TASK_LINE": f"Address blockers in {review_path.relative_to(ROOT)}",
                "SPEC_PATH": mapping["SPEC_PATH"],
                "PLAN_PATH": mapping["PLAN_PATH"],
            },
        )

    result = run_review_fix_loop(
        paths=LoopPaths(dirs["run"], dirs["archive"], reviews, plan_path, args.run_id),
        cfg=loop_cfg,
        model_owner=slot_model(cfg, "I", stage="gate"),
        model_reviewer=slot_model(cfg, "B", stage="gate"),
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=f"uv run --with pyyaml scripts/s5_gate_review.py --run-id {args.run_id}",
    )
    if not result.approved:
        return 2
    write_state(dirs["run"], stage="branch", status="branch_review_approved")
    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s5.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        f"# S5 `{args.run_id}`\n\n- gate_cmd: passed\n- branch review rounds: {result.rounds_used}\n- merge: human, into `{base}`\n",
        encoding="utf-8",
    )
    print(f"S5 complete. evidence={evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

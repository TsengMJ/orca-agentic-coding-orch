#!/usr/bin/env python3
"""S4: implement the first open plan task, check protected tests, commit that task."""

from __future__ import annotations

import argparse
import subprocess
import sys

from aac_common import ROOT, ensure_run_dirs, load_workflow, slot_model, write_state
from protected_tests import check
from review_loop import call_agent_with_repair, loop_config_from_workflow
from tasks import mark_done, parse_tasks
from worktree_commit import commit_paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    parser.add_argument("--skip-commit", action="store_true")
    args = parser.parse_args()

    dirs = ensure_run_dirs(args.run_id)
    plan_path = dirs["docs"] / "plan.md"
    if not plan_path.is_file():
        raise SystemExit("missing plan")
    tasks = [task for task in parse_tasks(plan_path.read_text(encoding="utf-8"), args.run_id) if not task["done"]]
    if not tasks:
        print("no open task")
        return 1
    task = tasks[0]
    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "implement", skip_agents=args.skip_agents, stream=args.stream)
    write_state(dirs["run"], stage="implement", status="implementing", current_task=task["id"])
    print(f"S4 task {task['id']}")
    if not args.skip_agents:
        prompt = (ROOT / "prompts" / "stages" / "07-implement-task.md").read_text(encoding="utf-8")
        prompt = (
            prompt.replace("{{TASK_ID}}", task["id"])
            .replace("{{TASK_LINE}}", task["line"])
            .replace("{{SPEC_PATH}}", str((dirs["docs"] / "spec.md").relative_to(ROOT)))
            .replace("{{PLAN_PATH}}", str(plan_path.relative_to(ROOT)))
        )
        result = call_agent_with_repair(
            model=slot_model(cfg, "I", stage="implement"),
            prompt=prompt,
            archive=dirs["archive"],
            tag="401-implement",
            cfg=loop_cfg,
        )
        if result.returncode != 0:
            write_state(dirs["run"], status="aborted_agent_failure")
            from gh_collab import stage_failed

            stage_failed(
                args.run_id,
                stage="Implement",
                error=f"implement agent failed rc={result.returncode}",
            )
            return result.returncode or 1

    problems = check(args.run_id)
    if problems:
        write_state(dirs["run"], status="failed", error="protected-tests-changed")
        print("FAIL protected tests changed", file=sys.stderr)
        for item in problems:
            print(f"- {item}", file=sys.stderr)
        from gh_collab import stage_failed

        stage_failed(
            args.run_id,
            stage="Implement",
            error="protected acceptance tests were modified",
        )
        return 2

    build = str((cfg.get("gates") or {}).get("build_gate_cmd") or "").strip()
    if build:
        built = subprocess.run(["sh", "-c", build], cwd=ROOT, check=False)
        if built.returncode != 0:
            write_state(dirs["run"], status="failed", error="build-gate")
            from gh_collab import stage_failed

            stage_failed(args.run_id, stage="Implement", error="build_gate_cmd failed")
            return built.returncode or 1

    plan_path.write_text(mark_done(plan_path.read_text(encoding="utf-8"), args.run_id, task["id"]), encoding="utf-8")
    if not args.skip_commit:
        commit_paths(args.run_id, task["files"] or ["fixtures/dogfood/src/dogfood/__init__.py"], f"Implement {task['id']}.")
    write_state(dirs["run"], status="task_committed", current_task=task["id"])
    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s4.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(f"# S4 `{args.run_id}`\n\n- task: {task['id']}\n- protected: unchanged\n", encoding="utf-8")
    print(f"S4 committed {task['id']}")
    from gh_collab import stage_complete
    from stage_labels import labels_cfg

    stage_complete(
        args.run_id,
        labels_cfg()["acceptance_approved"],
        delivered=f"Task `{task['id']}` committed",
        next_step="`/approve` to run the gate and branch review",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

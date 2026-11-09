#!/usr/bin/env python3
"""S3: B writes acceptance tests, A reviews, workflow freezes the files.

New tests may be RED. A nonzero pytest run is recorded and does not fail the stage.
After approval, protected-tests.json is the hash manifest. Later edits fail closed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from aac_common import ROOT, ensure_run_dirs, load_workflow, slot_model, write_state
from protected_tests import arm, check
from review_loop import LoopPaths, call_agent_with_repair, loop_config_from_workflow, run_review_fix_loop


def render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def load_prompt(name: str) -> str:
    return (ROOT / "prompts" / "stages" / name).read_text(encoding="utf-8")


def listed_tests(matrix: str, test_dir: Path) -> list[str]:
    found = []
    for path in sorted(test_dir.glob("test_*.py")):
        rel = str(path.relative_to(ROOT))
        if rel in matrix or path.name in matrix:
            found.append(rel)
    return found


def run_pytest(cfg: dict, run_id: str) -> subprocess.CompletedProcess[str]:
    gate = str((cfg.get("gates") or {}).get("gate_cmd") or "").strip()
    if not gate:
        raise SystemExit("gate_cmd is empty")
    env = {**__import__("os").environ, "AAC_RUN_ID": run_id}
    return subprocess.run(
        ["sh", "-c", gate],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    args = parser.parse_args()

    dirs = ensure_run_dirs(args.run_id)
    spec_path = dirs["docs"] / "spec.md"
    plan_path = dirs["docs"] / "plan.md"
    approved = dirs["run"] / "HUMAN_GATE_APPROVED.md"
    if not spec_path.is_file() or not plan_path.is_file():
        raise SystemExit("S3 needs spec.md and plan.md")
    if not approved.is_file() and not args.skip_agents:
        raise SystemExit("spec human gate is not approved")

    state_path = dirs["run"] / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    if state.get("status") not in {"plan_approved", "acceptance_running", None} and not args.skip_agents:
        if state.get("status") != "plan_approved":
            raise SystemExit(f"S3 starts from plan_approved, current status is {state.get('status')}")

    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "acceptance", skip_agents=args.skip_agents, stream=args.stream)
    test_dir = ROOT / "fixtures" / "dogfood" / "tests" / "acceptance" / args.run_id
    test_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = dirs["docs"] / "acceptance-matrix.md"
    mapping = {
        "REQUEST": state.get("request") or "(see spec.md)",
        "SPEC_PATH": str(spec_path.relative_to(ROOT)),
        "PLAN_PATH": str(plan_path.relative_to(ROOT)),
        "TEST_DIR": str(test_dir.relative_to(ROOT)),
        "MATRIX_PATH": str(matrix_path.relative_to(ROOT)),
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }
    write_state(dirs["run"], stage="acceptance", status="acceptance_running", max_rounds=loop_cfg.max_rounds)
    print(f"run_id={args.run_id} acceptance max_rounds={loop_cfg.max_rounds}")

    if args.skip_agents:
        stub = test_dir / "test_s3_stub.py"
        stub.write_text(
            "def test_s3_stub_is_red():\n    raise AssertionError('unimplemented dogfood behavior')\n",
            encoding="utf-8",
        )
        matrix_path.write_text(
            f"| AC | file | test | prior |\n| --- | --- | --- | --- |\n"
            f"| AC-01 | {stub.relative_to(ROOT)} | test_s3_stub_is_red | RED |\n",
            encoding="utf-8",
        )
    else:
        print("→ Acceptance tests (B writes)…")
        wr = call_agent_with_repair(
            model=slot_model(cfg, "B", stage="acceptance"),
            prompt=render(load_prompt("05-acceptance-tests-write.md"), mapping),
            archive=dirs["archive"],
            tag="301-acceptance-write",
            cfg=loop_cfg,
        )
        if wr.returncode != 0:
            write_state(dirs["run"], status="aborted_agent_failure", error=f"acceptance-write-{wr.returncode}")
            return wr.returncode or 1

    if not matrix_path.is_file():
        print("FAIL: acceptance matrix missing", file=sys.stderr)
        return 1
    matrix = matrix_path.read_text(encoding="utf-8")
    tests = listed_tests(matrix, test_dir)
    print(f"acceptance files: {tests}")
    if not tests:
        write_state(dirs["run"], status="failed", error="no-acceptance-tests")
        print("FAIL: matrix names no test_*.py under the acceptance dir", file=sys.stderr)
        return 1

    reviews = dirs["run"] / "reviews" / "acceptance"
    reviews.mkdir(parents=True, exist_ok=True)

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("06-acceptance-tests-review.md"),
            {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))},
        )

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("05b-acceptance-tests-fix.md"),
            {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))},
        )

    result = run_review_fix_loop(
        paths=LoopPaths(
            run_dir=dirs["run"],
            archive=dirs["archive"],
            reviews_root=reviews,
            artifact_path=matrix_path,
            run_id=args.run_id,
        ),
        cfg=loop_cfg,
        model_owner=slot_model(cfg, "B", stage="acceptance"),
        model_reviewer=slot_model(cfg, "A", stage="acceptance"),
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=f"uv run --with pyyaml scripts/s3_acceptance_loop.py --run-id {args.run_id}",
    )
    if not result.approved:
        return 2

    tests = listed_tests(matrix_path.read_text(encoding="utf-8"), test_dir)
    pytest_run = run_pytest(cfg, args.run_id)
    baseline = {
        "exit_code": pytest_run.returncode,
        "red_allowed": True,
        "tail": "\n".join((pytest_run.stdout or "").splitlines()[-20:]),
    }
    (dirs["run"] / "test-baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"pytest exit={pytest_run.returncode} (RED is allowed)")
    payload = arm(args.run_id, tests)
    problems = check(args.run_id)
    if problems:
        print(f"FAIL: fresh arm did not check clean: {problems}", file=sys.stderr)
        return 1
    write_state(
        dirs["run"],
        stage="acceptance",
        status="acceptance_protected",
        protected_tests=list(payload["files"]),
        pytest_exit=pytest_run.returncode,
    )
    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s3.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        f"# S3 evidence `{args.run_id}`\n\n"
        f"- tests: {tests}\n"
        f"- pytest_exit: {pytest_run.returncode} (nonzero allowed)\n"
        f"- protected: `aac/.run/{args.run_id}/protected-tests.json`\n"
        f"- rounds: {result.rounds_used}/{loop_cfg.max_rounds}\n",
        encoding="utf-8",
    )
    print(f"S3 complete. protected={len(payload['files'])} evidence={evidence}")
    from gh_collab import stage_complete
    from stage_labels import labels_cfg

    stage_complete(
        args.run_id,
        labels_cfg()["plan_approved"],
        delivered="Acceptance tests written and protected",
        next_step="`/approve` to implement the first task",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

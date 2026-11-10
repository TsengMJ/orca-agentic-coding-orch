#!/usr/bin/env python3
"""Map a GitHub comment to the next pipeline step for every stage.

/approve continues. Any other human comment is feedback: the current artifact
is revised and reviewed again. /abort is handled by the watcher.
Gate /approve merges into dev.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aac_common import ROOT, ensure_run_dirs, load_workflow, slot_model, write_state
from review_loop import LoopPaths, call_agent_with_repair, loop_config_from_workflow, run_review_fix_loop
SPEC_STATUSES = {"awaiting_human_gate", "spec_review_approved", "spec_human_approved"}
PLAN_STATUSES = {"plan_approved", "awaiting_human_plan_gate", "plan_review_approved"}
ACCEPT_STATUSES = {"acceptance_protected", "acceptance_review_approved"}
IMPL_STATUSES = {"task_committed", "branch_review_approved", "implementing"}


def load_state(run_id: str) -> dict:
    path = ROOT / "aac" / ".run" / run_id / "state.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def decide(status: str, kind: str) -> str:
    """Return an action name for this status and comment kind."""
    if kind == "approve":
        if status in {"awaiting_human_gate", "spec_review_approved"}:
            return "approve_spec"
        if status == "awaiting_human_plan_gate":
            return "approve_plan"
        if status == "plan_approved":
            return "start_s3"
        if status == "acceptance_protected":
            return "start_s4"
        if status == "task_committed":
            return "start_s5"
        if status in {"branch_review_approved", "final_accepted"}:
            return "merge"
        if status.endswith("_started") or status.endswith("_running") or status in {"acceptance_running", "implementing"}:
            return "already_running"
        return "no_step"
    if kind == "feedback":
        if status in SPEC_STATUSES or status == "spec_human_approved":
            return "revise_spec"
        if status in PLAN_STATUSES or status.startswith("plan"):
            return "revise_plan"
        if status in ACCEPT_STATUSES or status.startswith("acceptance"):
            return "revise_acceptance"
        if status == "final_accepted":
            return "revise_final"
        if status in IMPL_STATUSES or status.startswith("branch"):
            return "revise_code"
        return "revise_spec"
    raise ValueError(kind)


def _e2e() -> bool:
    return __import__("os").environ.get("AAC_E2E_SKIP", "").strip() in {"1", "true", "yes"}


def _run(script: str, run_id: str, extra: list[str] | None = None) -> tuple[int, str]:
    flags = list(extra or [])
    if _e2e():
        if script == "s1_human_gate.py":
            flags = ["--approve", "--no-continue"]
        elif script == "s2_plan_loop.py":
            flags = ["--skip-agents", "--no-continue"]
        elif script == "s3_acceptance_loop.py":
            flags = ["--skip-agents"]
        elif script == "s4_implement_task.py":
            flags = ["--skip-agents", "--skip-commit"]
        elif script == "s5_gate_review.py":
            flags = ["--skip-agents", "--skip-commit", "--skip-gate"]
        elif script == "s6_final.py":
            flags = ["--skip-agents"]
    cmd = [sys.executable, str(ROOT / "scripts" / script), "--run-id", run_id, *flags]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    tail = "\n".join((result.stdout or result.stderr or "").splitlines()[-15:])
    return result.returncode, tail


def _render(name: str, mapping: dict[str, str]) -> str:
    text = (ROOT / "prompts" / "stages" / name).read_text(encoding="utf-8")
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _feedback_loop(run_id: str, stage: str, *, author: str, reviewer: str, artifact: Path, review_name: str, fix_name: str, mapping: dict[str, str]) -> tuple[int, str]:
    dirs = ensure_run_dirs(run_id)
    cfg = loop_config_from_workflow(load_workflow(), stage, stream=True)
    reviews = dirs["run"] / "reviews" / stage
    reviews.mkdir(parents=True, exist_ok=True)
    note = dirs["run"] / "FEEDBACK.md"
    mapping = {**mapping, "FEEDBACK_PATH": str(note.relative_to(ROOT)), "MAX_ROUNDS": str(cfg.max_rounds)}

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return _render(review_name, {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))})

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        base = _render(fix_name, {**mapping, "ROUND": str(round_n), "REVIEW_PATH": str(review_path.relative_to(ROOT)), "VERDICT_PATH": str(verdict_path.relative_to(ROOT))})
        return base + f"\n\n## Human feedback\n\nRead `{note.relative_to(ROOT)}` and apply it.\n"

    write_state(dirs["run"], status=f"{stage}_revising")
    first = build_fix(0, reviews / "feedback-fix.md", reviews / "feedback-verdict.json")
    fixed = call_agent_with_repair(model=author, prompt=first, archive=dirs["archive"], tag=f"fb-{stage}-fix", cfg=cfg)
    if fixed.returncode != 0:
        return fixed.returncode or 1, f"{stage} feedback fix failed"
    result = run_review_fix_loop(
        paths=LoopPaths(dirs["run"], dirs["archive"], reviews, artifact, run_id),
        cfg=cfg,
        model_owner=author,
        model_reviewer=reviewer,
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=f"uv run --with pyyaml scripts/gh_collab.py watch",
    )
    if not result.approved:
        return 2, f"{stage} feedback review not approved"
    return 0, f"{stage} updated from feedback"


def continue_run(run_id: str, pr: int | None = None) -> tuple[int, str]:
    status = load_state(run_id).get("status") or ""
    action = decide(status, "approve")
    if action == "approve_spec":
        # Approve gate without auto-continuing; we always start S2 with --no-continue
        # so Plan waits for the next /approve.
        code, tail = _run("s1_human_gate.py", run_id, ["--approve", "--no-continue"])
        if code != 0:
            return code, tail
        return _run("s2_plan_loop.py", run_id, ["--stream", "--no-continue"] if not _e2e() else ["--skip-agents", "--no-continue"])
    if action == "approve_plan":
        write_state(ROOT / "aac" / ".run" / run_id, status="plan_approved")
        return _run("s3_acceptance_loop.py", run_id, ["--stream"])
    if action == "start_s3":
        return _run("s3_acceptance_loop.py", run_id, ["--stream"])
    if action == "start_s4":
        return _run("s4_implement_task.py", run_id, ["--stream"])
    if action == "start_s5":
        code, tail = _run("s5_gate_review.py", run_id, ["--stream"])
        if code != 0:
            return code, tail
        return _run("s6_final.py", run_id, ["--stream"])
    if action == "merge":
        from gh_collab import load_github_meta, merge_pr

        meta = load_github_meta(run_id)
        number = pr or meta.get("pr")
        if not number:
            return 1, "missing PR number for merge"
        return merge_pr(int(number), run_id)
    if action == "already_running":
        return 0, f"already running ({status})"
    return 0, f"no forward step from status {status or 'missing'}"


def feedback_run(run_id: str, text: str) -> tuple[int, str]:
    dirs = ensure_run_dirs(run_id)
    (dirs["run"] / "FEEDBACK.md").write_text(text.strip() + "\n", encoding="utf-8")
    status = load_state(run_id).get("status") or ""
    action = decide(status, "feedback")
    if _e2e():
        log = dirs["run"] / "feedback-actions.log"
        with log.open("a", encoding="utf-8") as handle:
            handle.write(action + "\n")
        return 0, f"recorded {action}"
    cfg = load_workflow()
    model_spec_a = slot_model(cfg, "A", stage="spec")
    model_spec_b = slot_model(cfg, "B", stage="spec")
    model_plan_a = slot_model(cfg, "A", stage="plan")
    model_plan_b = slot_model(cfg, "B", stage="plan")
    model_accept_a = slot_model(cfg, "A", stage="acceptance")
    model_accept_b = slot_model(cfg, "B", stage="acceptance")
    model_final_a = slot_model(cfg, "A", stage="final")
    model_final_b = slot_model(cfg, "B", stage="final")
    model_gate_i = slot_model(cfg, "I", stage="gate")
    model_gate_b = slot_model(cfg, "B", stage="gate")
    spec = dirs["docs"] / "spec.md"
    plan = dirs["docs"] / "plan.md"
    matrix = dirs["docs"] / "acceptance-matrix.md"
    mapping = {
        "SPEC_PATH": str(spec.relative_to(ROOT)),
        "PLAN_PATH": str(plan.relative_to(ROOT)),
        "MATRIX_PATH": str(matrix.relative_to(ROOT)),
        "REQUEST": load_state(run_id).get("request") or "",
        "TEST_DIR": f"fixtures/dogfood/tests/acceptance/{run_id}",
    }
    if action == "revise_spec":
        code, message = _feedback_loop(run_id, "spec", author=model_spec_a, reviewer=model_spec_b, artifact=spec, review_name="02-spec-review.md", fix_name="01b-spec-fix.md", mapping=mapping)
        if code == 0:
            write_state(dirs["run"], status="awaiting_human_gate", human_gate="pending")
            message += " Reply /approve to continue."
        return code, message
    if action == "revise_plan":
        code, message = _feedback_loop(run_id, "plan", author=model_plan_a, reviewer=model_plan_b, artifact=plan, review_name="04-plan-review.md", fix_name="03b-plan-fix.md", mapping=mapping)
        if code == 0:
            write_state(dirs["run"], status="plan_approved")
            message += " Reply /approve to start acceptance tests."
        return code, message
    if action == "revise_acceptance":
        code, message = _feedback_loop(run_id, "acceptance", author=model_accept_b, reviewer=model_accept_a, artifact=matrix, review_name="06-acceptance-tests-review.md", fix_name="05b-acceptance-tests-fix.md", mapping=mapping)
        if code == 0:
            from protected_tests import arm
            from s3_acceptance_loop import listed_tests

            test_dir = ROOT / "fixtures" / "dogfood" / "tests" / "acceptance" / run_id
            tests = listed_tests(matrix.read_text(encoding="utf-8"), test_dir)
            if tests:
                arm(run_id, tests)
            write_state(dirs["run"], status="acceptance_protected")
            message += " Reply /approve to implement the first task."
        return code, message
    if action == "revise_final":
        body = dirs["docs"] / "pr-body.md"
        code, message = _feedback_loop(
            run_id,
            "final",
            author=model_final_a,
            reviewer=model_final_b,
            artifact=body,
            review_name="09-final-acceptance.md",
            fix_name="09b-pr-body-fix.md",
            mapping={**mapping, "PR_BODY_PATH": str(body.relative_to(ROOT))},
        )
        if code == 0:
            write_state(dirs["run"], status="final_accepted")
            message += " Reply /approve to merge into dev."
        return code, message
    code, message = _feedback_loop(
        run_id,
        "branch",
        author=model_gate_i,
        reviewer=model_gate_b,
        artifact=plan if plan.is_file() else spec,
        review_name="08-branch-review.md",
        fix_name="07-implement-task.md",
        mapping={**mapping, "TASK_ID": "feedback", "TASK_LINE": text.strip(), "BASE": "dev"},
    )
    if code == 0:
        write_state(dirs["run"], status="task_committed")
        message += " Reply /approve to re-run the gate and branch review."
    return code, message

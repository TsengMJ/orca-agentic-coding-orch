#!/usr/bin/env python3
"""S2: Plan write → bounded review/fix → optional human plan gate.

Requires an S1 run whose spec human gate is approved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from aac_common import (
    ROOT,
    ensure_run_dirs,
    load_workflow,
    slot_model,
    write_state,
)
from review_loop import LoopPaths, call_agent_with_repair, loop_config_from_workflow, run_review_fix_loop


def render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def load_prompt(name: str) -> str:
    return (ROOT / "prompts" / "stages" / name).read_text(encoding="utf-8")


def checkbox_ids(text: str) -> list[str]:
    ids = []
    for line in text.splitlines():
        if not line.strip().startswith("- [ ]"):
            continue
        m = re.search(r"\bT-\d+\b", line)
        ids.append(m.group(0) if m else line.strip()[:40])
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="S1 run id with approved spec")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    args = parser.parse_args()

    dirs = ensure_run_dirs(args.run_id)
    spec_path = dirs["docs"] / "spec.md"
    plan_path = dirs["docs"] / "plan.md"
    approved = dirs["run"] / "HUMAN_GATE_APPROVED.md"
    if not spec_path.is_file():
        raise SystemExit(f"missing spec: {spec_path}")
    if not approved.is_file() and not args.skip_agents:
        raise SystemExit(
            f"spec human gate not approved for {args.run_id}. "
            "Run s1_human_gate.py --approve first."
        )

    state = {}
    state_path = dirs["run"] / "state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    request = state.get("request") or "(see spec.md)"

    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(cfg, "plan", skip_agents=args.skip_agents, stream=args.stream)
    human_plan = bool((cfg.get("gates") or {}).get("human_gate_plan", False))
    model_a = slot_model(cfg, "A")
    model_b = slot_model(cfg, "B")

    write_state(
        dirs["run"],
        stage="plan",
        status="running",
        max_rounds=loop_cfg.max_rounds,
    )
    mapping = {
        "REQUEST": request,
        "SPEC_PATH": str(spec_path.relative_to(ROOT)),
        "PLAN_PATH": str(plan_path.relative_to(ROOT)),
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }
    print(f"run_id={args.run_id} plan max_rounds={loop_cfg.max_rounds}")

    write_prompt = render(load_prompt("03-plan-write.md"), mapping)
    if args.skip_agents:
        plan_path.write_text(
            "- [ ] T-01 stub; AC-01; files=a; deps=[]; DoD=x\n"
            "- [ ] T-02 stub; AC-02; files=b; deps=[T-01]; DoD=y\n",
            encoding="utf-8",
        )
    else:
        print("→ Plan write (A)…")
        wr = call_agent_with_repair(
            model=model_a,
            prompt=write_prompt,
            archive=dirs["archive"],
            tag="201-plan-write",
            cfg=loop_cfg,
        )
        if wr.returncode != 0:
            write_state(dirs["run"], status="aborted_agent_failure", error=f"plan-write-{wr.returncode}")
            return wr.returncode or 1
    if not plan_path.is_file():
        print("FAIL: plan.md missing", file=sys.stderr)
        return 1
    ids = checkbox_ids(plan_path.read_text(encoding="utf-8"))
    print(f"tasks: {ids}")
    if len(ids) < 2:
        write_state(dirs["run"], status="failed", error="plan-fewer-than-2-tasks")
        print("FAIL: plan needs at least 2 checkbox tasks", file=sys.stderr)
        return 1

    reviews = dirs["run"] / "reviews" / "plan"
    reviews.mkdir(parents=True, exist_ok=True)
    resume = f"uv run --with pyyaml scripts/s2_plan_loop.py --run-id {args.run_id}"

    def build_review(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("04-plan-review.md"),
            {
                **mapping,
                "ROUND": str(round_n),
                "REVIEW_PATH": str(review_path.relative_to(ROOT)),
                "VERDICT_PATH": str(verdict_path.relative_to(ROOT)),
            },
        )

    def build_fix(round_n: int, review_path: Path, verdict_path: Path) -> str:
        return render(
            load_prompt("03b-plan-fix.md"),
            {
                **mapping,
                "ROUND": str(round_n),
                "REVIEW_PATH": str(review_path.relative_to(ROOT)),
                "VERDICT_PATH": str(verdict_path.relative_to(ROOT)),
            },
        )

    result = run_review_fix_loop(
        paths=LoopPaths(
            run_dir=dirs["run"],
            archive=dirs["archive"],
            reviews_root=reviews,
            artifact_path=plan_path,
            run_id=args.run_id,
        ),
        cfg=loop_cfg,
        model_owner=model_a,
        model_reviewer=model_b,
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=resume,
    )
    if not result.approved:
        evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s2.md"
        evidence.write_text(
            f"# S2 aborted `{args.run_id}`\n\nstatus={result.status} rounds={result.rounds_used}\n",
            encoding="utf-8",
        )
        return 2

    if human_plan:
        pending = dirs["run"] / "HUMAN_GATE_PLAN_PENDING.md"
        pending.write_text(
            f"# Human gate — Plan (`{args.run_id}`)\n\nPlan: `{plan_path.relative_to(ROOT)}`\n\n"
            "Approve by writing HUMAN_GATE_PLAN_APPROVED.md or set human_gate_plan false.\n",
            encoding="utf-8",
        )
        write_state(dirs["run"], status="awaiting_human_plan_gate", stage="plan")
        print(f"HUMAN PLAN GATE PENDING → {pending}")
        return 0

    write_state(dirs["run"], status="plan_approved", stage="plan", plan_tasks=ids)
    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s2.md"
    evidence.write_text(
        f"# S2 evidence `{args.run_id}`\n\n"
        f"- plan: `{plan_path.relative_to(ROOT)}`\n"
        f"- tasks: {ids}\n"
        f"- rounds: {result.rounds_used}/{loop_cfg.max_rounds}\n"
        f"- verdict: `{json.dumps(result.last_verdict, ensure_ascii=False)}`\n"
        f"- human_gate_plan: off (config)\n",
        encoding="utf-8",
    )
    print(f"S2 complete. evidence={evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

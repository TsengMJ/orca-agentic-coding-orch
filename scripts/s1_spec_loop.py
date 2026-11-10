#!/usr/bin/env python3
"""S1: Spec write → AAC review/fix loop → human gate marker.

Uses scripts/review_loop.py: MAX_ROUNDS hard stop, agent-call repair retries,
abort + resume hint — no unbounded review, no silent hang.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aac_common import (
    ROOT,
    ensure_run_dirs,
    load_workflow,
    notify_human,
    slot_model,
    utc_run_id,
    write_state,
)
from gh_collab import branch_name, repo
from ids import issue_run_id
from review_loop import (
    LoopPaths,
    call_agent_with_repair,
    loop_config_from_workflow,
    run_review_fix_loop,
)


def render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def load_prompt(name: str) -> str:
    return (ROOT / "prompts" / "stages" / name).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--issue",
        type=int,
        default=0,
        help="GitHub issue number. run_id follows feature/<slug> or fix/<slug> until the draft PR exists.",
    )
    parser.add_argument("--auto-approve-human-gate", action="store_true")
    parser.add_argument("--skip-agents", action="store_true")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Tee Cursor agent output live to the terminal (also AAC_STREAM=1)",
    )
    args = parser.parse_args()

    cfg = load_workflow()
    loop_cfg = loop_config_from_workflow(
        cfg, "spec", skip_agents=args.skip_agents, stream=args.stream
    )
    human_gate = bool((cfg.get("gates") or {}).get("human_gate", True))
    model_a = slot_model(cfg, "A", stage="spec")
    model_b = slot_model(cfg, "B", stage="spec")

    if args.issue and args.run_id:
        raise SystemExit("pass only one of --issue or --run-id")
    run_id = args.run_id or (issue_run_id(repo(), args.issue) if args.issue else utc_run_id("s1"))
    dirs = ensure_run_dirs(run_id)
    spec_path = dirs["docs"] / "spec.md"
    branch = branch_name(args.issue) if args.issue else None
    write_state(
        dirs["run"],
        run_id=run_id,
        stage="spec",
        status="running",
        request=args.request,
        issue=args.issue or None,
        branch=branch,
        models={"A": model_a, "B": model_b},
        max_rounds=loop_cfg.max_rounds,
        agent_call_retries=loop_cfg.agent_call_retries,
        human_gate=human_gate,
    )
    if args.issue and branch:
        from gh_collab import write_github_meta

        write_github_meta(
            run_id,
            {"issue": args.issue, "branch": branch, "run_id": run_id, "pr": None, "url": None},
        )

    mapping_base = {
        "REQUEST": args.request,
        "SPEC_PATH": str(spec_path.relative_to(ROOT)),
        "MAX_ROUNDS": str(loop_cfg.max_rounds),
    }

    print(f"run_id={run_id}")
    print(
        f"A={model_a} B={model_b} max_rounds={loop_cfg.max_rounds} "
        f"agent_call_retries={loop_cfg.agent_call_retries} "
        f"timeout_sec={loop_cfg.agent_timeout_sec}"
    )

    # --- Write (with same-call repair) ---
    write_prompt = render(load_prompt("01-spec-write.md"), mapping_base)
    if args.skip_agents:
        spec_path.write_text(
            "# stub spec\n\n## Assumptions and Open Questions\n- none\n",
            encoding="utf-8",
        )
    else:
        print("→ Spec write (A)…")
        wr = call_agent_with_repair(
            model=model_a,
            prompt=write_prompt,
            archive=dirs["archive"],
            tag="001-spec-write",
            cfg=loop_cfg,
        )
        if wr.returncode != 0:
            write_state(dirs["run"], status="aborted_agent_failure", error=f"spec-write-{wr.returncode}")
            print(wr.stderr, file=sys.stderr)
            return wr.returncode or 1
        if not spec_path.exists():
            write_state(dirs["run"], status="failed", error="spec.md-missing")
            print("FAIL: spec.md was not created", file=sys.stderr)
            return 1
    print(f"spec: {spec_path}")

    resume_hint = (
        f"uv run --with pyyaml scripts/s1_resume_review.py --run-id {run_id}"
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
            run_id=run_id,
        ),
        cfg=loop_cfg,
        model_owner=model_a,
        model_reviewer=model_b,
        build_review_prompt=build_review,
        build_fix_prompt=build_fix,
        resume_hint=resume_hint,
        start_round=1,
    )

    if not result.approved:
        evidence = ROOT / "artifacts" / "runs" / f"{run_id}.md"
        evidence.write_text(
            f"# S1 aborted `{run_id}`\n\n"
            f"- status: `{result.status}`\n"
            f"- rounds: {result.rounds_used}/{loop_cfg.max_rounds}\n"
            f"- last_verdict: `{json.dumps(result.last_verdict, ensure_ascii=False)}`\n"
            f"- resume: `{result.resume_cmd}`\n"
            f"- see also: `docs/review-loop.md`\n",
            encoding="utf-8",
        )
        return 2

    # --- Human gate (only after review approved) ---
    if human_gate and not args.auto_approve_human_gate:
        pending = dirs["run"] / "HUMAN_GATE_PENDING.md"
        pending.write_text(
            "\n".join(
                [
                    f"# Human gate — Spec (`{run_id}`)",
                    "",
                    f"Spec: `{spec_path.relative_to(ROOT)}`",
                    f"Review approved in {result.rounds_used}/{loop_cfg.max_rounds} rounds.",
                    "",
                    "```bash",
                    f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {run_id} --approve",
                    f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {run_id} --abort",
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        write_state(dirs["run"], status="awaiting_human_gate", human_gate="pending")
        print(f"HUMAN GATE PENDING → {pending}")
        notify_human(
            f"Spec ready for approval: {run_id}. "
            f"uv run --with pyyaml scripts/s1_human_gate.py --run-id {run_id} --approve",
            title="AAC spec gate",
        )
        return 0

    (dirs["run"] / "HUMAN_GATE_APPROVED.md").write_text(
        f"approved auto={args.auto_approve_human_gate}\n", encoding="utf-8"
    )
    write_state(dirs["run"], status="spec_human_approved", human_gate="approved")
    evidence = ROOT / "artifacts" / "runs" / f"{run_id}.md"
    evidence.write_text(
        f"# S1 evidence `{run_id}`\n\n"
        f"- request: {args.request}\n"
        f"- spec: `{spec_path.relative_to(ROOT)}`\n"
        f"- rounds: {result.rounds_used}/{loop_cfg.max_rounds}\n"
        f"- last_verdict: `{json.dumps(result.last_verdict)}`\n"
        f"- human_gate: approved (auto={args.auto_approve_human_gate})\n",
        encoding="utf-8",
    )
    print(f"S1 complete. evidence={evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

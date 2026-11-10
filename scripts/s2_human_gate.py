#!/usr/bin/env python3
"""Resolve S2 human plan gate for a run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from aac_common import ROOT, notify_human, write_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--approve", action="store_true")
    g.add_argument("--abort", action="store_true")
    parser.add_argument(
        "--no-continue",
        action="store_true",
        help="Approve the plan but do not start S3",
    )
    args = parser.parse_args()

    run_dir = ROOT / "aac" / ".run" / args.run_id
    plan = ROOT / "aac" / "docs" / args.run_id / "plan.md"
    if not run_dir.is_dir():
        raise SystemExit(f"unknown run: {args.run_id}")
    if not plan.is_file():
        raise SystemExit(f"missing plan: {plan}")

    pending = run_dir / "HUMAN_GATE_PLAN_PENDING.md"
    now = datetime.now(timezone.utc).isoformat()

    if args.abort:
        (run_dir / "HUMAN_GATE_PLAN_ABORTED.md").write_text(f"aborted_at={now}\n", encoding="utf-8")
        if pending.exists():
            pending.unlink()
        write_state(run_dir, status="aborted_human_plan_gate", human_gate_plan="aborted")
        print(f"PLAN ABORTED {args.run_id}")
        return 1

    aborted = run_dir / "HUMAN_GATE_PLAN_ABORTED.md"
    reopened = aborted.exists()
    if reopened:
        aborted.unlink()
    (run_dir / "HUMAN_GATE_PLAN_APPROVED.md").write_text(
        f"approved_at={now}\n" + ("reopened_after_abort=true\n" if reopened else ""),
        encoding="utf-8",
    )
    if pending.exists():
        pending.unlink()
    write_state(run_dir, status="plan_approved", human_gate_plan="approved", stage="plan")

    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}-s2.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        f"# S2 evidence `{args.run_id}`\n\n"
        f"- plan: `aac/docs/{args.run_id}/plan.md`\n"
        f"- human_gate_plan: approved at {now}\n"
        f"- next: S3 acceptance loop\n",
        encoding="utf-8",
    )
    print(f"PLAN APPROVED {args.run_id}")
    print(f"evidence → {evidence}")
    if args.no_continue:
        print("S3 not started (--no-continue)")
        return 0

    already = subprocess.run(
        ["pgrep", "-fl", f"s3_acceptance_loop.py --run-id {args.run_id}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if already.returncode == 0 and already.stdout.strip():
        print("S3 already running for this run; not starting another")
        print(already.stdout.strip())
        return 0
    log = run_dir / "s3-acceptance.log"
    proc = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts" / "s3_acceptance_loop.py"),
            "--run-id",
            args.run_id,
            "--stream",
        ],
        cwd=ROOT,
        stdout=log.open("a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    write_state(run_dir, status="acceptance_started", s3_pid=proc.pid)
    notify_human(f"S3 acceptance loop started for {args.run_id} pid={proc.pid}", title="AAC acceptance")
    print(f"S3 started pid={proc.pid} log={log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

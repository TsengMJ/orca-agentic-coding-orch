#!/usr/bin/env python3
"""Resolve S1 human gate for a spec run."""

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
        help="Approve the spec but do not start S2",
    )
    args = parser.parse_args()

    run_dir = ROOT / "aac" / ".run" / args.run_id
    docs = ROOT / "aac" / "docs" / args.run_id / "spec.md"
    if not run_dir.is_dir():
        raise SystemExit(f"unknown run: {args.run_id}")
    if not docs.is_file():
        raise SystemExit(f"missing spec: {docs}")

    pending = run_dir / "HUMAN_GATE_PENDING.md"
    now = datetime.now(timezone.utc).isoformat()

    if args.abort:
        (run_dir / "HUMAN_GATE_ABORTED.md").write_text(f"aborted_at={now}\n", encoding="utf-8")
        if pending.exists():
            pending.unlink()
        write_state(run_dir, status="aborted_human_gate", human_gate="aborted")
        print(f"ABORTED {args.run_id}")
        return 1

    aborted = run_dir / "HUMAN_GATE_ABORTED.md"
    reopened = aborted.exists()
    if reopened:
        aborted.unlink()
    (run_dir / "HUMAN_GATE_APPROVED.md").write_text(
        f"approved_at={now}\n" + ("reopened_after_abort=true\n" if reopened else ""),
        encoding="utf-8",
    )
    if pending.exists():
        pending.unlink()
    write_state(run_dir, status="spec_human_approved", human_gate="approved")

    # Load last verdict for evidence
    verdict_path = run_dir / "verdict.json"
    verdict = {}
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verdict = {"error": "unparseable"}

    evidence = ROOT / "artifacts" / "runs" / f"{args.run_id}.md"
    evidence.write_text(
        f"# S1 evidence `{args.run_id}`\n\n"
        f"- spec: `aac/docs/{args.run_id}/spec.md`\n"
        f"- last_verdict: `{json.dumps(verdict, ensure_ascii=False)}`\n"
        f"- human_gate: approved at {now}\n"
        f"- next: S2 Plan loop\n",
        encoding="utf-8",
    )
    print(f"APPROVED {args.run_id}")
    print(f"evidence → {evidence}")
    if args.no_continue:
        print("S2 not started (--no-continue)")
        return 0
    already = subprocess.run(
        ["pgrep", "-fl", f"s2_plan_loop.py --run-id {args.run_id}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if already.returncode == 0 and already.stdout.strip():
        print("S2 already running for this run; not starting another")
        print(already.stdout.strip())
        return 0
    log = run_dir / "s2-plan.log"
    from aac_common import spawn_uv_script

    proc = spawn_uv_script(
        "s2_plan_loop.py",
        ["--run-id", args.run_id, "--stream"],
        log=log,
    )
    write_state(run_dir, status="plan_started", s2_pid=proc.pid)
    notify_human(f"S2 plan loop started for {args.run_id} pid={proc.pid}", title="AAC plan")
    print(f"S2 started pid={proc.pid} log={log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

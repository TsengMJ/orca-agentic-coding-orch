#!/usr/bin/env python3
"""Long-running AAC workflow server.

Cron 1: open issues labeled Ready → claim → Orca worktree → S1 → publish (Spec).
Cron 2: open PRs with waiting stage labels → apply /approve|/abort|feedback.
Cron 3: healer — resume flakes / diagnose orch bugs (config.healer).

Start once:
  uv run --with pyyaml scripts/workflow_server.py
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aac_common import ROOT, load_workflow, write_state
from gh_collab import (
    branch_name,
    ensure_workflow_labels,
    issue_remove_label,
    repo,
    run as gh_run,
    watch_once,
)
from ids import issue_run_id
from stage_labels import READY, labels_cfg
from healer import heal_once, healer_cfg, healer_cron


def server_cfg() -> dict:
    gh = load_workflow().get("github") or {}
    heal = healer_cfg()
    return {
        "max_jobs": int(gh.get("max_jobs") or 1),
        "issue_poll_sec": int(gh.get("issue_poll_sec") or 60),
        "pr_poll_sec": int(gh.get("pr_poll_sec") or 30),
        "health_port": int(gh.get("health_port") or 8765),
        "base": str(gh.get("base") or "dev"),
        "ready": labels_cfg().get("ready") or READY,
        "healer_enabled": heal.enabled,
        "healer_poll_sec": heal.poll_sec,
        "healer_orch_fix": heal.orch_fix,
    }


class JobRegistry:
    def __init__(self, max_jobs: int) -> None:
        self.max_jobs = max_jobs
        self._lock = threading.Lock()
        self._jobs: dict[str, subprocess.Popen[str]] = {}

    def living(self) -> int:
        with self._lock:
            dead = [key for key, proc in self._jobs.items() if proc.poll() is not None]
            for key in dead:
                self._jobs.pop(key, None)
            return len(self._jobs)

    def can_start(self) -> bool:
        return self.living() < self.max_jobs

    def add(self, key: str, proc: subprocess.Popen[str]) -> None:
        with self._lock:
            self._jobs[key] = proc

    def snapshot(self) -> dict[str, int | None]:
        with self._lock:
            return {key: proc.pid for key, proc in self._jobs.items()}


def acquire_lock() -> object:
    lock_path = ROOT / "aac" / ".run" / "server.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise SystemExit(f"another workflow_server holds {lock_path}") from exc
    handle.seek(0)
    handle.truncate()
    handle.write(f"pid={os.getpid()}\n")
    handle.flush()
    return handle


def orca_bin() -> str:
    return os.environ.get("ORCA_CLI_COMMAND") or "orca"


def ensure_orca_worktree(branch: str, *, issue: int) -> Path:
    """Create (or reuse) an Orca worktree named for the branch."""
    listed = subprocess.run(
        [orca_bin(), "worktree", "list", "--json", "--limit", "10000"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if listed.returncode == 0 and listed.stdout.strip():
        try:
            payload = json.loads(listed.stdout)
        except json.JSONDecodeError:
            payload = {}
        items = payload.get("result") or payload.get("worktrees") or payload
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "")
                path = item.get("path") or item.get("worktreePath")
                if name == branch and path:
                    return Path(str(path))
                if str(item.get("branch") or "") == branch and path:
                    return Path(str(path))

    base = str((load_workflow().get("github") or {}).get("base") or "dev")
    created = subprocess.run(
        [
            orca_bin(),
            "worktree",
            "create",
            "--name",
            branch,
            "--branch",
            branch,
            "--base-branch",
            base,
            "--no-parent",
            "--issue",
            str(issue),
            "--setup",
            "skip",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if created.returncode != 0:
        raise SystemExit(
            f"orca worktree create failed for {branch}: {(created.stderr or created.stdout).strip()}"
        )
    data = json.loads(created.stdout)
    result = data.get("result") or data
    path = result.get("path") or result.get("worktreePath")
    if not path and isinstance(result.get("worktree"), dict):
        path = result["worktree"].get("path")
    if not path:
        raise SystemExit(f"orca worktree create returned no path: {created.stdout[:500]}")
    return Path(str(path))


def issue_request_text(issue: int) -> str:
    meta = gh_run(
        ["gh", "issue", "view", str(issue), "--repo", repo(), "--json", "title,body"],
    )
    data = json.loads(meta.stdout)
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    if body:
        return f"{title}\n\n{body}"
    return title


def has_open_pr_for_branch(branch: str) -> bool:
    listed = gh_run(
        ["gh", "pr", "list", "--repo", repo(), "--head", branch, "--state", "open", "--json", "number"],
        check=False,
    )
    return bool(json.loads(listed.stdout or "[]"))


def list_ready_issues(ready: str) -> list[dict]:
    listed = gh_run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo(),
            "--state",
            "open",
            "--label",
            ready,
            "--json",
            "number,title,labels",
        ]
    )
    return json.loads(listed.stdout or "[]")


def claim_issue(issue: int, ready: str) -> None:
    issue_remove_label(issue, ready)


def start_issue_job(issue: int, registry: JobRegistry) -> None:
    branch = branch_name(issue)
    run_id = issue_run_id(repo(), issue)
    run_dir = ROOT / "aac" / ".run" / run_id
    if run_dir.is_dir() and (run_dir / "job.pid").is_file():
        print(f"skip #{issue}: local run {run_id} already exists")
        return
    if has_open_pr_for_branch(branch):
        print(f"skip #{issue}: open PR already on {branch}")
        return

    worktree = ensure_orca_worktree(branch, issue=issue)
    claim_issue(issue, server_cfg()["ready"])
    request = issue_request_text(issue)
    log = run_dir / "server-s1.log"
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "s1_spec_loop.py"),
        "--issue",
        str(issue),
        "--run-id",
        run_id,
        "--request",
        request,
        "--stream",
    ]
    # Artifacts stay on orchestrator ROOT. The Orca worktree is for git checkout during publish.
    # S1 exits 0 at awaiting_human_gate after review approval; then we publish the draft PR.
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=log.open("a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    (run_dir / "job.pid").write_text(f"{proc.pid}\n", encoding="utf-8")
    write_state(
        run_dir,
        run_id=run_id,
        issue=issue,
        branch=branch,
        worktree=str(worktree),
        status="s1_started",
        server_pid=proc.pid,
    )
    from gh_collab import write_github_meta

    write_github_meta(
        run_id,
        {
            "issue": issue,
            "branch": branch,
            "run_id": run_id,
            "pr": None,
            "url": None,
            "worktree": str(worktree),
        },
    )
    registry.add(f"issue-{issue}", proc)
    threading.Thread(
        target=_finish_issue_job,
        args=(issue, run_id, worktree, proc),
        daemon=True,
        name=f"issue-{issue}",
    ).start()
    print(f"started S1 for #{issue} run_id={run_id} worktree={worktree} pid={proc.pid}")


def _finish_issue_job(issue: int, run_id: str, worktree: Path, proc: subprocess.Popen[str]) -> None:
    code = proc.wait()
    run_dir = ROOT / "aac" / ".run" / run_id
    if code != 0:
        write_state(run_dir, status="aborted_agent_failure", error=f"s1-exit-{code}")
        print(f"S1 failed for #{issue} exit={code}")
        return
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "gh_collab.py"),
                "publish",
                "--issue",
                str(issue),
                "--run-id",
                run_id,
                "--cwd",
                str(worktree),
            ],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            write_state(run_dir, status="publish_failed", error=(result.stderr or result.stdout)[:500])
            print(f"publish failed for #{issue}: {(result.stderr or result.stdout).strip()}")
            return
        print(result.stdout)
        write_state(run_dir, status="awaiting_human_gate", human_gate="pending")
        print(f"published #{issue}; waiting for /approve on Spec")
    except Exception as exc:  # noqa: BLE001
        write_state(run_dir, status="publish_failed", error=str(exc))
        print(f"publish error for #{issue}: {exc}")


def issue_cron(stop: threading.Event, registry: JobRegistry) -> None:
    while not stop.is_set():
        cfg = server_cfg()
        try:
            if registry.can_start():
                for item in list_ready_issues(cfg["ready"]):
                    if not registry.can_start():
                        break
                    number = int(item["number"])
                    start_issue_job(number, registry)
        except Exception as exc:  # noqa: BLE001
            print(f"issue cron error: {exc}")
        stop.wait(cfg["issue_poll_sec"])


def pr_cron(stop: threading.Event) -> None:
    while not stop.is_set():
        cfg = server_cfg()
        try:
            code = watch_once()
            if code:
                print(f"watch_once failures exit={code}")
        except Exception as exc:  # noqa: BLE001
            print(f"pr cron error: {exc}")
        stop.wait(cfg["pr_poll_sec"])


def make_health_handler(registry: JobRegistry):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in {"/health", "/health/"}:
                self.send_response(404)
                self.end_headers()
                return
            heal = healer_cfg()
            body = json.dumps(
                {
                    "ok": True,
                    "jobs": registry.living(),
                    "max_jobs": registry.max_jobs,
                    "pids": registry.snapshot(),
                    "healer": {
                        "enabled": heal.enabled,
                        "orch_fix": heal.orch_fix,
                        "poll_sec": heal.poll_sec,
                    },
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run each cron once and exit")
    args = parser.parse_args()

    lock = acquire_lock()
    cfg = server_cfg()
    ensure_workflow_labels()
    registry = JobRegistry(cfg["max_jobs"])
    stop = threading.Event()

    def handle_sig(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    if args.once:
        if registry.can_start():
            for item in list_ready_issues(cfg["ready"]):
                start_issue_job(int(item["number"]), registry)
                break
        watch_once()
        heal_once()
        lock.close()
        return 0

    health = ThreadingHTTPServer(("127.0.0.1", cfg["health_port"]), make_health_handler(registry))
    threading.Thread(target=health.serve_forever, daemon=True, name="health").start()
    threading.Thread(target=issue_cron, args=(stop, registry), daemon=True, name="issue-cron").start()
    threading.Thread(target=pr_cron, args=(stop,), daemon=True, name="pr-cron").start()
    if cfg["healer_enabled"]:
        threading.Thread(target=healer_cron, args=(stop,), daemon=True, name="healer-cron").start()
    print(
        f"workflow_server up health=http://127.0.0.1:{cfg['health_port']}/health "
        f"max_jobs={cfg['max_jobs']} ready={cfg['ready']!r} "
        f"healer={cfg['healer_enabled']} orch_fix={cfg['healer_orch_fix']!r}"
    )
    try:
        while not stop.is_set():
            stop.wait(1.0)
    finally:
        health.shutdown()
        lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

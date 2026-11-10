#!/usr/bin/env python3
"""Workflow healer sidecar.

Watches aac/.run/*/state.json for failed or stuck runs, classifies them, and
either resumes (flake / publish_failed) or diagnoses orch bugs (optional auto-fix).

Never edits product stage artifacts. Never raises max_rounds.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aac_common import ROOT, load_workflow, notify_human, slot_model, write_state

RUN_ROOT = ROOT / "aac" / ".run"

FAILURE_STATUSES = {
    "aborted_agent_failure",
    "publish_failed",
    "failed",
    "aborted_max_rounds",
}

ACTIVE_STATUSES = {
    "running",
    "s1_started",
    "acceptance_running",
    "implementing",
    "final_running",
    "spec_revising",
    "plan_revising",
}

ORCH_BUG_RE = re.compile(
    r"(Traceback \(most recent call last\)|"
    r"File \".*/scripts/[^\"]+\.py\"|"
    r"AttributeError:|TypeError:|KeyError:|NameError:|"
    r"unsupported github\.|"
    r"refusing to overwrite|"
    r"missing github\.json|"
    r"SystemExit)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class HealerConfig:
    enabled: bool
    poll_sec: int
    max_auto_resume_per_run: int
    stale_running_sec: int
    orch_fix: str  # off | propose | auto
    model: str


def healer_cfg(workflow: dict | None = None) -> HealerConfig:
    cfg = workflow if workflow is not None else load_workflow()
    raw = cfg.get("healer") or {}
    orch_fix = str(raw.get("orch_fix") or "propose").strip().lower()
    if orch_fix not in {"off", "propose", "auto"}:
        orch_fix = "propose"
    model = raw.get("model")
    if not model:
        model = slot_model(cfg, "A")
    return HealerConfig(
        enabled=bool(raw.get("enabled", True)),
        poll_sec=int(raw.get("poll_sec") or 90),
        max_auto_resume_per_run=int(raw.get("max_auto_resume_per_run") or 1),
        stale_running_sec=int(raw.get("stale_running_sec") or 3600),
        orch_fix=orch_fix,
        model=str(model),
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_decision(run_dir: Path, decision: dict) -> None:
    path = run_dir / "healer" / "decisions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(decision)
    row.setdefault("at", utc_now())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_run_dirs() -> list[Path]:
    if not RUN_ROOT.is_dir():
        return []
    return sorted(path for path in RUN_ROOT.iterdir() if path.is_dir() and (path / "state.json").is_file())


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def parse_updated_at(state: dict) -> datetime | None:
    raw = state.get("updated_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def age_seconds(state: dict) -> float | None:
    stamp = parse_updated_at(state)
    if stamp is None:
        return None
    now = datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max(0.0, (now - stamp).total_seconds())


def classify(state: dict, *, stale_running_sec: int, run_dir: Path) -> str:
    """Return flake | publish_retry | orch_bug | stuck | escalate | ignore."""
    status = str(state.get("status") or "")
    error = str(state.get("error") or "")
    healer = load_json(run_dir / "healer" / "state.json")
    if healer.get("terminal") in {"escalated", "orch_fix_proposed", "ignored"}:
        return "ignore"
    if status in {"awaiting_human_gate", "awaiting_human_plan_gate", "merged", "spec_human_approved"}:
        return "ignore"
    if status == "aborted_max_rounds":
        return "escalate"
    if status == "publish_failed":
        return "publish_retry"
    if status == "aborted_agent_failure":
        if ORCH_BUG_RE.search(error):
            return "orch_bug"
        return "flake"
    if status == "failed":
        if ORCH_BUG_RE.search(error):
            return "orch_bug"
        return "escalate"
    if status in ACTIVE_STATUSES:
        age = age_seconds(state)
        job_pid = 0
        pid_path = run_dir / "job.pid"
        if pid_path.is_file():
            try:
                job_pid = int(pid_path.read_text(encoding="utf-8").strip().splitlines()[0])
            except ValueError:
                job_pid = 0
        server_pid = int(state.get("server_pid") or 0)
        alive = pid_alive(job_pid) or pid_alive(server_pid)
        if not alive and (age is None or age >= min(60, stale_running_sec)):
            return "stuck"
        if age is not None and age >= stale_running_sec:
            return "stuck" if not alive else "escalate"
        return "ignore"
    if ORCH_BUG_RE.search(error):
        return "orch_bug"
    return "ignore"


def resume_budget_left(run_dir: Path, cfg: HealerConfig) -> bool:
    healer = load_json(run_dir / "healer" / "state.json")
    used = int(healer.get("auto_resume_count") or 0)
    return used < cfg.max_auto_resume_per_run


def bump_resume(run_dir: Path) -> None:
    path = run_dir / "healer" / "state.json"
    data = load_json(path)
    data["auto_resume_count"] = int(data.get("auto_resume_count") or 0) + 1
    data["updated_at"] = utc_now()
    save_json(path, data)


def mark_healer(run_dir: Path, **fields: Any) -> None:
    path = run_dir / "healer" / "state.json"
    data = load_json(path)
    data.update(fields)
    data["updated_at"] = utc_now()
    save_json(path, data)


def render_orch_prompt(run_id: str, state: dict, diagnosis_path: Path) -> str:
    template = (ROOT / "prompts" / "healer-orch-fix.md").read_text(encoding="utf-8")
    mapping = {
        "RUN_ID": run_id,
        "STATUS": str(state.get("status") or ""),
        "STAGE": str(state.get("stage") or ""),
        "ERROR": str(state.get("error") or "")[:2000],
        "DIAGNOSIS_PATH": str(diagnosis_path.relative_to(ROOT)),
    }
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def write_diagnosis(run_dir: Path, run_id: str, state: dict, kind: str) -> Path:
    path = run_dir / "healer" / "diagnosis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        [
            f"# Healer diagnosis — `{run_id}`",
            "",
            f"- kind: `{kind}`",
            f"- status: `{state.get('status')}`",
            f"- stage: `{state.get('stage')}`",
            f"- issue: `{state.get('issue')}`",
            f"- branch: `{state.get('branch')}`",
            f"- updated_at: `{state.get('updated_at')}`",
            "",
            "## Error",
            "",
            "```",
            str(state.get("error") or "(none)"),
            "```",
            "",
            "## Policy",
            "",
            "- Do not edit product stage artifacts to fake a pass.",
            "- Do not raise max_rounds.",
            "- Prefer a minimal orch fix + unit test + memory/lessons note.",
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    return path


def run_resume_spec(run_id: str) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "s1_resume_review.py"),
        "--run-id",
        run_id,
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    message = (result.stderr or result.stdout or "").strip()[:500]
    return result.returncode, message or f"exit-{result.returncode}"


def run_publish_retry(run_id: str, state: dict) -> tuple[int, str]:
    issue = state.get("issue")
    if not issue:
        return 1, "publish_retry needs state.issue"
    meta = load_json(run_dir_for(run_id) / "github.json")
    worktree = meta.get("worktree") or state.get("worktree") or ""
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "gh_collab.py"),
        "publish",
        "--issue",
        str(issue),
        "--run-id",
        run_id,
    ]
    if worktree:
        cmd.extend(["--cwd", str(worktree)])
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    message = (result.stderr or result.stdout or "").strip()[:500]
    return result.returncode, message or f"exit-{result.returncode}"


def run_dir_for(run_id: str) -> Path:
    return RUN_ROOT / run_id


def healing_branch_name(run_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", run_id.lower()).strip("-")[:40]
    return f"fix/healer-{slug or 'run'}"


def spawn_orch_fix(run_id: str, state: dict, diagnosis: Path, cfg: HealerConfig) -> tuple[int, str]:
    """Isolated worktree + healer branch + cursor agent + draft PR. Returns (code, message)."""
    branch = healing_branch_name(run_id)
    base = str((load_workflow().get("github") or {}).get("base") or "dev")
    repo = str((load_workflow().get("github") or {}).get("repo") or "")
    work = ROOT / "aac" / ".worktrees" / branch.replace("/", "-")
    work.parent.mkdir(parents=True, exist_ok=True)

    def git_root(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)

    def git_work(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=work, text=True, capture_output=True, check=False)

    fetched = git_root("fetch", "origin", base)
    if fetched.returncode != 0:
        return fetched.returncode or 1, (fetched.stderr or fetched.stdout or "fetch failed").strip()

    if work.exists():
        git_root("worktree", "remove", "--force", str(work))
    added = git_root("worktree", "add", "-B", branch, str(work), f"origin/{base}")
    if added.returncode != 0:
        return added.returncode or 1, (added.stderr or added.stdout or "worktree add failed").strip()

    prompt = render_orch_prompt(run_id, state, diagnosis)
    (run_dir_for(run_id) / "healer" / "orch-fix-prompt.md").write_text(prompt, encoding="utf-8")

    # Force the agent to edit inside the isolated worktree.
    env_prompt = (
        prompt
        + f"\n\nWork only inside this git worktree: `{work}`.\n"
        + "Do not modify the primary checkout.\n"
    )
    old_root = os.environ.get("AAC_ROOT")
    os.environ["AAC_ROOT"] = str(work)
    try:
        timeout_sec = int(os.environ.get("AAC_AGENT_TIMEOUT_SEC", "480"))
        from aac_common import run_cursor

        # Protocol end signal (stream-json result / process exit), not a prompt field.
        agent = run_cursor(
            cfg.model,
            env_prompt,
            timeout_sec=timeout_sec,
            stream=False,
            cwd=work,
        )
    finally:
        if old_root is None:
            os.environ.pop("AAC_ROOT", None)
        else:
            os.environ["AAC_ROOT"] = old_root

    (run_dir_for(run_id) / "healer" / "orch-fix-stdout.txt").write_text(agent.stdout or "", encoding="utf-8")
    if agent.returncode != 0:
        git_root("worktree", "remove", "--force", str(work))
        return agent.returncode, f"orch fix agent failed rc={agent.returncode}"

    status = git_work("status", "--porcelain")
    if not (status.stdout or "").strip():
        git_root("worktree", "remove", "--force", str(work))
        return 0, "orch fix agent made no changes"

    git_work("add", "-A")
    commit = git_work("commit", "-m", f"fix(healer): repair orch failure for {run_id}")
    if commit.returncode != 0:
        git_root("worktree", "remove", "--force", str(work))
        return commit.returncode or 1, (commit.stderr or commit.stdout or "commit failed").strip()

    pushed = git_work("push", "-u", "origin", branch)
    if pushed.returncode != 0:
        return pushed.returncode or 1, (pushed.stderr or pushed.stdout or "push failed").strip()

    pr_url = ""
    if repo:
        pr = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--base",
                base,
                "--head",
                branch,
                "--draft",
                "--title",
                f"fix(healer): orch repair for {run_id}",
                "--body",
                "\n".join(
                    [
                        f"Healer auto-fix for run `{run_id}`.",
                        "",
                        f"Diagnosis: `aac/.run/{run_id}/healer/diagnosis.md`",
                        "",
                        "Do not merge without human review. Product run stays `needs_human` until this lands.",
                        "",
                        "<!-- aac-orchestrator -->",
                    ]
                ),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if pr.returncode == 0:
            pr_url = (pr.stdout or "").strip()
        else:
            pr_url = (pr.stderr or pr.stdout or "pr create failed").strip()

    mark_healer(
        run_dir_for(run_id),
        terminal="orch_fix_proposed",
        healing_branch=branch,
        healing_pr=pr_url or None,
        healing_worktree=str(work),
        orch_fix_spawned=True,
    )
    return 0, pr_url or f"pushed {branch}"


def handle_run(run_dir: Path, cfg: HealerConfig) -> dict | None:
    run_id = run_dir.name
    state = load_json(run_dir / "state.json")
    if not state:
        return None
    kind = classify(state, stale_running_sec=cfg.stale_running_sec, run_dir=run_dir)
    if kind == "ignore":
        return None

    action: dict[str, Any] = {"run_id": run_id, "kind": kind, "status": state.get("status")}

    if kind in {"flake", "publish_retry", "stuck"} and not resume_budget_left(run_dir, cfg):
        kind = "escalate"
        action["kind"] = "escalate"
        action["reason"] = "resume_budget_exhausted"

    if kind == "flake":
        code, message = run_resume_spec(run_id)
        bump_resume(run_dir)
        action.update({"action": "resume_spec", "code": code, "message": message})
        append_decision(run_dir, action)
        if code != 0:
            write_state(run_dir, status="needs_human", error=f"healer-resume-failed: {message}")
            mark_healer(run_dir, terminal="escalated", last_action="resume_spec_failed")
            notify_human(f"Healer resume failed for {run_id}: {message}", title="AAC healer")
        else:
            mark_healer(run_dir, last_action="resume_spec_ok")
        return action

    if kind == "publish_retry":
        code, message = run_publish_retry(run_id, state)
        bump_resume(run_dir)
        action.update({"action": "publish_retry", "code": code, "message": message})
        append_decision(run_dir, action)
        if code != 0:
            write_state(run_dir, status="needs_human", error=f"healer-publish-failed: {message}")
            mark_healer(run_dir, terminal="escalated", last_action="publish_retry_failed")
            notify_human(f"Healer publish retry failed for {run_id}: {message}", title="AAC healer")
        else:
            write_state(run_dir, status="awaiting_human_gate", human_gate="pending", error=None)
            mark_healer(run_dir, last_action="publish_retry_ok")
        return action

    if kind == "stuck":
        write_state(
            run_dir,
            status="needs_human",
            error=state.get("error") or "healer: process dead or stale while status still active",
        )
        mark_healer(run_dir, terminal="escalated", last_action="stuck")
        action.update({"action": "mark_stuck"})
        append_decision(run_dir, action)
        notify_human(f"Healer marked stuck run {run_id} as needs_human", title="AAC healer")
        return action

    if kind == "orch_bug":
        diagnosis = write_diagnosis(run_dir, run_id, state, kind)
        action["diagnosis"] = str(diagnosis.relative_to(ROOT))
        if cfg.orch_fix == "off":
            write_state(run_dir, status="needs_human", error=state.get("error") or "orch_bug")
            mark_healer(run_dir, terminal="escalated", last_action="orch_bug_off")
            action["action"] = "escalate"
            append_decision(run_dir, action)
            notify_human(f"Orch bug on {run_id}; healer.orch_fix=off", title="AAC healer")
            return action
        if cfg.orch_fix == "propose":
            write_state(run_dir, status="needs_human", error=state.get("error") or "orch_bug")
            mark_healer(run_dir, terminal="orch_fix_proposed", last_action="diagnose")
            action["action"] = "diagnose"
            append_decision(run_dir, action)
            notify_human(f"Orch bug diagnosis for {run_id}: {diagnosis}", title="AAC healer")
            return action
        # auto
        if load_json(run_dir / "healer" / "state.json").get("orch_fix_spawned"):
            action["action"] = "skip_duplicate_orch_fix"
            append_decision(run_dir, action)
            return action
        write_state(run_dir, status="needs_human", error=state.get("error") or "orch_bug")
        code, message = spawn_orch_fix(run_id, state, diagnosis, cfg)
        action.update({"action": "orch_fix_auto", "code": code, "message": message})
        append_decision(run_dir, action)
        notify_human(f"Healer orch fix for {run_id}: {message}", title="AAC healer")
        return action

    # escalate
    write_state(run_dir, status="needs_human", error=state.get("error") or f"healer:{kind}")
    mark_healer(run_dir, terminal="escalated", last_action="escalate")
    action["action"] = "escalate"
    append_decision(run_dir, action)
    notify_human(f"Healer escalated {run_id} ({state.get('status')})", title="AAC healer")
    return action


def heal_once(cfg: HealerConfig | None = None) -> list[dict]:
    settings = cfg or healer_cfg()
    if not settings.enabled:
        return []
    actions: list[dict] = []
    for run_dir in list_run_dirs():
        try:
            result = handle_run(run_dir, settings)
        except Exception as exc:  # noqa: BLE001
            result = {"run_id": run_dir.name, "action": "healer_error", "message": str(exc)}
            append_decision(run_dir, result)
            print(f"healer error {run_dir.name}: {exc}")
        if result:
            actions.append(result)
            print(f"healer {result}")
    return actions


def healer_cron(stop: threading.Event) -> None:
    while not stop.is_set():
        settings = healer_cfg()
        if settings.enabled:
            try:
                heal_once(settings)
            except Exception as exc:  # noqa: BLE001
                print(f"healer cron error: {exc}")
        stop.wait(settings.poll_sec)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Scan once and exit")
    parser.add_argument("--run-id", default="", help="Only consider this run id")
    args = parser.parse_args()
    settings = healer_cfg()
    if not settings.enabled:
        print("healer.enabled=false")
        return 0
    if args.run_id:
        run_dir = run_dir_for(args.run_id)
        if not (run_dir / "state.json").is_file():
            raise SystemExit(f"missing state for {args.run_id}")
        result = handle_run(run_dir, settings)
        print(json.dumps(result or {"run_id": args.run_id, "action": "ignore"}, indent=2))
        return 0
    if args.once:
        actions = heal_once(settings)
        print(json.dumps(actions, indent=2))
        return 0
    stop = threading.Event()
    print(f"healer loop poll_sec={settings.poll_sec} orch_fix={settings.orch_fix}")
    try:
        healer_cron(stop)
    except KeyboardInterrupt:
        stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

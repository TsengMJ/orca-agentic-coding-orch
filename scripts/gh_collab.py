#!/usr/bin/env python3
"""One Issue → one draft PR, driven by stage labels.

publish: push an approved-by-review spec onto feature/<slug> or fix/<slug> and open a draft PR into dev.
check:   read the latest human /approve or /abort on that PR.
apply:   turn that comment into the local human gate (approve starts S2).
watch:   apply new comments on open PRs that carry a waiting stage label.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from aac_common import ROOT, load_workflow
from ids import branch_name as branch_from_title
from ids import issue_run_id, parse_run_id, pr_run_id, repo_slug
from stage_labels import (
    ABORT,
    LABEL_COLORS,
    LABEL_DESCRIPTIONS,
    READY,
    all_workflow_labels,
    approved_label,
    labels_cfg,
    next_waiting,
    tech_lead_note,
    waiting_labels,
)

ORCH_MARKER = "<!-- aac-orchestrator -->"


def gh_cfg() -> dict:
    cfg = (load_workflow().get("github") or {})
    if cfg.get("issue_pr") not in (None, "one-to-one"):
        raise SystemExit(f"unsupported github.issue_pr={cfg.get('issue_pr')!r}; only one-to-one is implemented")
    return cfg


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "command failed").strip())
    return result


def github_ssh_url(run_id: str | None = None) -> str:
    """Push URL for the product repo. Avoid HTTPS remotes that prompt in non-interactive agents."""
    return f"git@github.com:{repo(run_id)}.git"


def git_push_head(work: Path, branch: str, *, run_id: str | None = None, set_upstream: bool = True) -> None:
    url = github_ssh_url(run_id)
    cmd = ["git", "push"]
    if set_upstream:
        cmd += ["-u", url, f"HEAD:{branch}"]
    else:
        cmd += [url, f"HEAD:{branch}"]
    run(cmd, cwd=work)


def repo(run_id: str | None = None) -> str:
    """Product repo for Issues/PRs — not necessarily the orch checkout.

    Resolution order: run github.json `repo` → `AAC_GITHUB_REPO` → config `github.repo`.
    PRs must open in the project under development, never silently default away from
    an explicit per-run/product setting.
    """
    if run_id:
        meta = load_github_meta(run_id)
        configured = str(meta.get("repo") or "").strip()
        if configured:
            return configured
    env = os.environ.get("AAC_GITHUB_REPO", "").strip()
    if env:
        return env
    return str(gh_cfg().get("repo") or "TsengMJ/orca-agentic-coding-orch")


def load_github_meta(run_id: str) -> dict:
    path = ROOT / "aac" / ".run" / run_id / "github.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_github_meta(run_id: str, data: dict) -> None:
    path = ROOT / "aac" / ".run" / run_id / "github.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def branch_name(issue: int) -> str:
    meta = run(
        [
            "gh", "issue", "view", str(issue),
            "--repo", repo(),
            "--json", "title,labels",
        ]
    )
    data = json.loads(meta.stdout)
    names = {label.get("name", "").lower() for label in data.get("labels") or []}
    title = data["title"]
    kind = "fix" if "bug" in names or title.lower().startswith(("fix:", "fix/")) else "feature"
    return branch_from_title(kind, title)


def ensure_label(name: str, *, run_id: str | None = None) -> None:
    color = LABEL_COLORS.get(name, "ededed")
    desc = LABEL_DESCRIPTIONS.get(name, name)
    run(
        [
            "gh", "label", "create", name,
            "--repo", repo(run_id),
            "--color", color,
            "--description", desc,
            "--force",
        ],
        check=False,
    )


def ensure_workflow_labels(*, run_id: str | None = None) -> None:
    for name in sorted(all_workflow_labels()):
        ensure_label(name, run_id=run_id)


def pr_label_names(pr: int, *, run_id: str | None = None) -> set[str]:
    viewed = run(
        ["gh", "pr", "view", str(pr), "--repo", repo(run_id), "--json", "labels"],
        check=False,
    )
    if viewed.returncode != 0:
        return set()
    data = json.loads(viewed.stdout or "{}")
    return {label.get("name", "") for label in data.get("labels") or []}


def set_exclusive_pr_label(pr: int, label: str, *, run_id: str | None = None) -> None:
    """Keep exactly one workflow label on the PR."""
    ensure_label(label, run_id=run_id)
    current = pr_label_names(pr, run_id=run_id)
    for name in sorted(current & all_workflow_labels()):
        if name != label:
            run(
                ["gh", "pr", "edit", str(pr), "--repo", repo(run_id), "--remove-label", name],
                check=False,
            )
    if label not in current:
        run(
            ["gh", "pr", "edit", str(pr), "--repo", repo(run_id), "--add-label", label],
            check=False,
        )


def issue_remove_label(issue: int, label: str, *, run_id: str | None = None) -> None:
    run(
        [
            "gh", "issue", "edit", str(issue),
            "--repo", repo(run_id),
            "--remove-label", label,
        ],
        check=False,
    )


def post_pr_comment(pr: int, body: str, *, run_id: str | None = None) -> None:
    text = body.rstrip() + "\n\n" + ORCH_MARKER
    run(
        ["gh", "pr", "comment", str(pr), "--repo", repo(run_id), "--body", text],
        check=False,
    )


def post_issue_comment(issue: int, body: str, *, run_id: str | None = None) -> None:
    text = body.rstrip() + "\n\n" + ORCH_MARKER
    run(
        [
            "gh", "issue", "comment", str(issue),
            "--repo", repo(run_id),
            "--body", text,
        ],
        check=False,
    )


def report_stage(
    run_id: str,
    *,
    stage: str,
    delivered: str,
    next_step: str,
    outcome: str = "done",
    label: str | None = None,
) -> None:
    """Always update the product Issue/PR when a stage ends — success or failure.

    Prefer the draft PR once it exists; otherwise comment on the Issue so cron
    progress is still visible before publish.
    """
    meta = load_github_meta(run_id)
    if label:
        meta["label"] = label
        write_github_meta(run_id, meta)
    note = tech_lead_note(stage=stage, delivered=delivered, next_step=next_step, outcome=outcome)
    if os.environ.get("AAC_E2E_SKIP", "").strip().lower() in {"1", "true", "yes", "on"}:
        return
    pr = meta.get("pr")
    if pr:
        if label:
            set_exclusive_pr_label(int(pr), label, run_id=run_id)
        post_pr_comment(int(pr), note, run_id=run_id)
        return
    issue = meta.get("issue")
    if issue:
        post_issue_comment(int(issue), note, run_id=run_id)


def relocate_run(run_id: str, final_id: str) -> None:
    if run_id == final_id:
        return
    for root in (ROOT / "aac" / "docs", ROOT / "aac" / ".run"):
        src = root / run_id
        dst = root / final_id
        if not src.exists():
            continue
        if dst.exists():
            raise SystemExit(f"refusing to overwrite {dst}")
        shutil.move(src, dst)


def latest_human_command(comments: list[dict]) -> str | None:
    """Last /approve or /abort from a comment that is not an orchestrator note."""
    found: str | None = None
    for comment in comments:
        body = (comment.get("body") or "").strip()
        if ORCH_MARKER in body:
            continue
        first = body.splitlines()[0].strip().lower() if body else ""
        if first in {"/approve", "/abort"}:
            found = first
    return found


def publish(issue: int, run_id: str, *, cwd: Path | None = None) -> str:
    """Publish draft PR with Spec label. Returns final run_id."""
    kind, number = parse_run_id(run_id)
    if kind != "issue" or number != issue:
        raise SystemExit(f"run_id {run_id} does not match issue #{issue}")
    if repo_slug(repo()) not in run_id:
        raise SystemExit(f"run_id {run_id} does not match repo {repo()}")

    branch = branch_name(issue)
    work = cwd or ROOT
    spec = work / "aac" / "docs" / run_id / "spec.md"
    if not spec.is_file():
        # Prefer AAC_ROOT / ROOT docs when cwd is only for git.
        alt = ROOT / "aac" / "docs" / run_id / "spec.md"
        if alt.is_file():
            spec = alt
        else:
            raise SystemExit(f"missing spec: {spec}")
    meta = run(["gh", "issue", "view", str(issue), "--repo", repo(), "--json", "title,body,state"])
    issue_data = json.loads(meta.stdout)
    if issue_data.get("state") != "OPEN":
        raise SystemExit(f"issue #{issue} is {issue_data.get('state')}")

    base = str(gh_cfg().get("base") or "dev")
    run(["git", "fetch", "origin", base], cwd=work)
    run(["git", "checkout", "-B", branch, f"origin/{base}"], cwd=work)
    # Spec may live on the orchestrator ROOT while git work is in a worktree.
    dest_spec = work / "aac" / "docs" / run_id / "spec.md"
    dest_spec.parent.mkdir(parents=True, exist_ok=True)
    if spec.resolve() != dest_spec.resolve():
        dest_spec.write_bytes(spec.read_bytes())
    run(["git", "add", "-f", str(dest_spec.relative_to(work))], cwd=work)
    commit = run(["git", "status", "--porcelain"], check=False, cwd=work)
    if commit.stdout.strip():
        run(["git", "commit", "-m", f"Add spec for #{issue}.\n\nRun {run_id}."], cwd=work)
    git_push_head(work, branch, run_id=run_id, set_upstream=True)

    existing = run(
        ["gh", "pr", "list", "--repo", repo(), "--head", branch, "--json", "number,url,isDraft"],
        check=False,
    )
    prs = json.loads(existing.stdout or "[]")
    if prs:
        pr_url = prs[0]["url"]
        pr_number = int(prs[0]["number"])
    else:
        created = run(
            [
                "gh", "pr", "create",
                "--repo", repo(),
                "--base", base,
                "--head", branch,
                "--draft",
                "--title", issue_data["title"],
                "--body", "\n".join(
                    [
                        f"Refs #{issue}",
                        "",
                        f"Run `{run_id}`.",
                        "",
                        "Spec is ready. Comment `/approve` to start planning, or `/abort` to stop.",
                        "",
                        ORCH_MARKER,
                    ]
                ),
            ]
        )
        pr_url = created.stdout.strip()
        pr_number = int(pr_url.rstrip("/").split("/")[-1])

    final_id = pr_run_id(repo(), pr_number)
    relocate_run(run_id, final_id)
    if run_id != final_id and (work / "aac" / "docs" / run_id).exists():
        run(["git", "add", "-A", f"aac/docs/{run_id}", f"aac/docs/{final_id}"], cwd=work, check=False)
        status = run(["git", "status", "--porcelain"], check=False, cwd=work)
        if status.stdout.strip():
            run(["git", "commit", "-m", f"Name run {final_id}."], cwd=work)
            git_push_head(work, branch, run_id=final_id, set_upstream=False)

    cfg = labels_cfg()
    set_exclusive_pr_label(pr_number, cfg["spec"])
    prev = load_github_meta(final_id) or load_github_meta(run_id)
    write_github_meta(
        final_id,
        {
            "issue": issue,
            "pr": pr_number,
            "branch": branch,
            "run_id": final_id,
            "url": pr_url,
            "label": cfg["spec"],
            "repo": prev.get("repo") or repo(run_id),
            "worktree": prev.get("worktree") or (str(work) if work != ROOT else None),
        },
    )
    note = tech_lead_note(
        stage="Spec",
        delivered=f"Spec landed on `{branch}` as draft PR #{pr_number}",
        next_step="`/approve` to start the plan, or `/abort` to stop",
    )
    post_pr_comment(pr_number, note)
    print(f"run_id={final_id}")
    print(f"branch={branch}")
    print(pr_url)
    return final_id


def pr_for_issue(issue: int) -> dict:
    branch = branch_name(issue)
    listed = run(
        ["gh", "pr", "list", "--repo", repo(), "--head", branch, "--state", "open", "--json", "number,url"]
    )
    prs = json.loads(listed.stdout or "[]")
    if not prs:
        raise SystemExit(f"no open PR for branch {branch}")
    number = str(prs[0]["number"])
    viewed = run(
        ["gh", "pr", "view", number, "--repo", repo(), "--json", "comments,url,number,labels"]
    )
    data = json.loads(viewed.stdout)
    data["command"] = latest_human_command(data.get("comments") or [])
    return data


def check(issue: int) -> None:
    data = pr_for_issue(issue)
    print(json.dumps({"pr": data["number"], "url": data["url"], "command": data["command"]}, indent=2))


def classify_body(body: str) -> str | None:
    """approve, abort, feedback, or None when the comment is empty or ours."""
    if ORCH_MARKER in (body or ""):
        return None
    text = (body or "").strip()
    if not text:
        return None
    first = text.splitlines()[0].strip().lower()
    if first in {"/approve", "/abort"}:
        return first
    return "feedback"


def current_waiting_label(labels: list[dict] | set[str]) -> str | None:
    names = {item.get("name", "") if isinstance(item, dict) else str(item) for item in labels}
    for waiting in waiting_labels():
        if waiting in names:
            return waiting
    return None


def mark_abort(pr: int, run_id: str) -> None:
    cfg = labels_cfg()
    set_exclusive_pr_label(pr, cfg["abort"])
    post_pr_comment(pr, tech_lead_note(stage="Abort", delivered="Run stopped", next_step="No further orchestrator action"))
    run(
        [
            "gh", "pr", "close", str(pr),
            "--repo", repo(),
            "--comment", f"Aborted.\n\n{ORCH_MARKER}",
        ],
        check=False,
    )
    meta = load_github_meta(run_id)
    meta["label"] = cfg["abort"]
    write_github_meta(run_id, meta)


def mark_pr_ready(run_id: str) -> tuple[int, str]:
    """After S6: leave draft mode, sync PR body, wait for human merge."""
    meta = load_github_meta(run_id)
    pr = meta.get("pr")
    if not pr:
        return 0, "no PR linked; skip ready"
    if __import__("os").environ.get("AAC_E2E_SKIP", "").strip() in {"1", "true", "yes"}:
        meta["draft"] = False
        write_github_meta(run_id, meta)
        return 0, f"PR #{pr} marked ready (e2e)"
    body = ROOT / "aac" / "docs" / run_id / "pr-body.md"
    if body.is_file():
        run(
            [
                "gh", "pr", "edit", str(pr),
                "--repo", repo(),
                "--body-file", str(body),
            ],
            check=False,
        )
    ready = run(["gh", "pr", "ready", str(pr), "--repo", repo()], check=False)
    cfg = labels_cfg()
    set_exclusive_pr_label(int(pr), cfg["gate"])
    meta["label"] = cfg["gate"]
    meta["draft"] = False
    write_github_meta(run_id, meta)
    base = str(gh_cfg().get("base") or "dev")
    post_pr_comment(
        int(pr),
        tech_lead_note(
            stage="Gate",
            delivered="S6 accepted; draft converted to ready-for-review",
            next_step=f"`/approve` to merge into `{base}`, or merge on GitHub",
        ),
    )
    if ready.returncode != 0:
        msg = (ready.stderr or ready.stdout or "").strip()
        if "already ready" in msg.lower() or "not a draft" in msg.lower():
            return 0, f"PR #{pr} already ready for review"
        return ready.returncode or 1, msg or f"failed to mark PR #{pr} ready"
    return 0, f"PR #{pr} is ready for review"


def merge_pr(pr: int, run_id: str) -> tuple[int, str]:
    cfg = labels_cfg()
    # E2E must short-circuit before any `gh` call — CI/dogfood hosts may lack gh.
    if __import__("os").environ.get("AAC_E2E_SKIP", "").strip() in {"1", "true", "yes"}:
        from aac_common import write_state

        write_state(ROOT / "aac" / ".run" / run_id, status="merged", human_gate="merged")
        return 0, f"merged PR #{pr} into dev (e2e)"
    set_exclusive_pr_label(pr, cfg["gate_approved"])
    post_pr_comment(
        pr,
        tech_lead_note(
            stage="Gate",
            delivered="Gate approved; merging into dev",
            next_step="No further human gate",
        ),
    )
    base = str(gh_cfg().get("base") or "dev")
    # Ensure non-draft before merge (S6 should already have done this).
    run(["gh", "pr", "ready", str(pr), "--repo", repo()], check=False)
    result = run(
        [
            "gh", "pr", "merge", str(pr),
            "--repo", repo(),
            "--merge",
            f"--body=Gate_Approved merge into {base}.\n\n{ORCH_MARKER}",
        ],
        check=False,
    )
    if result.returncode != 0:
        return result.returncode or 1, (result.stderr or result.stdout or "merge failed").strip()
    from aac_common import write_state

    write_state(ROOT / "aac" / ".run" / run_id, status="merged", human_gate="merged")
    meta = load_github_meta(run_id)
    meta["label"] = cfg["gate_approved"]
    write_github_meta(run_id, meta)
    return 0, f"merged PR #{pr} into {base}"


def stage_complete(run_id: str, approved: str, *, delivered: str, next_step: str) -> None:
    """After a stage succeeds: swap *_Approved → next waiting label and post TL note."""
    nxt = next_waiting(approved)
    if nxt is None:
        return
    stage = approved.removesuffix("_Approved")
    report_stage(
        run_id,
        stage=stage,
        delivered=delivered,
        next_step=next_step,
        outcome="done",
        label=nxt,
    )


def stage_failed(run_id: str, *, stage: str, error: str, next_step: str = "Healer or human will resume") -> None:
    """Stage ended in failure/abort — still update the product Issue/PR."""
    report_stage(
        run_id,
        stage=stage,
        delivered=error,
        next_step=next_step,
        outcome="failed",
    )


def apply_comments(run_id: str, comments: list[dict], seen: set[str], *, pr: int | None = None) -> list[str]:
    """Apply new human comments in order. Seen ids are updated only after success."""
    from pipeline import continue_run, feedback_run

    meta = load_github_meta(run_id)
    pr_number = int(pr or meta.get("pr") or 0)
    messages: list[str] = []
    for comment in comments:
        cid = str(comment.get("id") or "")
        if not cid or cid in seen:
            continue
        kind = classify_body(comment.get("body") or "")
        if kind is None:
            seen.add(cid)
            continue
        if kind == "/abort":
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "s1_human_gate.py"), "--run-id", run_id, "--abort"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if pr_number:
                mark_abort(pr_number, run_id)
            code, message = result.returncode, "aborted"
        elif kind == "/approve":
            if pr_number:
                e2e = __import__("os").environ.get("AAC_E2E_SKIP", "").strip() in {"1", "true", "yes"}
                if e2e:
                    from pipeline import load_state

                    status = load_state(run_id).get("status") or ""
                    status_to_waiting = {
                        "awaiting_human_gate": "Spec",
                        "spec_review_approved": "Spec",
                        "plan_approved": "Plan",
                        "awaiting_human_plan_gate": "Plan",
                        "acceptance_protected": "Acceptance",
                        "task_committed": "Implement",
                        "branch_review_approved": "Gate",
                        "final_accepted": "Gate",
                    }
                    waiting = status_to_waiting.get(status)
                else:
                    waiting = current_waiting_label(pr_label_names(pr_number))
                if waiting:
                    approved = approved_label(waiting)
                    meta = load_github_meta(run_id)
                    meta["label"] = approved
                    write_github_meta(run_id, meta)
                    if not e2e:
                        set_exclusive_pr_label(pr_number, approved, run_id=run_id)
            code, message = continue_run(run_id, pr=pr_number or None)
        else:
            code, message = feedback_run(run_id, comment.get("body") or "")
        if code != 0:
            messages.append(f"failed {code}: {message}")
            break
        seen.add(cid)
        messages.append(message)
    return messages


def watch_once() -> int:
    waiting = set(waiting_labels())
    listed = run(
        [
            "gh", "pr", "list",
            "--repo", repo(),
            "--base", str(gh_cfg().get("base") or "dev"),
            "--state", "open",
            "--json", "number,headRefName,url,labels",
        ]
    )
    failures = 0
    for pr in json.loads(listed.stdout or "[]"):
        names = {label.get("name", "") for label in pr.get("labels") or []}
        if not (names & waiting):
            continue
        run_id = pr_run_id(repo(), int(pr["number"]))
        run_dir = ROOT / "aac" / ".run" / run_id
        if not run_dir.is_dir():
            print(f"skip PR {pr['number']}: no local run {run_id}")
            continue
        viewed = run(
            ["gh", "pr", "view", str(pr["number"]), "--repo", repo(), "--json", "comments,labels"]
        )
        payload = json.loads(viewed.stdout)
        comments = payload.get("comments") or []
        seen_path = run_dir / "github-seen.json"
        seen = set(json.loads(seen_path.read_text(encoding="utf-8"))) if seen_path.is_file() else set()
        messages = apply_comments(run_id, comments, seen, pr=int(pr["number"]))
        seen_path.write_text(json.dumps(sorted(seen), indent=2) + "\n", encoding="utf-8")
        for message in messages:
            print(f"PR {pr['number']}: {message}")
            if message.startswith("failed"):
                failures += 1
            # Tech Lead notes are posted by stage helpers; keep a short orch ack for apply result.
            if message.startswith("failed") or message.startswith("merged") or message == "aborted":
                post_pr_comment(int(pr["number"]), message, run_id=run_id)
    return 1 if failures else 0


def apply_cmd(issue: int, run_id: str) -> int:
    data = pr_for_issue(issue)
    command = data["command"]
    if command is None:
        print("no /approve or /abort yet")
        return 0
    if command == "/abort":
        mark_abort(int(data["number"]), run_id)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "s1_human_gate.py"), "--run-id", run_id, "--abort"],
            cwd=ROOT,
            check=False,
        )
        return result.returncode
    messages = apply_comments(
        run_id,
        [{"id": f"apply-{data['number']}", "body": "/approve"}],
        set(),
        pr=int(data["number"]),
    )
    print("\n".join(messages) or "ok")
    return 0 if not any(m.startswith("failed") for m in messages) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    pub = sub.add_parser("publish")
    pub.add_argument("--issue", type=int, required=True)
    pub.add_argument("--run-id", required=True)
    pub.add_argument("--cwd", default="", help="Git worktree path for checkout/commit/push")

    chk = sub.add_parser("check")
    chk.add_argument("--issue", type=int, required=True)

    app = sub.add_parser("apply")
    app.add_argument("--issue", type=int, required=True)
    app.add_argument("--run-id", required=True)

    sub.add_parser("watch", help="Apply new PR comments once on waiting-label PRs")
    sub.add_parser("ensure-labels", help="Create workflow labels in the GitHub repo")

    args = parser.parse_args()
    if args.cmd == "publish":
        publish(args.issue, args.run_id, cwd=Path(args.cwd) if args.cwd else None)
        return 0
    if args.cmd == "check":
        check(args.issue)
        return 0
    if args.cmd == "watch":
        return watch_once()
    if args.cmd == "ensure-labels":
        ensure_workflow_labels()
        print("ok")
        return 0
    return apply_cmd(args.issue, args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())

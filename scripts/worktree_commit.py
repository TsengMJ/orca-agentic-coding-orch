"""Commit selected paths on the run's feature/fix branch without touching the current checkout."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from aac_common import ROOT


def git(args: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(["git", *args], cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "git failed").strip())


def _write_meta(run_id: str, meta: dict) -> Path:
    path = ROOT / "aac" / ".run" / run_id / "github.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return path


def ensure_local_meta(run_id: str) -> dict:
    """Local dogfood fallback when no Issue/PR publish happened yet."""
    branch = f"local/{run_id}"
    work = ROOT / "aac" / ".worktrees" / run_id
    meta = {
        "run_id": run_id,
        "branch": branch,
        "worktree": str(work),
        "local": True,
        "pr": None,
        "issue": None,
    }
    _write_meta(run_id, meta)
    if not work.exists():
        # Branch from current HEAD so local dogfood can commit without origin/<branch>.
        git(["worktree", "add", "-b", branch, str(work), "HEAD"])
    print(
        f"[aac] no github.json — local branch `{branch}` (no push). "
        "Publish a draft PR for remote collab.",
        flush=True,
    )
    return meta


def commit_paths(run_id: str, paths: list[str], message: str) -> None:
    meta_path = ROOT / "aac" / ".run" / run_id / "github.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    elif os.environ.get("AAC_REQUIRE_GITHUB", "").strip().lower() in {"1", "true", "yes", "on"}:
        raise SystemExit(f"missing github.json for {run_id}; branch is not encoded in run_id")
    else:
        meta = ensure_local_meta(run_id)

    branch = meta.get("branch")
    if not branch:
        raise SystemExit(f"github.json for {run_id} has no branch")
    preferred = Path(str(meta["worktree"])) if meta.get("worktree") else None
    work = preferred if preferred and preferred.is_dir() else ROOT / "aac" / ".worktrees" / run_id
    local = bool(meta.get("local"))
    if not work.exists():
        if local:
            git(["worktree", "add", "-b", branch, str(work), "HEAD"])
        else:
            git(["fetch", "origin", branch])
            git(["worktree", "add", str(work), f"origin/{branch}"])
    for rel in paths:
        src = ROOT / rel
        if not src.is_file():
            continue
        dest = work / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        git(["add", "--", rel], cwd=work)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=work, text=True, capture_output=True, check=False)
    if not status.stdout.strip():
        print(f"nothing to commit on {branch}")
        return
    git(["commit", "-m", message], cwd=work)
    if local:
        print(f"local commit on {branch} (no push): {message}")
        return
    git(["push", "origin", f"HEAD:{branch}"], cwd=work)
    print(f"pushed {message} to {branch}")

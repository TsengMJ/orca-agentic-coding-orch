"""Commit selected paths on the run's feature/fix branch without touching the current checkout."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aac_common import ROOT


def git(args: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(["git", *args], cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "git failed").strip())


def commit_paths(run_id: str, paths: list[str], message: str) -> None:
    meta_path = ROOT / "aac" / ".run" / run_id / "github.json"
    if not meta_path.is_file():
        raise SystemExit(f"missing github.json for {run_id}; branch is not encoded in run_id")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    branch = meta.get("branch")
    if not branch:
        raise SystemExit(f"github.json for {run_id} has no branch")
    preferred = Path(str(meta["worktree"])) if meta.get("worktree") else None
    work = preferred if preferred and preferred.is_dir() else ROOT / "aac" / ".worktrees" / run_id
    if not work.exists():
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
    git(["push", "origin", f"HEAD:{branch}"], cwd=work)
    print(f"pushed {message} to {branch}")

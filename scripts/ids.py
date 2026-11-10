"""Ids for multi-repo AAC runs.

branch:  feature/<slug> or fix/<slug>     (unchanged; from issue title)
run_id:  {repo}-issue-{n} before PR       TsengMJ-orca-agentic-coding-orch-issue-12
         {repo}-pr-{n} after publish      TsengMJ-orca-agentic-coding-orch-pr-34
task_id: {run_id}-T<nn>                   …-pr-34-T01

Branch is recorded in aac/.run/<run_id>/github.json — not encoded in the run id.
Every PR merges into `dev`.
"""

from __future__ import annotations

import re

SLUG_RE = re.compile(r"[^a-z0-9]+")
ISSUE_RUN_RE = re.compile(r"^(.+)-issue-(\d+)$")
PR_RUN_RE = re.compile(r"^(.+)-pr-(\d+)$")
TASK_RE = re.compile(r"^(.+)-pr-(\d+)-T(\d+)$")


def slugify(title: str) -> str:
    slug = SLUG_RE.sub("-", title.lower()).strip("-")
    slug = slug[:48].strip("-")
    return slug or "change"


def branch_name(kind: str, title: str) -> str:
    if kind not in {"feature", "fix"}:
        raise ValueError(f"branch kind must be feature or fix, got {kind}")
    return f"{kind}/{slugify(title)}"


def repo_slug(repo: str) -> str:
    return repo.strip().replace("/", "-")


def issue_run_id(repo: str, issue: int) -> str:
    return f"{repo_slug(repo)}-issue-{int(issue)}"


def pr_run_id(repo: str, pr: int) -> str:
    return f"{repo_slug(repo)}-pr-{int(pr)}"


def task_id(run_id: str, number: int) -> str:
    if not PR_RUN_RE.match(run_id):
        raise ValueError(f"task ids require a pr run_id, got {run_id}")
    return f"{run_id}-T{number:02d}"


def parse_run_id(run_id: str) -> tuple[str, int]:
    """Return ("issue"|"pr", number). Branch is not in the run id."""
    issue = ISSUE_RUN_RE.match(run_id)
    if issue:
        return "issue", int(issue.group(2))
    pr = PR_RUN_RE.match(run_id)
    if pr:
        return "pr", int(pr.group(2))
    raise ValueError(f"run_id must be {{repo}}-issue-N or {{repo}}-pr-N, got {run_id}")


def repo_from_run_id(run_id: str) -> str:
    issue = ISSUE_RUN_RE.match(run_id)
    if issue:
        return issue.group(1)
    pr = PR_RUN_RE.match(run_id)
    if pr:
        return pr.group(1)
    raise ValueError(f"run_id must be {{repo}}-issue-N or {{repo}}-pr-N, got {run_id}")

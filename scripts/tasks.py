"""Checkbox tasks in plan.md. Accepts `<run_id>-T01` or a legacy `T-01`."""

from __future__ import annotations

import re


def parse_tasks(text: str, run_id: str) -> list[dict]:
    rows = []
    full = re.compile(rf"\b{re.escape(run_id)}-T(\d+)\b")
    legacy = re.compile(r"\bT-(\d+)\b")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ["):
            continue
        match = full.search(stripped) or legacy.search(stripped)
        if not match:
            continue
        number = int(match.group(1))
        files = []
        files_match = re.search(r"files=([^;]+)", stripped)
        if files_match:
            files = [part.strip() for part in files_match.group(1).split(",") if part.strip()]
        rows.append(
            {
                "id": f"{run_id}-T{number:02d}",
                "number": number,
                "done": stripped.startswith("- [x]") or stripped.startswith("- [X]"),
                "files": files,
                "line": stripped,
            }
        )
    return rows


def mark_done(text: str, run_id: str, task_id: str) -> str:
    """Mark only the checkbox whose first task id is task_id (not deps mentions)."""
    number = int(task_id.rsplit("-T", 1)[-1])
    primary = re.compile(
        rf"^(\s*)- \[ \] ((?:{re.escape(task_id)}|T-{number})\b.*)$"
    )
    lines = []
    for line in text.splitlines():
        match = primary.match(line)
        if match:
            lines.append(f"{match.group(1)}- [x] {match.group(2)}")
        else:
            lines.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def normalize_ids(text: str, run_id: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"{run_id}-T{int(match.group(1)):02d}"

    return re.sub(r"\bT-(\d+)\b", repl, text)

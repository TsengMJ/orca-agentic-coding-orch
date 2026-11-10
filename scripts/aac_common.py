#!/usr/bin/env python3
"""Shared helpers for AAC stage scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ["AAC_ROOT"]).resolve() if os.environ.get("AAC_ROOT") else _DEFAULT_ROOT
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from resolve_slot import (  # noqa: E402
    DEFAULT_CONFIG,
    apply_env_overrides,
    load_config,
    resolve_slot,
)


def utc_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def ensure_run_dirs(run_id: str) -> dict[str, Path]:
    docs = ROOT / "aac" / "docs" / run_id
    run = ROOT / "aac" / ".run" / run_id
    archive = run / "archive"
    reviews = run / "reviews" / "spec"
    for p in (docs, run, archive, reviews):
        p.mkdir(parents=True, exist_ok=True)
    return {"docs": docs, "run": run, "archive": archive, "reviews": reviews, "root": ROOT}


def seed_verdict(path: Path) -> None:
    path.write_text(
        json.dumps(
            {"approved": False, "blockers": ["pending-review"], "suggestions": []},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_verdict(path: Path) -> dict:
    if not path.exists():
        return {"approved": False, "blockers": ["missing-verdict.json"], "suggestions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"approved": False, "blockers": ["unparseable-verdict.json"], "suggestions": []}
    if not isinstance(data, dict):
        return {"approved": False, "blockers": ["verdict-not-object"], "suggestions": []}
    approved = data.get("approved") is True
    blockers = data.get("blockers")
    suggestions = data.get("suggestions")
    if not isinstance(blockers, list):
        return {"approved": False, "blockers": ["blockers-not-list"], "suggestions": []}
    if not isinstance(suggestions, list):
        suggestions = []
    # Fail closed: approved implies empty blockers
    if approved and blockers:
        return {
            "approved": False,
            "blockers": ["approved-true-with-blockers"] + [str(b) for b in blockers],
            "suggestions": [str(s) for s in suggestions],
        }
    if approved and not blockers:
        return {"approved": True, "blockers": [], "suggestions": [str(s) for s in suggestions]}
    return {
        "approved": False,
        "blockers": [str(b) for b in blockers] or ["not-approved"],
        "suggestions": [str(s) for s in suggestions],
    }


def append_suggestions(run_dir: Path, stage: str, round_n: int, suggestions: list[str]) -> None:
    if not suggestions:
        return
    path = run_dir / "suggestions.md"
    block = [f"## {stage}(round {round_n})", ""]
    for s in suggestions:
        block.append(f"- {s}")
    block.append("")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(block))


# Legacy prompt-printed marker. Recognized if an old prompt still emits it, but
# never injected: completion must come from cursor agent stream-json `result`
# (or process exit). Prompt-dependent end fields caused silent 480s hangs.
DONE_SENTINEL = "AAC_AGENT_DONE"
STREAM_RESULT_TYPE = "result"


def _close_pipes(proc: subprocess.Popen[str]) -> None:
    if proc.stdout is not None:
        try:
            proc.stdout.close()
        except OSError:
            pass


def _reap(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    _close_pipes(proc)


def _parse_end_signal(line: str) -> tuple[bool, int | None]:
    """Return (saw_end, forced_rc). forced_rc is set for stream-json error results."""
    stripped = line.strip()
    if not stripped:
        return False, None
    if DONE_SENTINEL in stripped and not stripped.lstrip().startswith("{"):
        return True, 0
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        if DONE_SENTINEL in stripped:
            return True, 0
        return False, None
    if not isinstance(event, dict):
        return False, None
    if event.get("type") == STREAM_RESULT_TYPE:
        is_error = event.get("is_error") is True or event.get("subtype") == "error"
        return True, (1 if is_error else 0)
    return False, None


def _tool_call_label(tool_call: object) -> str:
    if not isinstance(tool_call, dict):
        return "tool"
    for key, payload in tool_call.items():
        if key in {"hookAdditionalContexts", "toolCallId", "startedAtMs"}:
            continue
        name = key[:-8] if key.endswith("ToolCall") else key
        detail = ""
        if isinstance(payload, dict):
            args = payload.get("args")
            if isinstance(args, dict):
                for field in ("path", "globPattern", "command", "pattern", "query"):
                    if args.get(field):
                        detail = f" {args[field]}"
                        break
        return f"{name}{detail}"
    return "tool"


def _stream_line(line: str) -> None:
    """Pretty-print stream-json when possible; otherwise echo the raw line.

    Tool starts are shown so a long tool-only stretch is not mistaken for a hang.
    """
    stripped = line.strip()
    if not stripped:
        return
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        print(line, flush=True)
        return
    if not isinstance(event, dict):
        print(line, flush=True)
        return
    etype = event.get("type")
    if etype == "assistant":
        message = event.get("message") or {}
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if text:
                        print(text, end="", flush=True)
        return
    if etype == "tool_call" and event.get("subtype") == "started":
        label = _tool_call_label(event.get("tool_call"))
        print(f"\n[aac] tool {label}", flush=True)
        return
    if etype == "thinking" and event.get("subtype") == "delta":
        return
    if etype == STREAM_RESULT_TYPE:
        subtype = event.get("subtype") or "?"
        print(f"\n[aac] agent result subtype={subtype}\n", flush=True)
        return


def run_command_reaping_done(
    cmd: list[str],
    *,
    timeout_sec: int,
    grace_sec: int,
    stream: bool,
    cwd: Path,
    banner: str = "",
) -> subprocess.CompletedProcess[str]:
    """Run cmd; treat stream-json `result` (or process exit) as the end signal.

    If the CLI emits a protocol end event but does not exit, reap after grace_sec.
    Uses select() so a silent process cannot block past timeout_sec.
    """
    import select
    import time

    if banner and stream:
        print(banner, flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert proc.stdout is not None
    fd = proc.stdout.fileno()
    chunks: list[str] = []
    pending = ""
    saw_done = False
    done_at: float | None = None
    forced_rc: int | None = None
    start = time.monotonic()

    def _text() -> str:
        return "".join(chunks)

    def _note_and_return(note: str, rc: int) -> subprocess.CompletedProcess[str]:
        if stream:
            print(note, end="", flush=True)
        return subprocess.CompletedProcess(cmd, rc, _text() + note, "")

    try:
        while True:
            now = time.monotonic()
            if saw_done and done_at is not None and now - done_at >= grace_sec:
                _reap(proc)
                rc = 0 if forced_rc is None else forced_rc
                note = (
                    f"\n[aac] reaped agent {grace_sec}s after end signal "
                    f"(process did not exit)\n"
                )
                return _note_and_return(note, rc)
            if timeout_sec > 0 and now - start >= timeout_sec:
                _reap(proc)
                if saw_done:
                    rc = 0 if forced_rc is None else forced_rc
                    note = "\n[aac] reaped agent at wall timeout after end signal\n"
                    return _note_and_return(note, rc)
                note = f"\n[aac] cursor agent timed out after {timeout_sec}s\n"
                return _note_and_return(note, 124)

            wait = 0.5
            if saw_done and done_at is not None:
                wait = min(wait, max(0.05, grace_sec - (now - done_at)))
            if timeout_sec > 0:
                wait = min(wait, max(0.05, timeout_sec - (now - start)))
            ready, _, _ = select.select([fd], [], [], wait)
            if not ready:
                if proc.poll() is not None and not select.select([fd], [], [], 0)[0]:
                    break
                continue
            try:
                data = os.read(fd, 65536)
            except BlockingIOError:
                continue
            if not data:
                if proc.poll() is not None:
                    break
                continue
            text = data.decode("utf-8", "replace")
            chunks.append(text)
            pending += text
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                if stream:
                    _stream_line(line)
                end, rc_hint = _parse_end_signal(line)
                if end and not saw_done:
                    saw_done = True
                    done_at = time.monotonic()
                    if rc_hint is not None:
                        forced_rc = rc_hint
        if pending:
            if stream:
                _stream_line(pending)
            end, rc_hint = _parse_end_signal(pending)
            if end and not saw_done:
                saw_done = True
                if rc_hint is not None:
                    forced_rc = rc_hint
        rc = proc.wait()
        _close_pipes(proc)
        if stream:
            print("\n── end stream ──\n", flush=True)
        if saw_done:
            if forced_rc is not None:
                rc = forced_rc
            elif rc != 0:
                rc = 0
        return subprocess.CompletedProcess(cmd, rc, _text(), "")
    except Exception:
        _reap(proc)
        raise


def run_cursor(
    model: str,
    prompt: str,
    *,
    force: bool = True,
    timeout_sec: int | None = None,
    stream: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if timeout_sec is None:
        timeout_sec = int(os.environ.get("AAC_AGENT_TIMEOUT_SEC", "480"))
    grace_sec = int(os.environ.get("AAC_DONE_GRACE_SEC", "12"))
    if os.environ.get("AAC_STREAM", "").strip().lower() in {"1", "true", "yes", "on"}:
        stream = True
    # End-of-run is the CLI protocol (`--output-format stream-json` → type=result)
    # or process exit — never a prompt-required printed field.
    cmd = [
        "cursor",
        "agent",
        "-p",
        "--model",
        model,
        "--output-format",
        "stream-json",
    ]
    if force:
        cmd.append("--force")
    cmd.append(prompt)
    banner = f"\n── cursor stream model={model} ──" if stream else ""
    return run_command_reaping_done(
        cmd,
        timeout_sec=timeout_sec,
        grace_sec=grace_sec,
        stream=stream,
        cwd=cwd or ROOT,
        banner=banner,
    )


def archive_text(archive: Path, name: str, body: str) -> Path:
    path = archive / name
    path.write_text(body, encoding="utf-8")
    return path


def load_workflow() -> dict:
    return apply_env_overrides(load_config(DEFAULT_CONFIG))


def slot_model(cfg: dict, name: str, stage: str | None = None) -> str:
    return resolve_slot(cfg, name, stage=stage)["model"]


def spawn_uv_script(
    script: str,
    args: list[str],
    *,
    log: Path,
    cwd: Path | None = None,
) -> subprocess.Popen[str]:
    """Start a stage script via `uv run` so the child outlives ephemeral uv build envs.

    Spawning with `sys.executable` from a temporary uv env fails later when that
    path is deleted (seen when S2 tried to start S3 after the temp build vanished).
    """
    cmd = ["uv", "run", "--with", "pyyaml", str(ROOT / "scripts" / script), *args]
    return subprocess.Popen(
        cmd,
        cwd=cwd or ROOT,
        stdout=log.open("a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )


def notify_human(message: str, *, title: str = "AAC") -> None:
    """Ping the operator. Terminal line, optional notify_cmd, macOS notification."""
    print(f"\n*** {title}: {message}\n", flush=True)
    try:
        cfg = load_workflow()
        cmd = str((cfg.get("gates") or {}).get("notify_cmd") or "").strip()
    except Exception:  # noqa: BLE001
        cmd = ""
    if cmd:
        subprocess.run(
            ["sh", "-c", cmd + ' "$1"', "aac-notify", message],
            cwd=ROOT,
            check=False,
            timeout=60,
        )
    if sys.platform == "darwin":
        script = (
            "display notification "
            + json.dumps(message)
            + " with title "
            + json.dumps(title)
        )
        subprocess.run(["osascript", "-e", script], check=False, timeout=15)


def write_state(run_dir: Path, **fields: object) -> None:
    path = run_dir / "state.json"
    current: dict = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
    current.update(fields)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

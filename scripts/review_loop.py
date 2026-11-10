#!/usr/bin/env python3
"""AAC-aligned review ↔ repair loop.

Workflow (not the AI) ends the loop:
  review → verdict → (blockers → owner fix → review)* → approve | abort@MAX_ROUNDS

Agent timeouts / nonzero exits get bounded same-call retries (gate_loop style),
then abort with a paste-ready resume command — never hang forever.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from aac_common import (
    ROOT,
    append_suggestions,
    archive_text,
    read_verdict,
    run_cursor,
    seed_verdict,
    write_state,
)


@dataclass
class LoopConfig:
    stage: str
    max_rounds: int = 3
    agent_call_retries: int = 2
    agent_timeout_sec: int = 480
    notify_cmd: str = ""
    skip_agents: bool = False
    stream: bool = False


@dataclass
class LoopPaths:
    run_dir: Path
    archive: Path
    reviews_root: Path  # e.g. aac/.run/<id>/reviews/spec
    artifact_path: Path  # e.g. spec.md
    run_id: str


@dataclass
class LoopResult:
    approved: bool
    rounds_used: int
    last_verdict: dict = field(default_factory=dict)
    status: str = ""
    resume_cmd: str = ""
    error: str = ""


def _tail(text: str, n: int = 150) -> str:
    lines = (text or "").splitlines()
    return "\n".join(lines[-n:])


def _notify(cfg: LoopConfig, message: str) -> None:
    if not cfg.notify_cmd.strip():
        return
    try:
        # AAC style: message as first argument
        subprocess.run(
            ["sh", "-c", cfg.notify_cmd + ' "$1"', "aac-notify", message],
            cwd=ROOT,
            check=False,
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001 — notify must not crash abort path
        print(f"[aac] notify_cmd failed: {exc}", flush=True)


def call_agent_with_repair(
    *,
    model: str,
    prompt: str,
    archive: Path,
    tag: str,
    cfg: LoopConfig,
    on_retry_prompt: Callable[[str, str], str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one logical agent step; retry on timeout/nonzero up to agent_call_retries."""
    attempts = 1 + max(0, cfg.agent_call_retries)
    last: subprocess.CompletedProcess[str] | None = None
    current_prompt = prompt

    for attempt in range(1, attempts + 1):
        archive_text(archive, f"{tag}-attempt-{attempt}-prompt.md", current_prompt)
        if cfg.skip_agents:
            return subprocess.CompletedProcess(["skip"], 0, "skipped", "")

        print(f"  · agent call {tag} attempt {attempt}/{attempts} (model={model})")
        last = run_cursor(
            model,
            current_prompt,
            timeout_sec=cfg.agent_timeout_sec,
            stream=cfg.stream,
        )
        archive_text(archive, f"{tag}-attempt-{attempt}-stdout.txt", last.stdout or "")
        archive_text(archive, f"{tag}-attempt-{attempt}-stderr.txt", last.stderr or "")

        if last.returncode == 0:
            return last

        fail_log = _tail((last.stderr or "") + "\n" + (last.stdout or ""))
        print(
            f"  · agent call failed rc={last.returncode}"
            + (" (timeout)" if last.returncode == 124 else ""),
            flush=True,
        )
        if attempt >= attempts:
            break
        # gate_loop-style: feed failure back and retry same responsibility
        if on_retry_prompt:
            current_prompt = on_retry_prompt(prompt, fail_log)
        else:
            current_prompt = (
                prompt
                + "\n\n## Previous attempt failed — repair and finish the original task\n"
                + "The workflow ran your previous call and it failed "
                + f"(exit {last.returncode}). Last log lines:\n\n```\n"
                + fail_log
                + "\n```\n\nComplete the original instructions. Do not stop halfway.\n"
            )

    assert last is not None
    return last


def abort_max_rounds(
    paths: LoopPaths,
    cfg: LoopConfig,
    last_verdict: dict,
    rounds_used: int,
    *,
    resume_hint: str,
) -> LoopResult:
    blockers = last_verdict.get("blockers") or []
    body = "\n".join(
        [
            f"# Aborted — {cfg.stage} review exhausted MAX_ROUNDS={cfg.max_rounds}",
            "",
            f"rounds_used: {rounds_used}",
            f"last_blockers: {json.dumps(blockers, ensure_ascii=False)}",
            "",
            "Per AAC: the workflow ends the loop; do not keep reviewing past the cap.",
            "Edit the artifact / raise `gates.max_rounds` if needed, then resume:",
            "",
            "```bash",
            resume_hint,
            "```",
            "",
        ]
    )
    abort_path = paths.run_dir / "REVIEW_ABORTED_MAX_ROUNDS.md"
    abort_path.write_text(body, encoding="utf-8")
    write_state(
        paths.run_dir,
        status="aborted_max_rounds",
        stage=cfg.stage,
        round=rounds_used,
        last_verdict=last_verdict,
        max_rounds=cfg.max_rounds,
    )
    msg = f"aac {paths.run_id}: {cfg.stage} aborted after {rounds_used}/{cfg.max_rounds} review rounds"
    _notify(cfg, msg)
    try:
        from gh_collab import stage_failed

        stage_failed(
            paths.run_id,
            stage=cfg.stage.capitalize(),
            error=f"MAX_ROUNDS={cfg.max_rounds} exhausted; blockers={json.dumps(blockers, ensure_ascii=False)}",
            next_step=resume_hint,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[aac] stage_failed notify skipped: {exc}", flush=True)
    print(f"ABORT MAX_ROUNDS → {abort_path}", flush=True)
    print(f"RESUME:\n{resume_hint}", flush=True)
    return LoopResult(
        approved=False,
        rounds_used=rounds_used,
        last_verdict=last_verdict,
        status="aborted_max_rounds",
        resume_cmd=resume_hint,
        error="max_rounds",
    )


def abort_agent_failure(
    paths: LoopPaths,
    cfg: LoopConfig,
    *,
    round_n: int,
    step: str,
    rc: int,
    resume_hint: str,
) -> LoopResult:
    body = "\n".join(
        [
            f"# Aborted — agent failure during {cfg.stage} / {step}",
            "",
            f"round: {round_n}",
            f"exit: {rc}",
            "",
            "Same-call repair retries were exhausted. Branch/artifacts left in place.",
            "Resume after fixing the environment or shortening the task:",
            "",
            "```bash",
            resume_hint,
            "```",
            "",
        ]
    )
    path = paths.run_dir / "AGENT_CALL_ABORTED.md"
    path.write_text(body, encoding="utf-8")
    write_state(
        paths.run_dir,
        status="aborted_agent_failure",
        stage=cfg.stage,
        round=round_n,
        error=f"{step}-exit-{rc}",
    )
    _notify(cfg, f"aac {paths.run_id}: agent failure {step} rc={rc}")
    try:
        from gh_collab import stage_failed

        stage_failed(
            paths.run_id,
            stage=cfg.stage.capitalize(),
            error=f"agent failure during {step} (exit {rc})",
            next_step=resume_hint,
        )
    except Exception as exc:  # noqa: BLE001 — PR update must not hide abort
        print(f"[aac] stage_failed notify skipped: {exc}", flush=True)
    print(f"ABORT AGENT → {path}", flush=True)
    return LoopResult(
        approved=False,
        rounds_used=round_n,
        status="aborted_agent_failure",
        resume_cmd=resume_hint,
        error=f"{step}:{rc}",
    )


def run_review_fix_loop(
    *,
    paths: LoopPaths,
    cfg: LoopConfig,
    model_owner: str,
    model_reviewer: str,
    build_review_prompt: Callable[[int, Path, Path], str],
    build_fix_prompt: Callable[[int, Path, Path], str],
    resume_hint: str,
    start_round: int = 1,
) -> LoopResult:
    """Bounded review/fix loop. `start_round` for resume within the same MAX_ROUNDS budget."""
    if start_round < 1:
        raise ValueError("start_round must be >= 1")
    if start_round > cfg.max_rounds:
        return abort_max_rounds(
            paths,
            cfg,
            {"approved": False, "blockers": ["resume-past-max-rounds"], "suggestions": []},
            cfg.max_rounds,
            resume_hint=resume_hint,
        )

    last_verdict: dict = {"approved": False, "blockers": ["not-started"], "suggestions": []}
    live_verdict = paths.run_dir / "verdict.json"

    for round_n in range(start_round, cfg.max_rounds + 1):
        round_dir = paths.reviews_root / f"r{round_n}"
        round_dir.mkdir(parents=True, exist_ok=True)
        review_path = round_dir / "review.md"
        verdict_path = round_dir / "verdict.json"
        seed_verdict(verdict_path)
        seed_verdict(live_verdict)

        review_prompt = build_review_prompt(round_n, review_path, verdict_path)
        tag = f"{100 + round_n:03d}-{cfg.stage}-review-r{round_n}"
        print(f"→ {cfg.stage} review (reviewer) round {round_n}/{cfg.max_rounds}…")
        rr = call_agent_with_repair(
            model=model_reviewer,
            prompt=review_prompt,
            archive=paths.archive,
            tag=tag,
            cfg=cfg,
        )
        if cfg.skip_agents:
            verdict_path.write_text(
                json.dumps({"approved": True, "blockers": [], "suggestions": ["stub"]}, indent=2)
                + "\n",
                encoding="utf-8",
            )
            review_path.write_text("# stub review\n", encoding="utf-8")
        elif rr.returncode != 0:
            return abort_agent_failure(
                paths,
                cfg,
                round_n=round_n,
                step="review",
                rc=rr.returncode,
                resume_hint=resume_hint,
            )

        last_verdict = read_verdict(verdict_path)
        live_verdict.write_text(json.dumps(last_verdict, indent=2) + "\n", encoding="utf-8")
        # archive round verdict copy
        archive_text(
            paths.archive,
            f"{100 + round_n:03d}-verdict-{cfg.stage}-r{round_n}.json",
            json.dumps(last_verdict, indent=2) + "\n",
        )
        append_suggestions(paths.run_dir, cfg.stage, round_n, last_verdict.get("suggestions") or [])
        write_state(
            paths.run_dir,
            stage=cfg.stage,
            round=round_n,
            last_verdict=last_verdict,
            status="reviewing",
            max_rounds=cfg.max_rounds,
        )
        print(
            f"verdict r{round_n}: approved={last_verdict['approved']} "
            f"blockers={last_verdict['blockers']}"
        )

        if last_verdict.get("approved") and not last_verdict.get("blockers"):
            write_state(paths.run_dir, status=f"{cfg.stage}_review_approved", round=round_n)
            return LoopResult(
                approved=True,
                rounds_used=round_n,
                last_verdict=last_verdict,
                status=f"{cfg.stage}_review_approved",
            )

        # Last allowed review round still not approved → abort (no extra fix after final review)
        if round_n >= cfg.max_rounds:
            return abort_max_rounds(
                paths, cfg, last_verdict, round_n, resume_hint=resume_hint
            )

        # Owner repair
        fix_prompt = build_fix_prompt(round_n, review_path, verdict_path)
        ftag = f"{100 + round_n:03d}-{cfg.stage}-fix-r{round_n}"
        print(f"→ {cfg.stage} fix (owner) after round {round_n}…")
        fr = call_agent_with_repair(
            model=model_owner,
            prompt=fix_prompt,
            archive=paths.archive,
            tag=ftag,
            cfg=cfg,
        )
        if not cfg.skip_agents and fr.returncode != 0:
            return abort_agent_failure(
                paths,
                cfg,
                round_n=round_n,
                step="fix",
                rc=fr.returncode,
                resume_hint=resume_hint,
            )

    return abort_max_rounds(paths, cfg, last_verdict, cfg.max_rounds, resume_hint=resume_hint)


def loop_config_from_workflow(
    cfg: dict,
    stage: str,
    *,
    skip_agents: bool = False,
    stream: bool = False,
) -> LoopConfig:
    gates = cfg.get("gates") or {}
    env_stream = os.environ.get("AAC_STREAM", "").strip().lower() in {"1", "true", "yes", "on"}
    return LoopConfig(
        stage=stage,
        max_rounds=int(gates.get("max_rounds") or 3),
        agent_call_retries=int(gates.get("agent_call_retries") or 2),
        agent_timeout_sec=int(
            gates.get("agent_timeout_sec")
            or os.environ.get("AAC_AGENT_TIMEOUT_SEC")
            or 480
        ),
        notify_cmd=str(gates.get("notify_cmd") or os.environ.get("AAC_NOTIFY_CMD") or ""),
        skip_agents=skip_agents,
        stream=stream or env_stream,
    )

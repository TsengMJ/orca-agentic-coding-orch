#!/usr/bin/env python3
"""One-shot: Grok reviews the Counter acceptance tests while writing a probe log.

Does not advance the pipeline. Writes review/verdict under aac/.run/<id>/probe/r1/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from aac_common import ROOT, DONE_SENTINEL, archive_text, run_cursor, slot_model, load_workflow

RUN_ID = "feature-add-counter-to-dogfood-pr-6"
PROBE = ROOT / "aac" / ".run" / RUN_ID / "probe" / "r1"
MONITOR = ROOT / "aac" / ".run" / RUN_ID / "probe" / "monitor.log"


def prompt() -> str:
    review = PROBE / "review.md"
    verdict = PROBE / "verdict.json"
    return f"""# Acceptance tests — reviewer (A) PROBE

You are **Test Reviewer (slot A)**. Follow `memory/roles/roles/05-test-reviewer.md`.

Review the acceptance tests against the approved spec. RED tests for unimplemented behavior are expected and are not blockers. Do not edit product code or the tests.

## Inputs

- Spec: `aac/docs/{RUN_ID}/spec.md`
- Matrix: `aac/docs/{RUN_ID}/acceptance-matrix.md`
- Test dir: `fixtures/dogfood/tests/acceptance/{RUN_ID}`

## Write exactly

1. `{review.relative_to(ROOT)}`
2. `{verdict.relative_to(ROOT)}` as one JSON object:

```json
{{"approved": false, "blockers": ["F-001: ..."], "suggestions": ["S-001: ..."]}}
```

`approved` is true only when blockers is []. Prefer at most one blocker theme. If the suite maps AC-01..AC-12 with clear RED/GREEN priors, approve.

## Done when

Both files exist. Print `approved=<bool> blockers=<n>` and stop.
"""


def main() -> int:
    PROBE.mkdir(parents=True, exist_ok=True)
    (PROBE / "verdict.json").write_text(
        json.dumps({"approved": False, "blockers": ["pending-review"], "suggestions": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROBE / "review.md").unlink(missing_ok=True)
    MONITOR.write_text(f"probe_start={time.time()}\n", encoding="utf-8")
    model = slot_model(load_workflow(), "A")
    timeout = int((__import__("os").environ.get("AAC_AGENT_TIMEOUT_SEC") or "480"))
    print(f"model={model} timeout={timeout}s probe={PROBE}", flush=True)
    started = time.time()
    result = run_cursor(model, prompt(), timeout_sec=timeout, stream=True)
    elapsed = time.time() - started
    archive = ROOT / "aac" / ".run" / RUN_ID / "probe" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    archive_text(archive, "stdout.txt", result.stdout or "")
    archive_text(archive, "stderr.txt", result.stderr or "")
    review_ok = (PROBE / "review.md").is_file()
    verdict = {}
    try:
        verdict = json.loads((PROBE / "verdict.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        verdict = {"error": str(exc)}
    summary = {
        "elapsed_sec": round(elapsed, 1),
        "returncode": result.returncode,
        "stdout_bytes": len(result.stdout or ""),
        "saw_done": DONE_SENTINEL in (result.stdout or ""),
        "review_written": review_ok,
        "verdict": verdict,
        "stdout_tail": "\n".join((result.stdout or "").splitlines()[-8:]),
    }
    (PROBE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if result.returncode == 0 and review_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

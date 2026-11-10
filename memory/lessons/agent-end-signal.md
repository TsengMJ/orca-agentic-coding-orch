# Agent end signal (2026-11-10)

## Failure

Agent calls burned the full `480s` wall timeout even after the model had finished useful work. Operators saw `cursor agent timed out after 480s` and treated it as flake.

## Root cause

Completion depended on the **prompt** requiring a printed field (`AAC_AGENT_DONE`). That is not a real end signal:

- Models omit or delay the marker.
- Workflow then waits until `AAC_AGENT_TIMEOUT_SEC` instead of recognizing that the turn ended.
- Reaping-on-sentinel was a workaround for a hung CLI, but the contract itself was wrong.

## Fix

- Call `cursor agent -p --output-format stream-json`.
- Treat protocol `{"type":"result",...}` (or clean process exit) as done.
- If the CLI hangs after `result`, reap after `AAC_DONE_GRACE_SEC`.
- Do **not** inject or require a prompt-printed done marker. Legacy markers may still reap if emitted.

## Regression

`scripts/test_agent_end_signal.py` — result-then-hang reaps quickly; no-result hangs time out; `run_cursor` must not inject `AAC_AGENT_DONE`.

## Rule of thumb

Ask: “Is this end condition a protocol/OS signal, or are we hoping the model cooperates?” Only the former belongs in the orchestrator.
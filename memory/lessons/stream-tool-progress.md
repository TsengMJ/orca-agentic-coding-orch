# Stream tool progress (2026-11-10)

## Failure mode

With `--output-format stream-json` and pretty streaming, only assistant text was shown.
Long stretches of `tool_call` activity produced **terminal silence**, which looked like another hang even after the 480s end-signal fix.

## Fix

On `tool_call` / `subtype=started`, print a one-line `[aac] tool …` progress marker (name + path/command when present). Keep archives as raw NDJSON.

## Rule

Operator-visible liveness must not depend on the model chatting. Protocol events (tools, `result`) are the heartbeat.
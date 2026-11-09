# Review / repair loop (AAC-aligned)

Normative upstream:

- [how-it-works.md](https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/how-it-works.md) — ⟳ review loop
- [gates.md](https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/gates.md) — `MAX_ROUNDS`, gate_loop repair
- [artifact-contract.md](https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/artifact-contract.md) — graded verdicts
- [agent-session-lifecycle.md](https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/agent-session-lifecycle.md) — fresh reviewer every round

## Rules (workflow decides, not the AI)

```text
reviewer (fresh each round)
  → verdict.json
      approved && blockers==[]  → stage continues
      blockers                   → owner repairs (same stage)
                                   → optional deterministic gate
                                   → review again
      MAX_ROUNDS exhausted       → abort + notify human (+ resume cmd)
```

1. **Only blockers** reopen the loop. Suggestions append to `suggestions.md` and wait for final stage.
2. **`MAX_ROUNDS` (default 3)** bounds review rounds **and** command-gate repairs. Raising it is a config change, not an ad-hoc resume past the cap.
3. **Fail closed** on missing/invalid `verdict.json`.
4. **Agent call failure / timeout** is repaired like a gate failure: feed the last log lines back, retry the **same** call up to `agent_call_retries`. If still failing → abort the run (do not hang, do not silently edit artifacts as the coordinator).
5. **Resume** restores workflow state and continues from the incomplete stage with a **fresh** agent process — it is not unbounded extra review rounds beyond `MAX_ROUNDS` unless the operator raises `gates.max_rounds` / `AAC_MAX_ROUNDS` for that attempt.

## What went wrong in dogfood `s1-20261109T081826Z`

| Issue | AAC rule | What we did |
| --- | --- | --- |
| Owner fix hung | Timeout → repair retry → abort | Killed process; coordinator hand-edited the spec |
| Review still blocking after 3 | Abort + notify | Manually resumed to rounds 4–7 |

That violated the bound. The shared loop in `scripts/review_loop.py` restores the AAC behavior.

## Config knobs

| Key / env | Default | Meaning |
| --- | --- | --- |
| `gates.max_rounds` / `AAC_MAX_ROUNDS` | `3` | Max review (and later gate-repair) rounds per stage |
| `gates.agent_call_retries` / `AAC_AGENT_CALL_RETRIES` | `2` | Extra attempts after timeout/nonzero for the **same** agent call |
| `gates.agent_timeout_sec` / `AAC_AGENT_TIMEOUT_SEC` | `480` | Per-call wall clock |
| `gates.notify_cmd` / `AAC_NOTIFY_CMD` | empty | Optional shell; message is `$1` on abort |

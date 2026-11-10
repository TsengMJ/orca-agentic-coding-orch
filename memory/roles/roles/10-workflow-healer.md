# Role 10 — Workflow Healer (sidecar)

## Mission
監看失敗／卡住的 run，分類後在政策內自動恢復或提出 orch 修復；**不是**產品 Spec/Plan/Code 的作者，也**不**取代 Role 00 的 Policy Engine。

## Inputs
`aac/.run/*/state.json`、`job.pid`、stage logs、`github.json`、server 錯誤字串、`config/workflow.yaml` 的 `healer` 段。

## Allowed
- 對 **agent flake**（timeout／偶發非零）在預算內 **resume** 同一 stage（不提高 `max_rounds`）。
- 對 **`publish_failed`** 在預算內重試 `gh_collab publish`。
- 對明確 **orch bug**（traceback／scripts 例外／資料不一致且非產品內容問題）：寫 diagnosis、可選 spawn coding agent 修 `scripts/` / `config/` / `docs/` / `memory/lessons/`，開 draft PR，並 `notify_human`。
- 將每次決策 append 到 run 的 `healer/decisions.jsonl` 與 `healer/state.json`。
- 無法安全動作時標 `needs_human` 並通知操作者。

## Forbidden
- 手改或讓 agent 改 **產品 artifact**（`spec.md` / `plan.md` / acceptance tests / 產品碼）來「假裝」stage 通過。
- 靜默提高 `gates.max_rounds` 或跳過 human gate。
- Auto-merge 任何 healing PR；高風險（lease／權限／merge policy）變更一律停在 draft + human。
- 對同一 run 無限 resume；超過 `healer.max_auto_resume_per_run` 必須 escalate。
- 把 MAX_ROUNDS 耗盡當成 flake 再自動開下一輪審查。

## Algorithm
1. Scan `aac/.run/*/state.json`（忽略已 `healer.ignored` 或終態已處理）。
2. Classify: `flake` | `publish_retry` | `orch_bug` | `stuck` | `escalate`.
3. Act within budget; record action; never edit stage product files.
4. Orch fix agent（若 `healer.orch_fix=auto`）只改允許路徑，最後一行印 `AAC_AGENT_DONE`；開 draft PR 後停。
5. 產品 run 維持 `needs_human` 直到人確認 healing 合併或手動 resume。

## Output
`aac/.run/<run_id>/healer/state.json`、`diagnosis.md`（orch_bug）、可選 healing branch/PR URL、操作者通知。

## Acceptance
- Flake 在預算內可自動恢復且不超過 `max_rounds`。
- Orch bug 留下可審的 draft PR 或至少 diagnosis + notify；從不靜默改產品 artifact。
- Crash 後可從 `healer/state.json` 避免重複 spawn 同一修復。

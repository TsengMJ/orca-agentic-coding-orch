# Role 00 — Orchestrator / Policy Engine

## Mission
以確定性狀態機協調 Issue 全生命週期、保護驗收標準、隔離各 Agent、執行 Gate、決策 Resume/Merge。你不是 Coding Agent，不透過 LLM 推斷任務已完成。

失敗／卡死 run 的監看與 orch 修復由 sidecar **Role 10 Workflow Healer**（`scripts/healer.py`）處理；Healer 不得改產品 artifact，也不得靜默提高 `max_rounds`。Policy 與 Merge 仍只屬於本角色。

## Inputs
Issue、repo+base SHA、風險標籤、角色路由設定、Gate commands、Merge Policy、各階段 Artifact。

## Allowed
- 建立 worktree/branch、run_id、鎖與狀態機；派發 Stage、隔離 Prompt 與工作目錄。
- 執行 CI/build/test/安全掃描和完整性檢查；保存 stdout/stderr、exit status、artifact hash。
- 根據 `approved=true && blockers.length==0`、`head_sha`、CI 狀態決定轉移；推送 PR、依 Policy Merge。
- 合併不同 Reviewer 的 findings 並保留所有原始版本。

## Forbidden
- 依自然語言「已測過」跳過 Gate；在缺少證據時 Auto Merge。
- 讓 Reviewer 修改受審檔案；讓 Coding Agent 修改受保護的 Acceptance Tests。
- 靜默放寬 Gate、閾值、風險標籤或回滾基準。

## Algorithm
1. Snapshot Issue、base SHA、rules、Gate commands 和 policy version。
2. Spec A→B loop，最多 3 round；Spec 人工核准（預設）。
3. Plan A→B loop；必要時人工核准。
4. Tests B→A loop；驗證新增需求 RED、回歸保護 GREEN；凍結 protected tests 與 base SHA。
5. I 逐 Task Coding → Build Gate → integrity check → commit。
6. Full CI green 才啟動 Code Review/QA/Security；必要時 Reviewer 可並行，但輸出不可共享/互覆。
7. 任一 Blocker → 重回對應修復責任人 → Full CI → 所有必要審查重新檢查新 SHA。
8. 讀取 merge-policy.yaml；低風險條件全部滿足 Auto Merge；其餘人工。
9. 任一階段到上限、依賴不可用、資料不一致：狀態設 `needs_human`，保存證據並停止。

## Output
`state.json`、`decisions.jsonl`、CI logs、agent prompt/transcripts、PR body、Merge decision。每筆決策包含 run_id/stage/round/base_sha/head_sha/gate_results/previous_state/next_state/reason。

## Acceptance
Crash 後可從已保存狀態 resume，無重複啟動同一 run；stale review 無法放行新 HEAD；沒配置 Gate 無法自動 Merge。

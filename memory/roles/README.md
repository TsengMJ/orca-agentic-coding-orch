# Agent Team Role Specification v1.0

> 基於 [adversarial-ai-coding](https://github.com/yhchiu/adversarial-ai-coding) 的 A/B/I、structured review、protected acceptance tests、bounded retry 與 deterministic gates。QA/Security 平行驗證、分級自動合併和擴充輸出合約是本方案新增的設計，不應視為原專案內建功能。

## 目標

為同時處理多個 Issue 的開發團隊建立可追蹤、可恢復、可自動化的工作流：需求 → 審查 → 計畫 → 對抗式驗收測試 → 實作 → CI → 獨立審查/QA → 修復 → Merge Gate。控制權永遠在 Orchestrator/Policy Engine，不在 Agent 的自然語言自述。

## 核心不可違反規則 (Global Invariants)

1. **隔離**：每個 Issue 有獨立 worktree/branch/run_id；同一 repo 可多 Issue，單一檔案不得由兩個 Coding Agent 無協調地並行寫入。
2. **無直接交接**：Agent 不依靠彼此聊天紀錄，僅透過 Orchestrator 提供的版本化 Artifact、Commit SHA 與完整 Prompt 交接。
3. **職責分離**：Spec 作者不得撰寫最終受保護的驗收測試；Coding Agent 不得編輯、刪除、跳過 protected acceptance tests。
4. **Reviewer 唯讀**：Reviewer 可讀取代碼、執行非破壞性測試，只能寫入自身 review artifact；不能修正受審內容。
5. **可驗證性**：`approved=true` 只有在 blocker 為空且審查基準 Commit 未過期時才有效；測試聲稱不等同測試通過，CI 的 Exit Code 才是證據。
6. **Fail Closed**：缺少、無法解析、Schema 不符、目標 Commit 不符、Gate 未配置、證據缺失，均不得自動合併。
7. **有界重試**：每個 Review/Fix Loop 最多 `MAX_ROUNDS=3`（初始建議）；到上限就升級人工，禁止無限互相修。
8. **可追溯**：每個 Prompt、模型版本、回覆、Review、Test Log、Artifact Hash、Commit SHA、成本與耗時都要歸檔。
9. **風險分級**：修改 Orchestrator、Lease、Scheduler、權限、金流、資料遷移或其他核心基建為 high-risk，禁止全自動 Merge。
10. **Policy 不由 Agent 變更**：Approval 閾值、Gate 指令、受保護測試清單、基準 Commit 與工作流狀態必須由 Orchestrator/人員維護。

## 角色對照

| Stage | Producer | Reviewer | 預期交付 |
|---|---|---|---|
| Spec | A Spec Owner | B Spec Reviewer | `spec.md`, `review.md`, `verdict.json` |
| Plan | A Planner | B Plan Reviewer | `plan.md`, `review.md`, `verdict.json` |
| Acceptance Tests | B Test Author | A Test Reviewer | tests + protected list + review/verdict |
| Implement | I Coding Agent | build/integrity gates | commits + execution report |
| Branch Review | I/A fix | B Code Reviewer | review/verdict |
| Runtime Verification | none (read-only target) | C QA Agent | qa report, logs, verdict |
| Security (依風險) | none | D Security Reviewer | security report, verdict |
| Merge | Orchestrator | deterministic policy | final decision record |

A/B/I 代表槽位，不是永久 Agent 實體。對抗式驗收測試階段 B 是作者、A 是 Reviewer；實作階段 I 是作者、B 是 Reviewer。角色切換必須重新初始化 Context，並遵守目前角色權限。

## 工作流（有限狀態機）

1. **Intake**：記錄 Issue、基準 SHA、受影響模組、風險等級；先確認既有 CI 與回歸基準是否可跑。
2. **Spec Loop**：A 撰寫 Spec；B 審查；有 blocker → A 回覆/修正 → B 重審。完成後人工批准 Spec（預設開啟）。
3. **Plan Loop**：A 拆為可驗證、小而獨立的 Task；B 審查；有 blocker 回到 A；必要時人工批准 Plan。
4. **Acceptance Tests Loop**：B 寫驗收測試，A 審查；新功能測試原則上先 RED，既有行為的 regression guards 應先 GREEN。Orchestrator 凍結通過的測試與基準 SHA。
5. **Implementation**：I 按 Task 實作，執行 `BUILD_GATE_CMD`，確認 protected tests 未變，每個 Task 個別 Commit。若並行需獨立 worktree 和明確檔案 ownership。
6. **Full CI**：Orchestrator 執行 `GATE_CMD`，必要套件的 build、unit、integration、acceptance、regression 全部通過；不能只採信 Agent 的敘述。
7. **Independent Reviews**：B Code Review 與 C QA（高風險加 D Security/第二 QA）可並行。各自針對相同 `head_sha` 產生獨立結果，不得互相參考對方的初始 Review。
8. **Repair Loop**：Orchestrator 將 blockers 去重後交回 I（產品程式碼）或相應原作者（Spec/Plan/Tests）；必須回覆每一個 Finding。修正後重跑受影響 CI 及最終 Full CI，並讓所有先前 Reviewer 基於新 SHA 再驗證。
9. **Merge Gate**：Policy Engine 只根據同一 HEAD 的最新 CI、Review、QA、Security 和風險標籤做決定。高風險進人工批准；低風險且所有 Gate 皆 PASS 才可 Auto Merge。

## Review/Fix 協定

- Reviewer 產生 `review.md` 和 `verdict.json`，引用具體檔案、行號或測試重現命令與證據。
- `blockers` 為必修項目；`suggestions` 不阻擋，但要留在 Backlog/Final review；不可用 Suggestions 藏 correctness/security 問題。
- 被審者逐條以 `Fixed: ...` 或 `Disagree: ...` 回覆；`Disagree` 必須包含理由與反證，不能自行關閉 Blocker。
- Reviewer 重審時先確認舊問題的修復，再檢查新問題。若 Commit SHA 改變，之前的 Approval 立即過期。
- 連續重試超過上限、依賴環境故障或 Spec 衝突必須標示 Escalation，不可為了通過而關閉測試或降低標準。

## Merge Policy（第一版保守建議）

- Auto Merge 僅限 `risk=low`、spec 已獲准、受保護測試不變、所有必要 CI 綠燈、沒有未解決 Blocker、Review/QA 指向同一 HEAD、必備 Gate 有配置、沒有 `needs_human` 標籤。
- `risk=medium` 預設人工 Merge，可在累積品質數據後白名單放行。
- `risk=high` 一律人工批准，並執行既有功能回歸測試與故障注入（適用時）。
- 不使用 LLM 自評的「95% confidence」作為 Merge 條件；若需分數，必須有歷史資料校準，且不能覆蓋硬性 Gate。

## 初始並行與 Skill/Rule 配置

| Stage | 並行設定 | 載入 Skill / 規則（檔名建議，非宣稱已安裝） |
|---|---|---|
| Spec | A=1 B=1 | `requirements-analysis`, `spec-review` |
| Plan | A=1 B=1 | `task-decomposition`, `plan-review` |
| Tests | B=1 A=1 | `acceptance-test-design`, `regression-design` |
| Implementation | I=1（獨立模組可 2） | `test-driven-development`, `systematic-debugging` |
| Code Review | B=1 | `adversarial-code-review`, `performance-review` |
| QA | C=1（高風險 2） | `runtime-qa`, `fault-injection`, `e2e-testing` |
| Security | D=0/1 按風險 | `security-review`, `permissions-audit` |
| Merge | 非 Agent Policy Engine | `merge-policy.yaml` |

跨階段 Global Invariants 常駐；各 Role Spec 在開始任務時載入；Stage Skills 隨階段注入，不要為每個 Agent 複製一份全域準則。

## 檔案佈局（本方案建議）

```text
aac/
  docs/<RUN_ID>/spec.md
  docs/<RUN_ID>/plan.md
  .run/<RUN_ID>/state.json                  # workflow owned
  .run/<RUN_ID>/protected-tests.json       # workflow owned
  .run/<RUN_ID>/reviews/<stage>/<round>/review.md
  .run/<RUN_ID>/reviews/<stage>/<round>/verdict.json
  .run/<RUN_ID>/reviews/<stage>/<round>/replies.md
  .run/<RUN_ID>/qa/<head_sha>/report.md
  .run/<RUN_ID>/qa/<head_sha>/verdict.json
  .run/<RUN_ID>/ci/<head_sha>/results.json
  .run/<RUN_ID>/archive/                    # Prompt、Logs、Hash、模型版本
```

> 注意：這個佈局是擴充版建議，與 adversarial-ai-coding 原專案既有 `aac/.run/verdict.json` 等路徑不同；若要直接插入原專案，應先寫路徑 Adapter。

## 文件入口

- [Orchestrator](roles/00-orchestrator.md)
- [Spec Owner](roles/01-spec-owner.md)
- [Spec Reviewer](roles/02-spec-reviewer.md)
- [Planner](roles/03-planner.md)
- [Acceptance Test Author](roles/04-acceptance-test-author.md)
- [Test Reviewer](roles/05-test-reviewer.md)
- [Coding Agent](roles/06-coding-agent.md)
- [Code Reviewer](roles/07-code-reviewer.md)
- [Runtime QA](roles/08-runtime-qa.md)
- [Security Reviewer](roles/09-security-reviewer.md)
- [Review schema](contracts/review-output.md)
- [Merge policy](contracts/merge-policy.yaml)

## 參考資料

- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/how-it-works.md
- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/artifact-contract.md
- https://github.com/yhchiu/adversarial-ai-coding/blob/master/docs/gates.md
- https://github.com/yhchiu/adversarial-ai-coding/blob/master/resources/AGENTS.template.md

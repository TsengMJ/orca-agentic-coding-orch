# Project Skills — Dev / Test / Security

給 `memory/roles` 工作流用的 skill 庫。預設入口是 **pstack 的 `poteto-mode`**；其餘 skill 依階段注入，不要一次全塞進每個 Agent。

來源明細見 [`_meta/SOURCES.md`](_meta/SOURCES.md)。

## 必用：pstack

整包 pstack 已扁平安裝在本目錄頂層（`poteto-mode`、`tdd`、`interrogate`、`blast-radius`、`architect`、`setup-pstack`、verification skills、principles…）。

| Skill | 何時用 |
|---|---|
| `poteto-mode` | 任何非平凡開發任務的預設入口 |
| `setup-pstack` | 設定各角色模型與 reasoning budget |
| `tdd` | Bug fix 有便宜的本地測試路徑時 |
| `interrogate` | 對抗式 / 多模型 review，只留可跑證明的 findings |
| `blast-radius` | 小改動，要證明不會壞別處 |
| `create-verification-skill` / `maintain-verification-skill` | 專案級「像使用者一樣操作」的驗證 harness |
| `create-formal-verification-skill` | 併發 / 狀態機等測試難覆蓋的性質證明 |
| `architect` / `arena` / `swarm` | 設計定型、平行候選、平行切片 |

## 對齊 Role Stage

| Stage | 建議 Skill |
|---|---|
| Plan | `writing-plans`, `executing-plans`, pstack `architect` |
| Acceptance / Tests | `test-driven-development` (obra), pstack `tdd`, `principle-test-behavior-not-implementation` |
| Implementation | `poteto-mode`, `test-driven-development`, `systematic-debugging`, `using-git-worktrees`, `subagent-driven-development` |
| Code Review | `code-review` (Matt), `requesting-code-review`, `receiving-code-review`, `interrogate`, `review-bugbot`, `find-bugs` |
| Runtime QA | `verification-before-completion`, `webapp-testing`, `browser-testing-with-devtools`, pstack verification skills |
| Security | `security-review`, `security-threat-model`, `security-best-practices`, `security-and-hardening`, `security-model`, `gha-security-review`, `review-security` |
| Merge / babysit | `autopilot`, pstack shipping/babysit playbooks via `poteto-mode` |

## 頂層精選（非 pstack）

### 開發

- `test-driven-development` — obra/superpowers（實作前紅燈）
- `systematic-debugging` — 修 bug 前先系統除錯
- `debugging-and-error-recovery` — addyosmani 根因除錯
- `diagnosing-bugs` — Matt 診斷迴圈
- `writing-plans` / `executing-plans` / `subagent-driven-development` / `using-git-worktrees`
- `verification-before-completion` — 宣告完成前必須有證據

### 測試 / QA

- `webapp-testing` — Playwright 測本地 web app
- `browser-testing-with-devtools` — Chrome DevTools MCP 瀏覽器驗證

### 審查

- `code-review` — Matt 雙軸（Standards + Spec）
- `code-review-and-quality` — 多維度品質審查
- `requesting-code-review` / `receiving-code-review`
- `review-bugbot` / `find-bugs`
- `external/getsentry/code-review` — Sentry 工程審查慣例

### 安全

- `security-review` — getsentry OWASP 風格審查
- `security-threat-model` / `security-best-practices` — openai
- `security-and-hardening` — addyosmani
- `security-model` — 寫/維護 `SECURITY_MODEL.md` 給掃描工具
- `gha-security-review` — GitHub Actions 工作流安全
- `review-security` — Cursor Security Review subagent

### 其他

- `autopilot` — PR 合併就緒循環
- `external/addyosmani/test-driven-development` — 備選 TDD
- `external/mattpocock/tdd` — 備選；頂層 `tdd` 是 pstack

## 使用注意

1. **先跑 `setup-pstack`**（一次），再長期用 `poteto-mode`。
2. Security / QA / Code Review 角色保持唯讀：用 review/security skills 產 artifact，不要順便改受審碼。
3. 同名 skill 以頂層為準；`external/` 是備援或被覆蓋的版本。
4. 這份目錄是專案 memory；若要讓 Cursor/Claude 全域自動發現，可再同步到 `.agents/skills` 或 `.cursor/skills`。

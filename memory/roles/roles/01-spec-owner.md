# Role 01 — Spec Owner (A)

## Mission
將 Issue 轉成可實作、可測試、非猜測的 `spec.md`；回答每個 Reviewer Blocker 並修正需求說明。

## Read
Issue、產品/架構文件、現有 API/資料模型、舊版測試與既有行為、review findings。

## Write
僅 `spec.md` 與自身 `replies.md`；不能修改產品程式碼、受保護測試、Review verdict、Workflow state。

## Procedure
1. 寫清 Problem、Goal、Out of Scope、User Stories、功能與非功能需求、影響範圍。
2. 每項行為使用 AC 編號（AC-01...），可觀察且能由測試判定 PASS/FAIL。
3. 列出邊界條件、失敗路徑、Timeout/Retry/Concurrency、Backward Compatibility、Migration/Rollback。
4. 對不確定處列在 `Assumptions and Open Questions`，必要問題標 `Requires Human Decision`，不得假裝已決議。
5. 收到 Review 後，對每個 Finding 回覆 `Fixed: ...` 或 `Disagree: ...` 並列依據；修正後提交新版本。

## Required spec.md Sections
- Context / Problem / Goals
- Scope / Out of Scope
- Interfaces and Behaviors
- Acceptance Criteria (AC-ID + observable result)
- Failure / Edge Cases
- Backward Compatibility / Regression Targets
- Security / Reliability Requirements
- Assumptions and Open Questions
- Risks / Rollback

## Definition of Done
AC 無歧義、所有關鍵失敗路徑有預期行為、Review 無 Blockers，並通過人工 Spec Gate（預設）。

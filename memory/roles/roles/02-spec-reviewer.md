# Role 02 — Spec / Plan Reviewer (B)

## Mission
對抗式找出 Spec/Plan 的不可測試需求、漏掉的失敗路徑、矛盾、相容性與風險。審查內容，而非替 Owner 寫內容。

## Read
Issue、`spec.md` 或 `plan.md`、既有行為與架構、上輪 review/replies、被指定的 Commit 或 Artifact Hash。

## Write
本輪專屬的 `review.md`、`verdict.json`；不修改 Spec、Plan、Code、Tests 或其他 Reviewer 的審查結果。

## Review Checklist — Spec
- AC 是否有明確輸入、輸出、可觀察成功條件？
- 非正常路徑：timeout/retry/cancel/crash/duplicate/concurrency/partial failure？
- 權限與資料邊界、向後相容、性能、監控與回滾是否缺失？
- 是否存在默默補上的假設？是否與現有 API/資料模型衝突？
- 是否把非目標的需求不當塞入範圍？

## Review Checklist — Plan
- 每個 Task 是否有責任模組、明確 DoD、依賴與對應 AC？
- 是否分割到可單獨提交與驗證？是否存在循環依賴或檔案衝突？
- 是否有先建立回歸保護，再修改核心路徑？
- 是否有 build/QA 的明確 Gate，及修復超界時的處理？

## Output
按 `../contracts/review-output.md` 產生 Review + Verdict。Finding 必須帶目標、預期、實際、證據、修正目標；Blocker 不可只是主觀偏好。

## Do Not
不可為方便完成而降低標準；不可批准自己仍認為存在 correctness/security blocker 的 Spec；不可用「LGTM」取代證據。

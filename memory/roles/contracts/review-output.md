# Review Output Contract v1

所有 Reviewer 必須完成兩份檔案，供 Orchestrator 驗證。不接受只有聊天回覆。

## verdict.json（最低相容欄位）

```json
{
  "approved": false,
  "blockers": ["F-001: lease 逾時後可能重複執行"],
  "suggestions": ["增加流程時序圖"]
}
```

**強制規則**：`approved=true` iff `blockers=[]`；任何缺失、無法解析或矛盾均 Fail Closed。此三欄與原專案相容；下列 metadata 是本方案的附加檔案，不能塞入原專案有嚴格 Schema 驗證的 `verdict.json`。

## metadata.json（Orchestrator 產生）

```json
{
  "schema": 1,
  "run_id": "example-run",
  "stage": "code-review",
  "reviewer": "B",
  "round": 1,
  "head_sha": "full-git-commit-sha",
  "artifact_hash": "sha256:..."
}
```

## review.md（每個 Finding 必填）

```markdown
# Review: <stage> / <head_sha>

## F-001 [BLOCKER] Short title
- Target: `path/to/file.go:120-150` or `spec.md` acceptance AC-03
- Expected: ...
- Actual: ...
- Evidence: `go test ./... -run TestX -count=1` returned ...
- Reproduction: commands and prerequisites
- Impact: correctness / regression / security / spec / reliability
- Required change: observable result, not over-prescriptive implementation

### Worker reply
Fixed: <what changed, tests, commit SHA>
# or
Disagree: <why, with evidence>

## S-001 [SUGGESTION] Optional improvement
- Reason: ...
```

Reviewer 不得修改受審 Artifact。A/I 必須逐條回覆；不接受無證據的 Closed。為支援多 Reviewer 並行，Orchestrator 須依 `{stage, reviewer, round, head_sha}` 隔離檔案，不能互相覆寫。

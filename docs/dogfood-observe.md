# Dogfood：即時觀察 Spec 迴圈

目前 S1 只跑到 **Spec write → B review ↔ A fix（≤ MAX_ROUNDS）→ human gate**。  
Counter 這類需求先當「寫出可測 spec」的 dogfood；Implement 是 S4+。

## 推薦做法（兩個終端）

### Terminal 1 — 開跑（一定要 `--stream`）

```bash
cd /Users/tsengmingchun/orca/projects/orca-agentic-coding-orch

uv run --with pyyaml scripts/s1_spec_loop.py --stream --request "$(cat <<'EOF'
Add a Counter to fixtures/dogfood:

- class or module API: Counter(start: int = 0)
- methods: value() -> int, inc(by: int = 1) -> int, reset() -> None
- keep ping() unchanged
- reject non-int where appropriate with TypeError
EOF
)"
```

開頭會印 `run_id=s1-…`。之後每一輪會出現：

```text
── cursor stream model=grok-4.7-high ──   # A 寫 spec / fix
── cursor stream model=composer-2.5 ──    # B 審查
```

Agent 文字會**邊產邊印**；結束仍會寫進 `aac/.run/<run_id>/archive/`。

### Terminal 2 — 盯檔案交互（產物才是協議）

先設 run id（從 Terminal 1 複製）：

```bash
RUN=s1-YYYYMMDDTHHMMSSZ   # 換成實際 id
ROOT=/Users/tsengmingchun/orca/projects/orca-agentic-coding-orch
cd "$ROOT"

# 狀態機
watch -n 2 "python3 -m json.tool aac/.run/$RUN/state.json | head -50"

# 或手動刷新
cat aac/.run/$RUN/verdict.json
ls -lt aac/.run/$RUN/reviews/spec/
ls -lt aac/.run/$RUN/archive/ | head
```

重點檔：

| 檔案 | 誰寫 | 看什麼 |
| --- | --- | --- |
| `aac/docs/$RUN/spec.md` | A | Spec 長出來 / 被修 |
| `aac/.run/$RUN/reviews/spec/rN/review.md` | B ↔ A replies | 對抗 findings |
| `aac/.run/$RUN/reviews/spec/rN/verdict.json` | B | approved / blockers |
| `aac/.run/$RUN/state.json` | workflow | round / status |
| `aac/.run/$RUN/archive/*` | workflow | 每輪完整 prompt + stdout |

macOS 即時盯 spec（可選）：

```bash
fswatch -o "aac/docs/$RUN/spec.md" | while read; do echo "=== spec updated $(date) ==="; tail -n 30 "aac/docs/$RUN/spec.md"; done
```

## 跑完後

- 若 `HUMAN_GATE_PENDING.md`：讀 spec →  
  `uv run --with pyyaml scripts/s1_human_gate.py --run-id $RUN --approve`（或 `--abort`）
- 若 `REVIEW_ABORTED_MAX_ROUNDS.md`：這是正確的硬停；改 spec / 調高 `AAC_MAX_ROUNDS` 並 `--allow-raise-max-rounds` 再開
- 若 `AGENT_CALL_ABORTED.md`：同一步 retry 用完；看 archive 失敗 log 後 resume

## 注意

1. **交互在檔案，不在兩個 agent 聊天。** 你即時看的是 stream + `review.md` / `spec.md`。
2. S1 **不會**實作 Counter 程式碼；那是後面 Plan → Tests → Implement。
3. 不要開第二個 `s1_spec_loop` 打同一 `run_id`。
4. 沒加 `--stream` 時，終端要等整輪 agent 結束才看得到輸出（舊行為）。

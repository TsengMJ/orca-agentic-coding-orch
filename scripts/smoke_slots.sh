#!/usr/bin/env bash
# Smoke-test Cursor models configured for slots A and B.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

resolve() {
  uv run --with pyyaml "$ROOT/scripts/resolve_slot.py" "$1" --field model
}

MODEL_A="$(resolve A)"
MODEL_B="$(resolve B)"

echo "== hooks =="
orca agent hooks status | head -n 5 || true

echo "== resolve slots =="
uv run --with pyyaml "$ROOT/scripts/resolve_slot.py" A
uv run --with pyyaml "$ROOT/scripts/resolve_slot.py" B
uv run --with pyyaml "$ROOT/scripts/resolve_slot.py" I

echo "== dogfood gate =="
uv run --project fixtures/dogfood --group dev pytest -q

echo "== cursor A ($MODEL_A) =="
cursor agent -p --model "$MODEL_A" --output-format text "Reply with exactly: PONG-A"

echo "== cursor B ($MODEL_B) =="
cursor agent -p --model "$MODEL_B" --output-format text "Reply with exactly: PONG-B"

echo "S0 smoke OK"

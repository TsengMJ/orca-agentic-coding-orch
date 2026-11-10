#!/usr/bin/env bash
# Sample cursor-agent / probe artifacts every 15s until summary.json appears or timeout.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/aac/.run/feature-add-counter-to-dogfood-pr-6/probe/monitor.log"
PROBE="$ROOT/aac/.run/feature-add-counter-to-dogfood-pr-6/probe/r1"
END=$((SECONDS + ${1:-540}))
mkdir -p "$(dirname "$LOG")"
echo "monitor_start=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$LOG"
while (( SECONDS < END )); do
  ts=$(date -u +%H:%M:%S)
  ps_line=$(ps -ax -o pid=,etime=,pcpu=,rss=,state=,command= 2>/dev/null | rg -n "cursor-agent.*grok-4\.7-high|probe_grok_s3_review" | head -3 || true)
  review=$([ -f "$PROBE/review.md" ] && wc -c <"$PROBE/review.md" | tr -d ' ' || echo 0)
  verdict=$(python3 -c "import json,pathlib;p=pathlib.Path('$PROBE/verdict.json');
print(json.loads(p.read_text()).get('blockers',['?'])[:1] if p.exists() else ['missing'])" 2>/dev/null || echo missing)
  {
    echo "[$ts] review_bytes=$review verdict_blockers=$verdict"
    if [[ -n "$ps_line" ]]; then
      echo "$ps_line" | while read -r line; do echo "  proc $line"; done
    else
      echo "  proc none"
    fi
  } >>"$LOG"
  if [[ -f "$PROBE/summary.json" ]]; then
    echo "[$ts] summary present; monitor exit" >>"$LOG"
    break
  fi
  sleep 15
done
echo "monitor_end=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$LOG"

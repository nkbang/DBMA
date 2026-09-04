#!/bin/bash
# Supersedes run_tsu_queue.sh (killed 2026-08-15 23:38 CDT per Rev. Bang
# directive: "v1 완료시 v2 로 가지말고 다음 작업을 실행하라").
#
# Waits for Vol.1 to reach partial:false (read-only polling — never touches
# the production process), then runs Phase 0 baseline capture ONLY.
# Does NOT start Vol.2 and does NOT begin any Corpus Factory implementation
# — that requires a separate C1 relay per the transition order §0.
set -uo pipefail
cd ~/DBMA || exit 1

REPORT="NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu_report.json"

# NOTE: this script deliberately does NOT check process liveness itself —
# a Bash `run_in_background` sandbox in this environment was observed to
# not see PID 88689 via `ps aux` (2x false "process died" on a verified-
# alive process), while the separate hourly Monitor-based check (which
# uses the same `ps aux` pattern) sees it correctly every time. Process
# death detection is left entirely to that hourly monitor. This script
# only watches the filesystem checkpoint, which is reliable everywhere.
while true; do
  if [ -f "$REPORT" ]; then
    PARTIAL=$(python3 -c "import json;print(json.load(open('$REPORT')).get('partial'))" 2>/dev/null)
    if [ "$PARTIAL" = "False" ]; then
      echo "VOL01_COMPLETE — running Phase 0 baseline capture"
      bash .automation/night-shift/capture_vol01_baseline.sh
      echo "PHASE0_BASELINE_CAPTURED — awaiting Corpus Factory Task Order relay (not auto-dispatched)"
      exit 0
    fi
  fi
  sleep 300
done

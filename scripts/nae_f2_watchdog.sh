#!/usr/bin/env bash
# scripts/nae_f2_watchdog.sh — detect a hung F2 run and recover it (Gap 3).
#
# WHY: even with claim.py's HTTP timeout, a wedged Ollama daemon can leave the
# F2 runner stuck between calls with no forward progress. This watchdog turns a
# silent hang into an auto-recovery within ~STALL_SECS + a probe.
#
# With `--resume` live in build_tsu_for_identifier + run_fuller_f2.sh, a
# recovery restart resumes the current volume from its last checkpoint
# (loss ~= one checkpoint / ~100 candidates), not candidate 0.
#
# Run detached, alongside run_fuller_f2.sh:
#   nohup bash scripts/nae_f2_watchdog.sh > f2_watchdog.log 2>&1 &
#
# Env:
#   STALL_SECS     checkpoint-age threshold, seconds (default 1500)
#   PROBE_TIMEOUT  small-prompt Ollama probe timeout, seconds (default 45)
#   AUTO_RECOVER   1 = kill + launchctl kickstart + restart driver (default).
#                  0 = alert only (print, no action).
#   POLL_SECS      loop interval, seconds (default 120)
set -u

REPO="/Users/David/DBMA"
MODEL="my-theology-bot-v2:latest"
STALL_SECS="${STALL_SECS:-1500}"
PROBE_TIMEOUT="${PROBE_TIMEOUT:-45}"
AUTO_RECOVER="${AUTO_RECOVER:-1}"
POLL_SECS="${POLL_SECS:-120}"
cd "$REPO" || exit 1

log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

active_report() {  # newest tsu_report.json with partial==true
  local best="" best_m=0 m
  for r in NAE/corpus/tsu/Fuller_Complete_Works_Vol*/tsu_report.json; do
    [ -f "$r" ] || continue
    python3 -c "import json,sys;sys.exit(0 if json.load(open('$r')).get('partial') is True else 1)" 2>/dev/null || continue
    m=$(stat -f %m "$r"); [ "$m" -gt "$best_m" ] && best="$r" && best_m="$m"
  done
  echo "$best"
}

probe_ollama() {  # 0 = responsive, non-zero = timed out / failed
  timeout "$PROBE_TIMEOUT" curl -s http://localhost:11434/api/generate \
    -d "{\"model\":\"$MODEL\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":2}}" \
    -o /dev/null -w '%{http_code}' 2>/dev/null | grep -q '^200$'
}

recover() {
  log "RECOVER: killing runner + driver"
  pkill -f "NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works" 2>/dev/null
  pkill -f "bash scripts/run_fuller_f2.sh" 2>/dev/null
  sleep 3
  pkill -9 -f "NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works" 2>/dev/null
  pkill -9 -f "bash scripts/run_fuller_f2.sh" 2>/dev/null
  sleep 2
  log "RECOVER: launchctl kickstart Ollama"
  launchctl kickstart -k "gui/$(id -u)/com.ollama.ollama"
  local ok=0
  for _ in $(seq 1 20); do sleep 6; if probe_ollama; then ok=1; break; fi; done
  if [ "$ok" -ne 1 ]; then
    log "RECOVER: Ollama not responsive after ~2min — MANUAL INTERVENTION NEEDED"; return 1
  fi
  log "RECOVER: Ollama healthy — restarting F2 driver (--resume auto for partial volume)"
  nohup bash scripts/run_fuller_f2.sh > f2_run.log 2>&1 &
  log "RECOVER: driver restarted pid $!"
  return 0
}

log "F2 watchdog start — STALL_SECS=$STALL_SECS AUTO_RECOVER=$AUTO_RECOVER POLL=$POLL_SECS"
consec=0
while true; do
  sleep "$POLL_SECS"
  driver=$(pgrep -f "bash scripts/run_fuller_f2.sh" | head -1)
  [ -z "$driver" ] && { log "driver not running — watchdog idle (F2 done or stopped)"; consec=0; continue; }
  runner=$(pgrep -f "NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works" | head -1)
  [ -z "$runner" ] && { consec=0; continue; }   # between volumes
  et=$(ps -o etimes= -p "$runner" 2>/dev/null | tr -d ' '); et="${et:-0}"
  rpt=$(active_report); [ -z "$rpt" ] && { consec=0; continue; }
  age=$(( $(date +%s) - $(stat -f %m "$rpt") ))
  # suspect only once the runner has had time to reach a checkpoint
  { [ "$age" -lt "$STALL_SECS" ] || [ "$et" -lt "$STALL_SECS" ]; } && { consec=0; continue; }
  cpu=$(ps -o %cpu= -p "$runner" 2>/dev/null | tr -d ' ')
  log "SUSPECT stall: $(basename "$(dirname "$rpt")") ckpt age=${age}s runner et=${et}s cpu=${cpu}% — probing Ollama"
  if probe_ollama; then log "  Ollama responsive — runner slow, not wedged. No action."; consec=0; continue; fi
  consec=$((consec+1)); log "  Ollama probe FAILED (consec=$consec)"
  [ "$consec" -lt 2 ] && continue    # 2 consecutive probe failures required
  if [ "$AUTO_RECOVER" = "1" ]; then
    recover && consec=0 || log "recover failed — retry next cycle"
  else
    log "  AUTO_RECOVER=0 — ALERT ONLY. F2 is hung; recover manually."
  fi
done

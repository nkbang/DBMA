#!/bin/bash
# Sequential TSU generation queue for Fuller Vol02-08 (Order 003 Phase 4).
# Runs AFTER Vol01 finishes (checked below) — sequential, not parallel,
# to avoid contending for the same local LLM (my-theology-bot-v2:latest).
#
# Scope: Phase 1 (TSU generation) ONLY. Does NOT run Phase 2/3
# (embedding/Qdrant --apply) — those require review_status=="verified",
# which only a human review/promotion step can set
# (NAE/pipeline/tsu/review_promotion.py). This queue never touches that.
#
# On any volume's failure: STOP the queue (no auto-retry, no auto-skip) —
# write STOP.md and exit. A human/CUE decision is required before resuming.
set -uo pipefail

cd ~/DBMA || exit 1
EVIDENCE_ROOT=".automation/evidence/night-shift/tsu-processing-connection"
QUEUE_LOG="$EVIDENCE_ROOT/queue-vol02-08.log"
mkdir -p "$EVIDENCE_ROOT"

VOL01_REPORT="NAE/corpus/tsu/Fuller_Complete_Works_Vol01/tsu_report.json"
VOLUMES=(Fuller_Complete_Works_Vol02 Fuller_Complete_Works_Vol03 Fuller_Complete_Works_Vol04 \
         Fuller_Complete_Works_Vol05 Fuller_Complete_Works_Vol06 Fuller_Complete_Works_Vol07 \
         Fuller_Complete_Works_Vol08)

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S.000Z)] $1" | tee -a "$QUEUE_LOG"
}

log "queue start — waiting for Vol01 to finish"

# Wait for Vol01 (Phase 1, launched separately) to reach partial:false.
while true; do
  if [ -f "$VOL01_REPORT" ]; then
    PARTIAL=$(python3 -c "import json;print(json.load(open('$VOL01_REPORT')).get('partial'))" 2>/dev/null)
    if [ "$PARTIAL" = "False" ]; then
      log "Vol01 confirmed complete (partial=False) — starting queue"
      break
    fi
  fi
  if ! pgrep -f "NAE.pipeline.tsu.runner --identifier Fuller_Complete_Works_Vol01" > /dev/null; then
    log "Vol01 process is gone but tsu_report.json never reached partial=False — STOPPING queue, needs review"
    echo "Vol01 ended without completing (process gone, partial != False). Queue not started." \
      > "$EVIDENCE_ROOT/STOP.md"
    exit 1
  fi
  sleep 300
done

source ~/envs/dbma311/bin/activate

for VOL in "${VOLUMES[@]}"; do
  OUT_DIR="$EVIDENCE_ROOT/phase-1-tsu-generation/$VOL"
  mkdir -p "$OUT_DIR"
  log "starting TSU generation: $VOL"

  python -u -m NAE.pipeline.tsu.runner --identifier "$VOL" \
    > "$OUT_DIR/stdout.log" 2> "$OUT_DIR/stderr.log"
  CODE=$?
  echo "$CODE" > "$OUT_DIR/exit_code.txt"

  REPORT="NAE/corpus/tsu/$VOL/tsu_report.json"
  PARTIAL=$(python3 -c "import json;print(json.load(open('$REPORT')).get('partial'))" 2>/dev/null || echo "UNKNOWN")

  if [ "$CODE" -ne 0 ] || [ "$PARTIAL" != "False" ]; then
    log "$VOL FAILED (exit=$CODE, partial=$PARTIAL) — STOPPING queue, needs review"
    {
      echo "# TSU Queue STOP — $VOL"
      echo "exit_code: $CODE"
      echo "tsu_report.partial: $PARTIAL"
      echo "Remaining volumes not started: ${VOLUMES[*]/$VOL/}"
    } > "$EVIDENCE_ROOT/STOP.md"
    exit 1
  fi

  log "$VOL COMPLETE (partial=False)"
done

log "queue complete — all of Vol02-08 finished Phase 1"
echo "ALL_VOLUMES_COMPLETE" >> "$QUEUE_LOG"

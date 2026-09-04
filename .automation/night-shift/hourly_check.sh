#!/bin/bash
# CUE Directive — NAE TSU Extraction Continuation (2026-08-15).
# Read-only monitoring sidecar. NEVER touches Ollama, the model, or the
# production tsu.runner process. Restarting THIS script is always safe —
# it only observes.
#
# Checklist per directive §3: processed/total, throughput, process alive,
# error/failure count, evidence/state integrity. Intervene only on: process
# death, repeated errors, state/evidence corruption, data-loss risk,
# production-boundary violation. Never on "just slow".
#
# On a volume transition (active identifier changes), runs the §5
# completion audit for the volume that just finished.
set -u
cd ~/DBMA || exit 1

EVIDENCE_ROOT=".automation/evidence/night-shift/tsu-processing-connection"
STATE_FILE="/tmp/nae_tsu_hourly_check_state.json"
mkdir -p "$EVIDENCE_ROOT"

active_identifier() {
  ps aux | grep "NAE.pipeline.tsu.runner --identifier" | grep -v grep \
    | grep -o 'Fuller_Complete_Works_Vol[0-9]*' | head -1
}

completion_audit() {
  local VOL="$1"
  local OUT="$EVIDENCE_ROOT/phase-1-tsu-generation/${VOL}-completion-audit.md"
  local REPORT="NAE/corpus/tsu/$VOL/tsu_report.json"
  {
    echo "# Completion Audit — $VOL"
    echo "- audited_at: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
    echo
    echo "## 1. candidate/output counts (tsu_report.json)"
    python3 -c "
import json
d = json.load(open('$REPORT'))
print(f\"- candidates_evaluated: {d.get('candidates_evaluated')}\")
print(f\"- candidates_total: {d.get('candidates_total')}\")
print(f\"- claims_extracted: {d.get('claims_extracted')}\")
print(f\"- llm_errors: {d.get('llm_errors')}\")
print(f\"- partial: {d.get('partial')}\")
" 2>/dev/null
    echo
    echo "## 2. TSU output record count (tsu.json)"
    python3 -c "
import json
d = json.load(open('NAE/corpus/tsu/$VOL/tsu.json'))
print(f'- records in tsu.json: {len(d)}')
" 2>/dev/null
    echo
    echo "## 3. evidence completeness"
    ls -la "NAE/corpus/tsu/$VOL/" 2>&1
    echo
    echo "## 4. quality gate — n/a at this stage (review_status gate, not yet reviewed)"
    python3 -c "
import json
d = json.load(open('NAE/corpus/tsu/$VOL/tsu.json'))
statuses = {}
for r in d:
    s = r.get('review_status', '?')
    statuses[s] = statuses.get(s, 0) + 1
print('- review_status breakdown:', statuses)
" 2>/dev/null
    echo
    echo "## 5. production boundary (git diff)"
    echo '```'
    git diff --stat core/retrieval.py NAE/pipeline/tsu/*.py NAE/pipeline/ingest/*.py NAE/pipeline/registration/pipeline.py 2>&1
    echo '```'
  } > "$OUT"
  echo "[$(date '+%Y-%m-%d %H:%M %Z')] completion audit written: $OUT"
}

TS=$(date '+%Y-%m-%d %H:%M %Z')
ACTIVE=$(active_identifier)

PREV_ACTIVE=""
PREV_EVAL=0
PREV_TS_EPOCH=0
if [ -f "$STATE_FILE" ]; then
  PREV_ACTIVE=$(python3 -c "import json;print(json.load(open('$STATE_FILE')).get('active',''))" 2>/dev/null)
  PREV_EVAL=$(python3 -c "import json;print(json.load(open('$STATE_FILE')).get('evaluated',0))" 2>/dev/null)
  PREV_TS_EPOCH=$(python3 -c "import json;print(json.load(open('$STATE_FILE')).get('epoch',0))" 2>/dev/null)
fi
NOW_EPOCH=$(date +%s)

if [ -z "$ACTIVE" ]; then
  if [ -f "$EVIDENCE_ROOT/STOP.md" ]; then
    echo "[$TS] 🔴 STOP — $(head -3 "$EVIDENCE_ROOT/STOP.md" | tr '\n' ' ')"
    exit 1
  fi
  if grep -q "ALL_VOLUMES_COMPLETE" "$EVIDENCE_ROOT/queue-vol02-08.log" 2>/dev/null; then
    echo "[$TS] ✅ ALL VOLUMES COMPLETE (Vol01-08)"
    exit 0
  fi
  # No active process and no explicit terminal marker — this IS an
  # intervention condition per §4 (process death).
  echo "[$TS] 🔴 process not found, no STOP.md, no completion marker — investigate (possible unclean death)"
  exit 1
fi

# Volume transition detected — run completion audit for the one that finished.
if [ -n "$PREV_ACTIVE" ] && [ "$PREV_ACTIVE" != "$ACTIVE" ]; then
  echo "[$TS] volume transition detected: $PREV_ACTIVE -> $ACTIVE"
  completion_audit "$PREV_ACTIVE"
fi

REPORT="NAE/corpus/tsu/$ACTIVE/tsu_report.json"
if [ -f "$REPORT" ]; then
  python3 -c "
import json
d = json.load(open('$REPORT'))
ev = d.get('candidates_evaluated', 0)
tot = d.get('candidates_total', 1)
errs = d.get('llm_errors', 0)
pct = 100 * ev / tot if tot else 0
prev_ev = $PREV_EVAL
prev_epoch = $PREV_TS_EPOCH
now_epoch = $NOW_EPOCH
delta = ev - prev_ev
dt_hours = (now_epoch - prev_epoch) / 3600.0 if prev_epoch else None
rate = f'{delta/dt_hours:.0f}/h' if dt_hours and dt_hours > 0 else 'n/a(first check)'
err_rate = f'{100*errs/ev:.1f}%' if ev else '0%'
print(f'[$TS] $ACTIVE: {ev}/{tot} ({pct:.1f}%) | throughput={rate} | errors={errs} ({err_rate}) | process=alive')
"
  # Persist state for next hour's throughput delta.
  python3 -c "
import json
json.dump({'active': '$ACTIVE', 'evaluated': $(python3 -c "import json;print(json.load(open('$REPORT')).get('candidates_evaluated',0))" 2>/dev/null), 'epoch': $NOW_EPOCH}, open('$STATE_FILE', 'w'))
"
else
  echo "[$TS] $ACTIVE: running, no checkpoint written yet | process=alive"
fi

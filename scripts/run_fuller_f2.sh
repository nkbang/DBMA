#!/usr/bin/env bash
# scripts/run_fuller_f2.sh — F2: Fuller Vol.02–08 TSU generation, detached sequential driver.
#
# Runs each volume via `NAE.pipeline.tsu.runner --identifier`. This script:
#   - skips volumes whose tsu_report.json already shows "partial": false;
#   - passes --resume for any volume left "partial": true, so the runner
#     continues from its last checkpoint (candidates_evaluated) instead of
#     recomputing the whole volume from candidate 0. The resumed tsu.json is
#     byte-identical to a from-scratch run (NAE-TSU-BUILDER-RESUME-001,
#     docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md).
#
# Launch DETACHED (not inside an agent loop), e.g.:
#   nohup bash scripts/run_fuller_f2.sh > f2_run.log 2>&1 &
#   tail -f f2_run.log
#
# Commits + pushes each volume's tsu.json/tsu_report.json + incremental_state +
# tsu_id_state after its per-volume gate passes. STOPS on gate failure.
set -u

REPO="/Users/David/DBMA"
PY="$HOME/envs/dbma311/bin/python"
MODEL="my-theology-bot-v2:latest"
VOLS=(02 03 04 05 06 07 08)
cd "$REPO" || exit 1

log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

gate_ok() {  # $1 = tsu_report.json path
  "$PY" - "$1" <<'PYEOF'
import json, sys
r = json.load(open(sys.argv[1]))
ok = True
def bad(m):
    global ok; ok = False; print("  GATE FAIL:", m)
if r.get("partial") is not False: bad(f"partial={r.get('partial')}")
if r.get("builder_version") != "3.0.0": bad(f"builder_version={r.get('builder_version')}")
if r.get("model") != "my-theology-bot-v2:latest": bad(f"model={r.get('model')}")
ct = r.get("candidates_total") or 0
le = r.get("llm_errors") or 0
if ct and le / ct >= 0.02: bad(f"llm_errors {le}/{ct} >= 2%")
if r.get("candidates_evaluated") != ct: bad(f"evaluated {r.get('candidates_evaluated')} != total {ct}")
if not r.get("claims_extracted"): bad("claims_extracted == 0")
db = r.get("doctrine_breakdown") or {}
tot = sum(db.values()) or 1
if db and max(db.values())/tot >= 0.98: bad("single doctrine >= 98%")
if db and db.get("Other", 0) == max(db.values()): bad("'Other' is the top doctrine")
sys.exit(0 if ok else 1)
PYEOF
}

log "F2 start — volumes: ${VOLS[*]}"
for v in "${VOLS[@]}"; do
  ID="Fuller_Complete_Works_Vol${v}"
  RPT="NAE/corpus/tsu/${ID}/tsu_report.json"
  RESUME_FLAG=""
  if [ -f "$RPT" ]; then
    if "$PY" -c "import json,sys; sys.exit(0 if json.load(open('$RPT')).get('partial') is False else 1)"; then
      log "Vol${v}: already complete (partial=false) — skip"
      continue
    fi
    RESUME_FLAG="--resume"
    log "Vol${v}: partial report found — resuming from last checkpoint"
  fi
  log "Vol${v}: starting ($ID) ${RESUME_FLAG}"
  "$PY" -m NAE.pipeline.tsu.runner --identifier "$ID" --model "$MODEL" $RESUME_FLAG
  rc=$?
  log "Vol${v}: runner exited rc=$rc"
  if [ $rc -ne 0 ] || [ ! -f "$RPT" ]; then
    log "Vol${v}: STOP — runner failed or no report"; exit 1
  fi
  if gate_ok "$RPT"; then
    log "Vol${v}: gate PASS"
    git add "NAE/corpus/tsu/${ID}/tsu.json" "NAE/corpus/tsu/${ID}/tsu_report.json" \
            NAE/corpus/tsu/tsu_id_state.json NAE/pipeline/ingest/state/incremental_state.json 2>/dev/null
    git commit -q -m "feat(fuller): F2 TSU generation — ${ID}

builder 3.0.0 / my-theology-bot-v2:latest. review_status=generated.
Per-volume gate passed (partial:false, llm_errors <2%, doctrine sanity).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" \
      && git push origin dev/dbma-engine && log "Vol${v}: committed + pushed" \
      || log "Vol${v}: commit/push FAILED (continuing; commit manually)"
  else
    log "Vol${v}: STOP — gate failed, not committing, not proceeding"; exit 1
  fi
done
log "F2 done — all volumes complete"

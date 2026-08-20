#!/bin/bash
# ADR-022 Night Shift Regression Test Script
# C1 Independent Verification — 9 Scenarios
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
ROUND=0
MAX_ROUNDS=10
CORRECTION_COUNT=0
STOPPED=false

INCREMENTAL_HASH=$(shasum -a 256 /Users/David/DBMA/NAE/pipeline/ingest/state/incremental_state.json | awk '{print $1}')
PHASE_E_HASH=$(shasum -a 256 /Users/David/DBMA/.automation/workflows/phase-e.json | awk '{print $1}')

declare -A PASS_COUNT
declare -A FAIL_COUNT
for i in $(seq 1 9); do
    PASS_COUNT[$i]=0
    FAIL_COUNT[$i]=0
done

TOTAL_REQUESTS=0

log_evidence() {
    local scenario=$1
    local round=$2
    local result=$3
    local detail=$4
    echo "{\"scenario\":$scenario,\"round\":$round,\"result\":\"$result\",\"detail\":\"$detail\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"}" >> "$EVIDENCE_DIR/scenario-${scenario}-rounds.jsonl"
}

check_governance() {
    if grep -r '"to":"PROCESSING"' "$EVIDENCE_DIR/" 2>/dev/null; then
        echo "STOP: VALIDATION_PASSED -> PROCESSING transition detected!"
        STOPPED=true
        return 1
    fi
    if grep -r '"to":"COMPLETED"' "$EVIDENCE_DIR/" 2>/dev/null; then
        echo "STOP: VALIDATION_PASSED -> COMPLETED transition detected!"
        STOPPED=true
        return 1
    fi
    local current_incremental=$(shasum -a 256 /Users/David/DBMA/NAE/pipeline/ingest/state/incremental_state.json | awk '{print $1}')
    if [ "$current_incremental" != "$INCREMENTAL_HASH" ]; then
        echo "STOP: incremental_state.json modified!"
        STOPPED=true
        return 1
    fi
    local current_phase_e=$(shasum -a 256 /Users/David/DBMA/.automation/workflows/phase-e.json | awk '{print $1}')
    if [ "$current_phase_e" != "$PHASE_E_HASH" ]; then
        echo "STOP: phase-e.json modified!"
        STOPPED=true
        return 1
    fi
    return 0
}

run_scenario_1() {
    local task_id="NS-REPEAT-$(date +%s)"
    cat > "$TASKS_DIR/${task_id}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$task_id","title":"Night Shift Repeat Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=nightshift1"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF
    local first_response=$(curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$task_id\",\"title\":\"Night Shift Repeat Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift1\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
    local first_status=$(echo "$first_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [ "$first_status" != "validation_passed" ]; then
        log_evidence 1 $ROUND "FAIL" "First request not validation_passed: $first_response"
        FAIL_COUNT[1]=$((FAIL_COUNT[1] + 1))
        return 1
    fi
    local dup_count=0
    for i in $(seq 1 20); do
        local resp=$(curl -s -X POST "$WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"task_id\":\"$task_id\",\"title\":\"Night Shift Repeat Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift1\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
        local st=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
        if [ "$st" = "duplicate" ]; then
            dup_count=$((dup_count + 1))
        fi
    done
    if [ $dup_count -eq 20 ]; then
        log_evidence 1 $ROUND "PASS" "All 20 repeats returned duplicate"
        PASS_COUNT[1]=$((PASS_COUNT[1] + 1))
        return 0
    else
        log_evidence 1 $ROUND "FAIL" "Only $dup_count/20 duplicates"
        FAIL_COUNT[1]=$((FAIL_COUNT[1] + 1))
        return 1
    fi
}

run_scenario_2() {
    local task_id="NS-RACE-$(date +%s)"
    cat > "$TASKS_DIR/${task_id}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$task_id","title":"Night Shift Race Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=nightshift2"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF
    for i in $(seq 1 5); do
        curl -s -X POST "$WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"task_id\":\"$task_id\",\"title\":\"Night Shift Race Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift2\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}" \
            > "$EVIDENCE_DIR/race-${task_id}-${i}.json" 2>&1 &
    done
    wait
    local ids=$(python3 -c "
import json, sys
ids = set()
for i in range(1, 6):
    with open('$EVIDENCE_DIR/race-${task_id}-${i}.json') as f:
        d = json.load(f)
        tid = d.get('transition_id', '')
        ids.add(tid)
print(len(ids))
" 2>/dev/null || echo "0")
    if [ "$ids" -eq 5 ]; then
        log_evidence 2 $ROUND "PASS" "5 unique transition_ids in concurrent requests"
        PASS_COUNT[2]=$((PASS_COUNT[2] + 1))
        return 0
    else
        log_evidence 2 $ROUND "FAIL" "Only $ids/5 unique transition_ids"
        FAIL_COUNT[2]=$((FAIL_COUNT[2] + 1))
        return 1
    fi
}

run_scenario_3() {
    local task_id="NS-BADSCHEMA-$(date +%s)"
    cat > "$TASKS_DIR/${task_id}.json" <<EOF
{"task_id":"$task_id","title":"Bad Schema Test"}
EOF
    local resp=$(curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$task_id\",\"title\":\"Bad Schema Test\"}")
    local status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [ "$status" = "failed" ]; then
        log_evidence 3 $ROUND "PASS" "validation_failed for schema violation"
        PASS_COUNT[3]=$((PASS_COUNT[3] + 1))
        return 0
    else
        log_evidence 3 $ROUND "FAIL" "Expected failed, got: $status"
        FAIL_COUNT[3]=$((FAIL_COUNT[3] + 1))
        return 1
    fi
}

run_scenario_4() {
    local task_id="NS-NONEXIST-$(date +%s)"
    local resp=$(curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$task_id\",\"title\":\"NonExist Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
    local status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [ "$status" = "file_error" ]; then
        log_evidence 4 $ROUND "PASS" "file_error for non-existent task"
        PASS_COUNT[4]=$((PASS_COUNT[4] + 1))
        return 0
    else
        log_evidence 4 $ROUND "FAIL" "Expected file_error, got: $status"
        FAIL_COUNT[4]=$((FAIL_COUNT[4] + 1))
        return 1
    fi
}

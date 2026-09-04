#!/bin/bash
# Scenario 1: Same task repeated requests (duplicate detection)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-1-scenario-1.log"

echo "=== Scenario 1: Same Task Repeat (Duplicate Detection) ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file
TASK_ID="NS-REPEAT-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Night Shift Repeat Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=nightshift1"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF

echo "Created task: $TASK_ID" >> "$LOG_FILE"

# First request - expect validation_passed
FIRST_RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Night Shift Repeat Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift1\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
FIRST_STATUS=$(echo "$FIRST_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

echo "First request status: $FIRST_STATUS" >> "$LOG_FILE"
echo "First response: $FIRST_RESP" >> "$LOG_FILE"

if [ "$FIRST_STATUS" != "validation_passed" ]; then
    echo "FAIL: First request did not return validation_passed" >> "$LOG_FILE"
    echo "FAIL: First request did not return validation_passed"
    cat "$LOG_FILE"
    exit 1
fi

# Repeat 20 times - all should be duplicate
DUP_COUNT=0
for i in $(seq 1 20); do
    RESP=$(curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Night Shift Repeat Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift1\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
    ST=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [ "$ST" = "duplicate" ]; then
        DUP_COUNT=$((DUP_COUNT + 1))
    else
        echo "Request $i: status=$ST (expected duplicate)" >> "$LOG_FILE"
    fi
done

echo "Duplicate count: $DUP_COUNT / 20" >> "$LOG_FILE"

if [ $DUP_COUNT -eq 20 ]; then
    echo "PASS: All 20 repeats returned duplicate" >> "$LOG_FILE"
    echo "Scenario 1: PASS"
    echo "Last completed: Scenario 1 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 2" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Only $DUP_COUNT/20 duplicates" >> "$LOG_FILE"
    echo "Scenario 1: FAIL - Only $DUP_COUNT/20 duplicates"
    echo "Last completed: Scenario 1 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 2" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

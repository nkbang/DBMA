#!/bin/bash
# Scenario 9: Long-running integrity (50 concurrent requests, JSON validity check)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-9-scenario-9.log"

echo "=== Scenario 9: Long-running Integrity ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file
TASK_ID="NS-INTEGRITY-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Integrity Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=x"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF

echo "Created task: $TASK_ID" >> "$LOG_FILE"

# Launch 50 concurrent requests
echo "Launching 50 concurrent requests..." >> "$LOG_FILE"
for i in $(seq 1 50); do
    curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Integrity Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}" \
        > "$EVIDENCE_DIR/integrity-${TASK_ID}-${i}.json" 2>&1 &
done
wait

echo "All 50 requests completed. Checking JSON validity..." >> "$LOG_FILE"

# Check all response files are valid JSON
INVALID_JSON=0
for i in $(seq 1 50); do
    if ! python3 -c "import json; json.load(open('$EVIDENCE_DIR/integrity-${TASK_ID}-${i}.json'))" 2>/dev/null; then
        INVALID_JSON=$((INVALID_JSON + 1))
        echo "Invalid JSON in file $i" >> "$LOG_FILE"
    fi
done

echo "Invalid JSON files: $INVALID_JSON / 50" >> "$LOG_FILE"

# Check evidence file integrity (if it exists)
EVIDENCE_FILE="$EVIDENCE_DIR/evidence-${TASK_ID}.jsonl"
INVALID_LINES=0
TOTAL_LINES=0
if [ -f "$EVIDENCE_FILE" ]; then
    TOTAL_LINES=$(wc -l < "$EVIDENCE_FILE")
    while IFS= read -r line; do
        if ! echo "$line" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
            INVALID_LINES=$((INVALID_LINES + 1))
        fi
    done < "$EVIDENCE_FILE"
fi

echo "Evidence file lines: $TOTAL_LINES, invalid: $INVALID_LINES" >> "$LOG_FILE"

if [ $INVALID_JSON -eq 0 ] && [ $INVALID_LINES -eq 0 ]; then
    echo "PASS: All 50 requests valid JSON, evidence integrity OK ($TOTAL_LINES lines)" >> "$LOG_FILE"
    echo "Scenario 9: PASS"
    echo "Last completed: Scenario 9 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: None (all complete)" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: invalid_json=$INVALID_JSON invalid_lines=$INVALID_LINES" >> "$LOG_FILE"
    echo "Scenario 9: FAIL - invalid_json=$INVALID_JSON invalid_lines=$INVALID_LINES"
    echo "Last completed: Scenario 9 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: None (all complete)" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

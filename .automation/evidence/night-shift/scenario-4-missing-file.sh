#!/bin/bash
# Scenario 4: Non-existent file (file_error handling)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-4-scenario-4.log"

echo "=== Scenario 4: Non-existent File ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Request a task that doesn't exist in the tasks directory
TASK_ID="NS-NONEXIST-$(date +%s)"

RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"NonExist Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

echo "Task ID: $TASK_ID" >> "$LOG_FILE"
echo "Response: $RESP" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"

if [ "$STATUS" = "file_error" ]; then
    echo "PASS: file_error correctly returned for non-existent task" >> "$LOG_FILE"
    echo "Scenario 4: PASS"
    echo "Last completed: Scenario 4 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 5" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Expected 'file_error', got '$STATUS'" >> "$LOG_FILE"
    echo "Scenario 4: FAIL - Expected file_error, got $STATUS"
    echo "Last completed: Scenario 4 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 5" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

#!/bin/bash
# Scenario 5: Validation failure (production_mutation=true)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-5-scenario-5.log"

echo "=== Scenario 5: Validation Failure (production_mutation) ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file with production_mutation=true (should fail validation)
TASK_ID="NS-VALFAIL-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Validation Fail Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":true,"evidence":[],"audit":{},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=x"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF

echo "Created task with production_mutation=true: $TASK_ID" >> "$LOG_FILE"

# Send request - should fail validation due to production_mutation flag
RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Validation Fail Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

echo "Response: $RESP" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"

if [ "$STATUS" = "failed" ]; then
    echo "PASS: Validation correctly rejected production_mutation=true" >> "$LOG_FILE"
    echo "Scenario 5: PASS"
    echo "Last completed: Scenario 5 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 6" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Expected 'failed', got '$STATUS'" >> "$LOG_FILE"
    echo "Scenario 5: FAIL - Expected failed, got $STATUS"
    echo "Last completed: Scenario 5 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 6" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

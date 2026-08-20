#!/bin/bash
# Scenario 8: Docker restart + webhook activation verification
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-8-scenario-8.log"

echo "=== Scenario 8: Docker Restart + Webhook Activation ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# n8n was already restarted in scenario 7, verify webhook is responding
echo "Verifying webhook endpoint after restart..." >> "$LOG_FILE"

# Create a test task
TASK_ID="NS-ACTIVATE-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Activation Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=x"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF

echo "Created task: $TASK_ID" >> "$LOG_FILE"

# Send request to webhook
RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Activation Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

echo "Response: $RESP" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"

if [ "$STATUS" = "validation_passed" ]; then
    echo "PASS: Webhook correctly processes requests after Docker restart" >> "$LOG_FILE"
    echo "Scenario 8: PASS"
    echo "Last completed: Scenario 8 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 9" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Expected 'validation_passed', got '$STATUS'" >> "$LOG_FILE"
    echo "Scenario 8: FAIL - Expected validation_passed, got $STATUS"
    echo "Last completed: Scenario 8 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 9" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

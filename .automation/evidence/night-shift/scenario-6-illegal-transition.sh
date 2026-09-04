#!/bin/bash
# Scenario 6: Illegal transition (VALIDATION_PASSED -> PROCESSING)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-6-scenario-6.log"

echo "=== Scenario 6: Illegal Transition ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file with VALIDATION_PASSED state (illegal to process without human approval)
TASK_ID="NS-ILLEGAL-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Illegal Transition Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=x"},"automation":{"state":"VALIDATION_PASSED","failure_code":null,"last_transition_id":"fake#0001"}}
EOF

BEFORE_HASH=$(shasum -a 256 "$TASKS_DIR/${TASK_ID}.json" | awk '{print $1}')
echo "Before hash: $BEFORE_HASH" >> "$LOG_FILE"

# Send request - should be blocked by illegal_transition check
RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Illegal Transition Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=x\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}")
STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

AFTER_HASH=$(shasum -a 256 "$TASKS_DIR/${TASK_ID}.json" | awk '{print $1}')
echo "After hash: $AFTER_HASH" >> "$LOG_FILE"
echo "Response: $RESP" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"

if [ "$STATUS" = "illegal_transition" ] && [ "$BEFORE_HASH" = "$AFTER_HASH" ]; then
    echo "PASS: illegal_transition blocked, file unchanged" >> "$LOG_FILE"
    echo "Scenario 6: PASS"
    echo "Last completed: Scenario 6 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 7" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Expected 'illegal_transition' + unchanged file, got status='$STATUS' hashes='$BEFORE_HASH'->$'$AFTER_HASH'" >> "$LOG_FILE"
    echo "Scenario 6: FAIL - illegal_transition or file hash mismatch"
    echo "Last completed: Scenario 6 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 7" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

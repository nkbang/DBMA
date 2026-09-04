#!/bin/bash
# Scenario 3: Invalid task schema (schema validation failure)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-3-scenario-3.log"

echo "=== Scenario 3: Invalid Task Schema ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file with minimal/invalid schema
TASK_ID="NS-BADSCHEMA-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"task_id":"$TASK_ID","title":"Bad Schema Test"}
EOF

echo "Created task with invalid schema: $TASK_ID" >> "$LOG_FILE"

# Send request - should fail validation
RESP=$(curl -s -X POST "$WEBHOOK" \
    -H 'Content-Type: application/json' \
    -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Bad Schema Test\"}")
STATUS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

echo "Response: $RESP" >> "$LOG_FILE"
echo "Status: $STATUS" >> "$LOG_FILE"

if [ "$STATUS" = "failed" ]; then
    echo "PASS: Schema validation correctly rejected invalid task" >> "$LOG_FILE"
    echo "Scenario 3: PASS"
    echo "Last completed: Scenario 3 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 4" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Expected 'failed', got '$STATUS'" >> "$LOG_FILE"
    echo "Scenario 3: FAIL - Expected failed, got $STATUS"
    echo "Last completed: Scenario 3 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 4" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

#!/bin/bash
# Scenario 2: Concurrent requests (race condition)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
TASKS_DIR="/Users/David/DBMA/.automation/tasks"
WEBHOOK="http://localhost:5678/webhook/dbma-automation-phase-e"
LOG_FILE="$EVIDENCE_DIR/round-2-scenario-2.log"

echo "=== Scenario 2: Concurrent Requests (Race Condition) ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Create task file
TASK_ID="NS-RACE-$(date +%s)"
cat > "$TASKS_DIR/${TASK_ID}.json" <<EOF
{"schema_version":"1.0.0","task_id":"$TASK_ID","title":"Night Shift Race Test","owner":"C1-AUDIT","state":"INITIATED","phase":"VALIDATION","requires_human_approval":false,"production_mutation":false,"evidence":[],"audit":{"status":"pending"},"document_type":"sermon","source":{"type":"youtube","url":"https://www.youtube.com/watch?v=nightshift2"},"automation":{"state":null,"failure_code":null,"last_transition_id":null}}
EOF

echo "Created task: $TASK_ID" >> "$LOG_FILE"

# Export for Python subprocess
export EVIDENCE_DIR TASK_ID

# Launch 5 concurrent requests
for i in $(seq 1 5); do
    curl -s -X POST "$WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"task_id\":\"$TASK_ID\",\"title\":\"Night Shift Race Test\",\"owner\":\"C1-AUDIT\",\"document_type\":\"sermon\",\"source\":{\"type\":\"youtube\",\"url\":\"https://www.youtube.com/watch?v=nightshift2\"},\"automation\":{\"state\":null,\"failure_code\":null,\"last_transition_id\":null}}" \
        > "$EVIDENCE_DIR/race-${TASK_ID}-${i}.json" 2>&1 &
done
wait

echo "All 5 requests completed. Checking transition_ids..." >> "$LOG_FILE"

# Check all responses have unique transition_ids
UNIQUE_IDS=$(python3 -c "
import json, os
evidence_dir = os.environ['EVIDENCE_DIR']
task_id = os.environ['TASK_ID']
ids = set()
for i in range(1, 6):
    filepath = os.path.join(evidence_dir, f'race-{task_id}-{i}.json')
    with open(filepath) as f:
        d = json.load(f)
        tid = d.get('transition_id', '')
        ids.add(tid)
print(len(ids))
" 2>/dev/null || echo "0")

echo "Unique transition_ids: $UNIQUE_IDS / 5" >> "$LOG_FILE"

# Print all responses
for i in $(seq 1 5); do
    echo "Response $i: $(cat $EVIDENCE_DIR/race-${TASK_ID}-${i}.json)" >> "$LOG_FILE"
done

if [ "$UNIQUE_IDS" -eq 5 ]; then
    echo "PASS: All 5 transition_ids are unique" >> "$LOG_FILE"
    echo "Scenario 2: PASS"
    echo "Last completed: Scenario 2 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 3" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Only $UNIQUE_IDS/5 unique transition_ids" >> "$LOG_FILE"
    echo "Scenario 2: FAIL - Only $UNIQUE_IDS/5 unique transition_ids"
    echo "Last completed: Scenario 2 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 3" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

#!/bin/bash
# Scenario 7: n8n restart persistence (workflow auto-activation)
set -euo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
LOG_FILE="$EVIDENCE_DIR/round-7-scenario-7.log"

echo "=== Scenario 7: n8n Restart Persistence ===" > "$LOG_FILE"
echo "Start: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Restart n8n container
echo "Restarting n8n container..." >> "$LOG_FILE"
docker restart dbma_n8n >> "$LOG_FILE" 2>&1
echo "n8n restarted at $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

# Wait for n8n to fully start
echo "Waiting 15 seconds for n8n startup..." >> "$LOG_FILE"
sleep 15

# Check logs for workflow activation
LOGS=$(docker logs dbma_n8n --tail 30 2>&1)
echo "Last 30 lines of n8n logs:" >> "$LOG_FILE"
echo "$LOGS" >> "$LOG_FILE"

if echo "$LOGS" | grep -qi "activated.*workflow\|workflow.*activated\|phase-e"; then
    echo "PASS: Workflow auto-activated after restart" >> "$LOG_FILE"
    echo "Scenario 7: PASS"
    echo "Last completed: Scenario 7 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 8" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
elif [ "$TEST_RESP" = "200" ] || [ "$TEST_RESP" = "405" ]; then
    echo "PASS: Webhook endpoint responding (HTTP $TEST_RESP)" >> "$LOG_FILE"
    echo "Scenario 7: PASS"
    echo "Last completed: Scenario 7 (PASS) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 8" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
else
    echo "FAIL: Webhook not responding (HTTP $TEST_RESP)" >> "$LOG_FILE"
    echo "Scenario 7: FAIL - Webhook not responding (HTTP $TEST_RESP)"
    echo "Last completed: Scenario 7 (FAIL) at $(date -u +%Y-%m-%dT%H:%M:%S.000Z). Next: Scenario 8" > /Users/David/DBMA/.automation/evidence/night-shift/CHECKPOINT.md
    exit 1
fi

echo "End: $(date -u +%Y-%m-%dT%H:%M:%S.000Z)" >> "$LOG_FILE"

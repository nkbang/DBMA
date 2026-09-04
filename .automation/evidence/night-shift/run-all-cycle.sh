#!/bin/bash
# ADR-022 Night Shift Regression - Cycle Wrapper
# Runs all 9 scenarios, updates CHECKPOINT.md and cycle-summary.log
set -uo pipefail

EVIDENCE_DIR="/Users/David/DBMA/.automation/evidence/night-shift"
CHECKPOINT="$EVIDENCE_DIR/CHECKPOINT.md"
CYCLE_LOG="$EVIDENCE_DIR/cycle-summary.log"
SCENARIOS_DIR="/Users/David/DBMA/.automation/evidence/night-shift"

# Read current cycle from log file, or start at 1
if [ -f "$CYCLE_LOG" ]; then
    CYCLE=$(tail -1 "$CYCLE_LOG" | sed -n 's/^Cycle \([0-9]*\):.*/\1/p')
    CYCLE=${CYCLE:-0}
else
    CYCLE=0
fi
NEXT_CYCLE=$((CYCLE + 1))

PASS_COUNT=0
TOTAL=7
RAN_RESTART=false

run_scenario() {
    local script="$1"
    local name="$2"
    if bash "$script" > /dev/null 2>&1; then
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "Cycle $NEXT_CYCLE: FAIL at $name" >> "$CYCLE_LOG"
    fi
}

# Run core 7 scenarios every cycle
run_scenario "$SCENARIOS_DIR/scenario-1-repeat.sh" "scenario-1"
run_scenario "$SCENARIOS_DIR/scenario-2-concurrent.sh" "scenario-2"
run_scenario "$SCENARIOS_DIR/scenario-3-invalid.sh" "scenario-3"
run_scenario "$SCENARIOS_DIR/scenario-4-missing-file.sh" "scenario-4"
run_scenario "$SCENARIOS_DIR/scenario-5-validation-fail.sh" "scenario-5"
run_scenario "$SCENARIOS_DIR/scenario-6-illegal-transition.sh" "scenario-6"
run_scenario "$SCENARIOS_DIR/scenario-9-long-run-integrity.sh" "scenario-9"

# Run restart scenarios (7, 8) only every 12 cycles (~1 hour)
if (( NEXT_CYCLE % 12 == 0 )); then
    run_scenario "$SCENARIOS_DIR/scenario-7-n8n-restart-persistence.sh" "scenario-7"
    run_scenario "$SCENARIOS_DIR/scenario-8-docker-restart-activation.sh" "scenario-8"
    RAN_RESTART=true
    TOTAL=9
fi

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

# Update CHECKPOINT.md (overwrite)
if $RAN_RESTART; then
    echo "Last completed: Cycle $NEXT_CYCLE ($PASS_COUNT/$TOTAL PASS, restart-test included) at $TIMESTAMP. Next: Cycle $((NEXT_CYCLE + 1))" > "$CHECKPOINT"
else
    echo "Last completed: Cycle $NEXT_CYCLE ($PASS_COUNT/$TOTAL PASS) at $TIMESTAMP. Next: Cycle $((NEXT_CYCLE + 1))" > "$CHECKPOINT"
fi

# Append to cycle-summary.log
if $RAN_RESTART; then
    echo "Cycle $NEXT_CYCLE: $TIMESTAMP, $PASS_COUNT/$TOTAL PASS (restart-test)" >> "$CYCLE_LOG"
else
    echo "Cycle $NEXT_CYCLE: $TIMESTAMP, $PASS_COUNT/$TOTAL PASS" >> "$CYCLE_LOG"
fi

# Clean up test artifacts created by this cycle
rm -f /Users/David/DBMA/.automation/tasks/NS-*.json
rm -f /Users/David/DBMA/.automation/evidence/NS-*.jsonl

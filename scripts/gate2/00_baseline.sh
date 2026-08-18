#!/usr/bin/env bash
# 00_baseline.sh — Gate 1 baseline 재확인 (읽기 전용)
# Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase A
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVIDENCE_DIR="${SCRIPT_DIR}/../../evidence/gate2/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${EVIDENCE_DIR}"

echo "=== 00_baseline.sh: Gate 1 Baseline Verification ==="

# 1. git log -1 (현재 HEAD)
HEAD_HASH=$(git rev-parse --short HEAD)
echo "[1] Current HEAD: ${HEAD_HASH}"

# 2. git status --porcelain (clean 확인)
STATUS_PORCELAIN=$(git status --porcelain)
if [ -z "${STATUS_PORCELAIN}" ]; then
    CLEAN="true"
else
    CLEAN="false"
fi
echo "[2] Working tree clean: ${CLEAN}"

# 3. git log --oneline -1 598fbdc (baseline 포함 확인)
BASELINE_HASH=$(git rev-parse --short 598fbdc 2>/dev/null || echo "NOT_FOUND")
BASELINE_MSG=$(git log --oneline -1 598fbdc 2>/dev/null | head -1 || echo "NOT_FOUND")
echo "[3] Baseline commit 598fbdc: ${BASELINE_HASH}"
echo "    Message: ${BASELINE_MSG}"

# 4. baseline에서 HEAD까지의 거리
if [ "${BASELINE_HASH}" != "NOT_FOUND" ]; then
    BASELINE_LONG=$(git rev-parse 598fbdc)
    HEAD_LONG=$(git rev-parse HEAD)
    BETWEEN=$(git rev-list --count "${BASELINE_LONG}..${HEAD_LONG}" 2>/dev/null || echo "?")
    echo "[4] Commits between baseline and HEAD: ${BETWEEN}"
fi

# Evidence JSON
cat > "${EVIDENCE_DIR}/00_baseline.json" <<EOF
{
  "script": "00_baseline.sh",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "head_hash": "${HEAD_HASH}",
  "working_tree_clean": ${CLEAN},
  "baseline_commit": "${BASELINE_HASH}",
  "baseline_message": "${BASELINE_MSG}",
  "commits_since_baseline": "${BETWEEN:-null}"
}
EOF

echo "Evidence written to: ${EVIDENCE_DIR}/00_baseline.json"
echo "=== Done ==="

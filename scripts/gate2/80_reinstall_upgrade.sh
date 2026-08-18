#!/usr/bin/env bash
# 80_reinstall_upgrade.sh — Reinstall and upgrade in isolated temp directory
# Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase B
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 80_reinstall_upgrade.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Dry run: ${DRY_RUN}"

mkdir -p "${ISOLATED_DIR}"

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] Uninstall previous version"
    echo "[DRY-RUN] brew upgrade streamlit ollama"
    echo "[DRY-RUN] curl -L ... -o ${ISOLATED_DIR}/install_nae_beta.command"
    echo "[DRY-RUN] ${ISOLATED_DIR}/install_nae_beta.command --upgrade"
else
    echo "[SKIP] Actual upgrade skipped (unapproved)"
fi

echo "=== Done ==="

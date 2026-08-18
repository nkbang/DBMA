#!/usr/bin/env bash
# 90_uninstall.sh — Uninstall from isolated temp directory only
# Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase B
#
# IMPORTANT: This script ONLY removes files in /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 or any production path.
# Homebrew global package removal is OUT OF SCOPE (explicit).
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 90_uninstall.sh ==="
echo "Target directory: ${ISOLATED_DIR}"
echo "Dry run: ${DRY_RUN}"

# Check if isolated install dir exists (from a previous run)
if [ -d "${ISOLATED_DIR}" ]; then
    echo "Removing isolated install directory..."
    if [ "${DRY_RUN}" = "true" ]; then
        echo "[DRY-RUN] rm -rf ${ISOLATED_DIR}"
    else
        rm -rf "${ISOLATED_DIR}"
    fi
    echo "Removed: ${ISOLATED_DIR}"
else
    echo "No isolated directory found at ${ISOLATED_DIR} (nothing to remove)"
fi

# Check for orphan files in /tmp matching gate2 pattern
echo "Checking for orphan gate2 files..."
ORPHANS=$(find /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | head -5)
if [ -n "${ORPHANS}" ]; then
    echo "Found orphans:"
    echo "${ORPHANS}"
else
    echo "No orphan files found"
fi

echo "=== Done ==="

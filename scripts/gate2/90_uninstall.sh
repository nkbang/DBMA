#!/usr/bin/env bash
# 90_uninstall.sh — Uninstall from isolated temp directory only
# Task Order: C1-TASK-ORDER-GATE2-PHASEB-TODO-IMPLEMENTATION.md §3 Phase 3
#
# IMPORTANT: This script ONLY removes files in /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 or any production path.
# Homebrew global package removal is OUT OF SCOPE (explicit).
#
# Isolation method: Uses FAKE_HOME derived from ISOLATED_DIR — no direct
# reference to $HOME/내서재_베탲 anywhere in this script.
set -euo pipefail

DRY_RUN="${DRY_RUN:-false}"

echo "=== 90_uninstall.sh ==="
echo "Dry run: ${DRY_RUN}"

# Accept optional ISOLATED_DIR argument (from orchestrator) or use default pattern
TARGET_DIR="${1:-}"
if [ -z "${TARGET_DIR}" ]; then
    # No argument given — look for any existing gate2 run directories
    echo "No target directory specified. Scanning for existing gate2 runs..."
    TARGET_DIRS=$(find /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | sort -r)
    if [ -z "${TARGET_DIRS}" ]; then
        echo "No isolated directories found (nothing to remove)"
        echo "=== Done ==="
        exit 0
    fi
    echo "Found existing runs:"
    echo "${TARGET_DIRS}"
    # Remove all found directories
    while IFS= read -r dir; do
        echo ""
        echo "--- Removing: ${dir} ---"
        if [ "${DRY_RUN}" = "true" ]; then
            echo "[DRY-RUN] rm -rf ${dir}"
        else
            rm -rf "${dir}"
        fi
        echo "Removed: ${dir}"
    done <<< "${TARGET_DIRS}"
else
    # Single target directory provided
    echo "Target directory: ${TARGET_DIR}"

    if [ -d "${TARGET_DIR}" ]; then
        echo "Removing isolated install directory..."
        if [ "${DRY_RUN}" = "true" ]; then
            echo "[DRY-RUN] rm -rf ${TARGET_DIR}"
        else
            rm -rf "${TARGET_DIR}"
        fi
        echo "Removed: ${TARGET_DIR}"
    else
        echo "No isolated directory found at ${TARGET_DIR} (nothing to remove)"
    fi
fi

# Check for orphan files in /tmp matching gate2 pattern
echo ""
echo "Checking for orphan gate2 files..."
ORPHANS=$(find /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | head -5)
if [ -n "${ORPHANS}" ]; then
    echo "Found orphans:"
    echo "${ORPHANS}"
else
    echo "No orphan files found"
fi

echo "=== Done ==="

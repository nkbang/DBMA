#!/usr/bin/env bash
# 80_reinstall_upgrade.sh — Reinstall and upgrade in isolated temp directory
# Task Order: C1-TASK-ORDER-GATE2-PHASEB-TODO-IMPLEMENTATION.md §3 Phase 2
#
# Isolation method: HOME=${FAKE_HOME} subshell trick (same as 40_clean_install.sh).
# Reuses the same FAKE_HOME across two invocations to simulate upgrade scenario.
# PERSIST_ITEMS are verified after reinstallation.
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 80_reinstall_upgrade.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Dry run: ${DRY_RUN}"

# Create isolated directory and fake HOME (shared across both invocations)
mkdir -p "${ISOLATED_DIR}"
FAKE_HOME="${ISOLATED_DIR}/fakehome"
mkdir -p "${FAKE_HOME}"

# Resolve paths relative to PROJECT_ROOT
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_SCRIPT="${PROJECT_ROOT}/scripts/install_nae_beta.command"

if [ ! -f "${INSTALL_SCRIPT}" ]; then
    echo "FATAL: install_nae_beta.command not found at ${INSTALL_SCRIPT}" >&2
    exit 1
fi

ISOLATED_INSTALL_DIR="${FAKE_HOME}/내서재_베타"

# ── Step 1: First install (simulates initial beta installation) ──
echo ""
echo "--- Step 1: Initial install ---"
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] mkdir -p ${FAKE_HOME}"
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${INSTALL_SCRIPT}"
else
    HOME="${FAKE_HOME}" bash "${INSTALL_SCRIPT}"
fi

if [ -d "${ISOLATED_INSTALL_DIR}" ]; then
    echo "First install completed: ${ISOLATED_INSTALL_DIR}"
else
    echo "WARNING: First install did not create expected directory"
fi

# ── Step 2: Reinstall/upgrade (same FAKE_HOME — simulates user running again) ──
echo ""
echo "--- Step 2: Reinstall/upgrade (same FAKE_HOME) ---"
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${INSTALL_SCRIPT}"
else
    HOME="${FAKE_HOME}" bash "${INSTALL_SCRIPT}"
fi

echo "Reinstall completed: ${ISOLATED_INSTALL_DIR}"

# ── Step 3: Verify PERSIST_ITEMS survived the reinstall ──
# PERSIST_ITEMS from install_nae_beta.command line 43:
#   data/RAW, data/제련완성본, output, chroma_db, logs, config.yaml,
#   data/chat_session_history.json, data/inbox/logos_export
echo ""
echo "--- Step 3: PERSIST_ITEMS verification ---"
PERSIST_ITEMS=("data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "config.yaml" "data/chat_session_history.json" "data/inbox/logos_export")
PRESERVED=0
LOST=0

for item in "${PERSIST_ITEMS[@]}"; do
    if [ -e "${ISOLATED_INSTALL_DIR}/${item}" ]; then
        echo "  PRESERVED: ${item}"
        PRESERVED=$((PRESERVED + 1))
    else
        echo "  LOST:      ${item}"
        LOST=$((LOST + 1))
    fi
done

echo ""
echo "PERSIST_ITEMS result: ${PRESERVED}/${#PERSIST_ITEMS[@]} preserved, ${LOST} lost"

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] (Above is simulated — no actual files exist)"
fi

echo "=== Done ==="

#!/usr/bin/env bash
# 80_reinstall_upgrade.sh — Reinstall and upgrade in isolated temp directory (git archive snapshot)
# Task Order: C1-TASK-ORDER-GATE2-CLEAN-INSTALL-ISOLATION-REDESIGN.md §3
#
# IMPORTANT: This script writes ONLY to /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 (real beta installation path).
# It NEVER executes any script from the live repository (${PROJECT_ROOT}).
#
# Isolation method (dual):
#   1. git archive HEAD → tar -x into ISOLATED_REPO (script file itself is isolated)
#   2. HOME=${FAKE_HOME} override (brew/ollama config cache isolation)
# These are independent safety nets — both must be used together.
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
ISOLATED_REPO="${ISOLATED_DIR}/repo"
FAKE_HOME="${ISOLATED_DIR}/fakehome"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 80_reinstall_upgrade.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Isolated repo:      ${ISOLATED_REPO}"
echo "Fake HOME:          ${FAKE_HOME}"
echo "Dry run:            ${DRY_RUN}"

# Create isolated directory structure (shared across both invocations)
mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"

# Snapshot HEAD into the isolated directory.
# .gitattributes export-ignore automatically excludes NAE/, .automation/, test_seal_*/
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] git archive HEAD | tar -x -C ${ISOLATED_REPO}"
else
    git archive HEAD | tar -x -C "${ISOLATED_REPO}"
fi

ISOLATED_INSTALL_DIR="${ISOLATED_REPO}"

# ── Step 1: First install (simulates initial beta installation) ──
echo ""
echo "--- Step 1: Initial install ---"
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${ISOLATED_REPO}/scripts/setup_beta_tester.command"
else
    HOME="${FAKE_HOME}" LDFLAGS="-L/usr/local/lib" LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}" bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
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
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${ISOLATED_REPO}/scripts/setup_beta_tester.command"
else
    HOME="${FAKE_HOME}" LDFLAGS="-L/usr/local/lib" LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}" bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
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

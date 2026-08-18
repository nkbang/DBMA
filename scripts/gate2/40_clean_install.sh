#!/usr/bin/env bash
# 40_clean_install.sh — Clean install in isolated temp directory
# Task Order: C1-TASK-ORDER-GATE2-ORCHESTRATOR-SCAFFOLDING.md §3 Phase B
#
# IMPORTANT: This script writes ONLY to /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 (real beta installation path).
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 40_clean_install.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Dry run: ${DRY_RUN}"

# Create isolated directory
mkdir -p "${ISOLATED_DIR}"

# Override INSTALL_DIR for the install script
export INSTALL_DIR="${ISOLATED_DIR}/내서재_베타"

# Download and extract (using dry-run echo if requested)
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] brew install streamlit"
    echo "[DRY-RUN] brew install ollama"
    echo "[DRY-RUN] curl -L https://github.com/.../install_nae_beta.command -o ${ISOLATED_DIR}/install_nae_beta.command"
    echo "[DRY-RUN] chmod +x ${ISOLATED_DIR}/install_nae_beta.command"
    echo "[DRY-RUN] ${ISOLATED_DIR}/install_nae_beta.command"
else
    # Actual installation commands would go here
    # brew install streamlit ollama 2>/dev/null || true
    # curl -L ... -o "${ISOLATED_DIR}/install_nae_beta.command"
    # chmod +x "${ISOLATED_DIR}/install_nae_beta.command"
    # "${ISOLATED_DIR}/install_nae_beta.command"
    echo "[SKIP] Actual installation skipped (unapproved)"
fi

# Verify isolated install
if [ -d "${INSTALL_DIR}" ]; then
    echo "Install directory created: ${INSTALL_DIR}"
    ls -la "${INSTALL_DIR}" 2>/dev/null || true
else
    echo "Install directory not created (dry-run mode or skipped)"
fi

echo "=== Done ==="

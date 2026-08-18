#!/usr/bin/env bash
# 40_clean_install.sh — Clean install in isolated temp directory
# Task Order: C1-TASK-ORDER-GATE2-PHASEB-TODO-IMPLEMENTATION.md §3 Phase 1
#
# IMPORTANT: This script writes ONLY to /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 (real beta installation path).
#
# Isolation method: HOME=${FAKE_HOME} subshell trick — install_nae_beta.command
# hardcodes INSTALL_DIR="$HOME/내서재_베타" so export INSTALL_DIR=... is useless.
# By overriding HOME in the subshell, $HOME/내서재_베타 automatically resolves
# to ${FAKE_HOME}/내서재_베타 without modifying install_nae_beta.command at all.
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
DRY_RUN="${DRY_RUN:-false}"

echo "=== 40_clean_install.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Dry run: ${DRY_RUN}"

# Create isolated directory and fake HOME
mkdir -p "${ISOLATED_DIR}"
FAKE_HOME="${ISOLATED_DIR}/fakehome"
mkdir -p "${FAKE_HOME}"

# Resolve paths relative to PROJECT_ROOT for the install script
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_SCRIPT="${PROJECT_ROOT}/scripts/install_nae_beta.command"

if [ ! -f "${INSTALL_SCRIPT}" ]; then
    echo "FATAL: install_nae_beta.command not found at ${INSTALL_SCRIPT}" >&2
    exit 1
fi

# Execute install_nae_beta.command with HOME overridden to FAKE_HOME.
# This makes $HOME/내서재_베타 inside the script resolve to ${FAKE_HOME}/내서재_베탲
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] mkdir -p ${FAKE_HOME}"
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${INSTALL_SCRIPT}"
else
    HOME="${FAKE_HOME}" bash "${INSTALL_SCRIPT}"
fi

# Verify isolated install
ISOLATED_INSTALL_DIR="${FAKE_HOME}/내서재_베타"
if [ -d "${ISOLATED_INSTALL_DIR}" ]; then
    echo "Install directory created: ${ISOLATED_INSTALL_DIR}"
    ls -la "${ISOLATED_INSTALL_DIR}" 2>/dev/null || true
else
    echo "Install directory not created (dry-run mode or skipped)"
fi

echo "=== Done ==="

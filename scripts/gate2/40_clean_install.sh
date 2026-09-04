#!/usr/bin/env bash
# 40_clean_install.sh — Clean install in isolated temp directory (git archive snapshot)
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

echo "=== 40_clean_install.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Isolated repo:      ${ISOLATED_REPO}"
echo "Fake HOME:          ${FAKE_HOME}"
echo "Dry run:            ${DRY_RUN}"

# Create isolated directory structure
mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"

# Snapshot HEAD into the isolated directory.
# .gitattributes export-ignore automatically excludes NAE/, .automation/, test_seal_*/
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] git archive HEAD | tar -x -C ${ISOLATED_REPO}"
    echo "[DRY-RUN] HOME=${FAKE_HOME} bash ${ISOLATED_REPO}/scripts/setup_beta_tester.command"
else
    # git archive HEAD creates a clean snapshot — no uncommitted changes leak in
    git archive HEAD | tar -x -C "${ISOLATED_REPO}"

    # Execute setup_beta_tester.command from INSIDE the isolated repo.
    # Because the script file is inside ISOLATED_REPO, its internal
    # PROJECT_ROOT=$(dirname "$0")/.. calculation automatically resolves to
    # the isolated directory — this is the core isolation mechanism.
    HOME="${FAKE_HOME}" bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
fi

# Verify isolated install
ISOLATED_INSTALL_DIR="${ISOLATED_REPO}"
if [ -d "${ISOLATED_INSTALL_DIR}" ]; then
    echo "Install directory created: ${ISOLATED_INSTALL_DIR}"
    ls -la "${ISOLATED_INSTALL_DIR}" 2>/dev/null || true
else
    echo "Install directory not created (dry-run mode or skipped)"
fi

echo "=== Done ==="

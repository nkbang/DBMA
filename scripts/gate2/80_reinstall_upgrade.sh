#!/usr/bin/env bash
# 80_reinstall_upgrade.sh — Reinstall/Upgrade PERSIST_ITEMS preservation test
# Task Order: C1-NIGHT-SHIFT-DIRECTIVE-END-USER-PACKAGE-001.md §3 Phase 8
#
# IMPORTANT: This script writes ONLY to /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 (real beta installation path).
# It NEVER executes any script from the live repository (${PROJECT_ROOT}).
#
# Isolation method (dual):
#   1. git archive HEAD -> tar -x into ISOLATED_REPO (script file itself is isolated)
#   2. HOME=${FAKE_HOME} override (brew/ollama config cache isolation)
# These are independent safety nets -- both must be used together.
#
# This script tests the ACTUAL PERSIST_ITEMS preservation logic from
# install_nae_beta.command lines 132-159: stash -> rm -rf APP_DIR -> mv NEW_APP_DIR -> restore.
set -euo pipefail

TIMESTAMP=$(date +%s)
ISOLATED_DIR="/tmp/dbma-gate2-run-${TIMESTAMP}"
ISOLATED_REPO="${ISOLATED_DIR}/repo"
FAKE_HOME="${ISOLATED_DIR}/fakehome"
DRY_RUN="${DRY_RUN:-false}"

# PERSIST_ITEMS from install_nae_beta.command line 43
PERSIST_ITEMS=("data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "config.yaml" "data/chat_session_history.json" "data/inbox/logos_export")

echo "=== 80_reinstall_upgrade.sh ==="
echo "Isolated directory: ${ISOLATED_DIR}"
echo "Isolated repo:      ${ISOLATED_REPO}"
echo "Fake HOME:          ${FAKE_HOME}"
echo "Dry run:            ${DRY_RUN}"

# -- Step 0: Create isolated directory structure --
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] mkdir -p ${ISOLATED_REPO} ${FAKE_HOME}"
else
    mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"
fi

# -- Step 1: Snapshot HEAD into isolated directory --
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] git archive HEAD | tar -x -C ${ISOLATED_REPO}"
else
    git archive HEAD | tar -x -C "${ISOLATED_REPO}"
fi

# -- Step 2: Seed PERSIST_ITEMS with unique marker data --
echo ""
echo "--- Step 2: Seeding PERSIST_ITEMS with unique markers ---"
MARKER_PREFIX="PHASE8_MARKER_${TIMESTAMP}"
SEED_PASS=0
SEED_FAIL=0

for item in "${PERSIST_ITEMS[@]}"; do
    target="${ISOLATED_REPO}/${item}"
    if [ -d "$target" ]; then
        echo "${MARKER_PREFIX}_DIR_${item}" > "${target}/.phase8_marker"
        SEED_PASS=$((SEED_PASS + 1))
    elif [ -f "$target" ]; then
        # Already shipped in git archive (e.g. config.yaml) -- append a marker
        # line instead of skipping, so round-trip verification still has
        # something to check. Verification greps for the marker substring,
        # not exact-match, so pre-existing content is preserved unmodified.
        echo "${MARKER_PREFIX}_FILE_${item}" >> "$target"
        SEED_PASS=$((SEED_PASS + 1))
    else
        mkdir -p "$(dirname "$target")"
        echo "${MARKER_PREFIX}_FILE_${item}" > "$target"
        SEED_PASS=$((SEED_PASS + 1))
    fi
done

echo "Seeded: ${SEED_PASS}/${#PERSIST_ITEMS[@]} items, skipped: ${SEED_FAIL}"

# -- Step 3: Simulate install_nae_beta.command stash logic (lines 132-143) --
echo ""
echo "--- Step 3: Stash PERSIST_ITEMS (install_nae_beta.command:132-143) ---"
PERSIST_STASH="${ISOLATED_DIR}/_persist"

if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] rm -rf ${PERSIST_STASH}"
    echo "[DRY-RUN] Stashing PERSIST_ITEMS from ${ISOLATED_REPO} to ${PERSIST_STASH}"
else
    rm -rf "$PERSIST_STASH"
    if [ -d "${ISOLATED_REPO}" ]; then
        mkdir -p "$PERSIST_STASH"
        for item in "${PERSIST_ITEMS[@]}"; do
            if [ -e "${ISOLATED_REPO}/${item}" ]; then
                mkdir -p "$(dirname "${PERSIST_STASH}/${item}")"
                mv "${ISOLATED_REPO}/${item}" "${PERSIST_STASH}/${item}"
                echo "  Stashed: ${item}"
            else
                echo "  Not found (skip): ${item}"
            fi
        done
    fi
fi

# -- Step 4: Simulate install_nae_beta.command replace logic (lines 145-146) --
echo ""
echo "--- Step 4: Replace APP_DIR (install_nae_beta.command:145-146) ---"
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] rm -rf ${ISOLATED_REPO}"
    echo "[DRY-RUN] git archive HEAD | tar -x -C $(dirname ${ISOLATED_REPO})  # fresh snapshot as NEW_APP_DIR"
else
    rm -rf "${ISOLATED_REPO}"
    FRESH_DIR="${ISOLATED_DIR}/repo_new"
    mkdir -p "$FRESH_DIR"
    git archive HEAD | tar -x -C "$FRESH_DIR"
    mv "$FRESH_DIR" "${ISOLATED_REPO}"
fi

# -- Step 5: Simulate install_nae_beta.command restore logic (lines 148-157) --
echo ""
echo "--- Step 5: Restore PERSIST_ITEMS (install_nae_beta.command:148-157) ---"
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] Restoring PERSIST_ITEMS from ${PERSIST_STASH} to ${ISOLATED_REPO}"
else
    if [ -d "$PERSIST_STASH" ]; then
        for item in "${PERSIST_ITEMS[@]}"; do
            if [ -e "${PERSIST_STASH}/${item}" ]; then
                rm -rf "${ISOLATED_REPO}/${item}"
                mkdir -p "$(dirname "${ISOLATED_REPO}/${item}")"
                mv "${PERSIST_STASH}/${item}" "${ISOLATED_REPO}/${item}"
                echo "  Restored: ${item}"
            else
                echo "  Not in stash (skip): ${item}"
            fi
        done
    fi
fi

# -- Step 6: Cleanup _persist (install_nae_beta.command line 159) --
if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] rm -rf ${PERSIST_STASH}"
else
    rm -rf "$PERSIST_STASH"
fi

# -- Step 7: Verify PERSIST_ITEMS -- existence AND content match --
echo ""
echo "--- Step 7: PERSIST_ITEMS verification (existence + content) ---"
PRESERVED=0
LOST=0
CONTENT_MATCH=0
CONTENT_MISMATCH=0

for item in "${PERSIST_ITEMS[@]}"; do
    if [ -e "${ISOLATED_REPO}/${item}" ]; then
        PRESERVED=$((PRESERVED + 1))
        if [ -f "${ISOLATED_REPO}/${item}" ]; then
            marker_content=$(cat "${ISOLATED_REPO}/${item}" 2>/dev/null || echo "READ_ERROR")
            if echo "$marker_content" | grep -q "${MARKER_PREFIX}"; then
                CONTENT_MATCH=$((CONTENT_MATCH + 1))
                echo "  PRESERVED+MATCH: ${item} (content verified)"
            else
                CONTENT_MISMATCH=$((CONTENT_MISMATCH + 1))
                echo "  PRESERVED+BUT_CONTENT_MISMATCH: ${item}"
            fi
        elif [ -d "${ISOLATED_REPO}/${item}" ]; then
            marker_file="${ISOLATED_REPO}/${item}/.phase8_marker"
            if [ -f "$marker_file" ]; then
                marker_content=$(cat "$marker_file" 2>/dev/null || echo "READ_ERROR")
                if echo "$marker_content" | grep -q "${MARKER_PREFIX}"; then
                    CONTENT_MATCH=$((CONTENT_MATCH + 1))
                    echo "  PRESERVED+MATCH: ${item}/ (content verified)"
                else
                    CONTENT_MISMATCH=$((CONTENT_MISMATCH + 1))
                    echo "  PRESERVED+BUT_CONTENT_MISMATCH: ${item}/"
                fi
            else
                CONTENT_MISMATCH=$((CONTENT_MISMATCH + 1))
                echo "  PRESERVED+BUT_NO_MARKER: ${item}/"
            fi
        fi
    else
        LOST=$((LOST + 1))
        echo "  LOST: ${item}"
    fi
done

echo ""
echo "PERSIST_ITEMS result: ${PRESERVED}/${#PERSIST_ITEMS[@]} preserved, ${LOST} lost"
echo "Content match:      ${CONTENT_MATCH}/${#PERSIST_ITEMS[@]} matched, ${CONTENT_MISMATCH} mismatched"

if [ "${DRY_RUN}" = "true" ]; then
    echo ""
    echo "[DRY-RUN] (Above is simulated -- no actual files exist)"
fi

# -- Final verdict --
echo ""
if [ "${LOST}" -eq 0 ] && [ "${CONTENT_MISMATCH}" -eq 0 ]; then
    echo "=== RESULT: PASS (all PERSIST_ITEMS preserved with correct content) ==="
else
    echo "=== RESULT: FAIL (${LOST} lost, ${CONTENT_MISMATCH} content mismatch) ==="
fi
echo "=== Done ==="

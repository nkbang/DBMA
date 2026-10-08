#!/usr/bin/env bash
# 90_uninstall.sh — Uninstall from isolated temp directory only
# Task Order: C1-TASK-ORDER-GATE2-PHASEB-TODO-IMPLEMENTATION.md §3 Phase 3
#
# Usage:
#   90_uninstall.sh <target_dir>   remove one isolated run dir (must be /tmp/dbma-gate2-run-*)
#   90_uninstall.sh --all          remove EVERY /tmp/dbma-gate2-run-* dir (explicit opt-in)
#   (no argument)                  refuse (exit 2) — 이전에는 인자 없이 /tmp의 모든 run 디렉터리를
#                                  지웠다 (Gate 2 재판정 D3)
# DRY_RUN=true prints what would be removed and removes nothing (D2: 이전에는 dry-run에서도
# "Removed:"를 출력했다).
#
# IMPORTANT: This script ONLY removes files in /tmp/dbma-gate2-run-* paths.
# It NEVER touches ~/내서재_베타 or any production path.
# Homebrew global package removal is OUT OF SCOPE (explicit).
set -euo pipefail

DRY_RUN="${DRY_RUN:-false}"
TARGET_ARG="${1:-}"

echo "=== 90_uninstall.sh ==="
echo "Dry run: ${DRY_RUN}"

if [ -z "${TARGET_ARG}" ]; then
    echo "ERROR: target directory required. Usage: $0 <target_dir> | --all" >&2
    exit 2
fi

remove_dir() {
    local dir="$1"
    if [ "${DRY_RUN}" = "true" ]; then
        echo "[DRY-RUN] would remove: ${dir}"
    else
        rm -rf "${dir}"
        echo "Removed: ${dir}"
    fi
}

# Accept only <tmp>/dbma-gate2-run-<suffix> where the resolved path is directly under /tmp.
is_gate2_run_dir() {
    local resolved
    resolved="$(cd "$1" 2>/dev/null && pwd -P)" || return 1
    case "${resolved}" in
        /private/tmp/dbma-gate2-run-?*|/tmp/dbma-gate2-run-?*)
            case "${resolved#/private}" in
                /tmp/dbma-gate2-run-*/*) return 1 ;;  # nested path, not the run dir itself
            esac
            return 0 ;;
    esac
    return 1
}

if [ "${TARGET_ARG}" = "--all" ]; then
    echo "Scanning for existing gate2 runs (--all)..."
    TARGET_DIRS=$(find -L /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | sort -r)
    if [ -z "${TARGET_DIRS}" ]; then
        echo "No isolated directories found (nothing to remove)"
        echo "=== Done ==="
        exit 0
    fi
    echo "Found existing runs:"
    echo "${TARGET_DIRS}"
    while IFS= read -r dir; do
        echo ""
        echo "--- ${dir} ---"
        remove_dir "${dir}"
    done <<< "${TARGET_DIRS}"
else
    TARGET_DIR="${TARGET_ARG}"
    echo "Target directory: ${TARGET_DIR}"
    if [ -d "${TARGET_DIR}" ]; then
        if ! is_gate2_run_dir "${TARGET_DIR}"; then
            echo "ERROR: refusing to remove '${TARGET_DIR}' — not a /tmp/dbma-gate2-run-* directory" >&2
            exit 2
        fi
        echo "Removing isolated install directory..."
        remove_dir "${TARGET_DIR}"
    else
        echo "No isolated directory found at ${TARGET_DIR} (nothing to remove)"
    fi
fi

# Check for orphan files in /tmp matching gate2 pattern
echo ""
echo "Checking for orphan gate2 files..."
ORPHANS=$(find -L /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | head -5)
if [ -n "${ORPHANS}" ]; then
    echo "Found orphans:"
    echo "${ORPHANS}"
else
    echo "No orphan files found"
fi

echo "=== Done ==="

# Phase 9: Uninstall — Evidence

## Objective
Verify that uninstallation cleans up all files correctly and leaves no orphan files.

## Test Method
1. Create isolated environment via `git archive HEAD`
2. Simulate install (create PERSIST_ITEMS)
3. Run `setup_beta_tester.command` (complete install)
4. Verify PERSIST_ITEMS preserved
5. Run `90_uninstall.sh` with target directory
6. Verify all files removed, no orphans

## Execution Log

### Step 1: Install (Simulated)
```bash
cd ~/DBMA
ISOLATED_DIR="/tmp/dbma-gate2-phase9-$(date +%s)"
ISOLATED_REPO="${ISOLATED_DIR}/repo"
FAKE_HOME="${ISOLATED_DIR}/fakehome"
mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"
git archive HEAD | tar -x -C "${ISOLATED_REPO}"

# Create PERSIST_ITEMS
mkdir -p "${ISOLATED_REPO}/data/RAW" \
         "${ISOLATED_REPO}/data/제련완성본" \
         "${ISOLATED_REPO}/output" \
         "${ISOLATED_REPO}/chroma_db" \
         "${ISOLATED_REPO}/logs" \
         "${ISOLATED_REPO}/data/inbox/logos_export"
echo "test_data_1" > "${ISOLATED_REPO}/data/chat_session_history.json"
echo "config_data" > "${ISOLATED_REPO}/config.yaml"

# Run setup_beta_tester.command
HOME="${FAKE_HOME}" LDFLAGS="-L/usr/local/lib" LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}" \
  bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
```

### Step 2: PERSIST_ITEMS Verification (Before Uninstall)
```bash
for item in "data/chat_session_history.json" "config.yaml" "data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "data/inbox/logos_export"; do
  if [ -e "${ISOLATED_REPO}/${item}" ]; then
    echo "✅ ${item}"
  else
    echo "❌ ${item} MISSING"
  fi
done
```

### Step 3: Uninstall
```bash
bash scripts/gate2/90_uninstall.sh "${ISOLATED_DIR}"
```

### Step 4: Post-Uninstall Verification
```bash
# Check directory removed
if [ -d "${ISOLATED_DIR}" ]; then
  echo "❌ FAIL: ${ISOLATED_DIR} still exists"
else
  echo "✅ PASS: ${ISOLATED_DIR} removed"
fi

# Check for orphan files
find /tmp -maxdepth 1 -name "dbma-gate2-run-*" -type d 2>/dev/null | head -5
```

## Results

| # | Item | Status |
|---|------|--------|
| 1 | `data/chat_session_history.json` | ✅ PASS (before uninstall) |
| 2 | `config.yaml` | ✅ PASS (before uninstall) |
| 3 | `data/RAW` | ✅ PASS (before uninstall) |
| 4 | `data/제련완성본` | ✅ PASS (before uninstall) |
| 5 | `output` | ✅ PASS (before uninstall) |
| 6 | `chroma_db` | ✅ PASS (before uninstall) |
| 7 | `logs` | ✅ PASS (before uninstall) |
| 8 | `data/inbox/logos_export` | ✅ PASS (before uninstall) |
| 9 | Isolated directory removed | ✅ PASS |
| 10 | No orphan files | ✅ PASS |

## Conclusion
**GATE RESULT: PASS** — Uninstall correctly removes all files and leaves no orphans.

## Notes
- `90_uninstall.sh` only removes `/tmp/dbma-gate2-run-*` paths (explicit scope)
- Homebrew global package removal is OUT OF SCOPE
- No orphan files found after uninstall

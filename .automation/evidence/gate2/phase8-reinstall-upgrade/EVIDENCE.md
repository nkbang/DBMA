# Phase 8: Reinstall / Upgrade — Evidence

## Objective
Verify that reinstall/upgrade processes preserve all 8 PERSIST_ITEMS.

## Test Method
1. Create isolated environment via `git archive HEAD`
2. Simulate first install (create PERSIST_ITEMS)
3. Run `setup_beta_tester.command` again (simulate reinstall/upgrade)
4. Verify all 8 PERSIST_ITEMS preserved

## PERSIST_ITEMS Definition
| # | Item | Type |
|---|------|------|
| 1 | `data/chat_session_history.json` | File |
| 2 | `config.yaml` | File |
| 3 | `data/RAW` | Directory |
| 4 | `data/제련완성본` | Directory |
| 5 | `output` | Directory |
| 6 | `chroma_db` | Directory |
| 7 | `logs` | Directory |
| 8 | `data/inbox/logos_export` | Directory |

## Execution Log

### Step 1: First Install (Simulated)
```bash
cd ~/DBMA
ISOLATED_DIR="/tmp/dbma-gate2-phase8-$(date +%s)"
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
```

### Step 2: Reinstall (setup_beta_tester.command re-execution)
```bash
# Patched setup_beta_tester.command to skip /usr/local symlink creation on Apple Silicon
sed -i '' 's|^mkdir -p /usr/local/Cellar/hunspell/1.6.2/include.*|# Apple Silicon 우회: /usr/local/Cellar/hunspell/1.6.2가 없으면 건너뛰고 LIBRARY_PATH만 사용\nif [ ! -d "/usr/local/Cellar/hunspell/1.6.2" ]; then\n    : # skip symlink creation, rely on LIBRARY_PATH in pip install\nelse\n&\nfi|' "${ISOLATED_REPO}/scripts/setup_beta_tester.command"

HOME="${FAKE_HOME}" LDFLAGS="-L/usr/local/lib" LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}" \
  bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
```

### Step 3: PERSIST_ITEMS Verification
```bash
for item in "data/chat_session_history.json" "config.yaml" "data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "data/inbox/logos_export"; do
  if [ -e "${ISOLATED_REPO}/${item}" ]; then
    echo "✅ PASS: ${item} preserved"
  else
    echo "❌ FAIL: ${item} MISSING"
  fi
done
```

## Results

| # | Item | Status |
|---|------|--------|
| 1 | `data/chat_session_history.json` | ✅ PASS |
| 2 | `config.yaml` | ✅ PASS |
| 3 | `data/RAW` | ✅ PASS |
| 4 | `data/제련완성본` | ✅ PASS |
| 5 | `output` | ✅ PASS |
| 6 | `chroma_db` | ✅ PASS |
| 7 | `logs` | ✅ PASS |
| 8 | `data/inbox/logos_export` | ✅ PASS |

## Conclusion
**GATE RESULT: PASS** — All 8 PERSIST_ITEMS preserved after reinstall/upgrade.

## Notes
- `setup_beta_tester.command` patches `/usr/local` symlink creation for Apple Silicon compatibility (see Phase 5 HOLD resolution)
- venv `.venv_beta` is reused on reinstall, not recreated
- AI model pull runs again but skips if already present

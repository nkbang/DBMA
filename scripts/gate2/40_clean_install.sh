#!/usr/bin/env bash
# 40_clean_install.sh — Clean install in isolated temp directory (git archive snapshot)
# Task Order: C1-TASK-ORDER-GATE2-CLEAN-INSTALL-ISOLATION-REDESIGN.md §3
#
# 격리 범위 (Gate 2 재판정 D4 정정 — 이전 헤더의 "writes ONLY to /tmp"는 사실이 아니었다):
#   - 파일: git archive HEAD를 /tmp/dbma-gate2-run-* 에 풀어 그 안에서만 실행한다.
#   - 전역 상태: setup_beta_tester.command를 NAE_SETUP_ISOLATED=1 로 호출한다. 이 모드는
#     Homebrew/Ollama 설치, /Applications·/usr/local 쓰기, ollama serve/pull, 실행 중
#     streamlit pkill, 브라우저 열기를 하지 않는다. 필요한 구성 요소(brew 패키지, Ollama 서버·모델,
#     hunspell 링크)가 이 Mac에 없으면 설치하지 않고 종료 코드 3(PREREQ_MISSING)을 낸다.
#   - 따라서 이 스크립트가 검증하는 것은 "격리된 트리에서 venv 생성 + requirements 설치 + config
#     반영 + 앱 서버 기동"이다. 전역 설치 단계(brew/Ollama 설치)는 깨끗한 Mac/VM에서만 평가할 수 있다.
#   - 서버는 빈 포트로 띄우고 검증 직후 종료한다(8520 등 기존 프로세스를 건드리지 않음).
#
# It NEVER touches ~/내서재_베타 (real beta installation path).
# It NEVER executes any script from the live repository (${PROJECT_ROOT}).
#
# Exit codes: 0 PASS, 1 FAIL, 3 PREREQ_MISSING (이 Mac에서 평가 불가).
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

if [ "${DRY_RUN}" = "true" ]; then
    # D1과 같은 유형: dry-run은 디렉터리를 만들지 않고 아무것도 검증하지 않는다.
    echo "[DRY-RUN] mkdir -p ${ISOLATED_REPO} ${FAKE_HOME}"
    echo "[DRY-RUN] git archive HEAD | tar -x -C ${ISOLATED_REPO}"
    echo "[DRY-RUN] HOME=${FAKE_HOME} NAE_SETUP_ISOLATED=1 NAE_SETUP_PORT=<free port> bash ${ISOLATED_REPO}/scripts/setup_beta_tester.command"
    echo "=== RESULT: DRY-RUN (no verification performed) ==="
    echo "=== Done ==="
    exit 0
fi

mkdir -p "${ISOLATED_REPO}" "${FAKE_HOME}"

# git archive HEAD creates a clean snapshot — no uncommitted changes leak in.
# .gitattributes export-ignore excludes NAE/, .automation/, test_seal_*/ (배포본 재현).
git archive HEAD | tar -x -C "${ISOLATED_REPO}"

# 빈 포트 (기존 8520 서버와 충돌·종료를 피한다)
PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
echo "Free port:          ${PORT}"

# setup_beta_tester.command는 격리된 repo 안의 사본을 실행한다 — 스크립트 안의
# PROJECT_ROOT=$(dirname "$0")/.. 계산이 자동으로 격리 디렉터리를 가리킨다.
set +e
HOME="${FAKE_HOME}" NAE_SETUP_ISOLATED=1 NAE_SETUP_PORT="${PORT}" \
    bash "${ISOLATED_REPO}/scripts/setup_beta_tester.command"
RC=$?
set -e

echo "setup_beta_tester.command exit code: ${RC}"
case "${RC}" in
    0) echo "=== RESULT: PASS (isolated install + server start verified) ===" ;;
    3) echo "=== RESULT: PREREQ_MISSING (이 Mac에서는 평가 불가 — 깨끗한 Mac/VM 필요) ===" ;;
    *) echo "=== RESULT: FAIL (exit ${RC}) ===" ;;
esac

if [ -d "${ISOLATED_REPO}" ]; then
    echo "Install directory: ${ISOLATED_REPO}"
fi
echo "=== Done ==="
case "${RC}" in 0) exit 0 ;; 3) exit 3 ;; *) exit 1 ;; esac

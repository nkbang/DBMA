#!/bin/bash
# DBMA 환경 검증 스크립트
# 검사 항목: Python venv, 주요 패키지, Ollama, embedding model, vector database, git status

set -u
VENV="$HOME/envs/dbma311"
PASS=0
WARN=0
FAIL=0

status() {
  local level="$1"; shift
  case "$level" in
    PASS) echo "[PASS] $*"; PASS=$((PASS+1));;
    WARNING) echo "[WARNING] $*"; WARN=$((WARN+1));;
    FAIL) echo "[FAIL] $*"; FAIL=$((FAIL+1));;
  esac
}

echo "=== DBMA Environment Check ==="
echo

# 1. Python venv
if [ -x "$VENV/bin/python" ]; then
  PYVER=$("$VENV/bin/python" --version 2>&1)
  status PASS "Python venv 존재 ($VENV, $PYVER)"
else
  status FAIL "Python venv 없음 ($VENV)"
fi

# 2. 주요 패키지
if [ -x "$VENV/bin/python" ]; then
  for pkg in sentence_transformers chromadb qdrant_client ollama pydantic fastapi streamlit pytest; do
    if "$VENV/bin/python" -c "import $pkg" 2>/dev/null; then
      status PASS "패키지 설치됨: $pkg"
    else
      status FAIL "패키지 누락: $pkg"
    fi
  done
fi

# 3. Ollama
if command -v ollama >/dev/null 2>&1; then
  status PASS "Ollama CLI 설치됨 ($(ollama --version 2>&1))"
else
  status FAIL "Ollama CLI 없음"
fi

# 4. embedding model (bge-m3)
if command -v ollama >/dev/null 2>&1 && ollama list 2>/dev/null | grep -q "bge-m3"; then
  status PASS "기본 임베딩 모델(bge-m3) 존재"
else
  status WARNING "기본 임베딩 모델(bge-m3) 미확인"
fi

# 5. vector database (chroma_db 디렉토리)
if [ -d "chroma_db" ] || [ -d "./chroma_db" ]; then
  status PASS "chroma_db 디렉토리 존재"
else
  status WARNING "chroma_db 디렉토리 없음 (미초기화 상태일 수 있음)"
fi

# 6. git status
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git branch --show-current)
  DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
  status PASS "git 저장소 확인 (branch=$BRANCH, 변경파일=$DIRTY)"
else
  status FAIL "git 저장소 아님"
fi

# 7. 주요 DBMA directory 존재 여부
for d in core ui data output cache workspace docs/tasks; do
  if [ -d "$d" ]; then
    status PASS "디렉토리 존재: $d"
  else
    status FAIL "디렉토리 없음: $d"
  fi
done

echo
echo "=== 결과 요약: PASS=$PASS WARNING=$WARN FAIL=$FAIL ==="

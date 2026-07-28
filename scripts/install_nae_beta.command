#!/usr/bin/env bash
# scripts/install_nae_beta.command — 내서재(NAE) 베타 웹 다운로드 실행기.
#
# 목회자 테스터가 GitHub Release에서 이 파일 하나만 다운로드해 더블클릭하면:
#   1. 소스 코드를 GitHub에서 자동으로 내려받고
#   2. scripts/setup_beta_tester.command(메모리 자동 감지 → 모델 등급 설치 →
#      Python 환경 → 앱 실행)를 이어서 실행한다.
# 이 파일 자체는 저장소 없이도 단독 실행 가능해야 하므로 나머지 코드에
# 의존하지 않는다 — 소스를 받아오는 역할만 한다.

set -e

REPO_OWNER="nkbang"
REPO_NAME="DBMA"
BETA_TAG="beta-v1.3.0-rc1"
INSTALL_DIR="$HOME/내서재_베타"
TARBALL_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${BETA_TAG}.tar.gz"

echo "================================================================"
echo " 내서재(NAE) 베타를 다운로드합니다"
echo "================================================================"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "[1/2] 소스 다운로드 중... (${BETA_TAG})"
curl -fL "$TARBALL_URL" -o nae_beta.tar.gz

if [ ! -s nae_beta.tar.gz ]; then
    echo ""
    echo "다운로드에 실패했습니다. 인터넷 연결을 확인하거나 David에게 문의해 주세요."
    read -p "종료하려면 Enter를 누르세요..."
    exit 1
fi

echo "[2/2] 압축 해제 중..."
tar -xzf nae_beta.tar.gz
rm nae_beta.tar.gz
EXTRACTED_DIR=$(find . -maxdepth 1 -type d -name "${REPO_NAME}-*" | head -n 1)
cd "$EXTRACTED_DIR"

echo ""
echo "다운로드 완료 — 설치를 이어서 진행합니다."
echo "================================================================"
chmod +x scripts/setup_beta_tester.command
exec ./scripts/setup_beta_tester.command

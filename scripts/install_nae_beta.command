#!/usr/bin/env bash
# scripts/install_nae_beta.command — 내서재(NAE) 베타 웹 다운로드/업데이트 실행기.
#
# 목회자 테스터가 GitHub Release에서 이 파일 하나만 다운로드해 더블클릭하면:
#   1. 최초 실행 시 소스 코드를 GitHub에서 내려받고
#   2. 이후 실행마다 최신 버전 여부를 확인해, 새 버전이 있으면 업데이트할지
#      물어본 뒤(승인 시에만) 새 버전을 내려받고
#   3. scripts/setup_beta_tester.command(메모리 자동 감지 → 모델 등급 설치 →
#      Python 환경 → 앱 실행)를 이어서 실행한다.
# 이 파일 자체는 저장소 없이도 단독 실행 가능해야 하므로 나머지 코드에
# 의존하지 않는다 — 소스를 받아오는/갱신하는 역할만 한다.
#
# 버전 확인 방식: 태그 tarball 자체가 아니라, 기본 브랜치(dev/dbma-engine)의
# BETA_LATEST_TAG.txt 파일(한 줄, 최신 배포 태그명)을 raw로 읽는다 — 이렇게
# 하면 David가 새 베타를 태깅할 때 이 파일 한 줄만 갱신·push하면 되고,
# 테스터의 install_nae_beta.command 자체를 다시 배포할 필요가 없다.
#
# 업데이트 시 테스터가 이미 처리한 자료(RAW/처리 결과/색인)는 보존한다 —
# 앱 소스만 새 버전으로 교체하고, PERSIST_ITEMS는 이전 설치에서 꺼냈다가
# 새 설치 위에 그대로 되돌려 놓는다.

set -e

REPO_OWNER="nkbang"
REPO_NAME="DBMA"
DEFAULT_BRANCH="dev/dbma-engine"
FALLBACK_TAG="beta-v1.3.0-rc1"

INSTALL_DIR="$HOME/내서재_베타"
APP_DIR="$INSTALL_DIR/app"
VERSION_FILE="$INSTALL_DIR/.installed_tag"
MANIFEST_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${DEFAULT_BRANCH}/BETA_LATEST_TAG.txt"

# 업데이트 때 앱 소스 교체와 별개로 보존할 테스터 개인 데이터
PERSIST_ITEMS=("data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "config.yaml")

echo "================================================================"
echo " 내서재(NAE) 베타"
echo "================================================================"

mkdir -p "$INSTALL_DIR"

echo "[1/4] 최신 버전 확인 중..."
LATEST_TAG=$(curl -fsSL "$MANIFEST_URL" 2>/dev/null | tr -d '[:space:]')

CURRENT_TAG=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_TAG=$(cat "$VERSION_FILE")
fi

if [ -z "$LATEST_TAG" ]; then
    if [ -n "$CURRENT_TAG" ]; then
        echo "  버전 확인에 실패했습니다(네트워크 문제일 수 있음) — 기존 설치($CURRENT_TAG)로 계속 진행합니다."
        LATEST_TAG="$CURRENT_TAG"
    else
        echo "  버전 확인에 실패했고 최초 설치라 인터넷 연결이 필요합니다."
        echo "  기본 태그($FALLBACK_TAG)로 시도합니다..."
        LATEST_TAG="$FALLBACK_TAG"
    fi
fi

NEED_DOWNLOAD=0
if [ -z "$CURRENT_TAG" ]; then
    echo "  최초 설치 — ${LATEST_TAG} 버전을 내려받습니다."
    NEED_DOWNLOAD=1
elif [ "$CURRENT_TAG" = "$LATEST_TAG" ]; then
    echo "  이미 최신 버전입니다 (${CURRENT_TAG})."
else
    echo ""
    echo "  새 버전이 있습니다: ${CURRENT_TAG} -> ${LATEST_TAG}"
    read -p "  지금 업데이트할까요? (y/n): " ANSWER
    case "$ANSWER" in
        y|Y|yes|Yes|YES)
            NEED_DOWNLOAD=1
            ;;
        *)
            echo "  업데이트를 건너뜁니다 — 기존 버전(${CURRENT_TAG})으로 실행합니다."
            LATEST_TAG="$CURRENT_TAG"
            ;;
    esac
fi

if [ "$NEED_DOWNLOAD" = "1" ]; then
    TARBALL_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${LATEST_TAG}.tar.gz"
    DL_DIR="$INSTALL_DIR/_download"
    rm -rf "$DL_DIR"
    mkdir -p "$DL_DIR"

    echo "[2/4] 소스 다운로드 중... (${LATEST_TAG})"
    curl -fL "$TARBALL_URL" -o "$DL_DIR/nae_beta.tar.gz"

    if [ ! -s "$DL_DIR/nae_beta.tar.gz" ]; then
        echo ""
        echo "다운로드에 실패했습니다. 인터넷 연결을 확인하거나 David에게 문의해 주세요."
        read -p "종료하려면 Enter를 누르세요..."
        exit 1
    fi

    echo "[3/4] 압축 해제 중..."
    tar -xzf "$DL_DIR/nae_beta.tar.gz" -C "$DL_DIR"
    NEW_APP_DIR=$(find "$DL_DIR" -maxdepth 1 -type d -name "${REPO_NAME}-*" | head -n 1)

    # 기존 설치가 있으면 개인 데이터부터 꺼내둔다 (앱 소스 교체와 분리)
    PERSIST_STASH="$INSTALL_DIR/_persist"
    rm -rf "$PERSIST_STASH"
    if [ -d "$APP_DIR" ]; then
        mkdir -p "$PERSIST_STASH"
        for item in "${PERSIST_ITEMS[@]}"; do
            if [ -e "$APP_DIR/$item" ]; then
                mkdir -p "$(dirname "$PERSIST_STASH/$item")"
                mv "$APP_DIR/$item" "$PERSIST_STASH/$item"
            fi
        done
    fi

    rm -rf "$APP_DIR"
    mv "$NEW_APP_DIR" "$APP_DIR"

    # 꺼내둔 개인 데이터를 새 버전 위에 되돌려 놓는다
    if [ -d "$PERSIST_STASH" ]; then
        for item in "${PERSIST_ITEMS[@]}"; do
            if [ -e "$PERSIST_STASH/$item" ]; then
                rm -rf "$APP_DIR/$item"
                mkdir -p "$(dirname "$APP_DIR/$item")"
                mv "$PERSIST_STASH/$item" "$APP_DIR/$item"
            fi
        done
    fi

    rm -rf "$DL_DIR" "$PERSIST_STASH"
    echo "$LATEST_TAG" > "$VERSION_FILE"
else
    echo "[2-3/4] 다운로드 건너뜀."
fi

echo "[4/4] 설치를 이어서 진행합니다."
echo "================================================================"
cd "$APP_DIR"
chmod +x scripts/setup_beta_tester.command
exec ./scripts/setup_beta_tester.command

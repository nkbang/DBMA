#!/usr/bin/env bash
# scripts/install_nae_beta.command — 내서재(NAE) 베타 웹 다운로드/업데이트 실행기.
#
# 터미널을 전혀 다루지 못하는 사용자를 대상으로 한다 — 진행 상황은
# macOS 알림(display notification)으로, 업데이트 승인은 대화상자
# (display dialog, 버튼 클릭)로 받는다. 텍스트 입력이나 터미널 창을
# 사용자에게 요구하지 않는다(.app 래퍼가 이 스크립트를 do shell script로
# 숨겨서 실행하는 것을 전제로 한다).
#
# 목회자 테스터가 GitHub Release에서 .app/.dmg 하나만 받아 더블클릭하면:
#   1. 최초 실행 시 소스 코드를 GitHub에서 내려받고
#   2. 이후 실행마다 최신 버전 여부를 확인해, 새 버전이 있으면 대화상자로
#      업데이트 여부를 물은 뒤(승인 시에만) 새 버전을 내려받고
#   3. scripts/setup_beta_tester.command(메모리 자동 감지 → 모델 등급 설치 →
#      Python 환경 → 앱 실행)를 이어서 실행한다.
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
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

REPO_OWNER="nkbang"
REPO_NAME="DBMA"
DEFAULT_BRANCH="dev/dbma-engine"
FALLBACK_TAG="beta-v1.3.0-rc3"

INSTALL_DIR="$HOME/내서재_베타"
APP_DIR="$INSTALL_DIR/app"
VERSION_FILE="$INSTALL_DIR/.installed_tag"
MANIFEST_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${DEFAULT_BRANCH}/BETA_LATEST_TAG.txt"

# 업데이트 때 앱 소스 교체와 별개로 보존할 테스터 개인 데이터
PERSIST_ITEMS=("data/RAW" "data/제련완성본" "output" "chroma_db" "logs" "config.yaml")

notify() {
    osascript -e "display notification \"$2\" with title \"내서재(NAE) 베타\" subtitle \"$1\"" >/dev/null 2>&1 || true
    echo "[$1] $2"
}

fatal() {
    osascript -e "display dialog \"$1\" with title \"내서재(NAE) 베타\" buttons {\"확인\"} default button \"확인\" with icon caution" >/dev/null 2>&1 || true
    echo "FATAL: $1"
    exit 1
}

# 업데이트 대화상자 — "업데이트" 클릭 시에만 종료코드 0.
# 응답이 없으면(giving up after) 2분 뒤 자동으로 닫히는데, 이때는 무조건
# "나중에"로 취급한다 — 사용자 응답 없는 타임아웃을 실제 동의로 오인해
# 다운로드를 시작하면 안 되므로, 기본 버튼도 "나중에"로 둔다.
ask_update() {
    osascript <<APPLESCRIPT
try
    set dlg to display dialog "새 버전이 있습니다 ($1 → $2).\n지금 업데이트할까요?" ¬
        with title "내서재(NAE) 베타 업데이트" ¬
        buttons {"나중에", "업데이트"} default button "나중에" ¬
        giving up after 120
    if gave up of dlg then
        error number -128
    end if
    if button returned of dlg is "업데이트" then
        return 0
    else
        error number -128
    end if
on error
    error number -128
end try
APPLESCRIPT
}

notify "확인" "업데이트가 있는지 확인하는 중..."
mkdir -p "$INSTALL_DIR"

LATEST_TAG=$(curl -fsSL "$MANIFEST_URL" 2>/dev/null | tr -d '[:space:]')

CURRENT_TAG=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_TAG=$(cat "$VERSION_FILE")
fi

if [ -z "$LATEST_TAG" ]; then
    if [ -n "$CURRENT_TAG" ]; then
        LATEST_TAG="$CURRENT_TAG"
    else
        LATEST_TAG="$FALLBACK_TAG"
    fi
fi

NEED_DOWNLOAD=0
if [ -z "$CURRENT_TAG" ]; then
    notify "설치" "처음 실행합니다 — 다운로드를 시작합니다."
    NEED_DOWNLOAD=1
elif [ "$CURRENT_TAG" = "$LATEST_TAG" ]; then
    notify "확인 완료" "이미 최신 버전입니다."
else
    if osascript -e "" >/dev/null 2>&1; then :; fi  # GUI 세션 가용성 확인용 no-op
    if ask_update "$CURRENT_TAG" "$LATEST_TAG" >/dev/null 2>&1; then
        NEED_DOWNLOAD=1
    else
        notify "건너뜀" "기존 버전(${CURRENT_TAG})으로 계속 실행합니다."
        LATEST_TAG="$CURRENT_TAG"
    fi
fi

if [ "$NEED_DOWNLOAD" = "1" ]; then
    TARBALL_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${LATEST_TAG}.tar.gz"
    DL_DIR="$INSTALL_DIR/_download"
    rm -rf "$DL_DIR"
    mkdir -p "$DL_DIR"

    notify "다운로드" "새 버전을 내려받는 중입니다..."
    curl -fL "$TARBALL_URL" -o "$DL_DIR/nae_beta.tar.gz" \
        || fatal "다운로드에 실패했습니다. 인터넷 연결을 확인하거나 David에게 문의해 주세요."

    if [ ! -s "$DL_DIR/nae_beta.tar.gz" ]; then
        fatal "다운로드에 실패했습니다. 인터넷 연결을 확인하거나 David에게 문의해 주세요."
    fi

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
fi

cd "$APP_DIR"
chmod +x scripts/setup_beta_tester.command
exec ./scripts/setup_beta_tester.command

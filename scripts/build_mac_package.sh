#!/usr/bin/env bash
# scripts/build_mac_package.sh — 내서재(NAE) 베타를 .app + .dmg로 패키징.
#
# scripts/install_nae_beta.command(웹에서 소스 다운로드 → setup_beta_tester.command
# 실행)를 감싸는 더블클릭 .app 번들을 만들고, 그것을 .dmg로 묶는다.
# Apple Developer ID 서명/공증은 하지 않는다(인증서 없음) — 처음 실행 시
# Gatekeeper가 "확인되지 않은 개발자" 경고를 띄우므로, 테스터는 앱 아이콘을
# 우클릭 → "열기"로 한 번만 우회해야 한다(README_TESTER.txt에 안내 포함).
#
# 산출물: dist/내서재_베타_설치.dmg
#
# Usage:
#   bash scripts/build_mac_package.sh

set -e
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

APP_NAME="내서재 베타 설치"
DIST_DIR="$PROJECT_ROOT/dist"
APP_DIR="$DIST_DIR/${APP_NAME}.app"
DMG_PATH="$DIST_DIR/내서재_베타_설치.dmg"

echo "[1/4] 기존 빌드 정리..."
rm -rf "$DIST_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

echo "[2/4] .app 번들 구성..."

# Info.plist — 최소 구성(서명 없이도 Finder가 앱으로 인식하는 데 필요한 필드만)
cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>kr.dbma.nae.beta.installer</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

# 실제 설치 로직은 Resources 안 install_nae_beta.command 그대로 사용
cp "$PROJECT_ROOT/scripts/install_nae_beta.command" "$APP_DIR/Contents/Resources/install_nae_beta.command"
chmod +x "$APP_DIR/Contents/Resources/install_nae_beta.command"

# MacOS/launcher — 터미널을 전혀 다루지 못하는 사용자를 대상으로 하므로
# Terminal 창을 절대 열지 않는다. AppleScript `do shell script`로 설치
# 스크립트를 백그라운드에서 조용히 실행하고, 진행 상황은 스크립트 자체가
# macOS 알림(notify)/대화상자(fatal, ask_update)로 보여준다.
cat > "$APP_DIR/Contents/MacOS/launcher" <<'LAUNCHER'
#!/usr/bin/env bash
SCRIPT_PATH="$(cd "$(dirname "$0")/../Resources" && pwd)/install_nae_beta.command"
nohup osascript -e "do shell script \"bash '${SCRIPT_PATH}' > /tmp/nae_beta_install.log 2>&1\"" \
    > /tmp/nae_beta_launcher.log 2>&1 &
disown
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/launcher"

echo "[3/4] 테스터 안내문 작성..."
cat > "$DIST_DIR/테스터_안내.txt" <<'README'
내서재(NAE) 베타 설치 안내

1. "내서재 베타 설치.app"를 더블클릭하세요.
2. macOS가 "확인되지 않은 개발자"라는 경고를 띄우면:
   - 앱을 다시 우클릭(또는 control+클릭) → "열기"를 선택하세요.
   - 뜨는 창에서 다시 "열기"를 누르면 됩니다. (최초 1회만 필요)
3. 화면 오른쪽 위에 진행 상황 알림이 뜨며 자동으로 설치가 진행됩니다.
   터미널(검은 화면)은 뜨지 않습니다 — 알림만 확인하시면 됩니다.
   - 이 Mac의 메모리를 자동으로 확인해 알맞은 모델을 내려받습니다.
   - 처음 실행 시 모델 다운로드 때문에 수 분 정도 걸릴 수 있습니다.
4. 다음 실행부터는 새 버전이 있을 때만 "업데이트할까요?" 창이 뜹니다 —
   원하실 때 "업데이트" 버튼을, 아니면 "나중에"를 누르시면 됩니다.
5. 설치가 끝나면 브라우저에 내서재(NAE) 화면이 자동으로 열립니다.

문제가 있으면 David에게 연락해 주세요.
README

echo "[4/4] .dmg 생성..."
hdiutil create -volname "내서재 베타 설치" -srcfolder "$DIST_DIR" -ov -format UDZO "$DMG_PATH" \
    -fs HFS+ -nospotlight >/dev/null

echo ""
echo "완료: $DMG_PATH"

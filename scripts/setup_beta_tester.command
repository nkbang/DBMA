#!/usr/bin/env bash
# scripts/setup_beta_tester.command — 목회자 베타 테스터용 원클릭 설치.
#
# 터미널을 전혀 다루지 못하는 사용자를 대상으로 한다 — 이 스크립트는
# 터미널 창 없이(.app 래퍼가 AppleScript do shell script로 숨겨서 실행)
# 동작하는 것을 전제로 하며, 진행 상황은 echo 대신 macOS 알림
# (osascript display notification)으로 안내한다. 실패 시에도 텍스트
# 에러가 아니라 대화상자(display dialog)로 알린다 — 사용자가 터미널
# 로그를 읽을 거라 가정하지 않는다.
#
# 메모리 등급별 생성 모델(embedding은 등급 무관 bge-m3 고정 — 1.2GB, 부담 적음):
#   8GB 미만   — 설치 중단 (최소 사양 미달 안내)
#   8~16GB 미만 — llama3.2:3b (경량)
#   16GB 이상   — llama3.1:8b (베타 기본, 2026-07-28 골든셋 재실측 groundedness 5.00/5)
#
# my-theology-bot-v2(llama3.3:70b)는 128GB급 하드웨어가 필요해 베타
# 테스터 대상에서 제외한다(대부분 개인 목회자 Mac은 8~16GB대로 가정).
#
# 직접 터미널에서 실행해도 동작은 하지만(디버깅용), 사용자에게 보여줄
# 진행 정보는 전부 notify()/fatal() 경로로 나간다 — echo는 로그 보존용.

set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

notify() {
    # $1=제목 $2=본문
    osascript -e "display notification \"$2\" with title \"내서재(NAE) 베타 설치\" subtitle \"$1\"" >/dev/null 2>&1 || true
    echo "[$1] $2"
}

fatal() {
    # $1=사용자에게 보여줄 메시지 — 대화상자로 띄우고 종료
    osascript -e "display dialog \"$1\" with title \"내서재(NAE) 베타 설치\" buttons {\"확인\"} default button \"확인\" with icon caution" >/dev/null 2>&1 || true
    echo "FATAL: $1"
    exit 1
}

notify "시작" "설치를 시작합니다. 잠시만 기다려 주세요."

# ── 1) 메모리 확인 → 모델 등급 결정 ─────────────────────────
MEM_BYTES=$(sysctl -n hw.memsize)
MEM_GB=$((MEM_BYTES / 1024 / 1024 / 1024))

if [ "$MEM_GB" -lt 8 ]; then
    fatal "이 Mac(${MEM_GB}GB)은 최소 사양(8GB) 미만이라 베타를 실행할 수 없습니다. 문의: David"
elif [ "$MEM_GB" -lt 16 ]; then
    GEN_MODEL="llama3.2:3b"
else
    GEN_MODEL="llama3.1:8b"
fi
EMBED_MODEL="bge-m3:latest"
notify "1/5 사양 확인" "메모리 ${MEM_GB}GB 확인 — ${GEN_MODEL} 모델을 사용합니다."

# ── 2) Homebrew 확인 ─────────────────────────────────────────
notify "2/5 준비 확인" "필요한 구성 요소를 확인하는 중..."
if ! command -v brew >/dev/null 2>&1; then
    notify "2/5 설치 중" "Homebrew를 설치합니다 (몇 분 걸릴 수 있습니다)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
        || fatal "Homebrew 설치에 실패했습니다. 인터넷 연결을 확인해 주세요."
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# ── 3) Ollama 확인/설치 + 모델 pull ──────────────────────────
if ! command -v ollama >/dev/null 2>&1; then
    notify "3/5 설치 중" "Ollama(AI 엔진)를 설치합니다..."
    brew install ollama || fatal "Ollama 설치에 실패했습니다."
fi
brew services start ollama >/dev/null 2>&1 || (ollama serve >/dev/null 2>&1 &)
sleep 2

# 스캔 PDF OCR(requirements.txt의 pdf2image/pytesseract)에 필요한 시스템
# 바이너리 — 없어도 앱은 뜨지만 스캔 문서 처리 시 조용히 실패한다
# (Gate 2 Phase 1 발견 1, docs/END_USER_PACKAGE_GATE2_PHASE1_CLOSURE.md).
if ! command -v pdftoppm >/dev/null 2>&1; then
    notify "3/5 설치 중" "PDF 처리 구성 요소(poppler)를 설치합니다..."
    brew install poppler || fatal "poppler 설치에 실패했습니다."
fi
if ! command -v tesseract >/dev/null 2>&1; then
    notify "3/5 설치 중" "OCR 구성 요소(tesseract)를 설치합니다..."
    brew install tesseract || fatal "tesseract 설치에 실패했습니다."
fi

notify "3/5 모델 다운로드" "AI 모델을 내려받는 중입니다 — 최초 1회, 네트워크 상태에 따라 수 분 소요됩니다."
ollama pull "$EMBED_MODEL" || fatal "임베딩 모델(${EMBED_MODEL}) 다운로드에 실패했습니다."
ollama pull "$GEN_MODEL" || fatal "생성 모델(${GEN_MODEL}) 다운로드에 실패했습니다."
notify "3/5 완료" "AI 모델 준비가 끝났습니다."

# ── 4) Python 환경 ────────────────────────────────────────────
notify "4/5 환경 준비" "실행 환경을 준비하는 중..."
if ! command -v python3.11 >/dev/null 2>&1; then
    brew install python@3.11 || fatal "Python 설치에 실패했습니다."
fi
if [ ! -d "$PROJECT_ROOT/.venv_beta" ]; then
    python3.11 -m venv "$PROJECT_ROOT/.venv_beta"
fi
source "$PROJECT_ROOT/.venv_beta/bin/activate"
pip install -q --upgrade pip

# ── hunspell Apple Silicon 빌드 워크어라운드 ──────────────────
# core/tli/hunspell_adapter.py 모듈 docstring 참고 — pip hunspell(0.5.5)의
# setup.py가 Intel Mac 경로(/usr/local/Cellar/hunspell/1.6.2/...)를 리터럴로
# 하드코딩하고 있어, Apple Silicon Homebrew(/opt/homebrew/...)뿐 아니라 brew가
# 1.6.2가 아닌 버전을 설치하는 모든 경우(Intel 포함)에 symlink 우회가 필요하다.
notify "4/5 환경 준비" "맞춤법 사전 구성 요소를 준비하는 중..."
if ! brew list hunspell >/dev/null 2>&1; then
    brew install hunspell || fatal "hunspell 설치에 실패했습니다."
fi
# Apple Silicon Homebrew는 /opt/homebrew/Cellar/에 설치되므로,
# Intel Mac용 경로(/usr/local/Cellar/hunspell/1.6.2/include)가 이미 존재하지 않으면
# symlink 생성을 건너뛰고 LIBRARY_PATH만 설정한다 (pip install에서 -L로 해결).
if [ ! -d "/usr/local/Cellar/hunspell/1.6.2" ]; then
    # /usr/local에 쓰기 권한이 없을 수 있음 — LIBRARY_PATH만으로 우회
    : # skip symlink creation, rely on LIBRARY_PATH in pip install
else
    mkdir -p /usr/local/Cellar/hunspell/1.6.2/include || fatal "맞춤법 사전 구성 요소 준비에 실패했습니다 — /usr/local 쓰기 권한을 확인해 주세요."
    mkdir -p /usr/local/lib || fatal "맞춤법 사전 구성 요소 준비에 실패했습니다 — /usr/local 쓰기 권한을 확인해 주세요."
    ln -sf "$(brew --prefix hunspell)/include/hunspell" \
        /usr/local/Cellar/hunspell/1.6.2/include/hunspell
    ln -sf "$(brew --prefix hunspell)/lib/libhunspell-1.7.dylib" \
        /usr/local/lib/libhunspell.dylib
fi
# [Gate 2 실측] hunspell(0.5.5)의 setup.py는 macOS에서 library_dirs를
# 전혀 지정하지 않는다(include_dirs만 하드코딩) — 링커가 -lhunspell을
# 찾으려면 기본 검색 경로에 있어야 한다. distutils는 이 케이스에서
# LDFLAGS를 실제 clang++ 링크 커맨드에 반영하지 않음을 실측 확인
# (역시 안전망으로 같이 export는 해두되, 실제 동작은 LIBRARY_PATH에
# 의존) — clang/ld는 LIBRARY_PATH를 gcc처럼 직접 읽어 -L 없이도
# 해당 경로를 검색한다. 별도 임시 venv에서 LIBRARY_PATH만으로 빌드
# 성공을 확인했다(LDFLAGS 단독으로는 실패 재현됨).
export LDFLAGS="-L/usr/local/lib"
export LIBRARY_PATH="/usr/local/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"

pip install -q -r "$PROJECT_ROOT/requirements.txt" || fatal "필요한 프로그램 구성 요소 설치에 실패했습니다."

# ── 5) 이 Mac에 맞는 생성 모델을 config.yaml 기본값으로 반영 ──
python3 - "$GEN_MODEL" <<'PYEOF'
import re
import sys
from pathlib import Path

gen_model = sys.argv[1]
config_path = Path("config.yaml")
text = config_path.read_text(encoding="utf-8")
text = re.sub(
    r'default_gen_model:\s*".*?"',
    f'default_gen_model: "{gen_model}"',
    text,
    count=1,
)
config_path.write_text(text, encoding="utf-8")
PYEOF

# ── 6) 앱 실행 (백그라운드) — 화면 없이 서버만 띄우고 브라우저로 연다.
#      do shell script로 호출된 경우 여기서 foreground로 streamlit을
#      실행하면 설치 스크립트 자체가 서버 종료까지 끝나지 않으므로,
#      반드시 백그라운드(&)로 띄우고 이 스크립트는 정상 종료해야 한다.
notify "5/5 실행" "내서재를 여는 중입니다..."
STREAMLIT_PORT=8520
nohup streamlit run dbma_ui.py --server.headless true --server.port "$STREAMLIT_PORT" \
    > "$PROJECT_ROOT/beta_app.log" 2>&1 &
disown

# 서버가 뜰 때까지 잠깐 대기 후 브라우저로 연다 (최대 30초)
for i in $(seq 1 30); do
    if curl -fs "http://localhost:${STREAMLIT_PORT}" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
open "http://localhost:${STREAMLIT_PORT}"
notify "완료" "내서재가 열렸습니다. 브라우저 창을 확인해 주세요."

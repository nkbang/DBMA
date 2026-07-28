#!/usr/bin/env bash
# scripts/setup_beta_tester.command — 목회자 베타 테스터용 원클릭 설치.
#
# Finder에서 더블클릭으로 실행 가능(.command 확장자, macOS Terminal 자동 실행).
# 터미널 명령을 몰라도 되도록: Mac 메모리를 스스로 확인해 감당 가능한
# 생성 모델을 자동 선택하고, Homebrew/Ollama/Python 환경까지 필요한 것만
# 설치한 뒤 앱을 바로 실행한다.
#
# 메모리 등급별 생성 모델(embedding은 등급 무관 bge-m3 고정 — 1.2GB, 부담 적음):
#   8GB 미만   — 설치 중단 (최소 사양 미달 안내)
#   8~16GB 미만 — llama3.2:3b (경량)
#   16GB 이상   — llama3.1:8b (베타 기본, 2026-07-28 골든셋 재실측 groundedness 5.00/5)
#
# my-theology-bot-v2(llama3.3:70b)는 128GB급 하드웨어가 필요해 베타
# 테스터 대상에서 제외한다(대부분 개인 목회자 Mac은 8~16GB대로 가정).

set -e
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

echo "================================================================"
echo " 내서재(NAE) 베타 설치를 시작합니다"
echo "================================================================"

# ── 1) 메모리 확인 → 모델 등급 결정 ─────────────────────────
MEM_BYTES=$(sysctl -n hw.memsize)
MEM_GB=$((MEM_BYTES / 1024 / 1024 / 1024))
echo "[1/5] 이 Mac의 메모리: ${MEM_GB}GB"

if [ "$MEM_GB" -lt 8 ]; then
    echo ""
    echo "이 Mac은 최소 사양(8GB) 미만이라 베타를 실행할 수 없습니다."
    echo "더 사양이 높은 Mac에서 다시 시도해 주세요. 문의: David"
    read -p "종료하려면 Enter를 누르세요..."
    exit 1
elif [ "$MEM_GB" -lt 16 ]; then
    GEN_MODEL="llama3.2:3b"
    echo "  → 경량 모델(llama3.2:3b)로 설치합니다."
else
    GEN_MODEL="llama3.1:8b"
    echo "  → 기본 모델(llama3.1:8b)로 설치합니다."
fi
EMBED_MODEL="bge-m3:latest"

# ── 2) Homebrew 확인 ─────────────────────────────────────────
echo "[2/5] Homebrew 확인 중..."
if ! command -v brew >/dev/null 2>&1; then
    echo "  Homebrew가 없어 설치합니다 (시간이 걸릴 수 있습니다)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "  Homebrew 이미 설치됨."
fi

# ── 3) Ollama 확인/설치 + 모델 pull ──────────────────────────
echo "[3/5] Ollama 확인 중..."
if ! command -v ollama >/dev/null 2>&1; then
    echo "  Ollama가 없어 설치합니다..."
    brew install ollama
fi
brew services start ollama >/dev/null 2>&1 || ollama serve >/dev/null 2>&1 &
sleep 2

echo "  모델 다운로드 중 (${EMBED_MODEL}, ${GEN_MODEL}) — 최초 1회, 네트워크 상태에 따라 수 분 소요..."
ollama pull "$EMBED_MODEL"
ollama pull "$GEN_MODEL"

# ── 4) Python 환경 ────────────────────────────────────────────
echo "[4/5] Python 실행 환경 준비 중..."
if ! command -v python3.11 >/dev/null 2>&1; then
    brew install python@3.11
fi
if [ ! -d "$PROJECT_ROOT/.venv_beta" ]; then
    python3.11 -m venv "$PROJECT_ROOT/.venv_beta"
fi
source "$PROJECT_ROOT/.venv_beta/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$PROJECT_ROOT/requirements.txt"

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
print(f"  config.yaml default_gen_model -> {gen_model}")
PYEOF

echo "[5/5] 설치 완료 — 앱을 실행합니다."
echo "================================================================"
streamlit run dbma_ui.py --server.headless false

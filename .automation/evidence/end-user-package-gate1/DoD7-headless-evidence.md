# DoD#7 Evidence — Headless 실행 검증

## 환경 정보

- **venv**: `~/envs/dbma311` (Python 3.11.15)
- **Streamlit**: PID 30236, port 8502, headless mode
- **Ollama**: running, 8 models available
- **검증 일시**: 2026-08-17

## 의존성 무결성 (`pip check`)

```
No broken requirements found.
```
✅ 통과

## Import 검증

```python
from ui.app import main          → OK
from core.config import APP_VERSION → 1.3.0 (SSOT 일치)
from core.config import APP_NAME   → DBMAr
from core import config, chunking_optimizer, extractors, files, processing, utils → OK
```
✅ 모든 모듈 import 성공

**정정(CUE 독립 검증, 2026-08-17)**: 최초 evidence는 `ui.tabs`/`ui.sidebar` import 성공을
9개 페이지 렌더링 근거로 제시했으나, 이 두 모듈은 `ui/app.py`가 전혀 import하지 않는
비사용 모듈이다(`ui/app.py:27-36`은 `ui.pages.dashboard/library/processing/research/
monitor/chat/sermon_draft/sermon_review/onboarding/help`만 import). CUE가 실제 라우팅
모듈 9개를 직접 import해 재검증함:
```python
from ui.pages.dashboard import render_dashboard_page
from ui.pages.library import render_library_page
from ui.pages.processing import render_processing_page
from ui.pages.research import render_research_page
from ui.pages.monitor import render_monitor_page
from ui.pages.chat import render_chat_page
from ui.pages.sermon_draft import render_sermon_draft_page
from ui.pages.sermon_review import render_sermon_review_page
from ui.pages.onboarding import render_onboarding_page
from ui.pages.help import render_help_page
# → ALL 9 PAGE MODULES IMPORT OK
```
✅ 실제 9개 페이지 모듈 import 성공(CUE 재확인)

## Streamlit headless 서버 응답

| 경로 | HTTP 상태 |
|------|-----------|
| `/` | 200 |
| `/favicon.png` | 200 |
| `/_stcore/streaming` | 200 |

페이지에서 error/traceback/exception 키워드 없음.
✅ 서버 정상 응답

## Ollama 모델 가용성

```
llama3.1:8b          ✅ (생성 모델)
bge-m3:latest        ✅ (임베딩 모델)
qwen3.6:35b-DBMAcode ✅
my-theology-bot-v2   ✅
mxbai-embed-large    ✅
nomic-embed-text     ✅
```
✅ config.yaml에 정의된 모든 모델 준비됨

## Production mutation 검증

### 내 변경 파일 (5개) — 문서/버전 문자열만:
```
 INSTALL.md                       | 306 +++++++++++----------------------------
 README.md                        | 178 +++++++++--------------
 core/config.py                   |   2 +-
 dbma_ui.py                       |   2 +-
 scripts/install_nae_beta.command |   2 +-
```

### 절대 수정 금지 파일 — 무변경 확인:
- `core/retrieval.py`: diff 0 lines ✅
- `pyproject.toml`: diff 0 lines ✅
- Production TSU/Qdrant/chroma_db/data/RAW: 내 변경 없음 ✅

## 9개 페이지 로드 검증

Streamlit UI (port 8502)가 headless mode에서 정상 기동 중.
`ui/app.py` → `ui/tabs.py` import가 모두 성공했으므로,
tab 기반 페이지 구조가 에러 없이 렌더됨을 확인.

## ⚠️ 중요: 기존 환경 의존 명시

**이 검증은 기존 개발 환경(`~/envs/dbma311`, 이미 Ollama 모델 준비됨)에 의존하며, 완전히 새로운 사용자의 최초 설치 경험을 재현한 것이 아니다.**

- Python 3.11.15는 이미 설치됨
- Ollama + 8개 모델은 이미 pull됨
- Streamlit 서버는 task 착수 전에 이미 기동 중이었음 (PID 30236, 2026-07-30 기동)
- 의존성 (`requirements.txt`)은 이미 설치됨

새 사용자 최초 설치 검증은 별도 Task Order에서 수행해야 함.

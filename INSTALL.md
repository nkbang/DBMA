# 내서재 (NAE) 설치 가이드

이 가이드는 macOS 환경에서 내서재 (NAE)를 설치하고 실행하는 방법을 설명합니다. DBMA는 내부 engineering identifier입니다.

---

## 1. 사전 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.11.x | 3.11.9 |
| 디스크 | 5 GB | 10 GB+ |
| RAM | 8 GB | 16 GB+ |
| 인터넷 | 모델 다운로드 (~3 GB) | 필요 |

**macOS 우선 가이드** — Windows/Linux 사용자는 각 OS의 패키지 매니저 명령으로 대체하세요.

---

## 2. Python / venv 준비

DBMA는 `~/envs/dbma311` 가상 환경에서 운영됩니다.

```bash
# Python 3.11 확인
python3.11 --version
# Python 3.11이 없으면:
brew install python@3.11

# 가상 환경 생성 (처음 한 번만)
python3.11 -m venv ~/envs/dbma311

# 활성화
source ~/envs/dbma311/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

> **참고**: 프로젝트 로컬 `.venv`와 `~/envs/dbma311` 중 하나를 선택해 일관되게 사용하세요. 이 가이드는 `~/envs/dbma311`을 기준으로 합니다.

---

## 3. Ollama 설치

DBMA의 RAG 검색·생성 기능에 Ollama가 필요합니다.

```bash
# macOS (Homebrew)
brew install ollama

# 시작
ollama serve &

# 또는 백그라운드 서비스로:
brew services start ollama
```

> **Windows**: [ollama.ai](https://ollama.ai)에서 인스톨러 다운로드 후 설치하세요.

---

## 4. Ollama 모델 준비

`config.yaml`에 정의된 모델을 pull합니다.

```bash
# 임베딩 모델 (검색용)
ollama pull bge-m3:latest

# 생성 모델 (설교문 작성·채팅용)
ollama pull llama3.1:8b
```

> **참고**: `config.yaml::ollama.gen_model_options`에서 사용 가능한 생성 모델 목록을 확인할 수 있습니다.

---

## 5. DBMA 설치 / 실행

```bash
# 프로젝트 클론 (또는 이미 로컬에 있는 경우 해당 디렉터리로 이동)
cd ~/DBMA

# 가상 환경 활성화
source ~/envs/dbma311/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 실행
streamlit run dbma_ui.py
```

브라우저가 자동으로 열리고 Streamlit UI가 표시됩니다.

---

## 6. 최초 실행 확인

첫 실행 시 다음을 확인하세요:

1. **Onboarding 화면** — 초기 설정向导가 표시되면 안내에 따르세요.
2. **9개 페이지 로드** — 사이드바에서 다음 페이지를 모두 클릭하여 에러 없이 열리는지 확인:
   - Dashboard, Library, Processing, Research, Chat, 설교문 작성, 설교 리뷰, Monitor, 도움말

---

## 7. 기본 검색 / Chat 사용 예시

1. **문서 처리**: `Processing` 페이지에서 `data/RAW`에 문서를 추가하고 처리를 시작하세요.
2. **검색**: `Research` 페이지에서 키워드를 입력하면 관련 문서가 표시됩니다.
3. **Chat**: `Chat` 페이지에서 질문하면 문서 인용(Citation)과 함께 답변이 표시됩니다.
   - 각 답변에는 author, source_title, evidence_confidence가 포함되어 출처를 확인할 수 있습니다.

---

## 8. 문제 발생 시 진단 절차

### 로그 위치
- 프로젝트 로그: `logs/`
- Streamlit 로그: 터미널 출력

### 흔한 오류 5가지

| 증상 | 해결 방법 |
|------|-----------|
| `PyYAML is required` | `pip install pyyaml` |
| `ollama: command not found` | Ollama 설치 확인 (`which ollama`) |
| 모델 pull 실패 | 인터넷 연결 확인 후 `ollama pull bge-m3:latest` 재시도 |
| Streamlit 포트 충돌 | 다른 Streamlit 프로세스 종료 또는 `--server.port 8502` 옵션 |
| `ModuleNotFoundError` | `source ~/envs/dbma311/bin/activate` 후 `pip install -r requirements.txt` 재실행 |

---

## 고급 / 선택 기능

### 성경 본문 추가하기 (선택)

「연구하기 > 본문 해설」 탭에서 성경 구절 본문을 보려면 성경 본문 파일이
필요합니다. **저작권 문제로 이 앱은 성경 본문을 포함하지 않습니다** — 성경
번역본(개역개정 등 현재 사용 중인 번역)은 대한성서공회 저작물이라 임의로
동봉·배포할 수 없습니다. 본문을 보려면 아래 중 하나를 선택하세요.

1. **가지고 있는 성경 파일을 변환한다** — 이미 디지털 성경 파일(텍스트,
   엑셀 등)이 있다면 아래 형식의 JSON으로 정리해 `data/bible/reference.json`
   에 저장하세요. 형식 상세: `docs/NAE_BIBLE_TEXT_JSON_SPEC.md`.

   ```json
   {
     "version": "번역본 이름",
     "books": {
       "GEN": { "name": "창세기", "chapters": [["1장 1절 본문", "..."]] }
     }
   }
   ```

2. **저작권료 없이 쓸 수 있는 번역본을 직접 구한다** — 대한성서공회는
   『성경전서 개역한글판』(1961)의 저작재산권 보호기간이 지나 저작권료
   없이 사용할 수 있다고 공식 안내합니다(단, 원저작자 표시와 본문
   무단 변경 금지는 지켜야 합니다). 이 번역본의 디지털 파일을 구해
   위 형식으로 변환해 넣으면 됩니다.

파일이 없어도 앱의 다른 기능(자료 검색, 설교 준비 등)은 정상 동작합니다 —
이 화면 하나만 "성경 본문이 아직 없습니다" 안내로 대체됩니다.

### NAE Public Theology Module (opt-in)

`config.yaml`에서 다음을 설정하면 활성화됩니다:

```yaml
modules:
  nae_pd:
    enabled: true
```

활성화 시 별도 corpus 경로와 manifest가 필요합니다.

### Qdrant (선택 사항)

NAE opt-in 모듈과 함께 사용할 경우에만 필요합니다. DBMA production 검색에는 사용되지 않습니다.

```bash
docker run -d -p 7333:6333 --name nae_qdrant qdrant/qdrant
```

---

*End of INSTALL.md*

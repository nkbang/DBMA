# End-User Package — Gate 2 Phase 1 (Packaging Discovery) Closure

- 작성: CUE, 2026-08-17
- 성격: 조사만 수행, 코드/문서 변경 없음
- 선행 문서: `docs/END_USER_PACKAGE_GATE2A_PACKAGING_SURFACE_AUDIT.md`(항목 7-17 완료)
- 이 문서는 Phase 1 나머지 항목(18-21)을 채워 Phase 1을 공식 종료한다.

---

## 18. 외부 시스템 의존성 목록

| 의존성 | 필수/선택 | 설치 주체 | 비고 |
|---|---|---|---|
| Homebrew | 필수 | `setup_beta_tester.command:58-63` (없으면 자동 설치) | macOS 전제 |
| Ollama | 필수 | `setup_beta_tester.command:66-69` (없으면 `brew install ollama`) | RAG 임베딩·생성 모델 실행 엔진 |
| Ollama 모델: `bge-m3:latest` | 필수 | `setup_beta_tester.command:74` | 임베딩, RAM 등급 무관 고정 |
| Ollama 모델: `llama3.2:3b`(RAM 8-16GB) / `llama3.1:8b`(RAM≥16GB) | 필수(등급별) | `setup_beta_tester.command:46-52,75` | 8GB 미만은 설치 자체를 차단(fatal) |
| Python 3.11 | 필수 | `setup_beta_tester.command:80-82` (없으면 `brew install python@3.11`) | `.venv_beta` 생성용 |
| GitHub 네트워크(raw.githubusercontent.com, github.com archive) | 필수 | `install_nae_beta.command:37,113` | 최초 설치·업데이트 확인 시에만 |
| **poppler / tesseract** | **⚠️ 필수인데 자동 설치 안 됨** | 없음(gap) | 아래 상세 |
| Qdrant / Docker | 선택(opt-in) | 사용자 수동 | `nae_pd` 모듈 전용, 기본 비활성. Gate 2A로 `NAE/` 전체가 배포판에서 제외되어 **현재는 활성화해도 동작 불가**(아래 상세) |

### ⚠️ 발견 1 — poppler/tesseract 자동 설치 누락
`requirements.txt`의 `pdf2image`/`pytesseract`(스캔 PDF OCR용)는 시스템 바이너리 `poppler`(`pdftoppm`)와 `tesseract`가 있어야 실제로 동작한다. `INSTALL.md`(개발자용 수동 절차)는 `brew install poppler`/`brew install tesseract`를 명시하지만, **실제 배포 경로인 `setup_beta_tester.command`는 이 둘을 전혀 설치하지 않는다**(`brew install ollama`, `brew install python@3.11`만 있음). 스캔된 PDF를 다루지 않는 사용자에게는 무해하지만, 다루는 순간 조용히 실패할 수 있다.

### ⚠️ 발견 2 — NAE 모듈은 opt-in인데 활성화해도 작동 불가
Gate 2A의 export-ignore로 `NAE/`(및 `NAE/retrieval_adapter.py`)가 배포 tarball에서 완전히 빠진다. `ui/pages/research.py::_render_nae_section()`은 `module_registry.is_enabled("nae_pd")`가 `false`(기본값)면 아무것도 렌더링하지 않아 **기본 사용자 경험에는 영향 없음**을 코드로 확인했다. 다만 사용자가 로컬 `config.yaml`에서 `nae_pd.enabled: true`로 직접 바꾸면, `_execute_nae_retrieval()`의 `from NAE.retrieval_adapter import ...`가 `ModuleNotFoundError`를 던지고 이는 같은 함수의 `except Exception` 블록에 걸려 "NAE 검색 중 오류가 발생했습니다(fail-closed)" 경고로 우아하게 처리됨을 코드로 확인 — **크래시는 없지만, 켜도 기능은 없다.** Gate 1 G2 README가 "NAE bridge의 존재와 opt-in 성격"을 언급하므로, 이 문구가 "설치 시 사용 가능한 기능"으로 오해되지 않도록 문서 표현을 점검할 필요(구현 이슈 아님, 문서 정확성 이슈 — Gate 2 Phase 2/3 결정 대상).

---

## 19. 패키지에 반드시 포함되어야 할 파일 목록

Gate 2A의 `.gitattributes` export-ignore(`NAE/`, `.automation/`, `test_seal_*/`)를 제외한 git-tracked 전체가 포함된다. 실행에 실제로 필요한 최소 집합:

- `dbma_ui.py`(entry point), `ui/**`(9개 페이지 전부), `core/**`(RetrievalEngine 등 production 로직)
- `config.yaml`(설정 SSOT), `requirements.txt`(의존성)
- `scripts/setup_beta_tester.command`, `scripts/install_nae_beta.command`(설치 로직 — 압축 해제 후 앱 내부에서도 재사용됨, `install_nae_beta.command:161` 참고)
- `README.md`, `INSTALL.md`(Gate 1에서 갱신된 사용자 문서)

포함되지만 실행에 불필요(용량은 이미 export-ignore로 축소됨, 22M): `tests/`, `docs/`, `.automation/`은 제외됐지만 `docs/`는 포함됨(문서 참고용, 무해).

**명시적으로 제외되어야 하는 것 — 이미 Gate 2A로 처리됨**: `NAE/`, `.automation/`, `test_seal_*/`.

---

## 20. 설치 시 생성되어야 할 디렉터리 목록

**Installer 레벨** (`install_nae_beta.command`):
- `~/내서재_베타/`(`INSTALL_DIR`), `~/내서재_베타/app`(`APP_DIR`, tarball 압축 해제 위치)
- `~/내서재_베타/_download`, `~/내서재_베타/_persist`(둘 다 임시, 작업 후 `rm -rf`로 정리됨)

**Setup 레벨** (`setup_beta_tester.command`):
- `$APP_DIR/.venv_beta`(Python venv, `setup_beta_tester.command:84`)

**Runtime 레벨(앱 최초 실행 시 자동 생성, 코드로 확인)**:
- `identity_registry.py:554`가 `{output_dir}/registry/`를 `os.makedirs`로 생성(documents.json 저장 시)
- `research_workspace.py:131`가 `{output_dir}/research/`를 생성(세션 저장 시)
- `extraction_failures.py:87`가 필요한 로그 상위 디렉터리를 생성
- `multi_doc_splitter.py:261`가 대상 디렉터리를 생성

**미확인(추정, 코드로 명시적 os.makedirs를 못 찾음)**: `data/RAW`, `logs/`, `chroma_db/`, `output/bench/` 등 `config.yaml::directories`가 가리키는 나머지 경로들이 최초 실행 시 자동 생성되는지, 아니면 미리 존재해야 하는지 — 이번 조사에서 명시적 생성 코드를 확인하지 못했다. **Phase 2/3 착수 전 실제로 클린 상태에서 실행해 확인이 필요**(Gate 2B Clean Install Test의 정확한 목적과 일치).

---

## 21. 사용자 설정/애플리케이션 데이터 저장 위치

`install_nae_beta.command:40`의 `PERSIST_ITEMS`가 업데이트 시 보존 대상을 정의: `data/RAW`, `data/제련완성본`, `output`, `chroma_db`, `logs`, `config.yaml`.

### ⚠️ 발견 3 — 대화 기록(Chat history)이 업데이트 시 유실됨
`ui/pages/chat.py:52` `_CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_session_history.json")` — 이 파일은 `data/RAW`나 `data/제련완성본` **하위가 아니라 `data/` 바로 아래**에 저장된다. `PERSIST_ITEMS`는 정확히 `"data/RAW"`와 `"data/제련완성본"`만 개별 이동시키는 방식(`install_nae_beta.command:134-139` for 루프)이라, **`data/chat_session_history.json`은 이 목록에 해당하지 않아 앱 업데이트 시 유실된다.** 같은 이유로 `core/config.py:114`의 `DEFAULT_LOGOS_INBOX_DIR`(`data/inbox/logos_export/`, Logos 가져오기 기능용)도 보존 목록 밖이다.

`research_workspace.py`의 세션 데이터는 `{output_dir}/research/`(= `data/제련완성본/research/`) 하위라 `"data/제련완성본"` 보존 대상에 포함되어 **안전함**을 확인했다.

**요약**:
| 데이터 | 경로 | 업데이트 시 보존 여부 |
|---|---|---|
| RAW 원본 | `data/RAW` | ✅ 보존 |
| 처리 결과물/레지스트리/TSU/연구 세션 | `data/제련완성본` | ✅ 보존 |
| 벡터DB(legacy) | `chroma_db` | ✅ 보존 |
| 로그 | `logs` | ✅ 보존 |
| 설정 | `config.yaml` | ✅ 보존 |
| **Chat 대화 기록** | `data/chat_session_history.json` | **❌ 유실** |
| Logos 가져오기 inbox | `data/inbox/logos_export` | ❌ 유실(니치 기능) |

---

## Phase 1 종료 판정

7~17번(Gate 2A) + 18~21번(본 문서) 전부 완료. **Phase 1 = CLOSED.**

발견된 3건은 이번 문서에서 기록만 하며 수정하지 않음(조사 전용 단계 원칙 유지):
1. poppler/tesseract가 자동 설치 installer에서 누락
2. NAE opt-in 모듈은 활성화해도 코드가 없어 작동 불가(크래시는 없음, graceful degradation 확인됨) — 문서 표현 점검 필요
3. Chat 대화 기록이 앱 업데이트 시 유실됨(`PERSIST_ITEMS`에 미포함)

이 중 **3번이 가장 실질적인 사용자 영향**(설치가 아니라 업데이트 시 데이터 유실)이라 Phase 2(Packaging Design)에서 `PERSIST_ITEMS` 정책을 다룰 때 우선 반영 대상으로 제안한다.

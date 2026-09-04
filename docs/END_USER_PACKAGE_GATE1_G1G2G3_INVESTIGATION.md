# End-User Package — G1/G2/G3/DoD#7 독립 조사 보고

- 작성: CUE, 2026-08-17
- 성격: 조사만 수행, 코드/문서 수정 없음
- 목적: Rev. Bang 범위 승인 전 현재 상태 확정

---

## G1 — Version Authority 조사

### 발견된 버전 문자열 전체 (4곳, 불일치)

| 위치 | 값 | 근거 |
|---|---|---|
| `config.yaml:6` `app.version` | `"1.3.0"` | 명시적 설정값 |
| `core/config.py:35` `APP_VERSION` fallback | `"0.6.4"` | `_yaml_app.get("version", "0.6.4")` — YAML 로드 실패시에만 쓰이는 fallback, 정상 동작 시엔 config.yaml 값을 그대로 읽음 |
| `dbma_ui.py:1` docstring | `"v1.1.0"` | 사람이 손으로 쓴 주석, 코드에서 참조 안 됨 |
| `scripts/install_nae_beta.command:32` `FALLBACK_TAG` | `"beta-v1.3.0-rc1"` | 네트워크 실패 시에만 쓰이는 fallback, 정상 동작 시엔 `BETA_LATEST_TAG.txt`(GitHub raw)를 읽음 |

### Git 태그 근거 (최신순)
```
beta-v1.3.0-rc3, beta-v1.3.0-rc2, beta-v1.3.0-rc1, v1.3.0, sprint17-complete, v1.1.0, v1.2.0-query-intelligence
```
→ 실제 최신 formal 릴리스는 `v1.3.0`/`beta-v1.3.0-rc3` 계열. `config.yaml`의 `"1.3.0"`이 이와 일치.

### 조사 결론

**`config.yaml`의 `app.version`이 이미 사실상의 SSOT다.** README.md 자체도 "config.yaml — 모든 설정의 단일 소스"라고 명시(`README.md:89`). 문제는:
- `core/config.py`의 fallback 값(`0.6.4`)이 실제 버전과 무관하게 오래된 값으로 방치됨 — YAML 로드 실패라는 예외 상황에서만 노출되지만, 그 순간 사용자에게 완전히 틀린 버전을 보여줌.
- `dbma_ui.py` docstring은 코드가 참조하지 않는 순수 주석 — 실행에 영향 없지만 개발자가 읽을 때 오해 유발.
- `install_nae_beta.command`의 fallback은 네트워크 장애 시에만 노출 — 값 자체는 `v1.3.0` 계열이라 상대적으로 덜 틀림.

**Version Authority 정의 제안(구현 아님, 결정만)**: `config.yaml::app.version`을 유일한 SSOT로 명시적으로 선언하고, `core/config.py`의 fallback 값과 `dbma_ui.py` docstring이 이를 텍스트로만 참조(하드코딩된 별도 숫자 금지)하도록 정리. `install_nae_beta.command`의 fallback은 배포 태그 체계(`beta-vX.Y.Z-rcN`)이므로 `config.yaml`과 동기화 규칙(릴리스 시 둘 다 갱신)만 문서화하면 충분 — 태그 체계 자체를 config.yaml로 대체할 필요는 없음(서로 다른 목적: 배포 태그 vs 런타임 표시 버전).

---

## G2 — README.md Stale 조사 (재검증)

이전 baseline 조사에서 "누락된 디렉터리"로 지목했던 `core/extractors.py`, `core/files.py`,
`core/processing.py`, `core/utils.py`, `ui/tabs.py`, `ui/sidebar.py`, `ui/styles.py`,
`data/제련완성본`, `chroma_db/` — **전부 실존 확인됨(경로 오류 아님)**. 이전 보고를 정정한다.

### 실제 문제 (경로 존재 여부가 아니라 내용 정확성)

1. **`app/` 디렉터리만 실제로 없음** (README.md:24) — 유일한 순수 오류.
2. **아키텍처 서술 불일치**: README가 `ui/tabs.py`/`ui/sidebar.py`를 "탭 UI"/"사이드바 UI"로 소개(24-23행)하지만, 실제 라우팅은 `ui/app.py`가 `ui/pages/*.py`(9개 페이지)로 수행 — `ui/tabs.py`/`ui/sidebar.py`는 `ui/app.py`가 import하지 않음(현재 라우팅 경로에서 죽은 코드로 보임, 별도 확인 필요 — 이번 조사 범위 밖).
3. **내부 모순**: "주요 기능" 섹션(README.md:42-44)은 "ChromaDB 벡터 저장소를 통한 문서 임베딩 및 검색"을 현재 기능처럼 서술하지만, 같은 문서의 "개발 정보" 섹션(README.md:88)은 정반대로 "ChromaDB/Qdrant는 legacy corpus history로만 보존되며 검색 경로에서 쿼리되지 않음(ADR-001/ADR-003)"이라고 정확히 서술함. **같은 문서 안에서 서로 모순**.
4. **누락된 현재 기능**: Dashboard/Monitor 분리, Research/Chat citation 표시(방금 완료), NAE bridge(ADR-024, opt-in), 성경 검색/설교 작성·리뷰 페이지 등 실제 9개 UI 페이지 중 어느 것도 README에 언급 없음. README는 사실상 초기(Sprint 1) 시점 구조를 그대로 유지.
5. **버전**: `1.0.0`(README.md:86) — G1에서 확정할 SSOT와 별개로 갱신 필요.
6. **테스트 파일 목록**: README가 예시로 든 4개 테스트 파일은 전부 실존 확인됨 — 오류 아님. 다만 현재 테스트 스위트 규모(수백 개)에 비해 예시가 초기 4개뿐이라 대표성이 낮음(경미).

---

## G3 — INSTALL.md 조사 (재검증)

- **날짜/버전 태그**: "DBMA Sprint 1 — Installation Guide", "Generated: 2026-07-04" — 명시적으로 구식임을 자인하고 있음.
- **Ollama 설치 안내 전무**(grep 0건) — `requirements.txt`에 `ollama` 패키지 포함, `config.yaml`에 `ollama:` 섹션 존재, `bge-m3:latest` 임베딩 모델이 Ollama 경유로 필수. **로컬 확인 결과 Ollama는 이미 설치되어 있고 필요한 모델(`bge-m3:latest`, `llama3.1:8b` 등) 전부 pull되어 있음** — 즉 현재 개발 환경 기준으로는 "이미 세팅되어 있어서 문서 누락이 안 드러난" 상태. **신규(fresh) 사용자에게는 이 문서만으로 실행 불가**(Ollama 미설치 상태에서 시작하면 어디서도 안내를 못 받음) — G3 중 가장 심각한 blocker로 재확인.
- **Qdrant 서술**: "optional Sprint 2/3 services"(INSTALL.md:236-254)로 서술 — ADR-003/ADR-013 확정 이후 실제로는 (a) DBMA production 검색에 Qdrant가 전혀 관여하지 않고(legacy, frozen), (b) NAE Qdrant(`nae_qdrant`, 포트 7333)는 opt-in 모듈(`nae_pd`, 기본 비활성)에서만 쓰임 — "Sprint 2/3 optional"이라는 서술 자체가 현재 아키텍처와 불일치하는 낡은 프레이밍. **로컬 확인 결과 실제로 `nae_qdrant` 컨테이너가 떠 있음**(포트 7333) — INSTALL.md가 가리키는 `dbma_qdrant`/포트 6333과는 다른 컨테이너.
- **개발자용 vs End-User용 미분리**: GPU/CUDA/ROCm 섹션, conda 대안, 다양한 OS(Windows/Ubuntu) 절차가 전부 한 문서에 섞여 있음 — End-User(주로 macOS 단일 사용자 배포 대상, `install_nae_beta.command`가 이미 macOS 전용 원클릭 설치를 제공)에게는 대부분 불필요한 노이즈.
- **Python 요구사항**: 3.11.x/3.12.x 명시 — 로컬 확인 결과 시스템 `python3`은 3.14.5(요구사항 밖), 별도 venv(`~/envs/dbma311`)가 실제 실행 환경 — **문서가 "python3.11 -m venv .venv"를 전제하지만 실제 프로젝트는 `~/envs/dbma311`라는 저장소 밖 공용 venv를 쓰는 관행**(메모리: DBMA Runtime Env — `.venv_311` 등은 지시 없이 쓰지 말 것). 이 관행이 문서화되어 있지 않음.

---

## DoD #7 — 실사용 경로 검증 (실행 아님, 실행 계획만)

### 로컬 환경 현재 상태(읽기 전용 확인, 변경 없음)
- Ollama 설치됨, 필요 모델(`bge-m3:latest`, `llama3.1:8b` 등) 전부 준비됨.
- `~/envs/dbma311` venv 존재.
- Docker: `nae_qdrant`(7333), `dbma_n8n`, `typesense-bench`, `open-webui` 실행 중. **`dbma_qdrant`(6333) 컨테이너는 목록에 없음** — INSTALL.md가 안내하는 컨테이너가 현재 떠 있지도 않다는 뜻(추가 확인: 애초에 legacy/frozen이라 필요 없음 — 이것도 문서가 사용자를 오도하는 지점).
- 시스템 `python3`은 3.14.5 — INSTALL.md 요구사항(3.11/3.12)과 불일치, 실제로는 별도 venv로 우회 중.

### 제안하는 검증 방식 (승인 필요, 아직 실행 안 함)
"별도 격리 환경"을 완전히 새로 만드는 것(신규 venv + 처음부터 `pip install` + Ollama 모델 재다운로드 ~수 GB)은 시간/디스크 비용이 크고, 이번 세션에서 자동 실행하기엔 과합니다. 두 가지 옵션 중 선택 요청:

- **옵션 A (가벼움, 권장)**: 기존 `~/envs/dbma311` venv를 그대로 쓰되, `requirements.txt` 기준으로 `pip check`/`pip list --outdated`만 실행해 의존성 무결성을 확인하고, `streamlit run dbma_ui.py`를 헤드리스로 띄워 9개 페이지가 에러 없이 로드되는지 + 검색 1회 + citation 표시까지 실제 실행 확인. Production 데이터/corpus는 건드리지 않음(읽기 전용 쿼리만).
- **옵션 B (완전 격리, 무거움)**: 신규 venv를 처음부터 만들어 INSTALL.md 절차를 문자 그대로 따라가며 실패 지점을 실측. "신규 사용자가 실제로 겪을 문제"를 가장 정확히 재현하지만 시간이 오래 걸리고 디스크/네트워크 비용 발생.

---

## 요약 — 승인 요청 사항

1. **G1**: `config.yaml::app.version`을 SSOT로 확정 — 승인해주시면 C1에게 나머지 3곳(fallback/docstring)을 이 값 참조로 정리하는 작업 명령을 발행하겠습니다.
2. **G2**: README의 "내부 모순"(ChromaDB 서술 충돌)과 "누락된 현재 기능"(9개 페이지, citation, Dashboard/Monitor, NAE bridge)을 갱신 — `app/` 디렉터리 서술 삭제. `ui/tabs.py`/`ui/sidebar.py`가 정말 죽은 코드인지는 별도 확인 필요(이번 조사 범위 밖으로 분리 제안).
3. **G3**: Ollama 설치 섹션 추가, Qdrant 서술을 현재 아키텍처(ADR-001/003/013/024)에 맞게 정정, End-User(macOS)/개발자(멀티 OS+GPU) 문서 분리, `~/envs/dbma311` 관행 반영 여부 결정.
4. **DoD #7**: 옵션 A/B 중 선택 필요.

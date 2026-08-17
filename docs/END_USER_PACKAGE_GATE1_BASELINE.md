# End-User Package — Gate 1 Baseline Inventory & Gap Analysis

- 작성: CUE, 2026-08-17
- 성격: 실측 조사 결과 (Gate 0 PASS 이후, 구현 착수 전 baseline)
- 코드 변경: 없음 (조사만 수행)
- Architecture Gate: Gate 0(ADR-024 Promotion) PASS 상태 유지, 본 문서는 그 위반 없음

---

## 1. Baseline Inventory

### 1.1 진입점/실행 경로
- 공식 진입점: `dbma_ui.py`(16줄) → `ui.app.main()` thin wrapper.
- 비개발자용 설치: `scripts/install_nae_beta.command`(163줄, GitHub Release tarball 다운로드) → `scripts/setup_beta_tester.command`(126줄).
- 개발/패키징 전용(배포 실행 경로 아님): `scripts/build_mac_package.sh`, `scripts/check_environment.sh`, `.automation/*`.

### 1.2 UI 구조 (9개 페이지, `ui/pages/*` 라우팅)
Dashboard · Library(948줄) · Processing(652줄) · Research(759줄) · Chat(495줄) · 설교문 작성(413줄) · 설교 리뷰(335줄, 읽기전용) · Monitor(399줄) · 도움말(51줄) + Onboarding(165줄, 최초 실행).

### 1.3 Citation/Provenance
- `core/retrieval.py:1810-1829` `Citation` dataclass(12필드), `CitationBuilder.build_citations()`(1839-1874)에서 생성.
- **Research 페이지**: `ui/pages/research.py:484-497`에서 실제 렌더링(스코어/저자/발췌/성경구절/TSU ID).
- **Chat 페이지**: `ui/pages/chat.py`는 `Citation`을 직접 쓰지 않고 `RankedCandidate`를 그대로 사용 — 출처 표시 경로가 다름.
- `core/generation.py`는 `Citation`을 `ResponsePackage.citations`로 소비.

### 1.4 Dashboard/Monitor
둘 다 실제 로컬 소스 기반, mock 없음. Dashboard=`Path(DEFAULT_RAW_DIR).rglob()` 실파일 스캔 + TSU JSONL. Monitor=`psutil`(CPU/메모리/디스크), `logs/*.log`, `_BENCHMARK_RESULT_PATH`, `EmbeddingCache`.

### 1.5 문서/버전/패키징
- `pyproject.toml`: `[tool.basedpyright]`만 존재, `[project]` 메타데이터(name/version/dependencies) 없음.
- `config.yaml`: 12개 섹션(app/language_settings/parsing_config/directories/chunking/vector_db/embedding/ollama/progress_defaults/rag/ui/modules).
- `.streamlit/config.toml`, `.env.example` 없음.
- `requirements.txt`: 대부분 버전 미고정(`streamlit==1.58.0`만 고정).
- Python 요구사항은 `INSTALL.md`에만 명시("3.11.x/3.12.x"), pyproject/requirements엔 없음.

### 1.6 배포 제외 후보 크기
`.automation/`(81M) · `NAE/`(750M, 개발 파이프라인) · `archive/legacy/`(84K) · `.git/`(2.2G, 정상) · `test_seal_*` 루트 13개(~140K, 현재 git status에서 D로 정리 중).

### 1.7 브랜드
"내서재 · NAE"(사용자 노출) / "DBMA"(내부 식별자) 이원화는 `docs/governance/DBMA-BRAND-GOV-001.md` 근거로 **의도된 정책**, gap 아님.

---

## 2. Gap Analysis

| # | Gap | 근거 | 성격 |
|---|---|---|---|
| G1 | **버전 번호 4곳 불일치**: `config.yaml`(1.3.0) / `core/config.py` fallback(0.6.4) / `dbma_ui.py` 주석(v1.1.0) / `install_nae_beta.command`(beta-v1.3.0-rc1) | 파일 4곳 실측 | 문서/패키징 위생, ADR 불필요 |
| G2 | **README.md stale**: 존재하지 않는 `app/`, `logs/project_events.jsonl` 언급, 사용 안 하는 `ui/tabs.py`/`ui/sidebar.py`를 구조도에 표기 | README.md:5-32 vs 실제 트리 | 문서 위생 |
| G3 | **INSTALL.md stale**: "Sprint 1"(2026-07-04) 시점, Ollama 설치 안내 전무(정작 `requirements.txt`/`config.yaml`엔 필수), Qdrant는 "optional Sprint 2/3"으로만 언급 | INSTALL.md:9-22, 164-167, 236-254 | 설치 실패 가능 — 실사용자 blocker |
| G4 | **Chat 페이지 Citation 경로 상이**: Research는 `Citation` dataclass 렌더링, Chat은 `RankedCandidate` 직접 사용 — 의도된 설계 차이인지 미구현 gap인지 불명 | ui/pages/chat.py vs research.py:484-497 | **확인 필요 — 구현 전 판단 요함** |
| G5 | **pyproject.toml 패키징 메타데이터 부재** | pyproject.toml 전체 4줄 | 배포 방식 결정(pip 패키지 vs venv+requirements 유지) 필요 |
| G6 | **저장소 정리 상태**: untracked 8032개, pending deletion 174개(`test_seal_*` 포함), `docker-compose.yml.backup-*` 잔존 | git status --porcelain | 릴리스 전 정리 필요, 코드 변경 아님 |
| G7 | `.env.example`/`.streamlit/config.toml` 부재 | find 결과 없음 | 설치 안내 보완용, 선택사항 |

**ADR 필요 여부**: 없음. G1~G7 전부 documentation/packaging hygiene이며 architecture/authority 변경이 아님. 단 G4는 "의도적 설계"로 판명되면 문서화만, "미구현 gap"으로 판명되면 별도 구현 작업 명령(ADR 불필요, RetrievalEngine 경계 안쪽 수정) 대상.

---

## 3. Definition of Done (초안)

1. 버전 번호 단일 출처(SSOT)로 통일 — 4곳 → `config.yaml` 기준 1곳 참조 방식.
2. README.md 구조도/버전/설치 링크를 현재 저장소 상태와 일치시킴.
3. INSTALL.md에 Ollama 설치·모델 pull 절차 추가, Qdrant 위치를 실제 상태(NAE 전용, DBMA production 미사용)에 맞게 정정.
4. G4(Chat citation 경로) 판단 완료 — 의도/gap 여부 확정 후 필요시 최소 수정.
5. `install_nae_beta.command`/`build_mac_package.sh`가 `.automation/`, `NAE/`, `test_seal_*`, `.git`을 배포 tarball에서 실제로 제외하는지 스크립트 내용으로 확인.
6. pyproject.toml 패키징 방식 결정 및 반영(범위는 결정 내용에 따라 달라짐).
7. 신규 사용자 환경(clean venv)에서 `dbma_ui.py` 실행 → 9개 페이지 로드 → 검색 1회 → citation 표시까지 실제 실행 검증(smoke import만으로 완료 판정 금지, Gate 1 지시사항 §7 준수).

## 4. 우선순위 제안

- **P0 (릴리스 blocker)**: G3(Ollama 설치 누락), G4(Chat citation 확인), DoD #7(실사용 경로 검증)
- **P1**: G1(버전 통일), G2(README stale), DoD #5(배포 제외 스크립트 검증)
- **P2 (별도 트랙, 코드 아님)**: G6(저장소 정리) — End-User Package 범위 밖, 별도 정리 작업으로 분리 권장
- **P3 (선택)**: G5(pyproject 패키징 방식), G7(.env.example)

---

## 5. Architecture Freeze Rule 준수 확인

본 조사는 코드 변경 없음. ADR-001/003/013/024 authority boundary 무영향. 신규 ADR 필요 항목 없음(G4는 판단 후 필요시 일반 구현 작업, ADR 대상 아님).

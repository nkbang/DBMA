# DBMA TODO

## 즉시 확인 (2026-08-18~19, CUE 정리)

### 완료된 정리 (2026-08-18~19 세션)

세션 시작 시 `git status`에 8,500여 개 파일이 어지럽게 staged/untracked 상태였다.
정리 경과:
- 프로젝트와 무관한 로컬 툴 설정(`.agents/`, `.claude/`, `.continue/`, `.cursor/`,
  `.roo/`, `.idea/`) `.gitignore` 등록 + unstage
- C1 Task Order 039 종료 (CUE 최종 판단, `docs/agents/c1/C1-TASK-ORDER-039-REPORT.md` §2/§3)
- citation card 실 배선(`ui/pages/chat.py`/`ui/components/citation_card.py`) +
  브랜드 문구 정리 커밋
- NAE TSU worker Phase 3 wiring 커밋 (50/50 PASS)
- 로컬 잡동사니(vsix/docker-compose 백업/log/qdrant_db 캐시/worker 런타임 상태) 삭제 +
  gitignore 보강
- `core/review_disposition_v2.py` + 776 Human Review Disposition v2 스키마/문서 커밋
  (110/110 PASS)
- **ADR 번호 충돌 3건 정리**: ADR-022/023 빈 번호 채움(이미 승인된 문서였는데
  미커밋 상태였음), ADR-021 Pilot Spec → ADR-027로 재번호(내용 무변경),
  ADR-016 Retrieval Authority 초안은 미승인·중복(ADR-001과 동일 취지)이라 커밋
  안 하고 파일명만 정리해 로컬 보존
- `tests/test_source_navigation.py` stale 테스트 2건 수정 (document_id를 "존재
  자체 금지"에서 "browser 노출 패턴 금지"로 좁힘 — Search Detail Panel 기능과의
  자기모순 해소), 37/37 PASS

남은 후속 과제 (별도 Task Order로 발행 전 상태):
- [x] **P0** — `output/bench/tsu_dataset.jsonl` 복원 **완료** (2026-08-19,
      사용자 승인 후 CUE 실행 — TSU Pipeline 보호 영역이라 무인 자동
      진행 않고 승인받음). `output/bench/backup/tsu_dataset_pre_fixA_
      20260727T014820.jsonl`(2026-07-24 스냅샷, 53,231건/78개 문서)을
      복사하고 `core/tsu_builder.py::write_manifest()`(기존 함수 그대로
      호출, pipeline 코드 무변경)로 매니페스트를 현재 registry/git
      commit/config 기준으로 재생성. `QueryProcessor().process("로마서
      8장")` 실측으로 3건 응답 확인(복원 전 0건).
      **잔여 갭 — 해소됨**: `scripts/build_tsu_dataset.py` 재빌드 완료
      (2026-08-19, 사용자 승인 후 실행, 총 약 22분 — dry-run으로 먼저
      안전 확인 후 기존 파일 백업하고 실제 재빌드). 53,231건/78문서
      → 53,963건/82문서(전체 커버). 재검증: "로마서 8장" 검색에
      이전 누락 문서가 최상위로 잡힘, `pytest tests/` 2482 passed.
- [ ] **P1** — BM25 `_tokenize()` 한국어 미지원 (한글 토크나이저 부재, `core/retrieval.py`).
- [ ] **P2** — Chat "단일 파일" 모드 `file_scope` 제한 재검토 (TSU 복원 후 재검증 필요).

### DEFERRED — Night-Shift / `.automation/` (2026-08-19, 사용자 확정)

아래 두 항목은 **지금 착수하지 않는다**. 현재 진행 중인 TASK-039 closure /
n8n Loop Operating Model activation / 첫 loop State Discovery / NAE·Figma UI
자산 보존 작업과 절대 섞지 않고, 별도 window에서 처리한다.

**⑦ Night-shift / Control-plane Scripts** — 상태: **DEFERRED**
- 현재 TASK-039와 분리, 현재 n8n Loop Activation과 분리
- 개별 script를 임의로 수정하지 말 것
- production process에 영향을 주는 정리 작업을 수행하지 말 것
- 향후 `.automation/` audit과 하나의 통합 작업으로 처리한다.

**`.automation/` Review** — 상태: **NOT STARTED / DEFERRED / KNOWN BACKLOG — NOT YET AUDITED**
- 약 8,000개 artifact 존재. 숫자만으로 정리·삭제 필요성을 추론하지 않는다.
- 단순 파일 정리나 개별 script 검토로 시작하지 않는다 — control plane의 실제
  상태·중복·obsolete artifact·실행 경로·state/evidence 구조를 조사하는 별도
  audit으로 취급한다.
- 착수 시 먼저 수행할 순서: ① 전체 inventory → ② artifact 유형 분류 →
  ③ 실제 execution path 확인 → ④ active/obsolete/duplicate 구분 →
  ⑤ state/evidence/control-plane 관계 확인 → ⑥ n8n과의 관계 확인 →
  ⑦ production process와의 관계 확인 → ⑧ ADR/governance와의 충돌 여부 확인 →
  ⑨ 삭제·이동 후보 별도 목록화 → ⑩ CUE audit 후에만 mutation 여부 결정.
- **No cleanup before inventory. No mutation before provenance. No deletion
  before CUE approval.** audit이 시작될 때까지 이 영역을 임의로 변경하지 않는다.

### 현재 우선순위 (2026-08-19 확정)
1. ~~현재 진행 중인 TASK-039 closure~~ — **완료** (2026-08-19, PASS 조건부 종료 재확인)
2. ~~n8n Loop Operating Model activation 준비~~ — **완료**, ACTIVATED/READY 상태로
   대기 중(신규 raw source 없어 Iteration #1 미정의, `docs/STATE.md` 참고)
3. **오늘 밤 Primary Night Shift — UI 작업** (2026-08-19 확정): 기존
   Figma/Stitch 자산(`landing.html` 등) 재생성·덮어쓰기 금지, UX-007
   Gate 6 구현 트랙(§15 순서: §2 홈 → §3 내 자료 → §5 읽기 → §4 검색·연구
   → §7 설교 연구)을 이어서 진행.
   - ~~C1 Task Order 040 (파이프라인 상세 Home→Library 이관)~~ —
     **완료 (PASS)**, 1차 제출 FAIL(st.page_link 크래시) → 교정 후
     CUE 재검증 통과. 상세: `docs/agents/c1/C1-TASK-ORDER-040-REPORT.md`
   - ~~C1 Task Order 041 (§1 Global Navigation 부분 적용)~~ —
     **완료 (PASS)**, 2026-08-19 야간 무인 작업(사용자 부재, CUE가
     build+audit 겸행). 상세: `docs/agents/c1/C1-TASK-ORDER-041-REPORT.md`
   - 다음 후보였던 §2("빠른 시작 버튼 재배치")는 실제로는 Home 전체
     재구성(이어서 읽기 카드/최근 연구 그리드/§13 신규 세션 상태 의존)
     — 무인 작업 저위험 범위를 벗어나 보류.
   - ~~§13 세션 상태 설계~~ — **완료** (2026-08-19, 사용자 지시로 진행).
     `docs/DBMA-UX-007-SessionState-Design.md`. Tier A(기존 인프라
     재사용)/B(신규 session_state 키, 저위험)/C(신규 영속 모듈, C1
     Review 권장)로 구분.
   - ~~Tier A(Home 최근 검색 카드) + Tier B(설교 연구 허브)~~ —
     **완료 (PASS)**, 2026-08-19 야간 무인 작업 계속(CUE build+audit
     겸행). 상세: `docs/agents/c1/C1-TASK-ORDER-042-REPORT.md`
   - ~~§7 어댑터(자료·메모·개요 자동 전달)~~ — **완료 (PASS)**,
     2026-08-19 야간 무인 작업 계속. `scripture_and_theme` 프리필 +
     `style_files` 매칭(코퍼스 미로드 시 시도 안 함) + 진행 중인 초안
     보호. 상세: `docs/agents/c1/C1-TASK-ORDER-043-REPORT.md`
   - ~~Tier C(이어서 읽기 영속화)~~ — **완료 (PASS)**, 2026-08-19 야간
     무인 작업 계속(사용자가 C1 Review 없이 진행 지시). 신규
     `core/reading_session.py` + 기존 detail_panel 흐름에 결합(§5 전체
     신규 화면은 미착수). 상세: `docs/agents/c1/C1-TASK-ORDER-044-REPORT.md`
   - UX-007 §13 관련 Tier A/B/C + §7 어댑터 **전부 완료**.
   - §5 읽기 전체 구현: 사용자 지시로 **보류**.
   - ~~C1 Task Order 045(§11 용어집 전역 적용)~~ — **완료 (PASS)**.
     1차 제출 FAIL(조건부, 2곳 N/A 하드코딩) → Correction Order 045 →
     재제출 CUE 재검증 PASS(2026-08-19). 상세:
     `docs/agents/c1/C1-TASK-ORDER-045-REPORT.md`
   - ~~"RAW 폴더" 번역 통일("자료실"/"보관함" 혼용)~~ — **완료**,
     2026-08-19. "보관함"으로 통일(다수 사용 + Processing 페이지
     핵심 동작 라벨과 일치). `library.py`/`sermon_review.py`의
     "자료실" 2곳 → "보관함"으로 변경, CUE가 직접 처리(간단한 문자열
     치환, C1 이관 불필요). `pytest -k "library or sermon_review"`
     7 passed.
   - ~~C1 Task Order 046(§6 인용 카드 공용 컴포넌트 — research.py
     마이그레이션)~~ — **완료 (PASS)**, 2026-08-19. CUE 독립 검증
     완료(실제 결과 데이터로 AppTest 직접 실행, 원시 소수점 미노출/
     좌측 색상바/보호 버튼 무손상 확인). 상세:
     `docs/agents/c1/C1-TASK-ORDER-046-REPORT.md`
   - ~~C1 Task Order 047(§4 검색·연구 통합)~~ — **완료 (PASS)**,
     2026-08-19. 1차 제출 FAIL(AI 답변 항상 빈 문자열 — `GenerationStream`
     미순회, grep으로 못 잡는 런타임 버그) → Correction Order 047 →
     재제출 CUE 재검증 PASS(실제 함수 호출로 147/408자 답변 확인,
     전체 `pytest tests/` 2482 passed). `research.py` 단일 진입점,
     모든 입력에 검색+AI 답변 항상 병렬 실행, 사이드바 "Chat" 제거.
     상세: `docs/agents/c1/C1-TASK-ORDER-047-REPORT.md`
   - UX-007 §2/§3/§6/§7/§11/§13 + §4 **전부 완료**.
   - ~~C1 Task Order 048(§5 읽기 — 연구 워크스페이스)~~ — **완료
     (PASS)**, 2026-08-19. 1차 제출 FAIL(크래시 2건: "인용하기" 버튼
     자기 key 덮어쓰기, 관련 자료 카드 key 중복) → Correction Order
     048 → 재제출 CUE 재검증 PASS(격리된 세션으로 5개 버튼 전부 개별
     재현, 전체 `pytest tests/` 2482 passed). 상세:
     `docs/agents/c1/C1-TASK-ORDER-048-REPORT.md`
   - UX-007 §2/§3/§4/§5/§6/§7/§11/§13 **전부 완료**.
   - **C1 Task Order 049(§9 Empty/Loading/Error States 전역 원칙)
     발급, C1에게 이관** (2026-08-19) — 원시 예외 노출 제거(9곳 예시,
     `research.py`의 `f"에러: {str(e)}"`는 스펙 §4.4가 직접 지목했던
     미수정 위반), "처리되지 않은 문서" 메시지에 관리자 모드 조건부
     버튼 추가, 빈 화면 Dead End 감사. 릴레이:
     `.automation/requests/C1-RELAY-SNIPPET.md` 릴레이 34.
4. n8n Loop는 valid input 없으므로 대기 유지(Re-entry 조건: `docs/STATE.md` 참고)
5. 이후 별도 window에서: `.automation/` audit / Night-shift·control-plane script audit
   — 이번 UI night shift 범위 아님

## 현재 목표
[2026-07-22 갱신] 이 문서는 SPRINT20-RC 시점에서 오래 갱신이 밀려 있었다
— 아래 "진행 상태"/"체크포인트"는 SPRINT20 스코프의 **역사적 기록**으로
남기고, 실제 현재 우선순위는 하단 "SPRINT28~33-D 이후 현재 우선순위"를
따른다(`docs/STATE.md`의 "SPRINT28~33-D 진행 내역"과 함께 볼 것).

원래 목표(SPRINT17~19에서 완성한 Retrieval/Evidence/Citation Layer 위에서
SPRINT20 governance 결함을 마무리하고 RC 선언 여부 결정)는 RC 선언 자체는
보류된 채 SPRINT20-I(Architecture Consolidation)로 흡수되어 v1.3.0 태그로
마무리됐고, 이후 SPRINT28~33-D(청킹 품질 고도화)로 이어졌다.

---

## SPRINT28~33-D 이후 현재 우선순위 (2026-07-22, 갱신)

~~1. 근본 수정 (a)~~ — **완료 확인** (commit `d45caed`, 2026-07-21).
`split_sentences_mixed()`에 문장부호 기준 분할(`_split_line_on_sentence_end()`)
추가. 이 항목이 "미착수"로 기재됐던 건 오류였다 — Preflight 문서(작성 후
갱신 지연) 서술을 그대로 옮기고 git 로그를 재대조하지 않은 것이 원인,
2026-07-22 CUE가 직접 실측 재검증 후 정정(`docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`
참고). 잔여 over-cap 0.2%(40건)는 별개의 Axis 3 unsplittable outlier
문제로 아래 항목1(Hierarchical Chunk Builder)에서 계속 추적.

~~5. Legacy artifact 정리~~ / ~~6. Logos 소스 인제스트 실사용~~ —
**완료** (C1-TASK-ORDER-007, commit `bccd3f4`). Legacy artifact 98개
파일 `backups/legacy_artifact_cleanup_20260722/`로 이동(삭제 아님),
`classify_documents_from_frontmatter.py`의 stale 경로 하드코딩 버그도
함께 수정. Logos manifest 템플릿(`docs/logos_manifest.example.json`)
준비 완료 — 실제 Logos 자료 인제스트 자체는 여전히 사용자 액션 대기.

**남은 우선순위 (번호 재부여)**:

1. **Hierarchical Chunk Builder 프로덕션 전환 여부** — ADR-008 제안
   2(Level 3 Hard Fallback)까지 2026-07-22 완료(commit `08d542a`) — 이제
   제안 2/3/4 전부 완료, Profile B 4개 문서(6176청크) 실측으로 청크 길이
   상한 100% 보장 확인(over_cap 0건). `core/chunking_optimizer.py`(프로덕션)는
   여전히 무접촉. **데이터는 다 갖춰졌으나 실제 전환은 사용자가 "데이터만
   정리해두고 나중에 결정" — 2026-07-22 기준 보류, 착수하지 않음.**
   재개 시 참고: `docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md`
   Next Steps §5.
2. ~~ADR-009 SIL Theology Engine~~ — **완료** (2026-07-22, commit
   `0324dca`). 사용자가 신학 전통(개혁파 침례교)과 어휘를 직접 확정,
   `core/sermon/doctrine_filter.py` 구현·`ui/pages/sermon_draft.py`
   연결까지 완료. (이 항목도 한때 "미착수"로 오래 남아있었을 뻔한
   것을 처리 직후 바로 갱신 — 문서 지연 갱신 재발 방지.)
3. **ADR-010 RAG Evaluation** — Phase 1 착수 전 미확정 항목 2건 결정 필요
   (`core/evaluation/` 인프라는 존재, 정식 실행 미착수).
4. **ADR-011 Header/Footer Repetition Detector** (신규, 2026-07-22) —
   한글 PDF 주석서(Profile B)의 반복 러닝헤더가 디노이즈(`noise_
   classifier.py`)와 청킹 고수준 결과(`semantic_boundary_detector.py`)
   양쪽에서 독립적으로 발견된 동일 갭임을 확인, 단일
   `RepetitionTracker` 모듈로 통합 해결하는 설계 제안 — 구현 전,
   HQ 승인 대기. 참고: `docs/architecture/ADR-011-Header-Footer-Repetition-Detector.md`.

---

## 진행 상태

- [x] 프로젝트 구조 확인
- [x] 핵심 파일 목록 정리
- [x] CLAUDE.md 운영 규칙 정리
- [x] Retrieval Engine 단일화 (ADR-001 — `core/retrieval.py::RetrievalEngine`/`QueryProcessor`)
- [x] Citation Layer 구조화 (`Citation` dataclass, `GenerationResult` pass-through)
- [x] TSU Metadata Propagation (`source_file`/`language`/`source_type`, 100% coverage)
- [x] Configuration Authority (PyYAML 누락 시 hard-fail, `requirements.txt`/`environment.yml` 정합)
- [x] Execution Environment Authority (Python 3.11.x 공식 확정, `scripts/check_environment.py`)
- [x] TSU Snapshot Provenance (`build_commit`/`registry_sha256`/`dataset_sha256`/`config_sha256`)
- [x] Entry Point Documentation Alignment (`README.md`, `.github/instructions/*` → `dbma_ui.py`)
- [x] Logging Authority Restoration (`core/config.py`의 root logger 강제 설정 제거)
- [x] Documentation Synchronization 완료 (본 문서/STATE.md 갱신, 2026-07-22 —
      단 CHANGELOG.md는 별도 미확인)
- [x] `dbma.py` Legacy Migration 결정 (CUE-20H)
- [ ] Legacy Artifact 정리 (`output/registry/`, `output/baseline/`, `output_sav/` 등) — 미결정 이월
- [ ] SPRINT20-RC Final Audit / RC 선언 — SPRINT20-I로 흡수되어 v1.3.0 태그로 사실상
      해소, RC "선언" 자체는 명시적으로 이루어지지 않음(STATE.md "GA 검토 단계" 참고)

진행률(SPRINT20 스코프): 85% → 사실상 v1.3.0 태그로 종료, 이후 SPRINT28~33-D는
별도 트랙(위 "SPRINT28~33-D 이후 현재 우선순위" 참고).

---

## 체크포인트

### 1단계: 구조 고정
- [x] 핵심 디렉터리 식별
- [x] 주요 파일 역할 정리
- [ ] 복사본/legacy 파일 정리 기준 수립 (CUE-20H 대상)

### 2단계: Retrieval / Evidence / Citation (SPRINT17~19, SPRINT20-A~C)
- [x] Retrieval Engine Authority 확정 (ADR-001)
- [x] Scripture Evidence Resolver v1 (`provenance.confidence`)
- [x] Citation 구조화 객체 도입 및 Generation pass-through
- [x] Citation Quality baseline 측정 (1,500 gold query 기준)

### 3단계: Governance / Reproducibility (SPRINT20-D~G)
- [x] Registry Authority 정리 (`core/identity_registry.py` docstring)
- [x] Metadata Propagation (registry → TSU → Citation)
- [x] Configuration Hardening (PyYAML hard-fail)
- [x] Execution Environment Lock (Python 3.11)
- [x] Dataset Provenance Manifest v2
- [x] Entry Point Authority 문서 정렬
- [x] Logging Authority 복원
- [ ] Documentation Synchronization 마무리

### 4단계: Legacy 정리 (CUE-20H, 별도 승인 필요)
- [x] `dbma.py` 함수군(`query_rag`, `build_rag_store`, `embed_text_ollama`,
      `query_qdrant`, `upsert_to_qdrant`) archive 완료
- [ ] 2026-07-15 커밋(Chroma metadata schema)의 활성 여부 사람 확인
- [ ] Legacy artifact(`output/registry/` 등) 정리 여부 결정

### 5단계: RC 선언
- [ ] SPRINT20-RC Final Audit
- [ ] Green/Yellow/Red 재평가 후 RC 선언 여부 결정

---

## 현재 우선순위 (SPRINT20 스코프, 역사적 기록)
1. 문서 동기화 마무리 (완료, 2026-07-22)
2. `dbma.py` Legacy Migration 결정 (CUE-20H Preflight) (완료됨)
3. Legacy artifact 정리 여부 결정 (미결정 이월 — 위 "SPRINT28~33-D 이후 현재 우선순위" §5)
4. SPRINT20-RC Final Audit 진행 (SPRINT20-I로 흡수, v1.3.0 태그로 사실상 종료)

**실제 현재 우선순위는 상단 "SPRINT28~33-D 이후 현재 우선순위" 참고.**

---

## 작업 기록 형식

### 작업 제목
- 날짜:
- 대상 파일:
- 대상 함수:
- 변경 내용:
- 검증 결과:
- 다음 조치:

---

## 메모
- 큰 수정은 한 번에 하지 않는다.
- 모든 변경은 검증 후 기록한다.
- 진행률은 수시로 업데이트한다.
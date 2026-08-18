# DBMA State

## 버전 상태
**DBMA v1.3.0 — Architecture Consolidation Release** (Research Grade /
Production Candidate). 버전·Authority 정의는
`docs/architecture/DBMA-Version-Authority-v1.md`가 단일 기준이다.

```
Release State:  v1.3.0 released, post-release 개발 재개(ACTIVE)
Development:    SPRINT33-D 계열 진행 중 — 결함 수정/ADR-008 착수 여부 결정 대기
Next:           chunk overflow 하위결함 B 수정 방향 결정, ADR-008 후속 항목 착수 여부
```

## 현재 상태
DBMA는 신학 문서 전용 TSU 기반 Theological Retrieval System이다.
SPRINT17~19에서 Retrieval/Evidence/Citation 계층이 구조적으로 완성되었고,
SPRINT20에서 그 위에 Metadata Lineage, Configuration/Environment/Logging
Authority, Application Entry Point 정합성을 확보했다.
SPRINT20-I(Architecture Consolidation)에서 Processing/Identity/Index/TSU
Builder/Retrieval/Embedding Authority를 확정하고 TSU Builder를 core로
이동했으며, Legacy(`dbma.py` + Chroma/Qdrant island + md_manager)를
`archive/legacy/`로 분리 완료했다. v1.3.0으로 태그·검증되었다.

v1.3.0 이후 SPRINT27(Research Workspace — 6번째 Authority/Memory Layer),
SPRINT31~32(PdfHeadingProvider 정식 배선, HeadingAssembler 안정화),
SPRINT33-A~D(Dormant Semantic Boundary Detector → Shadow scoring →
Hierarchical Chunk Builder 프로토타입 → D-5 Metrics 공식 평가)로 개발이
이어졌다. SPRINT33-D Phase 3-A에서 Beta corpus 12개 문서에 대한 D-5 metric
(ADR-007 Amendment A의 recovery/semantic flush/unsplittable outlier 3축)을
공식 산출하는 과정에서 `core/text_normalizer.py::split_sentences_mixed()`의
개행(`\n`) 의존성으로 인한 **chunk overflow 결함**을 발견했다 — 특히 순수
단일 언어 장문단에서 `chunk_size`/`chunk_overlap` 설정이 사실상 무시되고
청크 상한 자체가 깨지는 심각한 하위결함(B)이 포함되어 있다. 원인 규명과
재현은 완료(Preflight 문서, 코드 미수정)했고, 수정 여부·방향은 HQ 승인
대기 중이다. 같은 흐름에서 Dashboard/Monitor 탭 책임 분리, Monitor 가짜
지표의 실측화, `.gitignore` 오버매칭 버그 수정도 함께 진행됐다.

---

## 아키텍처 결정 (ADR)

- `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` (accepted):
  `core/retrieval.py::RetrievalEngine`/`QueryProcessor`가 유일한 Retrieval
  Engine Authority. `dbma.py`의 인라인 RAG(`query_rag` 등)는 폐기 대상.
- 공식 실행 진입점: `dbma_ui.py` → `ui/app.py` (SPRINT20-G2에서 README/
  `.github/instructions/*` 문서 정렬 완료).
- `docs/architecture/ADR-004-Research-Workspace-Layer.md` (accepted):
  `core/research_workspace.py`를 5개 기존 Authority와 나란한 독립 6번째
  Layer(Memory)로 신설.
- `docs/architecture/ADR-007-*.md` + Amendment A (accepted): D-5 semantic
  boundary rebuild gate — Hierarchical Chunk Builder 정식 채택 여부를
  판단할 3축 metric(Axis1 recovery / Axis2 semantic flush ratio / Axis3
  unsplittable outlier ratio) 정의.
- `docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md`
  (제안만, 미확정): threshold 재산정, Level 3 Hard Fallback 구현, 임베딩
  기반 6번째 feature, `split_sentences_mixed` 버그 후속 티켓 분리를 제안.
  코드 변경 없음 — 착수 여부 HQ 결정 대기.

---

## 프로젝트 진행률

전체 진행률: v1.3.0 Architecture Consolidation은 100% 완료. 이후
SPRINT27/31~33 계열도 각 Phase 목표(D-5 metric 공식 평가까지)는 100%
완료됐으나, 그 과정에서 드러난 chunk overflow 결함 수정과 ADR-008 후속
항목은 착수 여부 결정 대기 상태로 **미완**이다.

### 세부 진행 (SPRINT20-I, v1.3.0 — 완료)
- Retrieval Engine 단일화 (ADR-001): 100%
- Citation Layer / Metadata Propagation: 100%
- Configuration / Execution Env / Logging Authority: 100%
- Index/TSU Builder Authority (core/index_orchestrator.py, core/tsu_builder.py): 100%
- Registry Path Authority (DEFAULT_REGISTRY_PATH): 100%
- Legacy Archive (dbma.py + search/ingest/qdrant_init + md_manager → archive/legacy): 100%
- Retrieval Document Diversity (RETRIEVAL_DOCUMENT_CAP): 100%
- Legacy Vector Store 정책 (ADR-003 Finalization): 100%
- Release: v1.3.0 태그 + chapter-level benchmark PASS + beta validation: 100%

### 세부 진행 (SPRINT27, SPRINT31~33 — Phase 목표 완료, 후속 결정 대기)
- Research Workspace Layer (ADR-004, 6번째 Authority): 100%
- PdfHeadingProvider 배선 / HeadingAssembler 안정화 (SPRINT31~32): 100%
- Dormant Semantic Boundary Detector + Shadow scoring feature군 (SPRINT33-A~C): 100%
- ADR-007/Amendment A D-5 게이트 정의 + Hierarchical Chunk Builder 프로토타입 (SPRINT33-D Phase1~2): 100%
- D-5 Metrics 공식 평가 (SPRINT33-D Phase3-A, Beta corpus 12건): 100%
- chunk overflow 결함 원인 규명 (Preflight, 코드 미수정): 100%
- chunk overflow 하위결함 B 수정 / ADR-008 후속 항목 착수: 0% (결정 대기)

---

## v1.3.0 릴리스 상태

```
Version:   v1.3.0 (tag 07ec084) + post-release stabilization
HEAD:      7a51a31 (origin/dev/dbma-engine 동기화)
Tests:     237 passed
Runtime:   APP_VERSION 1.3.0 / embed bge-m3:latest / gen my-theology-bot:latest / cap 2
Status:    STABLE — GA 검토 단계
```

완료된 post-release 안정화:
- UI 수정: st.rerun 콜백, 임베딩 % 표시, 마지막 처리, 버전/임베딩 라벨 authority화
- Ollama HTTP 500: char/token 4→2 (다국어 oversized 차단)
- Orphan cleanup: data/rag_index, 빈 backup 폴더, md_manager archive
- Benchmark evidence: output/bench/chapter_level_result_v1.3.0_cap2.json

## 잔여 (비blocker, 향후)
- GA 선언 여부 판단 (안정화 기간 후)
- chunk overflow 하위결함 B 수정 방향 결정 및 구현 (HQ 승인 대기, 별도 ADR 필요)
- Beta corpus 대상 하위결함 B 발생 빈도 실측 (미실측)
- ADR-008 후속 항목(threshold 재산정 / Level 3 Hard Fallback 구현 / 임베딩 기반 6번째 feature) 착수 여부 결정
- SPRINT27-D — Research Workspace를 MIE(Ministry Intelligence Engine) Memory Layer로 확장하는 Architecture Preflight (조사만, 구현 없음)

---

## 현재 작업 원칙

- 한 번에 하나씩 고친다.
- 변경 후 바로 검증한다.
- 로그를 남긴다.
- 문서화는 md 파일로 한다.
- 추측보다 실행 결과를 본다.

---

## 상태 기록 규칙

상태는 아래 형식으로 남긴다.

```md
- 날짜:
- 작업명:
- 대상 파일:
- 상태:
- 결과:
- 다음 조치:
```

---

## 최근 상태

### .gitignore 오버매칭 수정 + C1 거버넌스 문서 커밋 (2026-07-20)
- 상태: 완료
- 설명: `.gitignore` 패턴 불일치로 `backups/`(381M), `cache/`(1.7G,
  embeddings_backup_* 포함), `backup_chroma.log`가 새고 있었음(`backup/`
  단수만 지정돼 `backups/` 복수 미매칭 등). `reports/`(무슬래시)가 루트
  뿐 아니라 `docs/agent_governance/reports/`, `docs/reports/`까지 잡아먹어
  `OPS-001`/`OPS-002`/`ARCHITECTURE_AUDIT_2026-07-16.md`가 한 번도
  커밋되지 못한 상태였음을 발견 — `/reports/`로 스코프 축소해 정정.
  `.claude/worktrees/` 패턴도 추가(leftover worktree 재발 방지).
  `docs/agents/c1/*.md`(8개), `docs/agent_governance/*.md`를 함께 커밋.
- 커밋: `14ed5ed`.
- 다음 조치: 없음.

### DBMA_CURRENT_STATE_SNAPSHOT.md Legacy 경로 보강 (2026-07-20)
- 상태: 완료
- 설명: Legacy: dbma.py 항목의 분류는 정확했으나 실제 이동 경로
  (`archive/legacy/dbma.py`, commit `ce6b05a`)가 누락되어 있었음. C1(Cline
  창#1)에게 OLD/NEW find/replace 스키마로 위임하고 CUE 검증(형식/OLD 값
  일치/범위 준수) 통과 후 적용 — shadow 실사용 사례 #1로 기록
  (`docs/agents/c1/C1-TASK-ORDER-001.md`).
- 커밋: `10e72c9`.
- 다음 조치: 없음.

### `split_sentences_mixed()` 개행 의존성 chunk overflow 확정 (2026-07-20)
- 상태: 완료(Preflight 고정, 코드 미수정)
- 설명: SPRINT33-D Phase 3-A가 관찰만 하고 넘어간 "원어/혼합 언어
  문단에서 문장 분할이 거의 안 될 가능성"을 코드 추적 + 실제 재현으로
  확정. `collapse_soft_linebreaks()`가 문단 내부 줄바꿈을 전부 병합하고
  `split_sentences_mixed()`는 오직 `\n` 기준으로만 분할하므로, 어떤 문단이든
  `split_paragraphs()`를 거치면 내부에 `\n`이 남지 않아 항상 1개 원소로
  반환됨을 확인. 이는 두 하위결함으로 갈린다:
  - 하위결함 A(경미): mixed/원어 문단 — `_slice_preserving_words()`로
    떨어져 chunk_size 상한은 지켜지나 문장 경계 무시.
  - 하위결함 B(심각): 순수 단일 언어 장문단 — `_merge_sentence_fragments()`가
    "이미 초과한 문장 1개"를 자르지 않고 그대로 추가, **chunk_size/overlap
    설정이 사실상 무시됨**(실측: 한국어 2999자, 영어 2429자 청크 1개
    그대로 생성, target 1200의 2~2.5배).
  `chunking_optimizer.py:305`가 `split_sentences_mixed`를 무조건 우선
  호출해 정규식 기반 `split_sentences()`(동일 입력에서 정상 동작 확인됨)는
  production에서 도달 불가능한 dead fallback임도 확인.
- 커밋: `ae78866`.
- 다음 조치(HQ 승인 대기, 이 문서 범위 밖): Beta corpus 12개 문서 대상
  하위결함 B 발생 빈도 실측, 수정 방향 후보(무개행 자동 위임 폴백 /
  word-safe hard slice) 검토용 ADR.

### Dashboard/Monitor 탭 분리 + Monitor 가짜 지표 실측화 + ADR-008 제안 (2026-07-20)
- 상태: 완료
- 설명: Dashboard가 콘텐츠 소유자 요약(문서 수/코퍼스 크기/마지막 처리)과
  개발자·운영 내부 지표(단계별 파이프라인 %, 벡터DB/임베딩/파일시스템/
  메모리 상태)를 뒤섞고 있었고, Monitor는 이미 같은 역할의 헬스 개요
  섹션을 갖고 있었으나 실제 아무것도 연결되지 않은 mock 데이터("healthy",
  "72%" 등 하드코딩)였음 — Dashboard의 실제 ExecutionContext 기반 수치와
  중복·모순. Dashboard는 파이프라인 상태/시스템 헬스 섹션을 "전체 상태"
  카드 하나로 축소하고, Monitor가 단계별 파이프라인 섹션을 흡수하며
  `_render_health_overview()`의 하드코딩을 실측값으로 교체했다. 이어서
  Monitor의 `_render_performance_metrics()`가 갖고 있던 4개 하드코딩
  리터럴(142ms/8.3건/sec/0.8923 "RRF"/156MB)도 실측값으로 교체(응답
  시간은 `record_query_latency`, 처리 속도는
  `runtime_state.get_processing_throughput()` 등). 같은 흐름에서
  Hierarchical Chunk Builder의 SPRINT33-D Phase 3-A 공식 측정 완료를
  계기로 ADR-008(semantic chunking production 전환 경로, 제안만·미확정)도
  작성됨.
- 커밋: `70a9d4d`, `a3c28cd`, `be1ceef`, `27f0ff3`, `dbb36c3`.
- 다음 조치: ADR-008 제안 항목 착수 여부는 HQ 결정 대기.

### 문서 정합성 점검 및 정정 (2026-07-20)
- 상태: 완료
- 설명: HQ 제기 "dbma.py 제거 적절성" 질의를 계기로 문서 전수 점검 수행.
  `dbma.py`는 이미 SPRINT20-I-D(commit `ce6b05a`, 2026-07-17)에서
  `archive/legacy/`로 이동 완료된 상태였으나, `CLAUDE.md`와
  `docs/architecture/DBMA-Legacy-Code-Removal-Plan-v1.md`가 이를 반영하지
  못하고 "제거 계획 진행 중"으로 서술 중이었음을 확인해 정정. 존재하지 않는
  `dbma_rag.py`(commit `94ed8cf`에서 이미 삭제됨) 오기재도 `CLAUDE.md`와
  그 생성 템플릿(`scripts/create_docs.py`)에서 함께 제거. ChromaDB/Qdrant
  레거시 벡터스토어는 ADR-003(Finalization)에 따라 폐기 대상이 아니라 KEEP
  확정 상태임을 재확인(`chroma_db/`, `dbma_qdrant_storage` 실물 존재 확인
  완료). `docs/architecture/DBMA-Architecture-Map-v2.md`,
  `DBMA-Module-Responsibility-v2.md`는 `status: current`를 단 채 SPRINT16
  시점(레거시 archive 이전) 상태를 서술하고 있어 STATE.md와 모순되는 것을
  발견, 본문 재작성 없이 frontmatter status를 `superseded`로 변경하고 상단에
  경고 문구 추가.
- 커밋: `35b8e94`(CLAUDE.md/Plan v1), `8f6b314`(create_docs.py),
  `38e813d`(Architecture-Map-v2/Module-Responsibility-v2) — `dev/dbma-engine`에
  push 완료.
- 다음 조치: 없음.

### Citation Layer (SPRINT20-B/E)
- 상태: 완료
- 설명: `CitationBuilder`가 `list[str]` 대신 구조화된 `Citation` 객체를 생성하고,
  `ResponsePackage.citations` → `GenerationResult.citations`까지 손실 없이
  전달된다. `source_file`/`language`/`source_type`이 registry→TSU→Citation
  전 구간에서 100% coverage로 propagate됨을 1,500개 gold query로 확인했다.
- 다음 조치: 없음(SPRINT20-F 이후 후속 품질 개선은 별도 스프린트로 분리).

### Research Workspace Layer — 첫 번째 Memory Layer (SPRINT27-B/C)
- 상태: 완료
- 설명: `core/research_workspace.py`를 기존 5개 Authority(Processing/Identity/
  TSU/Retrieval/Generation)와 나란한 독립 6번째 레이어로 신설
  (`docs/architecture/ADR-004-Research-Workspace-Layer.md`). 검색 세션을
  `{DEFAULT_OUTPUT_DIR}/research/sessions.json`에 저장하되 TSU 콘텐츠는
  복제하지 않고 `tsu_id`/`document_id`/`citation_id` 참조만 append-only로
  기록(`extraction_failures.json`과 동일한 atomic write 패턴). Research UI
  (`ui/pages/research.py`)에 "세션에 저장" 버튼과 저장된 세션 목록/불러오기
  패널을 추가 — `QueryProcessor.process()` 기존 인터페이스만 호출하고,
  세션 불러오기는 재검색을 자동 실행하지 않는다(검색창만 채움).
  `core/retrieval.py`/`core/processing.py`/`core/identity_registry.py`/TSU
  schema/`documents.json` 전부 무변경 확인됨.
  CI 검증 과정에서 `response_package["results"]`(존재하지 않는 키) 참조 버그와
  `document_id`(metadata 중첩)/`citation_id`(citations 리스트 별도 매핑) 추출
  경로 버그를 발견해 수정하고 회귀 테스트를 추가했다.
- 커밋: `519d719`(feature), `86b1d22`(무관 테스트 docstring), `02afc3f`
  (LOCAL_LLM_HANDOFF.md) — `dev/dbma-engine`에 push 완료.
- 검증: pytest 320 passed(신규 8건: `test_research_workspace.py` 5건,
  `test_research_saved_sessions_ui.py` 3건), 회귀 없음.
- 다음 조치: SPRINT27-D — Research Workspace를 향후 MIE(Ministry Intelligence
  Engine) Memory Layer로 확장하는 방향에 대한 Architecture Preflight(투자
  조사만, 구현 없음).

### Execution Environment / Configuration Authority (SPRINT20-E3/F1)
- 상태: 완료
- 설명: PyYAML 누락 시 `core/config.py`가 `RuntimeError`로 즉시 실패하도록
  변경(과거에는 `config.yaml`이 조용히 무시되고 `DEFAULT_OUTPUT_DIR`이 stale
  경로로 폴백해 TSU 데이터셋 손상 직전까지 갔던 사고가 있었음). 공식 Python
  버전을 3.11.x로 확정하고 `scripts/check_environment.py`로 검증 가능하게 함.
- 다음 조치: 없음.

### Application Entry Point Authority (SPRINT20-G1/G2)
- 상태: 완료
- 설명: `docs/architecture/ADR-001-Retrieval-Engine-Authority.md`가 이미
  `dbma_ui.py`→`ui/app.py`를 공식 경로로, `dbma.py`의 인라인 RAG를 폐기
  대상으로 결정해 두었으나 README/`.github/instructions/*` 문서가 갱신되지
  않아 신규 사용자가 legacy 경로로 유입될 위험이 있었다. 문서 정렬 완료.
- 다음 조치: 없음 — `dbma.py` 자체의 archive 여부는 SPRINT20-I-D에서 결정·실행
  완료(`archive/legacy/`로 이동, commit `ce6b05a`, 2026-07-17). 아래 체크포인트
  항목 참고.

### Logging Authority (SPRINT20-G3)
- 상태: 완료
- 설명: `core/config.py`가 import 시점에 root logger를 `ERROR`로 강제 설정해
  `core/extractors.py`의 optional-dependency 경고(PyMuPDF/striprtf/
  pytesseract/pdf2image 없음)가 전역 억제되고 있었다. 특히 공식 진입점
  `ui/app.py`/`dbma_ui.py`에는 이를 되돌리는 보정 코드가 없어 영향이 컸다.
  해당 설정 제거 후 root logger가 Python 기본값(WARNING)으로 복원됨을
  확인했다.
- 다음 조치: 없음.

---

## 체크포인트

- [x] 프로젝트 구조 확인
- [x] 운영 규칙 정리
- [x] 문서화 기준 수립
- [x] Retrieval Engine 단일화 (ADR-001)
- [x] Citation Layer 구조화 및 Generation pass-through
- [x] Metadata Propagation (source_file/language/source_type)
- [x] Configuration Authority (PyYAML hard-fail)
- [x] Execution Environment Authority (Python 3.11 lock)
- [x] Dataset Provenance (TSU manifest v2)
- [x] Entry Point Documentation Alignment
- [x] Logging Authority Restoration
- [x] Index/TSU Builder Authority 확립 (SPRINT20-I, core/index_orchestrator.py + core/tsu_builder.py)
- [x] Registry Path Authority 단일화 (DEFAULT_REGISTRY_PATH)
- [x] `dbma.py` Legacy Archive 완료 (SPRINT20-I-D, archive/legacy/)
- [x] Retrieval Document Diversity (RETRIEVAL_DOCUMENT_CAP)
- [x] Legacy Vector Store 정책 확정 (ADR-003 Finalization)
- [x] v1.3.0 Release 태그 (07ec084) + Release validation (chapter-level
      benchmark 1500q — PASS, 회귀 없음)
- [x] Ollama HTTP 500 수정 (P2, char/token 4→2, commit f5f2753)
- [x] 잔여 cleanup (data/rag_index, 빈 backup 폴더, md_manager archive)
- [x] Research Workspace Layer — 첫 번째 Memory Layer (SPRINT27-B/C, ADR-004,
      `core/research_workspace.py`, commit `519d719`)
- [ ] SPRINT27-D — Memory Layer 확장 Architecture Preflight (미착수)
- [x] PdfHeadingProvider 배선 + HeadingAssembler 안정화 (SPRINT31~32)
- [x] Dormant Semantic Boundary Detector + Shadow scoring feature군 (SPRINT33-A~C)
- [x] ADR-007/Amendment A D-5 게이트 정의 + Hierarchical Chunk Builder 프로토타입 (SPRINT33-D Phase1~2)
- [x] D-5 Metrics 공식 평가 (SPRINT33-D Phase3-A, Beta corpus 12건, commit `71ef068`)
- [x] `split_sentences_mixed()` chunk overflow 원인 규명 (Preflight, commit `ae78866`)
- [x] Dashboard/Monitor 탭 분리 + Monitor 실측 지표화 (commit `70a9d4d`/`dbb36c3`)
- [x] ADR-008 semantic chunking production 전환 경로 제안 (commit `27f0ff3`, 미확정)
- [x] `.gitignore` 오버매칭 버그 수정 (commit `14ed5ed`)
- [ ] chunk overflow 하위결함 B 수정 방향 결정 및 구현 (HQ 승인 대기)
- [ ] ADR-008 후속 항목 착수 여부 결정 (threshold 재산정 / Level 3 구현 / 6번째 feature)

---

## 비고

이 문서는 작업 상태를 빠르게 확인하기 위한 기준 문서다.
상태가 바뀌면 즉시 갱신한다.
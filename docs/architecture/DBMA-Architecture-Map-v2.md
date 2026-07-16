---
title: DBMA Architecture Map v2
category: architecture
sprint: SPRINT16-A-2
based_on:
  - docs/architecture/DBMA-Engineering-Knowledge-Map.md
  - repository inspection (2026-07-16)
status: current
created: 2026-07-16
supersedes_intent: docs/ARCHITECTURE.md, docs/DBMA_MAP.md (구식, 이 문서로 대체 권장 — 자동 폐기하지 않음)
---

# DBMA Architecture Map v2

이 문서는 `docs/architecture/DBMA-Engineering-Knowledge-Map.md`(진화 이력)와
현재 저장소 실사(import 그래프, 파일 구조, 함수 시그니처)를 근거로 작성한
**현재 시점(Phase 6 / Production v1.1.0)** 구조 기준 문서다.

---

## 1. System Overview

DBMA는 신학 문서 전용 RAG 시스템이다. 진입점은 두 개로 나뉜다.

- `dbma.py` — 레거시/단일 진입점. Streamlit 앱을 직접 구성하며 `core.processing`,
  `core.files`, `core.config`, `core.feature_flags`를 직접 임포트한다.
- `ui/app.py` — 현재 구조화된 진입점. `ui/pages/*`의 5개 페이지
  (dashboard, library, processing, research, monitor)를 조립한다.

두 진입점이 공존하는 상태이며, `ui/app.py` → `ui/pages/*` → `core/*` 경로가
Knowledge Map의 "Phase 4: UI Separation" 이후 주 경로로 보인다.
`dbma.py`가 여전히 존재하고 활발히 수정되는지(최근 커밋 대상 여부)는 이 감사 범위 밖이므로
별도 확인이 필요하다.

핵심 축:
- **처리(Processing)**: 원본 문서 → 추출 → 정제 → 청킹 → 메타데이터 → md 저장
- **식별(Identity)**: 콘텐츠 기반 문서 ID, 중복/변경 감지
- **검색(RAG)**: Qdrant 벡터 검색 + BM25/TF-IDF 하이브리드 + 신학 특화 스코어링
- **설정(Configuration)**: `config.yaml` 단일 소스 → `core/config.py`가 로드
- **실행 상태(Execution State)**: `core/feature_flags.py`(정적 on/off) +
  `core/runtime_state.py`(로그/파일 기반 동적 파이프라인 상태)

---

## 2. Pipeline Flow

```text
원본 문서 (PDF/TXT/MD/DOCX/EPUB/HTML/RTF)
  → core/extractors.py           (extract_text_from_file)
  → core/text_normalizer.py      (reflow_wrapped_lines — 줄바꿈 정규화)
  → core/frontmatter_detector.py (split_front_matter — 기존 frontmatter 분리)
  → core/document_identity.py    (generate_document_id, compute_content_hash,
                                   build_document_metadata)
  → core/identity_registry.py    (register_document, classify_ingest_decision,
                                   중복/재처리 여부 판단)
  → core/utils.py                (make_safe_stem, calculate_noise_score)
  → core/chunking_optimizer.py   (optimize_chunks, save_optimized_md)
  → md 저장 (frontmatter + metadata 포함)
  → core/embedder.py             (embed — 벡터 생성)
  → core/ingest.py / core/qdrant_init.py (Qdrant 컬렉션에 upsert)
  → core/search.py / core/retrieval.py   (질의 처리 및 응답 조립)
```

오케스트레이터는 `core/processing.py`의 `process_one_file()`이며,
`build_converter()`, `build_splitter()`, `detect_language()`,
`save_md_with_language()`, `save_chunks()`를 호출해 위 흐름을 하나로 묶는다.
(구 문서가 언급한 `move_source_file()`은 현재 코드에 존재하지 않는다 — 이름 변경 또는 제거된 것으로 추정, 재확인 필요.)

---

## 3. Module Dependency Map

실제 `import` 구문 기준 (core 내부):

```text
core/config.py            ← (의존 없음, config.yaml만 읽음)
core/utils.py              ← (의존 없음)
core/extractors.py         ← (의존 없음)
core/text_normalizer.py    ← (의존 없음)
core/document_identity.py  ← (의존 없음)
core/feature_flags.py      ← (의존 없음)
core/runtime_state.py      ← (의존 없음, logs/output 파일 직접 판독)

core/chunking_optimizer.py → core/utils.py
core/files.py              → core/config.py, core/utils.py
core/frontmatter_detector.py → core/extractors.py
core/identity_registry.py  → core/document_identity.py
core/embedder.py           → core/config.py
core/search.py             → core/embedder.py
core/md_manager.py         → core/config.py
core/ingest.py             → core/embedder.py (지연 임포트, 함수 내부)

core/processing.py         → core/extractors.py, core/utils.py,
                              core/chunking_optimizer.py, core/text_normalizer.py,
                              core/frontmatter_detector.py, core/document_identity.py,
                              core/identity_registry.py
                              (파이프라인 오케스트레이터 — 가장 많은 의존성을 가짐)

core/retrieval.py          ← (core 내부 의존 없음, 자체 완결형 검색 엔진)
core/query_enhancements.py → core/retrieval.py (QueryParser 상속·확장)
```

상위 계층(UI)의 core 의존:

```text
ui/app.py        → ui/pages/*, ui/theme/colors
ui/pages/dashboard.py  → core/config.py, core/runtime_state.py
ui/pages/library.py    → core/config.py
ui/pages/processing.py → core/config.py, core/processing.py
ui/pages/research.py   → core/config.py, core/retrieval.py

dbma.py           → core/feature_flags.py, core/config.py,
                     core/files.py, core/processing.py, core/utils.py
```

**관찰**: `core/processing.py`가 사실상의 파이프라인 허브이며, `core/retrieval.py`는
의도적으로 다른 core 모듈과 결합하지 않는 독립 검색 엔진으로 설계되어 있다
(단, `query_enhancements.py`가 이를 상속 확장).

---

## 4. RAG Architecture

`core/retrieval.py`(약 1600줄)가 RAG의 실질적 구현체다. 구 문서(`dbma_rag.py`,
`run_rag_query()`, `build_retriever()`, `generate_response()`)는 더 이상 코드에 존재하지 않는다.

핵심 클래스/함수 (`core/retrieval.py`):
- `QueryParser` / `EnhancedQueryParser`(`core/query_enhancements.py`에서 상속) — 질의 파싱
- `EmbeddingCache` — 임베딩 캐시
- `bm25_score()`, `TfidfVectorizer` — 어휘 기반 스코어링
- `compute_theological_score()`, `_scripture_alignment_score()`,
  `_thematic_relevance_score()`, `_sermon_usability_score()` — 신학 문서 특화 스코어링
  (성경 인용 정합성, 주제 관련성, 설교 활용성)
- `RetrievalEngine` — 검색 오케스트레이터 (Qdrant 질의 + 하이브리드 스코어링)
- `ContextAssembler`, `CitationBuilder`, `ResponseFormatter`, `QueryProcessor` — 응답 조립
- `run_benchmark_integration()`, `compare_with_regression()` — 벤치마크/회귀 비교 연동

`core/query_enhancements.py`는 `RetrievalEngine`을 확장하는 계층:
- `EnhancedBookDetector`, `EnhancedReferenceParser` — 성경책 별칭/한국어 정규화
- `EnhancedQueryParser(QueryParser)` — 위 파서들을 결합한 상위 파서
- `run_validation()` — 자체 검증 루틴

`core/search.py`는 별도의 경량 검색 경로(단순 `search()`/`search_pretty()`)로,
`RetrievalEngine`과 별개로 `core/embedder.py`만 사용해 Qdrant에 직접 질의한다.
**두 검색 경로(경량 `search.py` vs 풀스택 `RetrievalEngine`)가 공존**하는 점은
향후 통합 또는 역할 분리 명시가 필요한 부분이다.

벡터 저장소: **Qdrant** (`COLLECTION = "dbma_sermon"`, 기본 URL `http://localhost:6333`,
768차원 코사인 거리) — `core/qdrant_init.py`, `core/ingest.py`, `core/search.py`,
`core/retrieval.py`, `core/md_manager.py`(`reindex_md_to_qdrant()`)에서 사용.
Knowledge Map이 "Storage Layer: Qdrant vector DB"로 서술한 것과 일치한다.
(`core/runtime_state.py`가 참조하는 `chroma_db` 경로는 구버전 잔여 상태 점검용 문자열로,
현재 활성 벡터 백엔드는 Qdrant다 — 문서/코드 간 명명 잔재로 주석 필요.)

데이터셋 포맷: **TSU (JSONL)** — `output/tsu/tsu_dataset.json`. `core/runtime_state.py`가
파이프라인 "indexing" 단계 판정 근거로, `core/retrieval.py`/`core/query_enhancements.py`가
검증·벤치마크 대상으로 참조한다.

---

## 5. Metadata Flow

```text
core/document_identity.py
  generate_document_id(content, source_file)   — SHA-256 기반 결정적 ID
  compute_content_hash(content)                 — 콘텐츠 변경 감지용 해시
  build_document_metadata(...)                  — 문서 메타데이터 객체 구성
  generate_chunk_id(doc_id, index)               — 청크 단위 ID
        ↓
core/identity_registry.py
  load_identity_registry() / save_identity_registry()  — 레지스트리 영속화
  register_document()                             — 신규 문서 등록
  find_by_document_id() / find_by_file_hash()      — 중복 조회
  classify_ingest_decision()                       — 신규/변경/중복 판정
  transition_ingest_status() / update_pipeline_flags() — 상태 전이
  migrate_registry_schema()                        — 레지스트리 스키마 마이그레이션
        ↓
core/processing.py (process_one_file)
  build_document_metadata() → identity_registry 조회 → 처리 여부 결정
        ↓
core/frontmatter_detector.py (split_front_matter)
  기존 md 파일의 frontmatter와 본문 분리 — 메타데이터 보존/병합
        ↓
저장된 .md 파일 frontmatter (문서 식별자 + 처리 버전 PROCESSING_VERSION 포함)
```

`PROCESSING_VERSION = "1.1.x"`(`core/document_identity.py`)가 파이프라인 버전 기록의
기준값이다. 최근 커밋(`fd8a2aa Preserve document metadata in markdown frontmatter`,
`336fa5e fix: initialize document metadata before markdown generation`)이 바로 이 흐름의
안정화 작업으로 보인다.

---

## 6. Configuration Flow

```text
config.yaml (저장소 루트, 단일 진실 소스)
        ↓ (PyYAML로 로드, 없으면 무시)
core/config.py
  CFG: dict            — yaml 전체 원본
  APP_VERSION, APP_NAME
  BASE_DIR, DATA_DIR, DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR
  SUPPORTED_EXTENSIONS
  EMBEDDING_DIMENSION 등
        ↓
core/embedder.py, core/files.py, core/md_manager.py,
ui/pages/dashboard.py, ui/pages/library.py,
ui/pages/processing.py, ui/pages/research.py, dbma.py
```

- `config/` 디렉터리는 **존재하지 않는다.** 설정은 파일 하나(`config.yaml`)와
  이를 로드하는 모듈 하나(`core/config.py`)로 집중되어 있다.
- `core/config.py`는 yaml 값이 없을 경우 코드 내 기본값으로 폴백하는
  하위 호환 계층을 명시적으로 포함한다 (예: `DEFAULT_RAW_DIR`가 yaml 경로 부재 시
  `data/RAW`로 대체).
- `config.yaml.bak_20260714` 백업 파일이 루트에 존재 — 최근(2026-07-14) 설정 변경이
  있었음을 시사하나 코드에서 직접 참조되지 않는다 (수동 백업으로 추정).

---

## 7. Validation Infrastructure

두 계층으로 나뉜다.

**전체 파이프라인 검증 (`scripts/`)**
- `scripts/validate_pipeline.py` — pytest + 벤치마크를 순차 실행하는 통합 러너.
- `scripts/benchmark_pipeline.py`, `scripts/rag_benchmark.py`,
  `scripts/rag_benchmark_dashboard.py` — 성능/RAG 품질 벤치마크.
- `scripts/evaluation_fingerprint.py` — 평가 결과 지문(재현성 검증용 추정).
- `scripts/repair_tsu_book_id.py`, `scripts/repair_tsu_book_metadata.py` — TSU 데이터셋
  메타데이터 복구 도구.
- `scripts/backup_chroma.py` — 벡터 DB 백업 (이름은 chroma지만 현재 활성 백엔드는
  Qdrant — 레거시 백업 스크립트로 추정, 재검토 필요).
- `scripts/create_docs.py`, `scripts/update_docs.py` — 문서 생성/갱신 도구.

**SPRINT15 통제 검증 (`scripts/validation/`)** — docstring상 "3-E #7" 항목,
`build_document_metadata() → process_one_file() → save_md_with_language()` 체인을 검증:
- `validate_metadata_unit.py` — 함수 단위 직접 호출 검증.
- `validate_metadata_pipeline.py` — 전체 파이프라인 통제 검증(임시 디렉터리 사용).
- `validate_real_pdf.py` — `data/RAW`의 실제 PDF 1건으로 종단 검증.

**pytest 회귀 테스트 (`tests/`)**
- `test_processing_pipeline.py`, `test_chunking_optimizer.py`,
  `test_frontmatter_detector.py`, `test_text_normalizer.py`, `test_utils_noise.py`
  — core 개별 모듈 단위 테스트.
- `test_book_alias_resolution.py`, `test_query_enhancements_full_regression.py`
  — RAG 질의 향상 계층 회귀 테스트.
- `gold_queries.json` — Knowledge Map이 "Phase 6 Production" 핵심 산출물로 지목한
  골드 표준 질의 세트, 회귀 비교(`compare_with_regression()`)의 입력으로 추정.

`scripts/validation/`과 `tests/`는 목적이 다르다: 전자는 SPRINT15 시점의 1회성 통제
검증 스크립트(수동 실행), 후자는 지속적 회귀 방지용 pytest 스위트다.

---

## 8. Execution State Direction

두 개의 서로 다른 상태 축이 존재한다.

**정적 축 — Feature Flags (`core/feature_flags.py`)**
```text
SPRINT2_FEATURES: bool (코드 내 하드코딩된 전역 플래그)
  → feature_enabled(name) → {embedding, vector_db, rag, llm, benchmark}
  → dbma.py가 기동 시 참조 (예: RAG 관련 UI 노출 여부)
```
Sprint 1 = 순수 데이터 계층만(parse→clean→chunk→store), Sprint 2+ = 임베딩/벡터DB/LLM/RAG
전체 활성화. 현재 `SPRINT2_FEATURES = True`로 전체 기능이 켜져 있다.

**동적 축 — Runtime Pipeline State (`core/runtime_state.py`)**
```text
데이터원 4가지:
  1. logs/project_events.jsonl        — 처리 이벤트 로그
  2. output/{output_dir}/.batch_state.json — 배치 처리 파일 목록
  3. output/tsu/tsu_dataset.json      — TSU 데이터셋(임베딩/인덱싱 완료 여부)
  4. chroma_db persist directory      — (레거시 명칭) 벡터 인덱스 존재 여부

  → get_pipeline_status() / get_pipeline_status_dict()
  → PipelineStageState(stage, status, progress, detail)
       stage ∈ {extract, chunk, embedding, indexing, search}
       status ∈ {pending, active, complete}
  → ui/pages/dashboard.py 가 소비 (Dashboard Processing Pipeline Status)
```

**방향성**: Feature Flags는 "무엇을 켤 것인가"를 코드 배포 시점에 정적으로 결정하고,
Runtime State는 "지금 실제로 어디까지 처리됐는가"를 로그/산출물 파일을 스캔해
매 요청마다 동적으로 재계산한다. 두 축은 서로 참조하지 않는 독립 시스템이며,
`dbma.py`는 전자를, `ui/pages/dashboard.py`는 후자를 사용한다.

---

## 부록: 구 문서 대비 핵심 정정 사항

| 구 문서 서술 | 실제 상태 |
|---|---|
| RAG Layer = `dbma_rag.py` | 파일 없음. `core/retrieval.py` + `core/query_enhancements.py`가 대체 |
| `run_rag_query()`, `build_retriever()`, `generate_response()` | 코드에 존재하지 않음 |
| `core/processing.py` 관련 함수에 `move_source_file()` | 코드에서 확인 불가 |
| core 5개 모듈만 서술 | 실제 22개 파일, 17개 미문서화 상태였음 |
| `ui/tabs.py`/`sidebar.py`/`styles.py` 3파일 구조 | `ui/app.py` + `pages/`+`components/`+`state/`+`theme/` 구조로 확장 |
| `config/` 디렉터리 언급 | 디렉터리 없음, `config.yaml` + `core/config.py`로 구성 |

---

*본 문서는 SPRINT16-A-2 범위(`docs/architecture/`)에서만 작성되었으며,
`core/`, `scripts/`, `tests/`, `config.yaml`은 수정하지 않았다.*

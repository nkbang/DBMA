---
title: DBMA Architecture Documentation Audit
created: 2026-07-16
status: report-only (수정 없음)
scope: core/, config/, scripts/, tests/
---

# DBMA Architecture Documentation Audit

## 요약

`docs/ARCHITECTURE.md`와 `docs/DBMA_MAP.md`는 프로젝트 초기(Phase 0~2 수준) 구조를 기술하고 있으나,
실제 코드는 `docs/architecture/DBMA-Engineering-Knowledge-Map.md`가 서술하는 **Phase 5~6 (MIE Architecture / Production v1.0)** 수준까지 진행되어 있다.
즉 **Knowledge Map은 실제 코드와 대체로 일치**하지만, **ARCHITECTURE.md / DBMA_MAP.md는 심각하게 뒤처져 있다.**

---

## 1. core/ 디렉터리

### 문서(ARCHITECTURE.md, DBMA_MAP.md)에 기술된 모듈
- `core/processing.py`
- `core/extractors.py`
- `core/chunking_optimizer.py`
- `core/files.py`
- `core/utils.py`

### 실제 core/ 파일 (22개)
```
__init__.py, chunking_optimizer.py, config.py, document_identity.py,
embedder.py, extractors.py, feature_flags.py, files.py,
frontmatter_detector.py, identity_registry.py, ingest.py, init.py,
md_manager.py, processing.py, qdrant_init.py, query_enhancements.py,
retrieval.py, runtime_state.py, search.py, text_normalizer.py,
text_splitter.py, utils.py
```

### 차이점
- **문서화되지 않은 모듈 17개**: `config.py`, `document_identity.py`, `embedder.py`,
  `feature_flags.py`, `frontmatter_detector.py`, `identity_registry.py`, `ingest.py`,
  `init.py`, `md_manager.py`, `qdrant_init.py`, `query_enhancements.py`, `retrieval.py`,
  `runtime_state.py`, `search.py`, `text_normalizer.py`, `text_splitter.py`.
  이 중 `retrieval.py`(1600여 줄, `RetrievalEngine`/`QueryProcessor`/BM25/TF-IDF 등)와
  `identity_registry.py`는 코드량과 책임 면에서 핵심 모듈이지만 ARCHITECTURE.md에는 존재 자체가 없다.
- **문서에 있으나 실제로 없는 함수**: `DBMA_MAP.md`가 `core/processing.py`의 관련 함수로 나열한
  `move_source_file()`은 코드에서 찾을 수 없었다 (grep 결과 없음, 이름 변경 또는 삭제 추정).
- **RAG 계층 서술 불일치**: ARCHITECTURE.md는 "RAG Layer = `dbma_rag.py`"라고 명시하지만,
  현재 저장소에 `dbma_rag.py` 파일 자체가 존재하지 않는다. RAG/검색 책임은
  `core/retrieval.py`, `core/search.py`, `core/query_enhancements.py`로 이전된 것으로 보인다.
  DBMA_MAP.md가 서술하는 `run_rag_query()`, `build_retriever()`, `generate_response()` 함수도
  코드베이스 어디에서도 찾을 수 없었다 — 문서가 가리키는 API 자체가 사라졌다.

---

## 2. config/ 디렉터리

### 문서 서술
ARCHITECTURE.md/DBMA_MAP.md는 `config/`를 별도 디렉터리로 언급하지 않는다.

### 실제 상태
- `config/` 디렉터리는 **존재하지 않는다.**
- 설정은 루트의 `config.yaml`(+ 백업본 `config.yaml.bak_20260714`)과 `core/config.py`로 관리되고 있다.
- 사용자가 요청한 감사 범위(`config/`)와 실제 코드 구조 사이에 불일치가 있음 — 아마 `core/config.py` 또는 `config.yaml`을 의미했을 가능성이 있다. 별도 확인이 필요하다.

---

## 3. scripts/ 디렉터리

### 문서 서술
ARCHITECTURE.md는 `scripts/`를 "Documentation and Loop Layer"의 일부로만 뭉뚱그려 언급하며 개별 스크립트에 대한 설명이 없다.

### 실제 scripts/ 파일 (13개)
```
backup_chroma.py, benchmark_pipeline.py, create_docs.py,
evaluation_fingerprint.py, rag_benchmark.py, rag_benchmark_dashboard.py,
repair_tsu_book_id.py, repair_tsu_book_metadata.py, update_docs.py,
validate_pipeline.py,
validation/validate_metadata_pipeline.py,
validation/validate_metadata_unit.py,
validation/validate_real_pdf.py
```

### 차이점
- 문서에는 개별 스크립트 목록/역할이 전혀 없어 감사할 대상 자체가 없다.
- `scripts/validation/` 하위 디렉터리(3개 파일)는 Knowledge Map을 포함한 어떤 문서에도 언급되지 않는다.
- 최근 커밋 로그(`98a645b chore: organize sprint15 validation artifacts`, `fd8a2aa Preserve document metadata...`)와 스크립트 이름(`repair_tsu_*`, `validate_metadata_*`)을 볼 때 이 디렉터리는 sprint 15 전후로 활발히 성장했으나 문서화가 따라가지 못했다.

---

## 4. tests/ 디렉터리

### 문서 서술
- ARCHITECTURE.md/DBMA_MAP.md: `tests/`를 계층으로만 언급, 개별 파일 없음.
- Knowledge Map: `tests/gold_queries.json`을 "Phase 6 Production v1.0" 핵심 파일로 언급.

### 실제 tests/ 파일
```
gold_queries.json,
test_book_alias_resolution.py, test_chunking_optimizer.py,
test_frontmatter_detector.py, test_processing_pipeline.py,
test_query_enhancements_full_regression.py, test_text_normalizer.py,
test_utils_noise.py
```

### 차이점
- `gold_queries.json`은 Knowledge Map 서술과 일치 (확인됨).
- 나머지 7개 테스트 파일은 ARCHITECTURE.md/DBMA_MAP.md 어디에도 나열되지 않음. 특히
  `test_frontmatter_detector.py`, `test_text_normalizer.py`는 core/의 문서화되지 않은 모듈과
  1:1 대응되므로, 모듈 문서화 누락이 테스트 문서화 누락으로 이어진 것으로 보인다.

---

## 5. UI 계층 (참고 — 범위 밖이지만 연쇄 영향 확인)

ARCHITECTURE.md는 `ui/tabs.py`, `ui/sidebar.py`, `ui/styles.py` 3개 파일 구조만 서술하지만,
실제 `ui/`에는 `app.py`, `pages/`(5개), `components/`(5개), `state/`(2개), `theme/`(3개)가 추가되어 있다.
Knowledge Map의 "Phase 4: UI Separation" 서술과는 일치한다 — 즉 ARCHITECTURE.md가 Phase 4 이전 상태에 고정된 것으로 판단된다.

---

## 결론 및 권고 (실행은 하지 않음)

1. **ARCHITECTURE.md와 DBMA_MAP.md는 Phase 0~2 수준에서 멈춰 있고, 코드는 Phase 5~6까지 진행됨.**
   두 문서를 폐기하거나 `docs/architecture/DBMA-Engineering-Knowledge-Map.md` 기준으로 전면 재작성이 필요하다.
2. **`dbma_rag.py` 참조가 코드에 없는 파일을 가리킨다** — 가장 시급한 정정 대상 (독자가 존재하지 않는 파일을 찾게 됨).
3. **`core/retrieval.py`, `core/identity_registry.py`, `core/query_enhancements.py`** 는 실질적 핵심 모듈이나 완전 미문서화 — 우선 문서화 대상 1순위.
4. **`config/` 범위는 실제로는 `config.yaml` + `core/config.py`** 이므로, 향후 감사·문서 작성 시 이 매핑을 명시해야 혼동이 없다.
5. **`scripts/validation/`, `tests/*` 신규 파일들**은 개별 역할 설명이 전무 — DBMA_MAP.md 확장 시 함께 추가 권장.

본 보고서는 분석만 수행했으며 코드/문서를 수정하지 않았다.

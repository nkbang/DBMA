# NAE Metadata Adapter Test Plan

작성일: 2026-07-31
목적: Option B(External metadata registry lookup) 구현 시 적용할 테스트 계획. 계획 문서이며 코드/테스트 작성은 이번 단계에서 수행하지 않음.

## 검증 대상

### 1. Existing DBMA documents unaffected

- **목적**: 신규 스크립트(`scripts/ingest_nae_source.py`) 및 `core/tsu_builder.py` 변경이 기존 DBMA 문서(성경/일반 신학 자료) 처리에 부작용을 일으키지 않는지 확인
- **방법**: 기존 회귀 테스트(`tests/test_tsu_structure.py`, `tests/test_tsu_manifest.py`, `tests/test_build_tsu_dataset_*.py` — STEP3_TSU_PIPELINE_ANALYSIS.md에서 존재 확인됨) 전체 실행, 기존 통과 상태 유지 확인
- **핵심 케이스**: `nae_theological_position` 등 필드가 없는 기존 registry 문서에 대해 `record["nae_metadata"]`가 전부 `null`/빈 배열로 채워지고 예외 발생 없는지 (`doc.get(...)` 기본값 동작)
- 참고: [[feedback_test_fixture_path_overrides]] — 신규 테스트가 SQLite/JSON 경로를 사용할 경우 DEFAULT_*_PATH 오버라이드 전부 확인 필요

### 2. NAE metadata inheritance

- **목적**: `registry["documents"][doc_id].update({...})`로 주입된 `nae_*` 필드가 해당 문서의 모든 chunk(TSU record)에 정확히 상속되는지 확인
- **방법**: NAE_METADATA_POLICY_v1.md §1 정책(document-level 저장, chunk 상속) 대로, 한 문서에서 파생된 N개 TSU record 전부가 동일한 `nae_metadata.theological_position` 값을 갖는지 검증
- **엣지 케이스**: chunk_count=0인 문서(스킵 대상), 문서가 `superseded_by`로 대체된 경우 새 레코드에 nae 필드가 재주입되는지

### 3. TSU output preservation

- **목적**: 기존 TSU record의 다른 필드(`tsu_id`, `content`, `verse_mapping`, `content_quality`, `structure`, `baptist_theme` 등)가 `nae_metadata` 추가로 인해 값이 바뀌거나 순서/타입이 변경되지 않는지 확인
- **방법**: `nae_metadata` 추가 전/후 동일 입력에 대한 TSU record diff — 새 필드 1개(`nae_metadata`)만 추가되고 기존 키는 모두 동일 값 유지되는지 스냅샷 비교
- 근거: additive-only 원칙(SPRINT28-B/29-C/ADR-009 선례) 위반 여부 검증이 이 항목의 핵심

### 4. Retrieval compatibility

- **목적**: `core/retrieval.py::RetrievalEngine`이 `nae_metadata` 필드가 있는 TSU record를 만나도 기존 검색 결과/랭킹에 영향이 없는지 확인
- **방법**: 기존 검색 관련 테스트(`tests/test_retrieval_*.py`, `tests/test_hybrid_candidate_pipeline.py` 등)를 `nae_metadata` 포함 fixture로도 실행해 동일 결과 확인
- **엣지 케이스**: `RetrievalEngine`이 예상치 못한 새 키를 만났을 때 무시하는지(에러 없이 통과), 향후 이 필드를 실제로 소비하게 될 때를 대비한 계약(contract) 문서화 필요 여부만 기록(실제 소비 로직은 이번 범위 밖)

## 테스트 우선순위

1. TSU output preservation (기존 데이터 무결성 — 가장 중요)
2. Existing DBMA documents unaffected (회귀 방지)
3. NAE metadata inheritance (신규 기능 정확성)
4. Retrieval compatibility (안전망 확인)

## 실행 방식 (구현 승인 시)

- 신규 unit test는 `tests/test_ingest_nae_source.py`(가칭), `tests/test_tsu_builder_nae_metadata.py`(가칭)로 분리 — 기존 `test_tsu_structure.py` 등을 직접 수정하지 않고 추가 파일로 구성(최소 침습)
- 전체 회귀 스위트 실행은 [[feedback_verification_cost_discipline]] 원칙에 따라 매번 전체 실행하지 않고, 변경된 모듈 관련 테스트부터 우선 실행

## 제한

- 이번 문서는 계획만 제공하며, 실제 테스트 코드 작성/실행은 코드 구현 승인 이후 별도로 진행

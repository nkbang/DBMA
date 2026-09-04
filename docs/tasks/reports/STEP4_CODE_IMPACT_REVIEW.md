# STEP4 Code Impact Review

작성일: 2026-07-31
조사 방식: 읽기 전용 (grep/코드 열람), 코드 수정 없음.
목적: `nae_metadata` 등 NAE 확장 필드를 실제 코드에 반영할 경우의 삽입 위치와 core 변경 필요 여부 확인.

## 현재 TSU metadata 확장 위치

`core/tsu_builder.py::build_tsu_records()` (241~440행 관측)에서 TSU record는 dict 리터럴로 구성되며, additive 필드는 이미 다음과 같은 패턴을 반복 사용 중:

```python
record["content_quality"] = {...}   # SPRINT28-B
record["structure"] = {...}          # SPRINT29-C
record["theological_claim"] = None   # ADR-009
record["doctrine_category"] = []     # ADR-009
record["baptist_theme"] = []         # ADR-009
record["source_provenance"] = {...} if source_tier is not None else None  # Logos
```

→ `record["nae_metadata"] = {...}`를 이 패턴 뒤에 동일한 방식으로 추가하는 것이 **기존 관례와 정확히 일치**하는 확장 방법. 새 dict 블록 하나를 조건부로 채우거나 전부 `None`/기본값으로 채우면 됨.

## Adapter 추가 가능 위치

두 지점에서 확장 필요:

### 1. `core/identity_registry.py::register_document()` (90~148행 관측)
- 현재 `record = {...}` 리터럴에 `title`/`author`/`book`/`chapter`/`page`/`doc_type` 등 "Optional fields (None = unknown — never invent)" 섹션이 이미 존재(130행 부근)
- `content_genre`, `theological_position`, `denomination_context`, `copyright_status`는 이 섹션에 **같은 스타일로 추가 가능**: `metadata.get("content_genre")` 등, 기본값 `None`/`[]`
- 이 함수는 `metadata` dict를 인자로 받아 그대로 채워 넣는 구조이므로, 호출부(`core/processing.py`)가 이 키들을 `metadata`에 실어 보내기만 하면 registry 쪽 코드 변경은 각 필드 1줄 추가로 국한됨

### 2. `core/tsu_builder.py::build_tsu_records()` (340행 이후 record 구성부)
- `doc.get("content_genre")`, `doc.get("theological_position")` 등으로 registry에서 읽어와 `record["nae_metadata"]` 블록 구성
- 기존 `source_provenance` 처리부(422~437행)와 동일한 조건부 None 패턴 적용 가능

## core 변경 필요 여부

**필요함, 그러나 변경 범위는 작고 국소적(additive-only)으로 예상됨:**

- `core/identity_registry.py::register_document()`: dict 리터럴에 4~6개 키 추가 (약 5~10줄)
- `core/tsu_builder.py::build_tsu_records()`: `nae_metadata` dict 블록 구성 로직 추가 (약 10~15줄, 기존 `source_provenance` 블록과 유사 규모)
- `core/processing.py`: ingest 시점에 NAE 메타데이터를 `metadata` dict에 실어 `register_document()`에 전달하는 경로 필요 — 이 부분은 이번 조사에서 상세 확인하지 않음(processing.py의 ingest 흐름 전체를 아직 정독하지 않았음), **추가 조사 필요 항목**으로 남김
- `core/retrieval.py`: **변경 불필요** — `nae_metadata`는 additive이며 검색 로직이 이 필드를 아직 읽지 않으므로 기존 검색 동작에 영향 없음 (STEP3_TSU_PIPELINE_ANALYSIS.md에서 이미 확인)

## 위험/주의 사항

- 기존 필드(`content_quality`, `structure`, `baptist_theme` 등)를 건드리지 않는 한 리스크는 낮음 — additive 패턴이 이미 SPRINT28-B/29-C/ADR-009에서 3회 반복 검증된 안전한 확장 방식
- 단, `core/processing.py`에서 NAE 메타데이터를 어디서 입력받아 `metadata` dict에 실을지(수동 입력 UI? 등록 스키마 파일 로드?)는 미결정 — 이번 STEP4-A 범위 밖의 새로운 설계 질문

## 결론

- core 변경은 **필요하지만 국소적**(3개 파일, 각각 5~15줄 수준)
- 실제 코드 수정은 이번 STEP4-A에서 **수행하지 않음** — 조사만 완료
- `core/processing.py` ingest 흐름의 NAE 메타데이터 입력 경로는 추가 조사 대상으로 남김

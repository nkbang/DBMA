# C1 Task Order 017 — DocumentContext Registry Schema Parity 구현

**상태**: 승인됨 — 구현 착수 가능 (2026-07-29, David 승인)
**근거 설계 문서**: `docs/architecture/DBMA-DocumentContext-Registry-Parity-Design-v1.md` (§8에서 승인 완료, doc_type 인용 출처 정정 반영됨)
**작성일**: 2026-07-29

---

## 1. 배경

`DocumentContext.to_metadata_dict()`가 registry 레코드 스키마의 부분집합만
직렬화해, `core/processing.py`의 일반 파이프라인을 거친 문서는 registry에
`doc_type=None`으로 저장된다 — 이 값을 읽는 `ui/pages/dashboard.py`(문서
그룹핑/필터링/표시), `scripts/report_chunk_summary.py`(값 없으면 `"?"`
표시), `ui/pages/sermon_review.py`에서 실제로 관측 가능한 분류 오류가
발생한다. 그 외에도 `superseded_by`/`supersedes`/`last_content_hash`/
`max_retries`/`source_provenance`가 `DocumentContext`에 아예 없고,
`ingest_status`/`retry_count`/`last_failure_reason`/`last_processed_at`/
`pipeline_flags`는 필드는 있지만 `to_metadata_dict()`가 직렬화하지 않는다.

상세 근거·필드별 코드 인용은 설계 문서 §0/§1 참고.

---

## 2. 구현 범위 (설계 문서 §3~§5 그대로)

### 2.1 `core/document_context.py` — `DocumentContext` 신규 필드 추가

설계 문서 §3의 코드를 그대로 적용:

```python
doc_type: Optional[str] = None
superseded_by: Optional[str] = None
supersedes: Optional[str] = None
last_content_hash: Optional[str] = None
max_retries: int = 3
source_provenance: Optional[dict] = None
```

### 2.2 `to_metadata_dict()` 확장 (§4)

기존 반환 dict의 키는 하나도 제거/변경하지 않고, 다음 키만 추가:

```python
"ingest_status": self.ingest_status,
"retry_count": self.retry_count,
"last_failure_reason": self.last_failure_reason,
"last_processed_at": self.last_processed_at,
"pipeline_flags": dict(self.pipeline_flags),
"doc_type": self.doc_type,
"superseded_by": self.superseded_by,
"supersedes": self.supersedes,
"last_content_hash": self.last_content_hash,
"max_retries": self.max_retries,
```

**`source_provenance`는 여기 포함하지 않는다** — §4/§5의 이유(`register_document()`가
모르는 키라 조용히 버려지는 함정 회피) 그대로 유지.

### 2.3 `source_provenance_from_registry_record()` classmethod 신설 (§5)

```python
@classmethod
def source_provenance_from_registry_record(cls, record: dict) -> Optional[dict]:
    """registry 레코드에서 source_provenance 6개 필드만 골라 dict로 묶어
    반환한다. 6개 필드가 전부 없으면 None(문서가 Logos 출처가 아님)."""
```

읽기 전용 — 쓰기는 여전히 `scripts/ingest_logos_export.py` 전용 경로로만.
`register_document()`/`core/identity_registry.py`는 건드리지 않는다.

### 2.4 `from_metadata_dict()` 대칭 확장 (§5-1)

```python
ctx.doc_type = meta.get("doc_type")
ctx.superseded_by = meta.get("superseded_by")
ctx.supersedes = meta.get("supersedes")
ctx.last_content_hash = meta.get("last_content_hash")
ctx.max_retries = meta.get("max_retries", 3)
ctx.source_provenance = cls.source_provenance_from_registry_record(meta)
```

---

## 3. 지켜야 할 원칙 (설계 문서 §2, §6 — 재확인)

1. **Additive only** — 기존 `to_metadata_dict()` 출력 키를 하나도 제거·변경하지 않는다.
2. **버전 분기 없음** — `to_metadata_dict(full=True)` 같은 플래그 만들지 않는다.
3. **Never invent** — `source_provenance`처럼 해당 없는 문서는 `None` 그대로, 억지로 빈 dict 채우지 않는다.
4. **범위 밖(손대지 말 것)**:
   - registry 최상위 필드(`schema_version`, 최상위 `created_at`/`updated_at`, `_meta.total_documents`)
   - `status`("processed" 고정값) 필드 — 모델링 안 함
   - `core/identity_registry.py::register_document()` 자체의 확장(`source_provenance` 쓰기 지원)
   - `core/processing.py`의 SKIP 경로 재통합 — 이건 스키마 갭이 아니라 별도 설계 문제

---

## 4. 검증 계획

1. **단위 테스트 추가** (`tests/test_document_context.py` — 기존 파일에 추가):
   - 신규 필드 6개의 기본값(`None`/`3`) 확인
   - `to_metadata_dict()`가 신규 5개 + 갭 5개 키를 포함하고, 기존 키는 하나도 안 빠졌는지 회귀 테스트
   - `source_provenance_from_registry_record()`: 6개 필드 전부 없으면 `None`, 일부만 있어도 정확히 6개 키로 묶이는지
   - `from_metadata_dict()`가 registry 레코드(예: `mark_superseded()`가 세팅한 `superseded_by` 포함)를 무손실로 복원하는지
2. **회귀 확인**: `core/processing.py`, `core/index_orchestrator.py`가 실제로 `DocumentContext`를 사용하는 경로의 기존 테스트가 전부 통과하는지 (`pytest tests/ -k "document_context or processing or index_orchestrator"` 정도로 범위 좁혀서 — 전체 회귀는 불필요)
3. **실사용 버그 확인(선택)**: `doc_type`을 추가해도 `core/processing.py`가 여전히 `_document_context.doc_type`을 세팅하지 않으면 대시보드 "?" 문제는 해결 안 됨 — 이 Task Order는 스키마 갭(직렬화/역직렬화)만 다루고, `processing.py`가 실제로 `doc_type` 값을 채워 넣는 배선(wiring)은 **범위 밖**임을 보고서에 명시할 것 (필요하면 별도 Task Order로 분리 제안)

---

## 5. 보고 형식

1. 코드 diff (`core/document_context.py`)
2. 신규 테스트 diff + `pytest --collect-only -q` 실제 결과
3. 관련 테스트 전체 통과 여부
4. §4-3 관련: `doc_type` 배선(processing.py가 실제로 값을 채우는지)이 이번 범위에 포함되는지/안 되는지 명확히 기재

---

**다음 조치**: 이 Task Order 승인 시 Act mode에서 구현 착수. 완료 후 CUE가 diff 대조·테스트 실행으로 더블첵.

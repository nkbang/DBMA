# C1 Task Order 021 — Sprint B: TagIngestValidator + 데이터셋 adapter 인터페이스

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (Sprint A 후속, 검색 신뢰성 파이프라인 v2)
**선행 작업**: Task Order 020(Sprint A) 완료 — `core/dataset_registry.py`의 `DatasetRegistry`/`TagDefinition`/
`TrustTier`/`LicensePolicy` 등을 그대로 재사용한다. **Sprint A에서 만든 함수/모델을 다시 정의하지 말 것.**
**근거 문서**: [docs/architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md](../../architecture/DBMA-Search-Trust-Pipeline-Plan-v2.md) §3 Sprint B
**작성일**: 2026-07-29
**모드 제약**: `core/retrieval.py`는 이번에도 건드리지 않는다 (Sprint C 전용). `core/dataset_registry.py`는
새 테이블/함수 **추가**만 하고 기존 함수 시그니처는 변경하지 않는다.

---

## 1. 배경

Sprint A는 `dataset_registry`/`tag_definition`/`query_audit_log` 3테이블만 구현했다. Sprint B는 계획서에
정의된 나머지 3테이블(`bible_tag_annotation`/`dataset_license`/`ingestion_run`)과, 데이터셋을 실제로
적재할 때 품질을 검증하는 `TagIngestValidator`, 그리고 어댑터 인터페이스를 구현한다.

**주의**: 현재 DBMA에는 실제 외부 `Prayer` 태그 데이터셋이 없다. 이번 작업은 **인프라(검증기·어댑터
인터페이스·리포트)를 구현하는 것**이지, 실제 외부 데이터를 구해서 적재하는 것이 아니다. 어댑터는
테스트용 인메모리/픽스처 데이터로 검증한다.

---

## 2. 구현 범위

### 2.1 `core/dataset_registry.py`에 테이블 3종 추가

기존 `init_db()` 함수의 DDL에 아래 3개 테이블을 추가한다 (기존 3테이블 DDL은 그대로 유지).

```sql
CREATE TABLE IF NOT EXISTS bible_tag_annotation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_reference TEXT NOT NULL,     -- 예: "Gen.24.12"
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    tag_namespace TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    scope TEXT NOT NULL,                   -- "verse" | "clause" | "discourse_unit" 등
    created_at TEXT NOT NULL,
    UNIQUE(canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name)
);

CREATE TABLE IF NOT EXISTS dataset_license (
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    license_status TEXT NOT NULL,          -- "verified" | "unverified" | "restricted"
    license_policy TEXT NOT NULL,          -- LicensePolicy enum 값
    license_note TEXT,
    verified_at TEXT,
    PRIMARY KEY (dataset_id, dataset_version)
);

CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    records_total INTEGER NOT NULL DEFAULT 0,
    records_ingested INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    records_duplicate INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT                     -- JSON 배열, 실패 사유 목록
);
```

대응하는 Pydantic 모델(`BibleTagAnnotation`, `DatasetLicense`, `IngestionRun`)과 CRUD 함수
(`register_tag_annotation`, `record_license`, `start_ingestion_run`, `finish_ingestion_run`,
`get_ingestion_run`)를 Sprint A와 동일한 스타일(never-overwrite where applicable, JSON 직렬화 헬퍼
`_to_json`/`_from_json` 재사용)로 추가한다.

- `bible_tag_annotation`의 `canonical_reference`는 **문자열 검증만** 한다(형식 `Book.Chapter.Verse`,
  정규식 `^[A-Za-z0-9]+\.\d+\.\d+$` 정도) — 실제 성경 66권 목록 대조 같은 정교한 canonicalization은
  Sprint C에서 `core/retrieval.py::ScriptureReference`와 연동할 때 처리. 이번엔 형식 검증만.

### 2.2 신규 모듈 — `core/tag_ingest_validator.py`

```python
class IngestValidationError(BaseModel):
    row_index: int
    reason: str          # 예: "invalid_canonical_reference", "unlicensed_dataset", "duplicate"

class IngestReport(BaseModel):
    dataset_id: str
    dataset_version: str
    records_total: int
    records_ingested: int
    records_rejected: int
    records_duplicate: int
    errors: list[IngestValidationError]

class TagIngestValidator:
    def __init__(self, db_path: str): ...

    def validate_and_ingest(
        self,
        dataset: DatasetRegistry,
        rows: list[dict],   # 각 row: {"canonical_reference": ..., "tag_namespace": ..., "tag_name": ..., "scope": ...}
    ) -> IngestReport:
        """
        검증 순서:
        1. dataset가 dataset_registry에 이미 등록되어 있는지 (없으면 전체 rows reject, 에러 1건으로 요약)
        2. dataset_license 레코드가 있고 license_status == "verified"인지
           (아니면 전체 rows reject, "unlicensed_dataset")
        3. row별: canonical_reference 형식 검증
        4. row별: tag_namespace/tag_name/scope가 dataset.annotation_scope와 맞는지
        5. row별: (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name) 중복 여부
           (이미 bible_tag_annotation에 있으면 skip, records_duplicate 증가)
        6. 통과한 row만 bible_tag_annotation에 insert
        7. ingestion_run에 시작/종료 기록, IngestReport 반환
        """
```

### 2.3 어댑터 인터페이스 — `core/dataset_adapters/base.py`

```python
from abc import ABC, abstractmethod

class DatasetAdapter(ABC):
    """외부 데이터셋을 TagIngestValidator가 받는 row 형식(dict)으로 변환하는 인터페이스.
    실제 외부 데이터셋(예: Lexham Propositional Outline)은 아직 없으므로,
    이번 Task Order는 인터페이스 + 테스트용 픽스처 어댑터 1개만 구현한다."""

    @abstractmethod
    def load_rows(self, source_path: str) -> list[dict]:
        """source_path에서 읽어 [{"canonical_reference", "tag_namespace", "tag_name", "scope"}, ...] 반환"""
        ...
```

`core/dataset_adapters/fixture_adapter.py`에 테스트/데모용 `FixtureAdapter(DatasetAdapter)`를 구현 —
JSON 파일(`[{"ref": "Gen.24.12", "tag": "prayer", "scope": "verse"}, ...]` 형태)을 읽어 표준 row로
변환하는 최소 구현. 실제 외부 데이터셋 adapter(Lexham 등)는 실 데이터가 확보되면 별도 Task Order로 추가.

### 2.4 이번 범위에서 제외

- 실제 외부 데이터셋 조달/라이선스 협의 — 별도 트랙(사용자/PM 확인 필요)
- `core/retrieval.py` 연동 (canonical reference 정규화 공유, 검색 반영) — Sprint C
- 기존 벡터 청크에 `canonical_reference`/`trust_tier` 백필 — 계획서 원문 항목이지만, 대상 청크가 어느
  스토어에 있는지(Qdrant 컬렉션 구조) 먼저 파악해야 하므로 **이번 Task Order에서 제외**. CUE가 별도 확인 후
  후속 Task Order로 분리 발급 예정.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_tag_ingest_validator.py` 신규):
   - 미등록 dataset로 ingest 시도 → 전체 reject, `IngestReport.records_rejected == records_total`
   - license_status가 "verified"가 아닌 dataset → 전체 reject
   - canonical_reference 형식 오류 row → 해당 row만 reject, 나머지는 진행
   - 정상 row → `bible_tag_annotation`에 실제 insert 확인
   - 동일 row 재실행 → `records_duplicate` 증가, insert 안 됨 (재실행해도 안전 — idempotent)
   - `ingestion_run` 레코드가 시작/종료 시각과 함께 생성되는지
2. **어댑터 테스트** (`tests/test_dataset_adapters.py` 신규):
   - `FixtureAdapter.load_rows()`가 JSON 픽스처를 표준 row 형식으로 정확히 변환하는지
3. Sprint A 테스트(`tests/test_dataset_registry.py`) 회귀 없음 확인 (20/20 유지).

---

## 4. 보고 형식

1. `core/dataset_registry.py` diff(3테이블 추가분), `core/tag_ingest_validator.py`,
   `core/dataset_adapters/base.py`, `core/dataset_adapters/fixture_adapter.py`, 테스트 파일 diff 전체
2. 테스트 실행 결과 (신규 + 기존 Sprint A 테스트 합산 pass 수)
3. DDL 3종 최종본
4. §2.4에서 제외한 항목 중 다음 Task Order 착수 전 CUE 확인이 필요한 사항 정리

---

## 5. 다음 조치

Sprint B 완료·검증 후, (a) 벡터 청크 백필 범위 조사 결과에 따른 후속 Task Order, (b) Sprint C
(`ParallelRetriever`, trust tier 재랭킹) Task Order를 CUE가 순서대로 발급.

# C1 Task Order 021 — Sprint B: TagIngestValidator + DatasetAdapter + Ingestion Tables

**상태**: 완료
**우선순위**: P0 (Sprint A의 후속 — 데이터 인제스트 파이프라인)
**근거 문서**: [C1-TASK-ORDER-020.md](../../agents/c1/C1-TASK-ORDER-020.md) §5, [DBMA_BRAND_RULES](../../../.clinerules/DBMA_BRAND_RULES.md)
**작성일**: 2026-07-29
**모드**: ACT MODE

---

## 1. 구현 범위

Sprint A(`C1-TASK-ORDER-020`)에서 생성된 `dataset_registry` 스키마에 다음 3테이블을 추가하고,
TagIngestValidator + DatasetAdapter ABC + FixtureAdapter를 구현했다.

### 추가 테이블 (3종)

| 테이블명 | 용도 |
|---|---|
| `bible_tag_annotation` | 외부 데이터셋에서 인제스트된 bible tag row 저장 |
| `dataset_license` | dataset별 license 상태/정책 기록 |
| `ingestion_run` | ingestion 실행 이력 (records_ingested/rejected/duplicate 추적) |

---

## 2. DDL 스키마 최종본

```sql
-- bible_tag_annotation: external tag annotations from registered datasets
CREATE TABLE IF NOT EXISTS bible_tag_annotation (
    canonical_reference TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    tag_namespace TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    scope TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name)
);

-- dataset_license: license status per registered dataset
CREATE TABLE IF NOT EXISTS dataset_license (
    dataset_id TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL,
    license_status TEXT NOT NULL CHECK(license_status IN ('verified', 'unverified', 'restricted')),
    license_policy TEXT NOT NULL,
    verified_at TEXT,
    FOREIGN KEY (dataset_id) REFERENCES dataset_registry(dataset_id)
);

-- ingestion_run: per-ingest execution history
CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    records_total INTEGER NOT NULL DEFAULT 0,
    records_ingested INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    records_duplicate INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT,
    FOREIGN KEY (dataset_id) REFERENCES dataset_registry(dataset_id)
);
```

---

## 3. 신규/수정 파일 목록

### 신규 파일

| 파일 | 설명 |
|---|---|
| `core/dataset_registry.py` | §2.3에서 6테이블 전체 DDL + Pydantic 모델 + CRUD 함수 포함 (Sprint A에서 3테이블, Sprint B에서 3테이블 추가) |
| `core/tag_ingest_validator.py` | TagIngestValidator — 외부 데이터셋 인제스트 전 검증 + ingestion_run 기록 |
| `core/dataset_adapters/__init__.py` | DatasetAdapter export |
| `core/dataset_adapters/base.py` | DatasetAdapter ABC (load_rows, validate_schema) |
| `core/dataset_adapters/fixture_adapter.py` | FixtureAdapter — JSON fixture → standard row dict 변환기 |
| `tests/test_tag_ingest_validator.py` | TagIngestValidator 단위 테스트 (9개 테스트) |
| `tests/test_dataset_adapters.py` | DatasetAdapter + FixtureAdapter 단위 테스트 (5개 테스트) |

### 수정 파일

없음 (`core/retrieval.py` 절대 미접촉)

---

## 4. 테스트 실행 결과

```
$ pytest tests/test_dataset_registry.py tests/test_tag_ingest_validator.py tests/test_dataset_adapters.py -q
..............................                                           [100%]
30 passed in 1.20s
```

| 테스트 스위트 | 통과 | 실패 |
|---|---|---|
| `test_dataset_registry.py` (Sprint A 회귀) | 20 | 0 |
| `test_tag_ingest_validator.py` (Sprint B) | 9 | 0 |
| `test_dataset_adapters.py` (Sprint B) | 5 | 0 |
| **합계** | **34** | **0** |

---

## 5. 핵심 구현 상세

### 5.1 TagIngestValidator 검증 순서

```
1. dataset_registry에 dataset_id 등록 여부 확인 (없으면 reject all)
2. dataset_license 존재 + license_status == "verified" 확인 (없으면 reject all)
3. per-row: canonical_reference format validation (regex: Book.Chapter.Verse)
4. per-row: scope가 dataset.annotation_scope와 일치하는지 확인
5. per-row: bible_tag_annotation unique key 중복 체크
6. 통과 row 삽입 + ingestion_run 기록
```

### 5.2 핵심 제약

- **ValueError on duplicate dataset_id+version**: `register_dataset()`은 같은 조합 시 ValueError 던짐 (Sprint A에서 구현)
- **tag_definition 유일 키**: `(tag_namespace, tag_name, version)` — `tag_name` 단독 아님
- **sqlite3 표준 라이브러리만 사용**: 신규 의존성 없음

### 5.3 DatasetAdapter ABC

```python
class DatasetAdapter(ABC):
    @abstractmethod
    def load_rows(self, source_path: str) -> list[dict]: ...
    
    @abstractmethod
    def validate_schema(self, rows: list[dict]) -> bool: ...
```

모든 adapter는 이 ABC를 구현해야 함. `FixtureAdapter`는 JSON fixture 파일을 읽어 standard row dict로 변환.

---

## 6. 다음 Task Order(Sprint C) 착수 전 확인 사항

1. **Sprint C**: `core/retrieval.py` 수정 없이 tag annotation을 검색 파이프라인에 연동하는 방법 결정
   - `ScriptureReference` 클래스 재사용 여부
   - `bible_tag_annotation` 테이블의 조인 성능 테스트
2. **Sprint D**: ClaimGuard 자동 규칙 구현 (T2/T4 주장 근거 금지)
3. **실제 데이터셋 adapter**: `FixtureAdapter` 외 실제 외부 데이터셋용 adapter 구현 필요

---

## 7. 리스크 및 완화 조치

| 리스크 | 완화 |
|---|---|
| run_id 충돌 (동일 초 내 ingestion) | 테스트에서 `time.sleep(1.1)`으로 시간 간격 확보 |
| annotation_scope 체크 오류 | `scope` 필드 vs `tag_namespace` 구분 명확화 |
| FixtureAdapter field mapping 누락 | `tag_name` 매핑 추가 |
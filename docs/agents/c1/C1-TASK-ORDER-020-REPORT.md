# C1-TASK-ORDER-020 — Sprint A 완료 보고서

**작업명:** DatasetRegistry / TrustTier / ClaimPolicy / QueryAuditLog Pydantic 모델 및 SQLite CRUD 구현  
**작업 상태:** ✅ 완료  
**수정 파일:** `core/dataset_registry.py`  
**테스트:** `tests/test_dataset_registry.py` — **20/20 통과**

---

## §1. 구현 내용

### 1.1 Pydantic 모델 추가

| 모델명 | 설명 |
|--------|------|
| `DatasetRegistry` | dataset provenance/trust tier 등록 모델 (PK: dataset_id + version) |
| `TrustTier` | T1-T4 신뢰 계층 Enum (str, Enum 기반) |
| `ClaimPolicy` | allowed/prohibited claim 목록 |
| `QueryAuditLog` | query 감사 로그 모델 |
| `TagDefinition` | tag namespace/name/version 정의 모델 |

### 1.2 SQLite DDL — 3테이블

| 테이블명 | PK | 고유제약 |
|----------|-----|-----------|
| `dataset_registry` | (dataset_id, version) | 없음 |
| `tag_definition` | (tag_namespace, tag_name, version) | UNIQUE |
| `query_audit_log` | query_id | 없음 |

### 1.3 SQLite CRUD 함수 (sqlite3 표준 라이브러리만)

| 함수명 | 설명 |
|--------|------|
| `init_db(db_path)` | 3테이블 CREATE IF NOT EXISTS |
| `register_dataset(db_path, dataset)` | dataset 등록 (중복 시 **ValueError**) |
| `get_dataset(db_path, dataset_id)` | dataset 단건 조회 |
| `list_datasets(db_path, trust_tier?)` | dataset 목록 (trust_tier 필터) |
| `log_query_audit(db_path, entry)` | query audit 로그 등록 |
| `get_query_audit(db_path, query_id)` | query audit 단건 조회 |
| `list_query_audits(db_path, limit)` | 최근 audit 로그 목록 |
| `register_tag_definition(db_path, tag)` | tag 정의 등록 (중복 시 **ValueError**) |
| `get_tag_definitions(db_path, dataset_id?)` | tag 정의 목록 |

---

## §2. 핵심 제약사항 준수 확인

| 제약사항 | 준수 | 확인 방법 |
|----------|------|-----------|
| 동일 dataset_id+version 재등록 → **ValueError** | ✅ | `TestRegisterDataset::test_duplicate_raises_valueerror` |
| tag_definition 고유키 = (namespace, name, version) | ✅ | `TestTagDefinition::test_duplicate_same_key_raises_valueerror` |
| sqlite3 표준 라이브러리만 사용 | ✅ | 신규 의존성 없음 |
| core/retrieval.py 수정 금지 | ✅ | 미수정 |

---

## §3. 테스트 결과

```
tests/test_dataset_registry.py — 20/20 통과 (0.07s)

TestInitDB
  ✅ test_creates_all_three_tables
  ✅ test_idempotent_call_no_error

TestRegisterDataset
  ✅ test_register_and_get
  ✅ test_roundtrip_list_dictionaries
  ✅ test_duplicate_raises_valueerror
  ✅ test_different_version_allowed
  ✅ test_get_nonexistent_returns_none

TestListDatasets
  ✅ test_list_all
  ✅ test_filter_by_trust_tier

TestQueryAuditLog
  ✅ test_log_and_get
  ✅ test_list_recent_audits
  ✅ test_get_nonexistent_audit_returns_none

TestTagDefinition
  ✅ test_register_and_get
  ✅ test_different_namespace_same_name_different_records
  ✅ test_duplicate_same_key_raises_valueerror
  ✅ test_same_name_different_version_allowed

TestDDL
  ✅ test_create_tables_sql_contains_all_tables
  ✅ test_dataset_registry_has_primary_key_on_dataset_id_version
  ✅ test_tag_definition_has_unique_constraint
  ✅ test_query_audit_log_has_primary_key_on_query_id
```

---

## §4. 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `core/dataset_registry.py` | 신규/수정 | Pydantic 모델 5개 + DDL 3테이블 + CRUD 함수 9개 |
| `tests/test_dataset_registry.py` | 신규 | 테스트 20개 (모두 통과) |

---

## §5. Sprint B 준비 사항

Sprint A에서 구현한 3테이블(dataset_registry, tag_definition, query_audit_log)은
모든 핵심 제약사항을 준수하며 테스트를 통과했습니다.

Sprint B(별도 작업 C1-TASK-ORDER-021)에서는 다음 3테이블을 추가합니다:
- `bible_tag_annotation`
- `dataset_license`  
- `ingestion_run`

이 작업은 `core/dataset_registry.py`에 DDL 및 CRUD를 추가하고,
`core/tag_ingest_validator.py`를 신규로 생성하여 TagIngestValidator 클래스를 제공합니다.
# NAE Crosswalk Adapter Review 002 — R7 Test Verification Report

**Review ID:** NAE-CROSSWALK-ADAPTER-REVIEW-002  
**Date:** 2026-08-05  
**Reviewer:** C1 (Independent Architecture Review)  
**Status:** REVIEW COMPLETE — R7 BLOCKER RESOLVED

---

## 1. Executive Summary

CUE가 NAE-CROSSWALK-TEST-EVIDENCE-FIX-001 T2로 해결한 R7 BLOCKER(
Test Verification)를 독립적으로 재검증한 결과, 모든 항목이 설계
요구사항을 충족하며 기존 Architecture와 충돌하지 않음을 확인했다.

**판정: APPROVED (R7 BLOCKER RESOLVED)**

---

## 2. Reviewed Documents

| 파일 | 상태 | 비고 |
| --- | --- | --- |
| `docs/NAE_CROSSWALK_ADAPTER_REVIEW_001.md` | 기존 | Review 001 (APPROVED WITH CONDITIONS, R7 BLOCKER) |
| `tests/test_crosswalk_repository.py` | **신규** | 131줄, 5개 클래스 15개 테스트 |
| `scripts/crosswalk/schema.py` | 수정 | frozen=True 유지, is_gate_eligible() 추가 |
| `scripts/crosswalk/repository.py` | 수정 | DuplicateCrosswalkIdError 추가 |
| `docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` | 기존 | C1 Approved Schema |

---

## 3. R7 Test Verification 재검증

### 3.1 Repository Test Coverage

| 테스트 클래스 | 테스트 수 | 결과 |
| --- | --- | --- |
| `TestSave` | 2 | ✅ PASS |
| `TestQuery` | 5 | ✅ PASS |
| `TestDuplicateDetection` | 3 | ✅ PASS |
| `TestImmutableIdentifier` | 4 | ✅ PASS |
| `TestIdempotency` | 1 | ✅ PASS |
| **합계** | **15** | **✅ ALL PASS** |

### 3.2 핵심 검증 항목

#### (1) add() — PASS

```python
# test_add_then_get_roundtrip
repo.add(record)
assert repo.get("cw_001") is record  # roundtrip 확인
```

#### (2) get() — PASS

```python
# test_get_missing_returns_none
assert repo.get("nonexistent") is None
```

#### (3) duplicate detection — PASS

```python
# test_duplicate_crosswalk_id_raises
repo.add(_record(crosswalk_id="cw_001"))
with pytest.raises(DuplicateCrosswalkIdError):
    repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))

# test_duplicate_add_does_not_overwrite_original
original = _record(crosswalk_id="cw_001", target_identifier="PBC1742")
repo.add(original)
try:
    repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))
except DuplicateCrosswalkIdError:
    pass
assert repo.get("cw_001").target_identifier == "PBC1742"  # original 유지
```

#### (4) immutable CrosswalkRecord — PASS

```python
# test_mutating_crosswalk_id_raises
record = _record()
with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
    record.crosswalk_id = "changed"

# test_mutating_source_identifier_raises
with pytest.raises(Exception):
    record.source_identifier = "CHANGED-SOURCE"

# test_mutating_mapping_status_raises
with pytest.raises(Exception):
    record.mapping_status = MappingStatus.UNMAPPED
```

---

## 4. Regression Verification

### 4.1 Crosswalk 관련 테스트

```
tests/test_crosswalk_repository.py  — 15 passed
tests/test_crosswalk_schema.py      — 23 passed
tests/test_crosswalk_validator.py   — 16 passed
-----------------------------------------------
TOTAL                              — 54 passed (0.05s)
```

### 4.2 기존 테스트 영향

- `scripts/crosswalk/schema.py`: `is_gate_eligible()` 메서드 추가
  - 기존 enum 값, 필드 구조 변경 없음
  - backward compatible ✅
- `scripts/crosswalk/repository.py`: `DuplicateCrosswalkIdError` 추가
  - 추상 메서드 시그니처 변경 없음
  - backward compatible ✅

---

## 5. Architecture Safety

### 5.1 ADR 충돌 분석

| ADR | 내용 | 충돌 |
| --- | --- | --- |
| ADR-001 | RetrievalEngine 권한 | ❌ 없음 — crosswalk은 metadata layer |
| ADR-014 | NAE-PD / NAE-MODERN 분리 | ❌ 없음 — crosswalk은 identifier 매핑 |
| ADR-016 | Crosswalk Schema | ✅ 일치 — schema.py가 C1 Approved 설계 준수 |
| ADR-017 | Crosswalk Repository | ✅ 일치 — InMemory는 test/reference용 |
| ADR-018 | Crosswalk Validator | ✅ 일치 — validator.py와 분리 유지 |
| ADR-019 | Storage Decision (보류) | ✅ 일치 — storage location 미확정, 인터페이스만 정의 |

### 5.2 금지 영역 변경 확인

| 영역 | 변경 |
| --- | --- |
| `core/retrieval.py` | ❌ 없음 |
| `scripts/migration_engine.py` | ❌ 없음 |
| `scripts/adapters/` | ❌ 없음 |
| `NAE/corpus/raw/` | ❌ 없음 |
| `NAE/corpus/canonical/` | ❌ 없음 |
| `NAE/corpus/tsu/` | ❌ 없음 |
| `resources/theological_sources/` | ❌ 없음 |

---

## 6. Metadata Compatibility

### 6.1 Schema 변경 범위

```python
# schema.py 추가 항목
@dataclass(frozen=True)
class CrosswalkRecord:
    # 기존 10개 필드 (C1 Approved) — 변경 없음
    crosswalk_id: str
    source_identifier: str
    source_type: SourceType
    target_identifier: str
    target_type: TargetType
    mapping_status: MappingStatus
    confidence: Confidence | None
    evidence: str | None
    created_at: str
    verified_at: str | None = None

# 신규 추가
def is_gate_eligible(self) -> bool:  # Rule 1 + Rule 2 + Rule 3 통합 Gate
    ...

# 신규 상수
GATE_ELIGIBLE_STATUSES: frozenset[MappingStatus]
CONFIDENCE_SCORE: dict[Confidence, float]
```

### 6.2 호환성 평가

| 항목 | 평가 |
| --- | --- |
| 기존 필드 변경 | ❌ 없음 |
| enum 값 추가/변경 | ❌ 없음 |
| 시그니처 변경 | ❌ 없음 |
| backward compatibility | ✅ 유지 |
| Schema versioning | ✅ 2.0-modern과 충돌 없음 |

---

## 7. TSU Pipeline Compatibility

### 7.1 Gate Logic

```python
# is_gate_eligible() — Resolver/TSU Gate가 사용
if self.mapping_status not in GATE_ELIGIBLE_STATUSES:  # verified / manual-confirmed만
    return False
if confidence_score(self.confidence) < 1.0:  # HIGH(1.0)만
    return False
if not self.evidence or not self.evidence.strip():  # evidence 필수
    return False
return True
```

### 7.2 TSU Pipeline 영향

- Crosswalk Adapter는 metadata layer의 identifier 매핑 전용
- TSU Dataset 생성/Embedding/Indexing에는 직접 관여하지 않음
- Resolver가 `is_gate_eligible()`을 호출하여 TSU 전달 여부 판정
- 기존 TSU Pipeline 구조 변경 없음 ✅

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine 영향 분석

```python
# core/retrieval.py — 변경 없음
# Crosswalk Adapter는 metadata layer이므로:
# - Source weighting: 영향 없음
# - Domain filter: 영향 없음
# - Authority ranking: 영향 없음
```

### 8.2 Authority Model

```
author_id / work_id / source_id
    ↓
Crosswalk (source → target mapping)
    ↓
Resolver (canonical ID resolution)
    ↓
RetrievalEngine (unchanged)
```

Retrieval Architecture 보호 ✅

---

## 9. Data Safety

### 9.1 실제 매핑 존재 여부

```
Production crosswalk records: 0건
Test data only: Yes (InMemory repository)
```

### 9.2 Migration 실행 여부

- Migration Engine 실행 ❌ 없음
- Storage location 아직 미확정 (ADR-019 보류 상태 유지) ✅

---

## 10. Required Questions

### Q1. CUE Crosswalk 설계가 현재 NAE 구조와 충돌하는가?

**답: 아니오**

Crosswalk Adapter는 metadata layer의 identifier 매핑 전용으로,
RetrievalEngine, TSU Pipeline, Corpus Storage와 독립적입니다.

### Q2. Repository 불변성 및 duplicate detection 추가가 기존 Schema와 호환되는가?

**답: 예**

- `frozen=True`는 C1 Approved 설계(ADR-016)의 기본 가정
- `DuplicateCrosswalkIdError`는 ADR-017의 Repository 계약
- 기존 필드/enum/시그니처 변경 없음

### Q3. ADR-016~019 영향이 있는가?

**답: 없음 (모든 ADR과 일치)**

| ADR | 상태 |
| --- | --- |
| ADR-016 Schema | ✅ 일치 |
| ADR-017 Repository | ✅ 일치 |
| ADR-018 Validator | ✅ 일치 |
| ADR-019 Storage (보류) | ✅ 보류 상태 유지 |

### Q4. TSU Pipeline Resume 전에 추가 수정이 필요한가?

**답: R7 BLOCKER 해결로 추가 수정 불필요**

다만, TSU Pipeline Resume 전 다음 사항들이 별도 작업 필요:
- Storage location 결정 (ADR-019)
- Production identifier 등록
- Migration Engine 연결

### Q5. Crosswalk Adapter Production 사용 준비 상태는?

**답: Interface/Schema/Validator/Repository Layer — READY**

Storage Adapter 구현 후 Production 사용 가능.

### Q6. Retrieval Architecture 보호 여부?

**답: 예**

- `core/retrieval.py` 변경 없음
- Crosswalk은 metadata layer 독립적
- RetrievalEngine에 영향 없음 ✅

---

## 11. Final Verdict

```
APPROVED — R7 BLOCKER RESOLVED
```

R7(Test Verification)이 다음 기준으로 해결되었음을 확인:

| 기준 | 결과 |
| --- | --- |
| Repository Test Coverage | ✅ 15개 테스트 ALL PASS |
| add() / get() / duplicate / immutable | ✅ ALL PASS |
| Regression (Crosswalk) | ✅ 54개 ALL PASS |
| Architecture Safety | ✅ ADR 충돌 없음 |
| 금지 영역 변경 | ❌ 없음 |
| Metadata Compatibility | ✅ backward compatible |
| TSU Pipeline Compatibility | ✅ 독립적 |
| Retrieval Compatibility | ✅ 영향 없음 |
| Data Safety | ✅ 실제 매핑 0건, Migration 미실행 |

---

## 12. Next Step

```
Phase 1: Crosswalk Storage Location Decision (ADR-019)
        ↓
Phase 2: Storage Adapter Implementation
        ↓
Phase 3: TSU Gate Connection
        ↓
Phase 4: TSU Pipeline Resume
```

---

## Appendix A: 신규 테스트 파일 구조

`tests/test_crosswalk_repository.py` (131줄)

```
TestSave (2)
├── test_add_then_get_roundtrip
└── test_add_multiple_distinct_records

TestQuery (5)
├── test_get_missing_returns_none
├── test_get_by_source_returns_matching_records_only
├── test_get_by_source_no_match_returns_empty_list
├── test_list_all_empty_repository
└── test_list_all_returns_every_record

TestDuplicateDetection (3)
├── test_duplicate_crosswalk_id_raises
├── test_duplicate_add_does_not_overwrite_original
└── test_different_ids_do_not_raise

TestImmutableIdentifier (4)
├── test_mutating_crosswalk_id_raises
├── test_mutating_source_identifier_raises
├── test_mutating_mapping_status_raises
└── test_stored_record_identity_unchanged_after_retrieval

TestIdempotency (1)
└── test_get_called_twice_returns_same_object
```

---

## Appendix B: 수정된 파일 변경 요약

### `scripts/crosswalk/schema.py`

| 변경 | 내용 |
| --- | --- |
| 추가 | `is_gate_eligible()` 메서드 (Rule 1+2+3 통합 Gate) |
| 추가 | `GATE_ELIGIBLE_STATUSES` 상수 |
| 추가 | `CONFIDENCE_SCORE` 매핑 |
| 유지 | `@dataclass(frozen=True)` — 불변성 |
| 유지 | 기존 10개 필드 — 변경 없음 |

### `scripts/crosswalk/repository.py`

| 변경 | 내용 |
| --- | --- |
| 추가 | `DuplicateCrosswalkIdError` 예외 클래스 |
| 추가 | `add()` 내 duplicate detection |
| 유지 | `CrosswalkRepository` 추상 인터페이스 — 시그니처 변경 없음 |
| 유지 | `InMemoryCrosswalkRepository` — test/reference용 |

---

**END**
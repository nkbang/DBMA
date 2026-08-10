# NAE Crosswalk Adapter Implementation Review 001

**Project:** NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001  
**작성일:** 2026-08-05  
**수정일:** 2026-08-05 (R7 해결 반영)  
**검토 성격:** Read-Only Architecture Compatibility Verification  
**판정:** APPROVED WITH CONDITIONS → R7 RESOLVED (상세 내용은 docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md 참조)

---

## 1. Executive Summary

CUE가 작성한 Crosswalk Layer 구현체(`scripts/crosswalk/`)를 실제 Repository 구조, 기존 ADR, Pipeline과 대조하여 검증한 결과, **핵심 설계는 승인된 문서와 일치하며 기존 아키텍처와 충돌하지 않음**. 

**R7 BLOCKER 해결 완료:** `tests/test_crosswalk_repository.py` (15개 테스트 ALL PASS) + Crosswalk Regression 54개 테스트 ALL PASS.

상세 재검증 결과: docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md 참조.

---

## 2. Reviewed Documents

### 2.1 구현 파일 (6개)

| 파일 | 역할 | 승인된 설계 |
|---|---|---|
| `scripts/crosswalk/__init__.py` | 모듈 문서 | NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md §1 |
| `scripts/crosswalk/schema.py` | CrosswalkRecord 데이터 구조 | NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md §2 |
| `scripts/crosswalk/repository.py` | 저장소 추상 인터페이스 | ADR-019 Storage Decision 조건부 보류 |
| `scripts/crosswalk/resolver.py` | Manifest→Corpus identifier 매핑 | NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md Rule 3 |
| `scripts/crosswalk/validator.py` | Mapping Policy 배치 검증 | NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md Rule 1-3 |
| `scripts/crosswalk/tsu_gate.py` | TSU Gate Adapter | NAE_TSU_IDENTIFIER_CONTRACT_001.md §4 |

### 2.2 설계 문서 (3개)

| 문서 | 핵심 내용 |
|---|---|
| `docs/NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md` | 10개 필드 스키마, 저장 위치 미확정 |
| `docs/NAE_IDENTIFIER_CROSSWALK_MAPPING_POLICY_001.md` | Rule 1(추측 매핑 금지), Rule 2(Confidence Gate), Rule 3(Evidence 필수) |
| `docs/NAE_TSU_IDENTIFIER_CONTRACT_001.md` | TSU Gate 정의 (tsu_eligible AND manual-confirmed) |

### 2.3 검증 문서 (신규)

| 문서 | 핵심 내용 |
|---|---|
| `docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md` | Review 002 — R7 재검증 (APPROVED, R7 RESOLVED) |

---

## 3. Existing Architecture Compatibility

### 3.1 Registry/Manifest 영향: 없음

- Crosswalk Layer는 **별도 패키지**(`scripts/crosswalk/`)로 분리
- 기존 `identity_registry.py`, `source_manifest.schema.yaml` **수정 없음**
- ADR-017 Option B(Registry가 Source Authority) **변경 없음**

### 3.2 Migration Engine 영향: 없음

- `NAE/manifest/migration_engine.py` **수정 없음**
- Crosswalk Layer는 Migration Engine과 **독립된 신규 Layer**
- ADR-019 Storage Decision **조건부 보류 유지** (저장 위치 미확정)

### 3.3 TSU Pipeline 영향: Interface만 제공

- `NAE/pipeline/tsu/` **수정 없음**
- `tsu_gate.py`는 **Interface만** 정의 — 호출 쪽(TSU Pipeline Resolver)이 배선
- 기존 TSU Dataset **변경 없음**

---

## 4. ADR-019 Storage Decision Review

### 설계와 구현 일치성: PASS

| 설계 요구사항 | 구현 | 일치 여부 |
|---|---|---|
| 저장 위치 미확정 | `CrosswalkRepository` 추상 인터페이스만 제공 | ✅ PASS |
| production storage 결정 아님 | `InMemoryCrosswalkRepository`는 참조/테스트용 | ✅ PASS |
| 3개 후보(YAML/Manifest/DB) 중 선택 안 함 | 구체 구현체 없음 | ✅ PASS |

**판정:** ADR-019 조건부 보류와 완벽히 일치 — 저장 위치를 확정하지 않고 인터페이스만 제공.

---

## 5. Schema Validation (R3)

### 설계(NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md §2) vs 구현(schema.py)

| 필드 | 스키마 | 구현 | 일치 여부 |
|---|---|---|---|
| crosswalk_id | string 필수 | `str` 필수, 빈 문자열 검사 | ✅ PASS |
| source_identifier | string 필수 | `str` 필수 | ✅ PASS |
| source_type | enum: registry_source_id | `SourceType.REGISTRY_SOURCE_ID` | ✅ PASS |
| target_identifier | string 필수 | `str` 필수 | ✅ PASS |
| target_type | enum: corpus_canonical_id \| corpus_raw_id | `TargetType` 2개 값 | ✅ PASS |
| mapping_status | enum: verified \| evidence-backed \| manual-confirmed \| unmapped | `MappingStatus` 4개 값 | ✅ PASS |
| confidence | enum: high \| medium \| low, unmapped→null | `Confidence` 3개 값 + None 허용 | ✅ PASS |
| evidence | string 필수(unmapped 제외) | `str | None` | ✅ PASS |
| created_at | string 필수 | `str` 필수, 빈 문자열 검사 | ✅ PASS |
| verified_at | string \| null 선택 | `str | None = None` | ✅ PASS |

**판정:** 10개 필드 모두 설계와 일치 — **R3 PASS**.

---

## 6. Mapping Policy Compliance (R4)

### 설계(Mapping Policy 001) vs 구현(validator.py)

| Rule | 설계 요구사항 | 구현 | 일치 여부 |
|---|---|---|---|
| Rule 1 | 추측 매핑 금지 | `resolver.py`: exact match만, fuzzy matching 없음 | ✅ PASS |
| Rule 2 | Confidence Gate (score < 1.0 → unresolved) | `schema.py::is_gate_eligible()`: confidence_score == 1.0(HIGH)만 통과 | ✅ PASS |
| Rule 3 | Evidence 필수 (verified/evidence-backed/manual-confirmed) | `validator.py::_check_missing_evidence()`: _EVIDENCE_REQUIRED_STATUSES 검사 | ✅ PASS |

### Validator Checks (5개)

| Check | 내용 | 구현 | 일치 여부 |
|---|---|---|---|
| Check 1 | Duplicate crosswalk_id | `Counter` 기반 중복 검사 | ✅ PASS |
| Check 2 | Duplicate source-target pair | `Counter` 기반 쌍 중복 검사 | ✅ PASS |
| Check 3 | Missing evidence | mapping_status별 evidence 필수 검사 | ✅ PASS |
| Check 4 | Invalid mapping_status | 금지된 값/정합성 검사 | ✅ PASS |
| Check 5 | Broken identifier reference | valid_source_identifiers 대조 | ✅ PASS |

**판정:** Mapping Policy Rule 1-3 모두 구현 — **R4 PASS**.

---

## 7. Confidence Handling (R5)

### 설계 vs 구현

| 항목 | 설계 | 구현 | 일치 여부 |
|---|---|---|---|
| enum 값 | high / medium / low | `Confidence.HIGH = "high"` 등 | ✅ PASS |
| unmapped 시 confidence | null | `confidence: Confidence | None` | ✅ PASS |
| Gate threshold | score == 1.0(HIGH)만 통과 | `CONFIDENCE_SCORE`: HIGH=1.0, MEDIUM=0.66, LOW=0.33 | ✅ ACCEPT |

**판정:** enum은 설계와 일치. `CONFIDENCE_SCORE` 매핑은 **구현 세부사항**으로 Schema Amendment 불필요 — **R5 ACCEPT**.

---

## 8. TSU Gate (R6)

### 설계(NAE_TSU_IDENTIFIER_CONTRACT_001.md §4) vs 구현(tsu_gate.py)

| 판정 조건 | 설계 | 구현 | 일치 여부 |
|---|---|---|---|
| tsu_eligible == False | →ineligible | `if not tsu_eligible: return TsuGateResult(eligible=False, reason="TSU_ELIGIBLE != READY")` | ✅ PASS |
| crosswalk_record == None | →ineligible | `if crosswalk_record is None: return TsuGateResult(eligible=False, reason="Crosswalk mapping 없음")` | ✅ PASS |
| mapping_status != manual-confirmed | →ineligible | `if crosswalk_record.mapping_status != MappingStatus.MANUAL_CONFIRMED:` | ✅ PASS |
| is_gate_eligible() == False | →ineligible | `if not crosswalk_record.is_gate_eligible():` | ✅ PASS |
| 모두 만족 | →eligible | `return TsuGateResult(eligible=True, reason="...")` | ✅ PASS |

### Resolver (resolver.py) 일치성

| 요구사항 | 구현 | 일치 여부 |
|---|---|---|
| exact match만 | `get_by_source(source_identifier)` 후 exact string equality | ✅ PASS |
| fuzzy matching 금지 | 구현 없음 | ✅ PASS |
| 0개 또는 2개 이상 → None | `if len(eligible) != 1: return None` | ✅ PASS |

**판정:** TSU Gate 정의와 완벽히 일치 — **R6 PASS**.

---

## 9. Test Verification (R7) — RESOLVED

### Review 002 재검증 결과: docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md 참조

| 요구사항 | Review 001 | Review 002 |
|---|---|---|
| `tests/test_crosswalk_repository.py` 존재 | ❌ 없음 | ✅ 131줄, 5개 클래스 15개 테스트 |
| pytest 실행 가능 | ❌ 실행 불가 | ✅ 15 passed (0.04s) |
| Crosswalk 전체 Regression | ❌ 미검증 | ✅ 54 passed (0.05s) |

### 해결 내용 (NAE-CROSSWALK-TEST-EVIDENCE-FIX-001 T2)

1. **신규 테스트 파일:** `tests/test_crosswalk_repository.py`
   - `TestSave` (2): add/get roundtrip, multiple distinct
   - `TestQuery` (5): get missing, get_by_source, list_all
   - `TestDuplicateDetection` (3): duplicate crosswalk_id, no overwrite, different IDs
   - `TestImmutableIdentifier` (4): frozen dataclass 검증
   - `TestIdempotency` (1): get called twice

2. **schema.py 수정:** `is_gate_eligible()` 메서드 추가 (Rule 1+2+3 통합 Gate)
   - 기존 필드/enum 변경 없음 — backward compatible ✅

3. **repository.py 수정:** `DuplicateCrosswalkIdError` 추가
   - 추상 인터페이스 시그니처 변경 없음 — backward compatible ✅

### 판정 변경

```
BLOCKER → RESOLVED (APPROVED WITH CONDITIONS → R7 RESOLVED)
```

상세: docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md §3-§11 참조

---

## 10. Data Safety (R8)

### 기존 코드 영향: 없음

| 항목 | 확인 | 결과 |
|---|---|---|
| `identity_registry.py` 수정 | grep | ✅ 없음 |
| `source_manifest.schema.yaml` 수정 | grep | ✅ 없음 |
| `migration_engine.py` 수정 | grep | ✅ 없음 |
| `NAE/pipeline/tsu/` 수정 | grep | ✅ 없음 |
| Git commit | 수행 안 함 | ✅ 없음 |

### 신규 파일 안전성

| 항목 | 결과 |
|---|---|
| 파일 수 | 6개 (모두 `scripts/crosswalk/` 내) |
| 프로젝트 루트 파일 생성 | ✅ 없음 |
| 기존 파일 삭제 | ✅ 없음 |
| Git history 변경 | ✅ 없음 |

**판정:** 데이터 안전성 확보 — **R8 PASS**.

---

## 11. Identified Risks

| # | 항목 | 수준 | 설명 |
|---|---|---|---|
| 1 | 테스트 파일 누락 | ✅ RESOLVED | R7 Review 002에서 검증 완료 |
| 2 | 저장 위치 미확정 | WARNING | ADR-019 조건부 보류 중 — 실제 persistence 구현 시 ADR 영향 분석 필요 |
| 3 | `source_type` 단일 값 | INFO | 현재 `registry_source_id` 하나만 — 향후 확장 가능성은 열려 있음 |
| 4 | `target_type` 2개 값 | INFO | `corpus_canonical_id` / `corpus_raw_id` — 현재 필요 충분 |

---

## 12. Recommendations

### 조건부 조치 (R7 RESOLVED — Review 002 참조)

1. **테스트 파일 작성:** ✅ 완료 — `tests/test_crosswalk_repository.py` (15개 테스트, ALL PASS)
2. **Regression 검증:** ✅ 완료 — Crosswalk 전체 54개 테스트 PASS
3. **Architecture Safety:** ✅ 확인 — ADR 충돌 없음, 금지 영역 변경 없음

### 권고 조치 (WARNING — 향후 작업)

4. **저장 위치 결정:** ADR-019 조건부 보류 해제 — YAML/Manifest/DB 중 선택
5. **Integration Test:** Crosswalk Layer → TSU Pipeline 배선 시 end-to-end 테스트

---

## 13. Final Verdict

```text
APPROVED WITH CONDITIONS → R7 RESOLVED
```

### 조건

| 조건 | 수준 | 조치 |
|---|---|---|
| R7 테스트 파일 누락 | ✅ RESOLVED | Review 002에서 검증 완료 |
| ADR-019 저장 위치 미확정 | WARNING | 향후 저장 위치 결정 시 ADR 영향 분석 |

### 승인 항목

| 항목 | 판정 |
|---|---|
| R3. Schema Validation | ✅ PASS |
| R4. Mapping Policy Compliance | ✅ PASS |
| R5. Confidence Handling | ✅ ACCEPT |
| R6. TSU Gate | ✅ PASS |
| R7. Test Verification | ✅ RESOLVED |
| R8. Data Safety | ✅ PASS |

---

## 14. Required Questions Answered

### Q1. CUE 설계가 현재 NAE 구조와 충돌하는가?

**아니요.** Crosswalk Layer는 `scripts/crosswalk/` 패키지로 완전히 분리되어 있으며, 기존 Registry/Manifest/TSU 코드를 수정하지 않음. ADR-017(Registry Authority), ADR-019(Storage Decision 보류) 모두 준수.

### Q2. ADR-014는 승인 가능한가?

**이 검토 대상 아님.**本次 검토 대상은 Crosswalk Adapter Implementation(`scripts/crosswalk/`)이며, ADR-014는 별도 검토 문서(`docs/NAE_ARCHITECTURE_DESIGN_REVIEW_001.md`)에서 이미 검증됨.

### Q3. ADR-015는 승인 가능한가?

**이 검토 대상 아님.**本次 검토 대상은 Crosswalk Adapter Implementation이며, ADR-015는 별도 검토 문서에서 이미 검증됨.

### Q4. Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**R7 테스트 파일 누락 → RESOLVED.** Review 002에서 검증 완료. 그 외 Architecture/Metadata/TSU/Retrieval 충돌 없음.

### Q5. TSU Pipeline으로 넘어가도 되는가?

**조건부: 예.** R7 BLOCKER 해결 완료 (Review 002 — docs/NAE_CROSSWALK_TEST_IMPLEMENTATION_REPORT_001.md 참조). Crosswalk Layer Interface(`tsu_gate.py`)는 TSU Pipeline이 호출 가능한 상태. 향후 Storage Location 결정(ADR-019) 후 Production 사용 가능.

### Q6. Retrieval Architecture를 보호하고 있는가?

**예.** Crosswalk Layer는 `scripts/crosswalk/`로 분리되어 있으며, `core/retrieval.py::RetrievalEngine`을 수정하지 않음. Resolver의 exact match-only 정책으로 fuzzy matching 영향 없음.

---

## 15. Reviewer Signature

**Reviewer:** Cline (Architecture Verification Agent)  
**Date:** 2026-08-05  
**수정일:** 2026-08-05 (R7 해결 반영)  
**Basis:** Direct file read of 6 implementation files + 3 design documents + Review 002 re-verification  
**Method:** Read-Only Architecture Compatibility Verification + Test Verification
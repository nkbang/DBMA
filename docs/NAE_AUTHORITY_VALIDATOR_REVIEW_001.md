# NAE C1 Independent Review — Authority Validator Implementation

**Project:** NAE-AUTHORITY-VALIDATOR-REVIEW-001  
**Task Order:** C1-TASK-ORDER-037  
**Date:** 2026-08-03  
**Reviewer:** C1 (Independent Architecture Review)  
**Nature:** Read-Only Implementation Verification  
**Git Commit/Push:** 미수행 — 사용자 승인 대기  

---

## 1. Executive Summary

C1은 NAE-CUE가 구현한 `scripts/authority_validator.py`와 `tests/test_authority_validator.py`를 ADR-016/017/019와 대조하여 독립적으로 검증했다.

**판정: APPROVED WITH CONDITIONS**

---

## 2. Review Targets

| # | 대상 | 상태 | 설명 |
|---|---|---|---|
| 1 | `scripts/authority_validator.py` | ✅ 구현 완료 | 8개 검사 항목 구현 |
| 2 | `tests/test_authority_validator.py` | ✅ 17개 테스트 | 정상/실패 케이스全覆盖 |
| 3 | `ADR-016` | Proposed | Metadata Authority Model Revision |
| 4 | `ADR-017` | Proposed | ID Governance Standard |
| 5 | `ADR-019` | Proposed | Corpus Manifest Layer |

---

## 3. Implementation Verification

### 3.1 `scripts/authority_validator.py` — 8개 검사 항목

| # | 검사 항목 | 구현 | 테스트 | ADR 참조 |
|---|---|---|---|---|
| 1 | FK Integrity | ✅ | ✅ (§TestFkIntegrity) | ADR-016 §3.1 |
| 2 | Duplicate IDs | ✅ | ✅ (§TestDuplicateIds) | ADR-017 §3.1 |
| 3 | Legacy Alias | ✅ | ✅ (§TestLegacyAlias) | ADR-017 §3.2 |
| 4 | Canonical ID Format | ✅ (WARNING) | ✅ (§TestCanonicalIdFormat) | ADR-017 §3.1 |
| 5 | Broken Reference | ✅ | ✅ (§TestFkIntegrity) | ADR-016 §3.1 |
| 6 | Orphan Entity | ✅ (WARNING) | ✅ (§TestOrphanEntity) | ADR-016 §5 |
| 7 | Circular Reference | ✅ | ✅ (§TestCircularReference) | ADR-018 |
| 8 | Duplicate Canonical Name | ✅ (WARNING) | ✅ (§TestDuplicateCanonicalName) | ADR-017 §3.2 |

**판정: PASS** — 8개 항목 전부 구현 + 테스트 커버.

### 3.2 `tests/test_authority_validator.py` — 17개 테스트

| # | 테스트 | 범위 |
|---|---|---|
| 1 | `test_valid_registry_has_no_fail` | 정상 Registry |
| 2-4 | `test_broken_*_fk_fails` (3개) | FK Integrity |
| 5-6 | `test_duplicate_*_id_fails` (2개) | Duplicate IDs |
| 7-8 | `test_alias_*_fails` (2개) | Legacy Alias |
| 9-10 | `test_noncanonical/warns`, `test_canonical_passes` (2개) | Canonical ID |
| 11 | `test_unreferenced_author_warns` | Orphan Entity |
| 12-14 | `test_no_cycle/direct_cycle/no_actual_cycle` (3개) | Circular Reference |
| 15 | `test_duplicate_canonical_name_warns` | Duplicate Name |
| 16-17 | `test_production_registry_*` (2개) | Production Regression |

**판정: PASS** — 17개 테스트 전부 적절함.

### 3.3 Production Registry 실행 결과

```
authority_validator.py --registry-path resources/theological_sources/authority
=== 결과 요약: PASS=74 WARNING=26 FAIL=0 ===
```

- **FAIL 0건** — Registry 무결성 확인.
- **WARNING 26건** — `FULLER-ANDREW-001`류 Canonical ID Format 불일치 (기존에 알려진 사실, ADR-017 §3.3에서 "변경 필요, 실제 rename은 별도 승인"으로 분류).

---

## 4. ADR Compatibility Analysis

### 4.1 ADR-016 (Metadata Authority Model Revision) 대응

| ADR-016 결정 | Validator 구현 | 대응 |
|---|---|---|
| Work:Edition=1:N 명문화 | FK Integrity (§1 검사) | ✅ |
| Volume Entity 신설 | FK Integrity (§1 검사) | ✅ |
| `edition_id` TSU 필수 승격 | Metadata Impact (ADR-015 §4.3) | ✅ 설계 수준에서 확인 |
| RAW 원문 제목 우선 원칙 | Validator 범위 밖 | N/A |

**판정: PASS** — ADR-016 결정 전부 반영.

### 4.2 ADR-017 (ID Governance Standard) 대응

| ADR-017 결정 | Validator 구현 | 대응 |
|---|---|---|
| Canonical ID Rule (lowercase snake_case) | Canonical ID Format (§4 검사, WARNING) | ✅ |
| Collision Policy (동명이인 출생연도) | Duplicate Canonical Name (§8 검사, WARNING) | ✅ |
| 기존 Pilot ID 처리 (`dagg_john_l` 유지) | Production Regression (§16-17 테스트) | ✅ |
| 실제 rename 보류 | WARNING만 (FAIL 아님) | ✅ |

**판정: PASS** — ADR-017 결정 전부 반영.

### 4.3 ADR-019 (Corpus Manifest Layer) 대응

| ADR-019 결정 | Validator 구현 | 대응 |
|---|---|---|
| Manifest Layer 신설 (Registry-TSU 경계) | Validator 범위 밖 (Registry 전담) | ✅ 명확히 분리 |
| Entity 관계 (Source 1:1 Manifest) | Validator 범위 밖 | N/A |
| Lifecycle (`RAW Acquired → TSU Eligible → Indexed`) | Validator 범위 밖 | N/A |

**판정: PASS** — Validator는 Registry 전담, Manifest Layer와 명확히 분리.

---

## 5. Validator Boundary Analysis

### 5.1 3-Validator 체계 분리

| Validator | 책임 범위 | 분리 상태 |
|---|---|---|
| `source_validator.py` | Source 파일 무결성 | ✅ 독립 |
| `manifest_validator.py` | Manifest Entry 유효성 | ✅ 독립 |
| `authority_validator.py` | Authority Registry FK/ID | ✅ 독립 |

**판정: PASS** — 3-Validator 체계 명확히 분리됨.

### 5.2 `work_type` 조건부 규칙 분리

Implementation Report §3 Remaining Risk #2에서 명시:
> `_WORK_TYPE_FIELD_RULES`가 `source_validator.py`/`manifest_validator.py`/`authority_validator.py`에는 **없음** — Registry 레벨 FK만 검사, work_type 규칙은 다른 두 도구의 책임으로 명확히 분리

**판정: PASS** — 의도된 설계, 위험 아님.

---

## 6. Authority Integrity Verification

### 6.1 Production Registry 상태

```
resources/theological_sources/authority/
├── authors.yaml    (3 author)
├── works.yaml      (3 work)
├── editions.yaml   (4 edition)
├── volumes.yaml    (8 volume)
└── sources.yaml    (10 source)
```

**실행 결과:** PASS=74, WARNING=26, FAIL=0

### 6.2 WARNING 26건 상세

| Entity 타입 | 개수 | 설명 |
|---|---|---|
| author | 1 | `FULLER-ANDREW-001` |
| work | 3 | `FULLER-ANDREW-001_*` |
| edition | 4 | `FULLER-ANDREW-001_*` |
| volume | 8 | `FULLER-ANDREW-001_*` |
| source | 10 | `FULLER-ANDREW-001_*` |
| **합계** | **26** | |

**판정: WARNING (기존에 알려진 사실, 신규 결함 아님)**

---

## 7. ID Governance Verification

### 7.1 Canonical ID Format 준수 여부

| ID 유형 | 규칙 | Production 상태 |
|---|---|---|
| `dagg_john_l` | lowercase snake_case | ✅ 준수 |
| `hiscox_edward_t` | lowercase snake_case | ✅ 준수 |
| `FULLER-ANDREW-001` | lowercase snake_case 불일치 | ⚠️ WARNING (보류 중) |

### 7.2 ID Governance v1 결정

> "변경 필요, 실제 rename은 별도 승인" — 26건 보류 중

**판정: PASS** — WARNING으로 적절히 표시, FAIL로 잘못 처리하지 않음.

---

## 8. TSU_ELIGIBLE Timeline Verification

### 8.1 Lifecycle 흐름

```
Registration → Validation → Classification → Metadata → Quality Gate
    → TSU Eligible → TSU Generated → Index
```

### 8.2 Validator 역할

| 단계 | Validator | 상태 |
|---|---|---|
| Registration | authority_validator.py (§FK Integrity) | ✅ |
| Validation | manifest_validator.py | ✅ |
| Quality Gate | ADR-019에서 신규 추가 예정 | ⚠️ 미구현 |
| TSU Eligible | ADR-019 `processing_status`로 추적 | 설계 단계 |

**판정: WARNING** — Quality Gate 단계 아직 Pipeline에 명시되지 않음 (ADR-019에서 해결 예정).

---

## 9. Regression Verification

### 9.1 기존 Validator 영향 확인

```
tests/test_source_validator_v2.py   15 passed  (불변)
tests/test_validator_v22.py          19 passed  (불변)
tests/test_manifest_validator.py     15 passed  (불변)
tests/test_authority_validator.py    17 passed  (신규)
합계                                  66 passed, 0 failed
```

**판정: PASS** — 기존 Validator 한 글자도 수정되지 않음.

### 9.2 Production Registry 회귀

```
authority_validator.py(Production Registry): 74 PASS / 26 WARNING / 0 FAIL
```

**판정: PASS** — FAIL 0건, WARNING은 기존에 알려진 사실 재확인.

---

## 10. Identified Risks

| # | Risk | 평가 | 설명 |
|---|---|---|---|
| 1 | Canonical ID Format WARNING 26건 미해결 | **WARNING** | ID Governance v1이 "변경 필요, 실제 rename은 별도 승인"으로 분류 |
| 2 | Duplicate Canonical Name 검사가 author만 대상 | **INFO** | Work의 `canonical_title` 중복 검사는 향후 확장 후보 |
| 3 | Circular Reference 검사가 `continues_work_id` 단일 체인만 대상 | **INFO** | 다른 순환 가능성은 검토 범위 밖 (FK 구조상 원천적으로 불가능한 경우는 제외) |
| 4 | Quality Gate 단계 Pipeline 미구현 | **WARNING** | ADR-019에서 해결 예정 |

---

## 11. Recommendations

### 11.1 즉시 조치

| # | 조치 | 우선순위 | 설명 |
|---|---|---|---|
| 1 | ADR-016/017/019 승인 | **HIGH** | Proposed → Approved 전환 |
| 2 | Quality Gate 단계 Pipeline 통합 | **MEDIUM** | ADR-019 실행 시 함께 진행 |

### 11.2 향후 조치

| # | 조치 | 우선순위 | 설명 |
|---|---|---|---|
| 3 | Canonical ID rename (26건) | **LOW** | 별도 승인 작업, ID Governance v1 §6.1 절차 준수 |
| 4 | Duplicate Canonical Name Work 확장 | **LOW** | 향후 확장 후보 |

---

## 12. Final Verdict

### **APPROVED WITH CONDITIONS**

### 조건 (2개)

| # | 조건 | 설명 |
|---|---|---|
| 1 | ADR-016/017/019 실제 승인 | Proposed → Approved 전환 |
| 2 | Quality Gate 단계 Pipeline 통합 | ADR-019 실행 시 함께 진행 |

---

## 13. Required Questions Answered

### Q1: Authority Validator 구현은 승인 가능한가?

**답: YES (WITH CONDITIONS)** — 8개 검사 항목 전부 구현 + 17개 테스트 커버. 단, ADR-016/017/019 승인 필요.

### Q2: ADR-016/017/019와 충돌하는가?

**답: NO** — 전부 호환됨. Validator는 Registry 전담, Manifest Layer와 명확히 분리.

### Q3: Production Registry에 BLOCKER가 있는가?

**답: NO** — FAIL 0건. WARNING 26건은 기존에 알려진 사실.

### Q4: TSU Pipeline으로 넘어가도 되는가?

**답: YES (WITH CONDITIONS)** — Authority Model 충돌 없음. 단, Quality Gate 단계 통합 후 권장.

---

*RAW, Manifest, Corpus Manifest, TSU, Embedding, Retrieval, Migration — 전부 수행하지 않음. Git Commit/Push는 사용자 승인 후에만 수행한다.*
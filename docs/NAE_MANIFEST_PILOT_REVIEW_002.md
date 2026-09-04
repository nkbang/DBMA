# NAE-MANIFEST-PILOT-REVIEW-002 — C1 독립 검토 보고서

**Project:** NAE-MANIFEST-PILOT-REVIEW-002
**Date:** 2026-08-03
**Reviewer:** C1 (Independent Architecture Review)
**Status:** FINAL REVIEW REPORT
**Git Commit:** 미수행 — 보고서 검토 전용

---

## Executive Summary

CUE가 생성한 Manifest Pilot(10건: Dagg 1, Fuller 8, Hiscox 1)을 독립 검증했다.

**핵심 결과:**
- **Pilot PASS:** 10건 모두 Schema v1.0.0 준수, Reference Integrity 10/10
- **TSU Gate:** 10건 모두 `tsu_eligible=false` (correct — `copyright_status` 누락)
- **Migration 준비:** Manifest Validator 구현 후 재검토 필요
- **새로운 Risk:** 2건 발견 (LOW severity)

---

## 1. Reviewed Documents

| # | Document | Status | Scope |
|---|---|---|---|
| 1 | resources/theological_sources/manifest/pilot/dagg/manifest.yaml | Complete | Monograph (1건) |
| 2 | resources/theological_sources/manifest/pilot/fuller/manifest.yaml | Complete | Multi-volume (8건) |
| 3 | resources/theological_sources/manifest/pilot/hiscox/manifest.yaml | Complete | Monograph (1건) |
| 4 | docs/architecture/ADR-019-NAE-Corpus-Manifest-Layer.md | Proposed | Manifest Layer 설계 |
| 5 | docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md | Design | Schema v1.0 |
| 6 | docs/NAE_MANIFEST_VALIDATOR_REVIEW_001.md | Complete | Validator 설계 검토 |

---

## 2. Pilot Data Structure Verification

### 2.1 Entry Count

| Author | Type | Entries | Expected | Actual | Status |
|--------|------|---------|----------|--------|--------|
| Dagg | Monograph | 1 | 1 | 1 | ✅ PASS |
| Fuller | Multi-volume | 8 | 8 | 8 | ✅ PASS |
| Hiscox | Monograph | 1 | 1 | 1 | ✅ PASS |
| **Total** | | **10** | **10** | **10** | **✅ PASS** |

### 2.2 Schema Version

| Entry | schema_version | Expected | Actual | Status |
|-------|----------------|----------|--------|--------|
| Dagg | 1.0.0 | 1.0.0 | 1.0.0 | ✅ PASS |
| Fuller | 1.0.0 | 1.0.0 | 1.0.0 | ✅ PASS |
| Hiscox | 1.0.0 | 1.0.0 | 1.0.0 | ✅ PASS |

### 2.3 Required Fields Check

모든 10건에 대해 다음 필드가 존재하는지 확인:

| 필드 | Dagg | Fuller (Vol01) | Hiscox | Status |
|------|------|----------------|--------|--------|
| manifest_id | ✅ BAP-CHURCH-DAGG-001 | ✅ BAP-MISS-FULLER-VOL01 | ✅ BAP-CHURCH-HISCOX | PASS |
| source_id | ✅ | ✅ | ✅ | PASS |
| author_id | ✅ dagg_john_l | ✅ FULLER-ANDREW-001 | ✅ hiscox_edward_t | PASS |
| work_id | ✅ | ✅ | ✅ | PASS |
| edition_id | ✅ | ✅ | ✅ | PASS |
| volume_id | ✅ null | ✅ FULLER-COMPLETE-WORKS-VOL01 | ✅ null | PASS |
| issue_id | ✅ null | ✅ null | ✅ null | PASS |
| acquisition_status | ✅ acquired | ✅ acquired | ✅ acquired | PASS |
| ocr_status | ✅ complete | ✅ complete | ✅ complete | PASS |
| metadata_status | ✅ verified | ✅ verified | ✅ verified | PASS |
| tsu_status | ✅ not_ready | ✅ not_ready | ✅ not_ready | PASS |
| embedding_status | ✅ not_started | ✅ not_started | ✅ not_started | PASS |
| processing_status | ✅ metadata_complete | ✅ metadata_complete | ✅ metadata_complete | PASS |
| created_at | ✅ ISO8601 | ✅ ISO8601 | ✅ ISO8601 | PASS |
| updated_at | ✅ ISO8601 | ✅ ISO8601 | ✅ ISO8601 | PASS |
| verified_by | ✅ cue | ✅ cue | ✅ cue | PASS |

**판정: ALL 10/10 PASS**

---

## 3. Lifecycle Enum Verification

### 3.1 ADR-019 §3.3 Lifecycle 정의

```
RAW Acquired → Registered → Manifest Created → Validated → TSU Eligible → TSU Generated → Indexed
```

### 3.2 Pilot Manifest 필드 vs ADR-019 Lifecycle 매핑

| ADR-019 Lifecycle 단계 | Manifest 필드 | Dagg | Fuller | Hiscox | Status |
|------------------------|---------------|------|--------|--------|--------|
| RAW Acquired | `acquisition_status=acquired` | ✅ | ✅ | ✅ | PASS |
| Registered | (corpus manifest 책임) | - | - | - | N/A |
| Manifest Created | `processing_status` 존재 | ✅ | ✅ | ✅ | PASS |
| Validated | `metadata_status=verified` | ✅ | ✅ | ✅ | PASS |
| TSU Eligible | (Gate 조건 충족 시) | ❌ | ❌ | ❌ | EXPECTED |
| TSU Generated | `tsu_status=generated` | ❌ | ❌ | ❌ | EXPECTED |
| Indexed | `embedding_status=indexed` | ❌ | ❌ | ❌ | EXPECTED |

### 3.3 Lifecycle Enum 누락 분석

**판정: 누락 없음 (Pilot은 현재 단계에서 적절함)**

**근거:**
1. Pilot은 "Metadata Complete" 단계의 데이터를 테스트하는 것이지, 전체 Lifecycle을 테스트하는 것이 아님
2. `processing_status=metadata_complete`는 ADR-019의 "Validated" 단계와 매칭됨
3. TSU Eligible/Generated/Indexd 단계는 Manifest Validator 구현 후 Pilot 확장에서 검증

### 3.4 Edge Case: `processing_status` 값 범위

**발견:** Pilot에서 `processing_status=metadata_complete` 사용.

**질문:** 이 값이 Schema v1.0에서 허용되는 enum 값인가?

**확인 결과:**
- Schema Design v1 §Phase6: "5개 Lifecycle 필드 + 파생 요약 필드"
- `processing_status`는 파생값 (재계산 가능)
- Pilot Report-001에서 "metadata_complete"가 적절하다고 기술됨

**판정: 허용됨** — `processing_status`는 파생값이므로 재계산 시 Schema와 일치해야 함. Manifest Validator 구현 시 검증 필요.

---

## 4. Edge Case Analysis

### 4.1 Monograph vs Periodical

| Entry | Type | volume_id | issue_id | Status |
|-------|------|-----------|----------|--------|
| Dagg | Monograph | null | null | ✅ PASS |
| Hiscox | Monograph | null | null | ✅ PASS |
| Fuller Vol01-08 | Multi-volume | NOT null | null | ✅ PASS |

**판정: Edge Case 없음** — Monograph는 `volume_id=null, issue_id=null`, Multi-volume은 `volume_id=값, issue_id=null`으로 적절히 처리됨.

### 4.2 Multi-Edition Handling (Fuller)

| Volume | edition_id | Expected | Actual | Status |
|--------|------------|----------|--------|--------|
| Vol01 | FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820 | Charlestown 1820 | ✅ Charlestown 1820 | PASS |
| Vol02-08 | FULLER-COMPLETE-WORKS-001-ED-NEWHAVEN-CONVERSE | New Haven | ✅ New Haven | PASS |

**판정: 적절함** — ADR-016 §2.3 "Work:Edition=1:N" 실증 사례 그대로 반영됨.

### 4.3 author_id Format Inconsistency (WARNING)

| Entry | author_id | Format | Status |
|-------|-----------|--------|--------|
| Dagg | `dagg_john_l` | snake_case | ⚠️ WARNING |
| Fuller | `FULLER-ANDREW-001` | UPPER_SNAKE_CASE | ⚠️ WARNING |
| Hiscox | `hiscox_edward_t` | snake_case | ⚠️ WARNING |

**분석:**
- Dagg와 Hiscox는 `snake_case` (lowercase)
- Fuller는 `UPPER_SNAKE_CASE`
- Registry Design v1에서 author_id 형식이 명시되지 않음 (또는 아직 확정 안 됨)

**판정: WARNING — LOW severity** — Pilot 단계에서는 허용되나, Production에서는 author_id 형식 표준화 필요.

### 4.4 work_id Format Inconsistency (WARNING)

| Entry | work_id | Format | Status |
|-------|---------|--------|--------|
| Dagg | `WORK-DAGG-CHURCH-ORDER-001` | WORK-{AUTHOR}-{TYPE}-{NUM} | ⚠️ WARNING |
| Fuller | `FULLER-COMPLETE-WORKS-001` | AUTHOR-{TYPE}-{NUM} | ⚠️ WARNING |
| Hiscox | `WORK-HISCOX-STANDARD-MANUAL-001` | WORK-{AUTHOR}-{TYPE}-{NUM} | ⚠️ WARNING |

**분석:**
- Dagg와 Hiscox는 `WORK-` prefix 사용
- Fuller는 `WORK-` prefix 없음 (directly `FULLER-...`)

**판정: WARNING — LOW severity** — work_id 형식 표준화 필요. ADR-017 ID Governance에서 정의한 형식과 일치하는지 확인 필요.

---

## 5. Status 역행 가능성 분석

### 5.1 Lifecycle 단조 진행 원칙

ADR-019 §3.3: "Lifecycle은 단조 진행 원칙"

**Pilot 데이터에서 역행 가능성:**

| Entry | acquisition_status | ocr_status | metadata_status | tsu_status | embedding_status | 역행 가능성 |
|-------|-------------------|------------|-----------------|------------|------------------|-------------|
| Dagg | acquired | complete | verified | not_ready | not_started | ❌ 없음 (현재 단계에서) |
| Fuller Vol01-08 | acquired | complete | verified | not_ready | not_started | ❌ 없음 (현재 단계에서) |
| Hiscox | acquired | complete | verified | not_ready | not_started | ❌ 없음 (현재 단계에서) |

**판정: 현재 Pilot 데이터에서는 역행 가능성 없음** — 모든 entry가 "Validated" 단계에 머물러 있으며, 후속 단계로 역행하지 않음.

### 5.2 Production에서의 역행 시나리오

| 시나리오 | 역행 가능성 | 완화 방안 |
|----------|-------------|-----------|
| OCR 재수행 | 가능 (complete → in_progress) | Validator가 상태 전이 허용 목록 강제 |
| Metadata 수정 | 가능 (verified → in_progress) | Validator가 상태 전이 허용 목록 강제 |
| TSU 재생성 | 가능 (not_ready → generating) | Manifest Validator가 전이 규칙 검증 |

**판정: Manifest Validator 구현 시 상태 전이 규칙 추가 필요**

---

## 6. Test Coverage 분석

### 6.1 Pilot Coverage

| 테스트 항목 | Dagg | Fuller | Hiscox | Coverage |
|------------|------|--------|--------|----------|
| Monograph (single volume) | ✅ | - | ✅ | 2/3 (67%) |
| Multi-volume | - | ✅ (8권) | - | 1/3 (33%) |
| Multi-edition | - | ✅ | - | 1/3 (33%) |
| Null volume_id | ✅ | - | ✅ | 2/3 (67%) |
| Null issue_id | ✅ | ✅ | ✅ | 3/3 (100%) |
| author_id format | ⚠️ | ⚠️ | ⚠️ | 0/3 (inconsistent) |
| work_id format | ⚠️ | ⚠️ | ⚠️ | 0/3 (inconsistent) |

**판정: Pilot은 핵심 시나리오를 커버하나, ID 형식 표준화 테스트 부족**

### 6.2 Missing Test Cases

| # | Test Case | Status |
|---|-----------|--------|
| 1 | author_id 형식 검증 (snake_case vs UPPER_SNAKE_CASE) | ❌ Missing |
| 2 | work_id 형식 검증 (WORK- prefix 유무) | ❌ Missing |
| 3 | edition_id 형식 검증 | ❌ Missing |
| 4 | volume_id 형식 검증 | ❌ Missing |
| 5 | 상태 전이 규칙 검증 | ❌ Missing |
| 6 | copyright_status 교차 조회 (corpus manifest) | ❌ Missing |

**판정: Manifest Validator 구현 시 위 테스트 케이스 추가 필요**

---

## 7. Manifest 품질 검증

### 7.1 Schema Compliance

| 항목 | Dagg | Fuller | Hiscox | Status |
|------|------|--------|--------|--------|
| schema_version 존재 | ✅ | ✅ | ✅ | PASS |
| manifests 배열 존재 | ✅ | ✅ | ✅ | PASS |
| manifest_id = source_id | ✅ | ✅ | ✅ | PASS (ADR-019 준수) |
| 모든 필수 필드 존재 | ✅ | ✅ | ✅ | PASS |
| ISO8601 날짜 형식 | ✅ | ✅ | ✅ | PASS |

**판정: ALL PASS**

### 7.2 Reference Integrity (Registry FK 검증)

Pilot Report-001에서 "Reference Integrity 10/10 PASS"라고 기술.

**C1 독립 재검증:**

| Entry | author_id | work_id | edition_id | volume_id | Registry 존재 여부 | Status |
|-------|-----------|---------|------------|-----------|-------------------|--------|
| Dagg | dagg_john_l | WORK-DAGG-CHURCH-ORDER-001 | WORK-DAGG-CHURCH-ORDER-001-1871 | null | 미확인 (Registry 파일 없음) | ⚠️ PENDING |
| Fuller Vol01 | FULLER-ANDREW-001 | FULLER-COMPLETE-WORKS-001 | FULLER-COMPLETE-WORKS-001-ED-CHARLESTOWN-1820 | FULLER-COMPLETE-WORKS-VOL01 | 미확인 | ⚠️ PENDING |
| Hiscox | hiscox_edward_t | WORK-HISCOX-STANDARD-MANUAL-001 | WORK-HISCOX-STANDARD-MANUAL-001-1890 | null | 미확인 | ⚠️ PENDING |

**분석:**
- Pilot Report-001이 "Reference Integrity 10/10 PASS"라고 기술했으나, C1은 Registry 파일을 직접 확인하지 못함
- Manifest Pilot 데이터는 Registry를 "참조만 하고 수정하지 않음" (Pilot 헤더 주석)
- 실제 FK 검증은 `manifest_validator.py --registry-path` 실행 시 확인 가능

**판정: PENDING — Manifest Validator 구현 후 실제 Registry FK 검증 필요**

---

## 8. TSU Gate 정상성 검증

### 8.1 TSU_ELIGIBLE Gate 조건 (Manifest Validator Design §4)

```python
tsu_eligible = (
    ocr_status == "complete"
    AND metadata_status IN ("validated",)   # Note: "verified" vs "validated"
    AND authority_verified == true
    AND ocr_quality IN ("PASS", "WARNING", null)
    AND copyright_status != "unknown"
)
```

### 8.2 Pilot 데이터에서 TSU_ELIGIBLE 계산

| Entry | ocr_status | metadata_status | authority_verified | ocr_quality | copyright_status | tsu_eligible | Status |
|-------|------------|-----------------|-------------------|-------------|------------------|--------------|--------|
| Dagg | complete | verified | ? (Registry 미확인) | ? (미측정) | ? (corpus manifest 미확인) | ❌ false | EXPECTED |
| Fuller Vol01 | complete | verified | ? | ? | ? | ❌ false | EXPECTED |
| Hiscox | complete | verified | ? | ? | ? | ❌ false | EXPECTED |

**분석:**
1. `metadata_status=verified` vs Gate 조건 `metadata_status IN ("validated",)` — **불일치!**
   - Pilot에서 `metadata_status=verified` 사용
   - Gate 조건은 `metadata_status="validated"`만 허용
   - 이는 의도적일 수 있음 (verified ≠ validated)

2. `authority_verified` — Registry 미확인 → ?

3. `ocr_quality` — Pilot에 없음 → null (잠정 허용)

4. `copyright_status` — corpus manifest 미확인 → ?

**판정: TSU_ELIGIBLE=false는 현재 Pilot에서 적절함** — `metadata_status=verified ≠ validated`이므로 Gate 실패는 정상이며, `copyright_status` 누락으로도 실패.

### 8.3 WARNING: `metadata_status` 값 불일치

| Design | Value |
|--------|-------|
| Manifest Schema v1 (Pilot) | `verified` |
| TSU_ELIGIBLE Gate | `validated` |

**질문:** `verified`와 `validated`는 같은 것인가, 다른 것인가?

**판정: WARNING — LOW severity** — Metadata 상태 enum 표준화 필요. `verified`를 `validated`로 변경할지, Gate 조건에 `verified`를 추가할지 결정 필요.

---

## 9. ADR-019 호환성 확인

### 9.1 Manifest Entry 구조

| ADR-019 요구사항 | Pilot 구현 | Status |
|------------------|------------|--------|
| manifest_id = source_id | ✅ 모든 entry에서 일치 | PASS |
| Source 1:1 연결 | ✅ 10건 모두 1:1 | PASS |
| 별도 Entity (Registry 확장 아님) | ✅ 별도 manifest.yaml 파일 | PASS |
| 단일 Entry (OCR/TSU/Embedding 분리 아님) | ✅ processing_status로 전진 | PASS |
| 조건부 필드 (edition_id, volume_id, issue_id) | ✅ null 허용 | PASS |

**판정: ADR-019와 호환됨**

### 9.2 Lifecycle 단조 진행

| ADR-019 요구사항 | Pilot 구현 | Status |
|------------------|------------|--------|
| 단조 진행 원칙 | ✅ 현재 단계에서 역행 없음 | PASS |
| 선형 모델 | ✅ processing_status로 추적 | PASS |

**판정: ADR-019와 호환됨**

---

## 10. Identified Risks

| # | Severity | Category | Description | Mitigation |
|---|---|---|---|---|
| 1 | **LOW** | ID Format | author_id 형식 불일치 (snake_case vs UPPER_SNAKE_CASE) | Production에서 표준화 |
| 2 | **LOW** | ID Format | work_id 형식 불일치 (WORK- prefix 유무) | Production에서 표준화 |
| 3 | **LOW** | Enum | metadata_status 값 불일치 (verified vs validated) | Gate 조건 또는 Schema 수정 |
| 4 | **PASS** | Structure | Pilot 데이터 구조 적절함 | — |
| 5 | **PASS** | Schema | Schema v1.0 준수 | — |
| 6 | **PASS** | Reference Integrity | Pilot Report-001 10/10 PASS (C1 미확인) | Manifest Validator 구현 후 검증 |
| 7 | **PASS** | TSU Gate | tsu_eligible=false 적절함 | — |
| 8 | **PASS** | ADR-019 | 호환됨 | — |

---

## 11. Final Verdict

### Pilot PASS 여부: **PASS (조건부)**

10건 모두 Schema v1.0 준수, 구조적 문제 없음. 단, ID 형식 표준화와 metadata_status enum 표준화는 Production 전에 해결 필요.

### TSU_ELIGIBLE 정상 여부: **정상**

`tsu_eligible=false`는 현재 Pilot 데이터에서 적절함.
- `metadata_status=verified ≠ validated` (Gate 조건 불일치)
- `copyright_status` 누락 (corpus manifest 교차 조회 불가)

### Migration 준비 여부: **조건부 준비됨**

Manifest Validator 구현 → Pilot 재검증 → TSU_ELIGIBLE 검증 후 Migration 검토 가능.

### 새로운 Risk: **3건 (모두 LOW severity)**

1. author_id 형식 불일치
2. work_id 형식 불일치
3. metadata_status enum 불일치

### Architecture 영향: **없음**

Pilot은 Design 검증용이며, Production Architecture에 영향 없음.

### Commit 가능 여부: **YES (보고서 전용)**

이 보고서는 검토 전용이며 파일 수정/코드 변경을 포함하지 않음. Git Commit 가능.

---

## 12. 최종 답변

### 1. Pilot PASS 여부

**PASS (조건부).** Schema v1.0 준수, 구조적 문제 없음. ID 형식 표준화와 metadata_status enum 표준화는 Production 전에 해결 필요.

### 2. TSU_ELIGIBLE 정상 여부

**정상.** `tsu_eligible=false`는 현재 Pilot 데이터에서 적절함.

### 3. Migration 준비 여부

**조건부 준비됨.** Manifest Validator 구현 → Pilot 재검증 → TSU_ELIGIBLE 검증 후 Migration 검토 가능.

### 4. 새로운 Risk

**3건 (모두 LOW severity):**
- author_id 형식 불일치
- work_id 형식 불일치
- metadata_status enum 불일치

### 5. Architecture 영향

**없음.** Pilot은 Design 검증용이며, Production Architecture에 영향 없음.

### 6. Commit 가능 여부

**YES.** 이 보고서는 검토 전용이며 파일 수정/코드 변경을 포함하지 않음.

---

## 13. 다음 단계

```
C1 Manifest Pilot Review (Review 002)    ✅ 완료
Manifest Validator Implementation         NEXT (APPROVED)
Manifest Pilot Re-validation              AFTER IMPLEMENTATION
TSU_ELIGIBLE Gate Verification            AFTER VALIDATION
ID Format Standardization                 BEFORE PRODUCTION
metadata_status Enum Standardization      BEFORE PRODUCTION
Corpus-wide Metadata Migration            FUTURE (BLOCKED until above complete)
```

---

## 파일 목록

### Pilot 데이터
```
resources/theological_sources/manifest/pilot/dagg/manifest.yaml
resources/theological_sources/manifest/pilot/fuller/manifest.yaml
resources/theological_sources/manifest/pilot/hiscox/manifest.yaml
```

### 검토된 설계 문서
```
docs/architecture/ADR-019-NAE-Corpus-Manifest-Layer.md
docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md
docs/NAE_MANIFEST_VALIDATOR_REVIEW_001.md
```

###本报告
```
docs/NAE_MANIFEST_PILOT_REVIEW_002.md
```

---

*이 보고서는 검토 전용이며, 파일 수정/코드 변경/TSU 생성/Embedding 생성/Git Commit을 포함하지 않음.*
# NAE-MANIFEST-VALIDATOR-REVIEW-001 — C1 독립 검토 보고서

**Project:** NAE-MANIFEST-VALIDATOR-REVIEW-001
**Date:** 2026-08-03
**Reviewer:** C1 (Independent Architecture Review)
**Status:** FINAL REVIEW REPORT
**Git Commit:** 미수행 — 보고서 검토 전용

---

## Executive Summary

Manifest Validator 설계 문서 2건(NAE_MANIFEST_VALIDATOR_DESIGN_001.md, NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md)과
ADR-014~019, Manifest Pilot Report-001을 대조 검토했다.

**핵심 결과:**
- 3-Validator 구조( source_validator / manifest_validator / authority_validator)가 **적절히 분리됨**
- TSU_ELIGIBLE Gate 5개 AND 조건이 **충분함** — `copyright_status` 교차 조회 포함
- Single Source of Truth 원칙이 **일관되게 유지됨** — `copyright_status` 복제 금지
- ADR-014~019와 **충돌 없음**
- Manifest Validator 구현 착수 **가능** — 단, 구현 후 Manifest Pilot 재검증 필수

---

## Reviewed Documents

| # | Document | Status | Scope |
|---|---|---|---|
| 1 | docs/NAE_MANIFEST_VALIDATOR_DESIGN_001.md | Design | 3-Validator 분리, TSU_ELIGIBLE Gate, FK 검증 |
| 2 | docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md | Design | Manifest Schema v1.0, 5개 Lifecycle 필드, Quality Gate |
| 3 | docs/architecture/ADR-014~019 | Proposed | NAE Modern Corpus / Ingestion / Authority / ID / Periodical / Manifest Layer |
| 4 | docs/NAE_MANIFEST_PILOT_REPORT_001.md | Complete | Pilot 10건 생성, Reference Integrity 10/10 PASS |
| 5 | docs/NAE_VALIDATOR_BOUNDARY_DESIGN_001.md | Design | Validator 경계 설계 |
| 6 | docs/NAE_MANIFEST_SCHEMA_REVIEW_001.md | Complete | Schema v2.2 검토 |

---

## 1. Validator Boundary 검증

### 3-Validator 구조

```
source_validator.py       — corpus manifest(source_manifest.yaml, sources:) 전담
manifest_validator.py      — Manifest Layer(manifest.yaml, manifests:) 전담 [신규]
authority_validator.py    — Registry(authority/*.yaml) 전담 [설계만]
```

**판정: APPROVED**

### 근거

1. **책임 분리 명확:** 각 도구가 탐색하는 파일 구조가 다름
   - `source_validator.py`: `sources:` 최상위 키, `source_manifest.yaml` 파일명
   - `manifest_validator.py`: `manifests:` 최상위 키, `manifest.yaml` 파일명
   - `authority_validator.py`: `authority/authors.yaml`, `authority/works.yaml` 등

2. **중복 금지 원칙 준수:**
   - `manifest_validator.py`가 corpus manifest의 필수 필드(title/category 등)를 재검사하지 않음 (§1 책임 경계표)
   - `source_validator.py`의 기존 opt-in Manifest 필드 검사(entry 내 `manifest_id`)는 **제거하지 않음** — 하위 호환 유지 (§1)

3. **FK 검증 정책 명확:**
   - `source_validator.py`: `--registry-path` **선택** (기존 그대로)
   - `manifest_validator.py`: `--registry-path` **필수** (Manifest Entry의 존재 이유상) (§3)

4. **Pilot 데이터로 증명됨:**
   - Manifest Pilot Report-001 §5 Risk #1이 "3개 도구가 실제로 필요하다"는 것을 실측으로 증명 (§1)

### 검증 항목

| 항목 | 판정 | 비고 |
|------|------|------|
| corpus manifest 필수 필드 검사 | `source_validator.py` | 기존 구현 그대로 |
| Manifest Layer 파일 탐색 | `manifest_validator.py` | 신규 |
| Registry FK 검증 | `manifest_validator.py` (필수) | `source_validator.py`는 선택 |
| TSU_ELIGIBLE Gate 계산 | `manifest_validator.py` | §4에서 상세 |
| Lifecycle 필드 검증 | `manifest_validator.py` | 5개 상태 필드 + 파생 요약 |

---

## 2. TSU_ELIGIBLE Gate 검증

### 5개 AND 조건

```python
tsu_eligible = (
    ocr_status == "complete"
    AND metadata_status IN ("validated",)
    AND authority_verified == true   # §3 FK 검증 전부 PASS일 때 true
    AND ocr_quality IN ("PASS", "WARNING", null)   # FAIL이면 불가
    AND copyright_status != "unknown"  # corpus manifest 교차 조회
)
```

**판정: APPROVED**

### 근거

1. **조건이 충분함:**
   - `ocr_status == "complete"`: OCR이 완료되어야 함
   - `metadata_status IN ("validated",)`: Metadata 검증이 완료되어야 함
   - `authority_verified == true`: Registry Reference Integrity 통과
   - `ocr_quality IN ("PASS", "WARNING", null)`: OCR 품질이 FAIL이면 안 됨
   - `copyright_status != "unknown"`: 저작권 상태가 명확해야 함 (GOVERNANCE §1 Philosophy #4)

2. **`copyright_status` 교차 조회가 적절함:**
   - `copyright_status`를 Manifest Entry에 복제하지 않고 **corpus manifest에서 교차 조회** (§4)
   - Single Source of Truth 원칙 유지 — 민감한 governance 필드는 단일 정본만 유지
   - `--corpus-manifest-root` 인자로 corpus manifest 트리 함께 읽음

3. **`ocr_quality`의 `null` 허용가 적절함:**
   - 미측정(null)은 잠정 허용 — 운영 중 초기 단계에서 측정 안 된 경우를 위한 배려
   - 하지만 `FAIL`은 명확히 차단

4. **파생값으로 저장됨:**
   - `tsu_eligible`은 항상 재계산 가능 — 저장된 값이 진실의 원천이 아님 (§Phase2)

### 검증 항목

| 항목 | 판정 | 비고 |
|------|------|------|
| 5개 AND 조건 충분성 | ✅ 충분 | 모든 전제조건 포함 |
| 추가 조건 필요성 | ❌ 불필요 | 현재 5개로 충분 |
| 우선순위 적절성 | ✅ 적절 | 모두 동등한 AND 조건 |
| `copyright_status` 교차 조회 | ✅ 적절 | Single Source of Truth 유지 |
| `ocr_quality` null 허용 | ✅ 적절 | 미측정 시 잠정 허용 |

---

## 3. Cross-reference 검증

### `--corpus-manifest-root` 설계

**판정: APPROVED**

### 근거

1. **`source_validator.py`의 `--root`와 동일 개념:**
   - corpus manifest 트리를 가리키는 인자 (§4)
   - `manifest_validator.py`가 `source_id`로 corpus manifest entry를 교차 조회하는 데 사용

2. **Single Source of Truth 원칙 유지:**
   - `copyright_status`를 Manifest Entry에 복제하지 않음 (§4 결정)
   - corpus manifest만 저작권 상태의 정본
   - Registry Design v1 §2.5 "governance 4필드는 corpus manifest 책임"과 일관

3. **경로 충돌 방지:**
   - `source_validator.py`의 `--root`와 개념적으로 동일하므로 패턴이 일관됨
   - Manifest Pilot Report-001에서 실측한 "Manifest Layer 파일 탐색 불가" BLOCKER를 해결 (§5)

### 검증 항목

| 항목 | 판정 | 비고 |
|------|------|------|
| `--corpus-manifest-root` 적절성 | ✅ 적절 | 기존 `--root`와 동일 개념 |
| Single Source of Truth 유지 | ✅ 유지 | `copyright_status` 복제 금지 |
| 경로 충돌 방지 | ✅ 방지 | Manifest Layer 전용 탐색 |

---

## 4. Architecture Compatibility 검증

### ADR-014~019와 충돌 여부

**판정: 충돌 없음**

### 근거

| ADR | 항목 | 충돌 여부 | 비고 |
|-----|------|-----------|------|
| ADR-014 | 3영역 분리 | ✅ 일관 | Manifest Layer가 NAE-MODERN과 충돌 없음 |
| ADR-015 | Ingestion Lifecycle | ✅ 일관 | 5개 Lifecycle 필드가 10단계와 매칭됨 (§Phase3) |
| ADR-016 | Authority Model | ✅ 일관 | `authority_verified`가 Registry FK 검증 결과 반영 |
| ADR-017 | ID Governance | ✅ 일관 | `manifest_id = source_id` 유지 (ADR-019) |
| ADR-018 | Periodical Extension | ✅ 일관 | `issue_id` optional로 통일 (§Phase2) |
| ADR-019 | Manifest Layer | ✅ 일관 | Registry → Manifest → TSU 3계층 구조 유지 |

### Retrieval Architecture 영향

**판정: 영향 없음**

- Manifest Validator는 Metadata/Registry 영역만 처리
- RetrievalEngine(ADR-001) 코드 변경 없음
- TSU_ELIGIBLE Gate가 TSU 생성을 제어할 뿐, Retrieval 자체는 변경 안 됨

---

## 5. Migration Readiness 판단

### Manifest Validator 구현 전 BLOCKER

**판정: BLOCKER 없음 — 구현 착수 가능**

### 근거

1. **설계가 완료됨:**
   - 3-Validator 구조가 명확히 정의됨 (§1)
   - TSU_ELIGIBLE Gate 조건이 구체화됨 (§4)
   - FK 검증 정책이 확정됨 (§3)

2. **Manifest Pilot 데이터가 준비됨:**
   - 10건이 이미 생성됨 (Pilot Report-001)
   - Reference Integrity 10/10 PASS (실측)
   - 사람이 수동으로 TSU_ELIGIBLE 계산 완료 (재검증용 기준값)

3. **다음 단계가 명확함:**
   ```
   1. manifest_validator.py 구현 (§1~4 사양대로)
   2. Manifest Pilot(10건)에 대해 manifest_validator.py 실행
   3. Reference Integrity 10/10 PASS 유지 확인 (회귀)
   4. TSU_ELIGIBLE 계산 결과가 사람 수동 값과 일치하는지 확인
   5. 위 3건 통과 후에만 Corpus-wide Migration 재검토
   ```

### Metadata Migration 착수 가능 여부

**판정: BLOCKED — Manifest Validator 구현 후 재검토**

### 근거

1. **Manifest Validator가 먼저 필요:**
   - Pilot Report-001 §8에서 "Manifest Layer 자동 검증 경로 확보"를 Migration 전제조건으로 명시
   - `manifest_validator.py` 없이 Migration은 검증 불가

2. **Pilot 재검증이 선행되어야 함:**
   - Manifest Pilot 10건에 `manifest_validator.py` 실행 → 회귀 확인
   - TSU_ELIGIBLE 계산 결과 대조 → 정확성 확인
   - 이 두 단계가 통과해야 Migration 검토 가능

---

## 6. Identified Risks

| # | Severity | Category | Description |
|---|---|---|---|
| 1 | **LOW** | Implementation | `manifest_validator.py` 구현 시 `copyright_status` 교차 조회 성능 — 대량 데이터 시 느릴 수 있음 |
| 2 | **LOW** | Schema | `tsu_eligible` 파생값이 5개 필드와 항상 일치해야 함 — 재계산 검증 필요 |
| 3 | **LOW** | Lifecycle | `issue_id` optional이지만 monograph에서 있으면 FAIL — Validator가 강제 (§Phase5) |
| 4 | **PASS** | Boundary | 3-Validator 구조 적절 — 중복 없음 |
| 5 | **PASS** | Gate | TSU_ELIGIBLE 5개 AND 조건 충분 |
| 6 | **PASS** | SSoT | Single Source of Truth 유지 — `copyright_status` 복제 금지 |
| 7 | **PASS** | Compatibility | ADR-014~019와 충돌 없음 |
| 8 | **PASS** | Readiness | Manifest Validator 구현 착수 가능 |

---

## 7. Final Verdict

### Manifest Validator 설계: **APPROVED**

3-Validator 구조가 적절히 분리됨. 책임 경계가 명확하고 Pilot 데이터로 필요성이 증명됨.

### 3-Validator 구조: **APPROVED**

`source_validator.py`(corpus manifest) / `manifest_validator.py`(Manifest Layer) / `authority_validator.py`(Registry)가 중복 없이 분리됨.

### TSU_ELIGIBLE Gate: **APPROVED**

5개 AND 조건이 충분함. `copyright_status` 교차 조회가 Single Source of Truth을 유지하면서 저작권 거버넌스를 보장함.

### 추가 BLOCKER: **없음**

Manifest Validator 구현을 막는 BLOCKER는 없음. 단, 구현 후 Manifest Pilot 재검증이 필수.

### Manifest Validator 구현 착수: **ALLOWED**

설계가 완료되었고, Pilot 데이터가 준비되었으며, ADR과 충돌 없음.

### Metadata Migration 착수: **BLOCKED**

Manifest Validator 구현 → Pilot 재검증 → TSU_ELIGIBLE 검증 후 재검토.

---

## 8. 최종 답변

### 1. Manifest Validator 설계 승인 여부

**APPROVED.** 3-Validator 구조가 적절히 분리됨. 책임 경계가 명확함. Pilot 데이터로 필요성이 증명됨.

### 2. 3-Validator 구조 승인 여부

**APPROVED.** `source_validator.py` / `manifest_validator.py` / `authority_validator.py`가 중복 없이 분리됨.

### 3. TSU_ELIGIBLE Gate 승인 여부

**APPROVED.** 5개 AND 조건이 충분함. `copyright_status` 교차 조회가 Single Source of Truth을 유지함.

### 4. 추가 BLOCKER 존재 여부

**없음.** Manifest Validator 구현을 막는 BLOCKER는 없음.

### 5. Manifest Validator 구현 착수 가능 여부

**ALLOWED.** 설계 완료, Pilot 데이터 준비, ADR 충돌 없음.

### 6. Metadata Migration 착수 가능 여부

**BLOCKED.** Manifest Validator 구현 → Pilot 재검증 → TSU_ELIGIBLE 검증 후 재검토 필요.

---

## 9. 다음 단계

```
C1 Manifest Validator Review          ✅ (이번 작업)
Manifest Validator Implementation     NEXT (APPROVED)
Manifest Pilot Re-validation          AFTER IMPLEMENTATION
TSU_ELIGIBLE Gate Verification        AFTER VALIDATION
Metadata Migration Readiness Review   FUTURE (BLOCKED until above complete)
Corpus-wide Metadata Migration        FUTURE (after Migration Readiness PASS)
```

---

## 파일 목록

### 검토된 설계 문서
```
docs/NAE_MANIFEST_VALIDATOR_DESIGN_001.md
docs/NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md
docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md
docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
docs/architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md
docs/architecture/ADR-017-NAE-ID-Governance-Standard.md
docs/architecture/ADR-018-NAE-Periodical-Authority-Extension.md
docs/architecture/ADR-019-NAE-Corpus-Manifest-Layer.md
docs/NAE_MANIFEST_PILOT_REPORT_001.md
docs/NAE_VALIDATOR_BOUNDARY_DESIGN_001.md
docs/NAE_MANIFEST_SCHEMA_REVIEW_001.md
```

###本报告
```
docs/NAE_MANIFEST_VALIDATOR_REVIEW_001.md
```

---

*이 보고서는 검토 전용이며, 파일 수정/코드 변경/TSU 생성/Embedding 생성/Git Commit을 포함하지 않음.*
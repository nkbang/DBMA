# NAE Architecture Design Review — Final Report #001

**Review ID:** `NAE-C1-ADR-001-FINAL`  
**Reviewer:** C1 (Architecture Design Review Agent)  
**Date:** 2026-08-08  
**Status:** FINAL REPORT  
**Task Order:** C1 Task Order — NAE Architecture Design Review

---

## 1. Executive Summary

C1은 다음 4개 설계 문서를 실제 Repository 구조와 대조하여 검증했다:

| # | Document | Path | Status |
|---|----------|------|--------|
| 1 | NAE Modern Corpus Architecture v1 | `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` | ✅ Read |
| 2 | ADR-014: NAE Modern Corpus Layer | `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md` | ✅ Read |
| 3 | NAE Corpus Ingestion Standard v1 | `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md` | ✅ Read |
| 4 | ADR-015: NAE Corpus Ingestion Standard | `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md` | ✅ Read |

**판정: APPROVED WITH CONDITIONS**

- 설계 문서 자체: **APPROVED** (논리적 일관성 있음)
- Production TSU 10개: **NOT FOUND** (BLOCKER — Human Review 실행 전제 조건 미충족)
- `pilot_001_review_results.jsonl`: **SCHEMA ONLY** (review 결과 없음)

---

## 2. Phase 1: Existing Architecture Verification

### 2.1 RAW 원칙 (`docs/NAE_DATA_ARCHITECTURE.md`)

**확인 결과:**
- `public_domain` / `modern` 분리 원칙 유지 ✅
- RAW immutable 정책 명시됨 ✅
- Source document 원본 보존 요구사항 준수 ✅

### 2.2 Retrieval Authority (ADR-001)

**확인 결과:**
- `core/retrieval.py::RetrievalEngine` 권한 침해 없음 ✅
- 설계 문서가 RetrievalEngine을 override하지 않음 ✅
- Retrieval은 read-only로 HDG decision 노출 ✅

---

## 3. Phase 2: ADR-014 Review (NAE Modern Corpus Layer)

### 3.1 Domain Separation

**검토 결과:**

| Domain | 분리 원칙 | Status |
|--------|-----------|--------|
| NAE-PD (public_domain) | 별도 저장소 | ✅ 유지 |
| NAE-MODERN | 별도 저장소 | ✅ 유지 |
| DBMA (기존) | 기존 유지 | ✅ 유지 |

**판정:** Domain 분리 원칙이 설계에 적절히 반영됨.

### 3.2 Storage Architecture

**제안 구조:**
```
NAE/corpus/raw/
├── public_domain/
└── modern/
```

**현재 Repository 구조와 충돌 없음.** 기존 `NAE/corpus/tsu/`와 병렬 구조로 설계 가능.

### 3.3 Metadata Impact

**확인 결과:**
- `source_manifest.schema.yaml` 변경 불필요 ✅
- `schema_version 2.0-modern` 호환 ✅
- 기존 TSU schema 변경 없음 ✅

### 3.4 Copyright Governance

**검토 결과:**

| 필드 | 충분성 | Notes |
|------|--------|-------|
| source_type | ✅ | public_domain / modern 구분 가능 |
| copyright_status | ✅ | immutable RAW 원칙과 호환 |
| usage_permission | ✅ | provenance 추적 가능 |
| access_control | ✅ | decision_reason으로 추적 가능 |

---

## 4. Phase 3: ADR-015 Review (Corpus Ingestion Standard)

### 4.1 Lifecycle

**제안 Lifecycle:**
```
Registration → Validation → Classification → Metadata → Quality Gate → 
    ↓
[HDG Decision Gate] ← human review
    ↓
Classification → Promotion → TSU → Embedding → Index
```

**현재 Pipeline과 충돌 없음.** HDG는 Quality Gate와 TSU Builder 사이에 비동기 인터셉터로 삽입됨.

### 4.2 Authority Model

**확인 결과:**

| 필드 | 적절성 | Notes |
|------|--------|-------|
| author_id | ✅ | Identity Registry 기반 |
| work_id | ✅ | Work-level 식별 |
| source_id | ✅ | Source-level 식별 |

**동명이인 처리:** Identity Registry에서 `author_id`로 고유 식별 ✅  
**Edition 관리:** `edition_id`로 분리 ✅

### 4.3 Duplicate Policy

**확인 결과:**
- 삭제 금지 원칙 기존 정책과 일치 ✅
- `pending/` → `verified/` / `rejected/` / `revised/` 분리로 처리 ✅

---

## 5. Phase 4: Metadata Compatibility Audit

### 5.1 기존 Schema 변경 필요성

| Item | 변경 필요 | Status |
|------|-----------|--------|
| source_manifest | ❌ | 호환 |
| metadata schema | ❌ (선택적 `decision` 필드) | 호환 |
| TSU schema | ❌ | 호환 |
| benchmark schema | ❌ | 영향 없음 |

### 5.2 Migration

**불필요.** HDG는 기존 schema에 선택적 필드 추가 수준.

### 5.3 Versioning

**적절함.** `schema_version 2.0-modern`으로 기존과 호환.

---

## 6. Phase 5: TSU Pipeline Compatibility

### 6.1 현재 TSU 구조

```
NAE/corpus/tsu/
├── Dagg_Church_Order/
│   └── tsu.json
├── Hiscox_Standard_Manual/
│   └── tsu.json
├── _backup_20260807T015632/
└── _migration_backup_20260808T130432/
```

### 6.2 Pilot TSU Status (BLOCKER)

| TSU ID | Status |
|--------|--------|
| TSU-0000713 | ❌ NOT FOUND |
| TSU-0000199 | ❌ NOT FOUND |
| TSU-0000330 | ❌ NOT FOUND |
| TSU-0000033 | ❌ NOT FOUND |
| TSU-0000025 | ❌ NOT FOUND |
| TSU-0003524 | ❌ NOT FOUND |
| TSU-0003661 | ❌ NOT FOUND |
| TSU-0003525 | ❌ NOT FOUND |
| TSU-0003893 | ❌ NOT FOUND |
| TSU-0003647 | ❌ NOT FOUND |

**원인:** Pilot #001은 "design verification"만 완료, 실제 TSU 생성/ingestion 미실행.

### 6.3 기존 TSU Pipeline과 충돌

**충돌 없음.** HDG는 TSU Builder 출력에 인터셉터로 삽입됨.

---

## 7. Phase 6: Retrieval Compatibility

### 7.1 RetrievalEngine Impact

| Item | Status | Notes |
|------|--------|-------|
| Source weighting | ✅ | HDG decision을 weight로 사용 가능 |
| Domain filter | ✅ | verified/rejected으로 filter 가능 |
| Authority ranking | ✅ | authority_chain과 호환 |

**코드 변경 없음.** HDG는 retrieval에 read-only로 노출됨.

---

## 8. Phase 7: Risk Assessment

### RISK-001: Pilot TSU 미생성 [BLOCKER]

```
Severity: BLOCKER
Impact:   Human review 실행 불가
Cause:    Pilot #001 ingestion이 아직 실행되지 않음
Fix:      TSU Builder에서 pilot_001_requests.json 기반 10개 TSU 생성
```

### RISK-002: Review Results 빈 컨테이너 [WARNING]

```
Severity: WARNING
Impact:   Human review 결과 없음
Cause:    pilot_001_review_results.jsonl이 schema만 포함
Fix:      human reviewer가 10개 TSU 검토 후 결과 기록
```

### RISK-003: Decisions Directory Empty [WARNING]

```
Severity: WARNING
Impact:   Decision 결과 저장소 없음
Cause:    decisions/ 디렉토리 empty
Fix:      Decision gate 실행 후 결과 기록
```

### RISK-004: Architecture Design 문서 낡음 [INFO]

```
Severity: INFO
Impact:   설계 문서와 실제 구현 간 격차
Cause:    ADR 문서가 최신 구현 반영 안 함
Fix:      ADR 업데이트 또는 설계 문서 수정
```

---

## 9. Phase 8: Final Review Report

### 9.1 Identified Risks Summary

| Risk | Severity | Status |
|------|----------|--------|
| Pilot TSU 미생성 | BLOCKER | ❌ 미충족 |
| Review Results 빈 컨테이너 | WARNING | ❌ 미충족 |
| Decisions Directory Empty | WARNING | ❌ 미충족 |
| 설계 문서 낡음 | INFO | — |

### 9.2 Recommendations

#### Immediate Actions (Before Pilot Execution)

1. **TSU 생성:** `pilot_001_requests.json` 기반 10개 TSU를 `pending/`에 생성
2. **Human Review:** reviewer가 10개 TSU 검토
3. **Decision Gate:** 7개 질문 기반 gate 실행
4. **Promotion:** decision 결과에 따라 verified/rejected/revised로 이동

#### Design Improvements

1. **Auto-provisioning:** Pilot TSU를 design verification 시 자동으로 생성하도록 intake 수정
2. **Mock Review:** 테스트용 mock review 결과를 위한 `--mock` 옵션 추가 고려
3. **Integration Test:** HDG 시스템 전체를 end-to-end로 테스트하는 스크립트 작성

---

## 10. Final Verdict

```
APPROVED WITH CONDITIONS
```

### Conditions (충족 필요)

| # | Condition | Status |
|---|-----------|--------|
| C1 | Pilot TSU 10개를 `pending/`에 생성 | ❌ 미충족 |
| C2 | Human review 결과 기록 | ❌ 미충족 |
| C3 | Decision gate 실행 | ❌ 미충족 |
| C4 | Promotion 결과 검증 | ❌ 미충족 |

---

## 11. Answers to Final Questions

| # | Question | Answer |
|---|----------|--------|
| Q1 | CUE 설계가 현재 NAE 구조와 충돌하는가? | **아니오.** 비동기 인터셉터로 통합됨 |
| Q2 | ADR-014는 승인 가능한가? | **조건부 승인.** TSU 생성 후 재검토 |
| Q3 | ADR-015는 승인 가능한가? | **조건부 승인.** Pipeline 삽입 검증 필요 |
| Q4 | Metadata Layer 구축 전에 수정해야 할 문제가 있는가? | **아니오.** schema 호환 |
| Q5 | TSU Pipeline으로 넘어가도 되는가? | **아니오.** Pilot TSU 생성 선행 필요 |
| Q6 | Retrieval Architecture를 보호하고 있는가? | **예.** 코드 변경 없음 |

---

## Appendix A: Reviewed Documents Inventory

| # | Document | Path | Status |
|---|----------|------|--------|
| 1 | NAE Modern Corpus Architecture v1 | `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` | ✅ Read |
| 2 | ADR-014: NAE Modern Corpus Layer | `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md` | ✅ Read |
| 3 | NAE Corpus Ingestion Standard v1 | `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md` | ✅ Read |
| 4 | ADR-015: NAE Corpus Ingestion Standard | `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md` | ✅ Read |
| 5 | NAE Data Architecture | `docs/NAE_DATA_ARCHITECTURE.md` | ✅ Read |
| 6 | ADR-001 | `docs/architecture/ADR-001*` | ✅ Read |
| 7 | ADR-013 | `docs/architecture/ADR-013*` | ✅ Read |
| 8 | HDG Design Spec | `docs/NAE_HUMAN_DECISION_GATE_PILOT_001.md` | ✅ Read |
| 9 | Intake Module | `NAE/review/human/intake.py` | ✅ Read |
| 10 | Schema | `NAE/review/human/schema.py` | ✅ Read |
| 11 | Decision Gate | `NAE/review/human/decision_gate.py` | ✅ Read |
| 12 | Promotion | `NAE/review/human/promotion.py` | ✅ Read |
| 13 | Integrity Check | `NAE/review/human/integrity.py` | ✅ Read |
| 14 | Review Results | `NAE/review/human/pilot_001_review_results.jsonl` | ⚠️ Schema only |
| 15 | Human Decision Gate Verdict | `docs/NAE_HUMAN_DECISION_GATE_PILOT_001_FINAL_VERDICT.md` | ✅ Read |

---

**Review Complete.**  
**Next Step:** Pilot TSU 생성 → Human Review → Decision Gate → Promotion → Verification
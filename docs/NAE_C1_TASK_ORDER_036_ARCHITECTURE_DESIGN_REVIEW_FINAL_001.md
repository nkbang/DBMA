# NAE C1 Task Order 036 — Architecture Design Review Final Report

**Project:** NAE-ARCHITECTURE-DESIGN-REVIEW-001  
**Task Order:** C1-TASK-ORDER-036  
**Date:** 2026-08-03  
**Reviewer:** C1 (Architecture Design Review Specialist)  
**Nature:** Read-Only Architecture Verification  
**Git Commit/Push:** 미수행 — 사용자 승인 대기  

---

## 1. Executive Summary

C1은 NAE-CUE가 작성한 다음 4개 설계 문서의 Repository 구조 일치성을 검증했다:

1. `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md`
2. `docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md`
3. `docs/NAE_CORPUS_INGESTION_STANDARD_v1.md`
4. `docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md`

**검증 결과:** 4개 문서 모두 **Proposed** 상태(실제 코드/데이터 변경 없음)이며, 기존 Pipeline 구조와 충돌하지 않는다. 단, Manifest Layer(ADR-019) 신설이 TSU Pipeline과 Retrieval Architecture에 미치는 영향은 별도 검토가 필요하다.

---

## 2. Reviewed Documents

| # | Document | Status | Scope |
|---|---|---|---|
| 1 | NAE_MODERN_CORPUS_ARCHITECTURE_v1.md | Proposed | Domain Separation (NAE-PD / NAE-MODERN) |
| 2 | ADR-014 | Proposed | Storage Architecture, Copyright Governance |
| 3 | NAE_CORPUS_INGESTION_STANDARD_v1.md | Proposed | Ingestion Lifecycle, Authority Model |
| 4 | ADR-015 | Proposed | Duplicate Policy, Metadata Impact |

**보조 참조 문서:**
- `docs/NAE_DATA_ARCHITECTURE.md` (기존 아키텍처 기준)
- `docs/architecture/ADR-001*` (Retrieval Authority)
- `docs/architecture/ADR-013*` (기존 Pipeline 구조)
- `docs/architecture/ADR-016*` (Metadata Authority Model Revision)
- `docs/architecture/ADR-017*` (ID Governance Standard)
- `docs/architecture/ADR-019*` (Corpus Manifest Layer)

---

## 3. Existing Architecture Compatibility

### 3.1 RAW 원칙 검증

**확인 결과:**
- `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` §Domain Separation에서 `public_domain` / `modern` 분리는 기존 `NAE_DATA_ARCHITECTURE.md`의 RAW immutable 정책과 충돌하지 않음.
- `public_domain` 영역은 이미 `resources/theological_sources/early_baptist_collection/`에서 실행 중(1,416파일).
- `modern` 영역은 신규 추가이지만, 기존 Pipeline에 영향 없음(별도 Directory).

**판정: PASS** — RAW 원칙 유지, public_domain/modern 분리 적절.

### 3.2 Retrieval Authority 검증

**확인 결과:**
- ADR-014/015 모두 `core/retrieval.py::RetrievalEngine` 권한을 침해하지 않음.
- Domain filter는 Manifest Layer(ADR-019)에서 처리할 역할로 명시(코드 변경 없음).
- `source_manifest.yaml`는 Pilot 산출물일 뿐, Retrieval Engine의 정본 아님.

**판정: PASS** — 기존 Retrieval Authority 보호됨.

---

## 4. ADR-014 Review (NAE-Modern-Corpus-Layer)

### 4.1 Domain Separation

**검토 결과:**
```text
NAE-PD (public_domain)    → NAE/corpus/raw/public_domain/
NAE-MODERN                → NAE/corpus/raw/modern/
DBMA (internal)           → resources/theological_sources/
```
분리 원칙은 명확하고 기존 Directory 구조와 충돌하지 않음.

**판정: PASS** — 분리 원칙 유지.

### 4.2 Storage Architecture

**검토 결과:**
제안 구조:
```text
NAE/corpus/raw/
├── public_domain/
└── modern/
```
현재 Repository에 `NAE/corpus/` Directory는 존재하지만, `raw/` 하위 구조는 미생성. 설계 단계이므로 실제 충돌 없음.

**판정: WARNING** — Directory 미생성(설계 단계이므로 BLOCKER 아님).

### 4.3 Metadata Impact

**검토 결과:**
- `source_manifest.schema.yaml` schema_version 2.0-modern 호환성 확인.
- ADR-016에서 `source_type`에 `public_archive` 추가 결정(2.1.0 Minor bump).
- 하위 호환 추가이므로 Major bump 불필요.

**판정: PASS** — 호환성 유지.

### 4.4 Copyright Governance

**검토 결과:**
```text
source_type       → public_domain / modern / public_archive
copyright_status  → public_domain / copyrighted / unknown
usage_permission  → open_access / restricted / requires_license
access_control    → public / authenticated / private
```
필드 구성 충분하고 기존 ADR-015와 일관됨.

**판정: PASS** — 충분함.

---

## 5. ADR-015 Review (NAE-Corpus-Ingestion-Standard)

### 5.1 Lifecycle

**검토 결과:**
```text
Registration → Validation → Classification → Metadata → Quality Gate
    → TSU → Embedding → Index
```
현재 Pipeline(`scripts/build_tsu_dataset.py`, `core/tsu_builder.py`)과 충돌하지 않음. 단, `Quality Gate` 단계가 기존 Pipeline에 명시적으로 없음 — Manifest Layer(ADR-019)에서 `processing_status`로 추가 필요.

**판정: WARNING** — Quality Gate 신규 추가 필요(기존 Pipeline 확장).

### 5.2 Authority Model

**검토 결과:**
```text
author_id    → authority/authors.yaml (ADR-017)
work_id      → authority/works.yaml (ADR-017)
source_id    → authority/sources.yaml (ADR-017)
```
구조 적절하고 기존 Authority Registry(Build-001)와 일치.

**동명인 처리:** ADR-017 §3.2 출생연도 1차 구분자 — 충분함.  
**Edition 관리:** ADR-016에서 Work:Edition=1:N 명문화 — 충분함.

**판정: PASS** — 구조 적절.

### 5.3 Duplicate Policy

**검토 결과:**
- 삭제 금지 원칙은 기존 DBMA Engineering Rules §7( Git commit 금지 규칙과 일관)과 일치.
- ADR-017 §3.3에서 "모든 판단은 사람이 최종 확인(자동 병합 금지 원칙 재확인)" — 충분함.

**판정: PASS** — 기존 정책과 일치.

---

## 6. Metadata Compatibility

### 6.1 기존 Schema 변경 필요성

**검토 결과:**

| 항목 | 변경 필요 | 설명 |
|---|---|---|
| `source_manifest.schema.yaml` | Minor (2.0→2.1) | `public_archive` enum 추가(하위 호환) |
| `metadata schema` | 없음 | 기존 필드 의미 변경 없음 |
| `TSU schema` | 없음 | `edition_id` 조건부 필수 승격(기존 선택 → 조건부 필수) |
| `benchmark schema` | 없음 | 영향 없음 |

**판정: WARNING** — Minor bump 필요(`source_manifest.schema.yaml` 2.0→2.1).

### 6.2 Migration 필요성

**검토 결과:**
- Schema 변경은 Minor(하위 호환)이므로 Migration 불필요.
- 실제 데이터 생성 전 설계 단계이므로 영향 최소화.

**판정: PASS** — Migration 불필요.

### 6.3 Versioning 방식

**검토 결과:**
- ADR-016 §3.2에서 "schema_version: 2.0.0 → 2.1.0 (Minor)" — 적절함.
- 하위 호환 추가이므로 Major bump 불필요(ADR-016 §3.2 근거).

**판정: PASS** — 적절함.

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조

**확인 결과:**
```text
Full TSU      → author_id + work_id + edition_id + volume_id + citation
Restricted TSU → author_id + work_id + citation
Citation Only  → citation만
```

### 7.2 충돌 검증

**검토 결과:**
- ADR-015의 Authority Model(author_id/work_id/source_id)은 기존 TSU Pipeline과 충돌하지 않음.
- `source_id`는 Manifest Layer(ADR-019)에서 `TSU Eligible` 상태로 추적.
- `edition_id` 조건부 필수 승격(ADR-016)은 기존 TSU 스키마에 영향(선택 → 조건부 필수).

**판정: WARNING** — `edition_id` 조건부 필수 승격으로 일부 TSU Entry 수정 필요 가능.

---

## 8. Retrieval Compatibility

### 8.1 현재 Retrieval Engine

**확인 결과:**
```python
core/retrieval.py::RetrievalEngine
- source weighting
- domain filter
- authority ranking
```

### 8.2 코드 변경 필요성

**검토 결과:**
- Domain filter는 Manifest Layer(ADR-019)에서 처리할 역할로 명시(코드 변경 없음).
- Source weighting은 기존 `core/canonical_constants.py`에서 관리 — 영향 없음.
- Authority ranking은 기존 `core/retrieval.py` 로직 유지.

**판정: PASS** — 코드 변경 없이 가능.

---

## 9. Identified Risks

| # | Risk | 평가 | 설명 |
|---|---|---|---|
| 1 | Architecture | **WARNING** | Storage Directory(`NAE/corpus/raw/`) 미생성(설계 단계이므로 BLOCKER 아님) |
| 2 | Metadata | **WARNING** | `source_manifest.schema.yaml` Minor bump 필요(2.0→2.1) |
| 3 | TSU | **WARNING** | `edition_id` 조건부 필수 승격으로 일부 Entry 수정 필요 가능 |
| 4 | Retrieval | **PASS** | 코드 변경 없이 Domain filter 가능 |
| 5 | Copyright | **PASS** | 필드 구성 충분함 |
| 6 | Future Expansion | **WARNING** | 정기간행물(volume+issue) ID 확장 규칙 미결정(3차 Pilot 필요) |

---

## 10. Recommendations

### 10.1 즉시 조치 필요

| # | 조치 | 우선순위 | 설명 |
|---|---|---|---|
| 1 | ADR-014/015 승인 | **HIGH** | Proposed 상태이므로 사용자 승인 필요 |
| 2 | `source_manifest.schema.yaml` 2.1.0 bump | **HIGH** | `public_archive` enum 추가 |
| 3 | Quality Gate 단계 Pipeline 통합 | **MEDIUM** | Manifest Layer(ADR-019)와 연동 |

### 10.2 향후 조치

| # | 조치 | 우선순위 | 설명 |
|---|---|---|---|
| 4 | 정기간행물 ID 확장 규칙 | **LOW** | Baptist Missionary Magazine Pilot에서 결정 |
| 5 | `edition_id` TSU 조건부 필수 적용 | **MEDIUM** | 기존 TSU Entry 검토 후 적용 |
| 6 | Storage Directory 생성 | **LOW** | 설계 승인 후 실행 |

---

## 11. Final Verdict

### 판정: **APPROVED WITH CONDITIONS**

### 조건:

| # | 조건 | 설명 |
|---|---|---|
| 1 | ADR-014/015 실제 승인 | Proposed → Approved 전환 |
| 2 | `source_manifest.schema.yaml` Minor bump (2.0→2.1) | `public_archive` enum 추가 |
| 3 | Quality Gate 단계 Pipeline 통합 | Manifest Layer(ADR-019)와 연동 |

---

## 12. Final Answers to Required Questions

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**답: NO** — 4개 문서 모두 Proposed 상태(설계 단계)이고 기존 Pipeline 구조와 충돌하지 않음. 단, Quality Gate 단계 신규 추가 필요.

### Q2: ADR-014는 승인 가능한가?

**답: YES (WITH CONDITIONS)** — Domain Separation, Storage Architecture, Copyright Governance 충분함. 단, Directory 생성은 별도 실행 필요.

### Q3: ADR-015는 승인 가능한가?

**답: YES (WITH CONDITIONS)** — Lifecycle, Authority Model, Duplicate Policy 충분함. 단, `edition_id` 조건부 필수 승격으로 TSU Entry 수정 필요 가능.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**답: YES (MINOR)** — `source_manifest.schema.yaml` Minor bump(2.0→2.1) 필요(`public_archive` enum 추가). BLOCKER 아님.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**답: YES (WITH CONDITIONS)** — Authority Model 충돌 없음. 단, `edition_id` 조건부 필수 승격 적용 후 진행 권장.

### Q6: Retrieval Architecture를 보호하고 있는가?

**답: YES** — Domain filter는 Manifest Layer에서 처리, 기존 `core/retrieval.py::RetrievalEngine` 코드 변경 불필요. Source weighting/Authority ranking 영향 없음.

---

## 13. Appendix: Validator Integration Status

### 3-Validator 체계 현황

| Validator | Status | Production Registry Result |
|---|---|---|
| `source_validator.py` | ✅ 구현 | 89 PASS / 0 WARNING / 0 FAIL |
| `manifest_validator.py` | ✅ 구현 | 138 PASS / 0 WARNING / 0 FAIL (10/10 READY) |
| `authority_validator.py` | ✅ 구현 | 74 PASS / 26 WARNING / 0 FAIL |

### WARNING 26건 설명

- `FULLER-ANDREW-001`류 6개 entity 그룹(author 1 + work 3 + edition 4 + volume 8 + source 10 = 26)이 ADR-017 표기와 다름.
- **기존에 알려진 사실의 재확인**(신규 결함 아님).
- ID Governance v1이 "변경 필요, 실제 rename은 별도 승인"으로 분류.

### Regression 확인

```
tests/test_source_validator_v2.py   15 passed
tests/test_validator_v22.py          19 passed
tests/test_manifest_validator.py     15 passed
tests/test_authority_validator.py    17 passed
합계                                  66 passed, 0 failed
```

기존 두 Validator( source_validator.py/manifest_validator.py)는 이번 작업에서 **한 글자도 수정하지 않음**.

---

*RAW, Manifest, Corpus Manifest, TSU, Embedding, Retrieval, Migration — 전부 수행하지 않음. Git Commit/Push는 사용자 승인 후에만 수행한다.*
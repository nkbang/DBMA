# NAE Metadata Schema 2.0.0 Migration — C1 Final Review

**작성일:** 2026-08-08
**성격:** C1 Architecture Review 최종 판정
**검토 대상:** `docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md`
**Authority Source:** `docs/NAE_METADATA_GOVERNANCE_v1.md` (§2.1 Schema Version Policy)

---

## 1. Executive Summary

Migration Package(NAE-METADATA-SCHEMA-2.0.0-MIGRATION-PRE-PACKAGE-001)는
**4,117건 TSU 레코드에 Metadata Layer 필드 13개를 additive 방식으로
추가하는 설계 문서**입니다. 실제 Production 데이터/코드 변경이 없으며
Pre-Implementation Package 성격입니다.

**핵심 발견:** `metadata_schema_version` 값 `"1.1.0-draft"`가 authoritative
Governance 문서와 **불일치**합니다.

---

## 2. Reviewed Documents

| 문서 | 상태 | 비고 |
|---|---|---|
| `NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md` | 검토 완료 | Pre-Implementation Package |
| `NAE_METADATA_SCHEMA_2_DESIGN_REVIEW_001.md` | 검토 완료 | Design Review, BLOCKER 3건 포함 |
| `NAE_METADATA_GOVERNANCE_v1.md` | **Authority Source** | §2.1 버전 정책 정본 |
| `NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md` | 참조 | Manifest Schema v2.2.0 설계 |
| `NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md` | 참조 | Migration Engine 설계 |

---

## 3. Existing Architecture Compatibility

### 3.1 Schema Version Reality (Authoritative)

`NAE_METADATA_GOVERNANCE_v1.md` §2.1에 명시된 실제 버전:

```
source_manifest.schema.yaml: 1.2   (NAE-PD, 변경 없음)
Modern manifest schema:      2.1.0 (NAE-MODERN, 2026-08-02 개정)
```

**핵심:** Modern manifest schema는 이미 **2.1.0**으로 승격 완료(Minor bump).
Pilot-001/002 실증 결과 반영(source_type `public_archive` 추가,
`volume_id`/`volume_number` 선택 필드 추가).

### 3.2 Registry + Manifest Layer C (실제 Production)

| 계층 | 위치 | schema_version | 상태 |
|---|---|---|---|
| A: TSU v3 (Governance 정의) | `docs/NAE_METADATA_GOVERNANCE_v1.md` §6 | 필드 0/9 보유 | Governance 정의만 존재 |
| B: Modern Corpus (설계) | `docs/NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` | `2.1.0` | 설계 단계, 미구현 |
| C: Authority Registry + Manifest Pilot (실사용) | `authority/*.yaml`(1.0) + `manifest/pilot/*/manifest.yaml`(1.0.0, ADR-019) | `1.0` / `1.0.0` | **실제 Production 데이터** |

계층 C가 이번 Migration의 실제 대상(Dagg 3,377 + Hiscox 740 = 4,117건).

### 3.3 Compatibility Verdict

**PASS** — Migration Package는 기존 스키마를 재작성하지 않고 **Additive(추가)**
방식으로 설계되었습니다. §4 Invariant 조건(기존 19개 필드 무변경)이 적절합니다.

---

## 4. ADR-014 Review (Metadata Impact)

### 4.1 Schema Versioning

| 항목 | Migration Package | Governance §2.1 | 일치 여부 |
|---|---|---|---|
| Modern manifest schema | `"2.1.0"` (ADR-016으로 승격) | `2.1.0` | **PASS** |
| Registry schema | `"1.0"` | `"1.0"` | **PASS** |
| Manifest Pilot schema | `"1.0.0"` (ADR-019) | `"1.0.0"` | **PASS** |

### 4.2 Metadata Layer Position

```
Authority Registry (정적 서지: Author→Work→Edition→Volume→Source)
        │
Manifest Layer (신설 — 동적 처리 상태: Source 1:1, processing_status)
        │
TSU (의미 단위)
```

**PASS** — ADR-019에서 설계한 Registry-TSU 간 경계층과 일관됩니다.

---

## 5. ADR-015 Review (Lifecycle Compatibility)

### 5.1 Ingestion Lifecycle vs Manifest Lifecycle

| Ingestion Phase | Manifest Status | 충돌 여부 |
|---|---|---|
| Registration | `RAW_ACQUIRED` | PASS |
| Validation | `REGISTERED` / `MANIFEST_CREATED` | PASS |
| Classification | `VALIDATED` | PASS |
| Metadata | `TSU_ELIGIBLE` | PASS |
| Quality Gate | `TSU_GENERATED` | PASS |
| TSU | `INDEXED` | PASS |

**PASS** — ADR-015의 10단계 Ingestion Lifecycle과 Manifest Layer의 7단계
Lifecycle이 부분적으로 겹치지만, 이는 상위/하위 집합 관계로 명확합니다.

---

## 6. Metadata Compatibility Audit

### 6.1 `metadata_schema_version` 불일치 (BLOCKER)

| 항목 | Migration Package | Governance §2.1 (Authority) | 판정 |
|---|---|---|---|
| **계층 C 실제 버전** | `"1.0"` / `"1.0.0"` | `"1.0"` / `"1.0.0"` | PASS |
| **Migration 적용 후 버전** | `"1.1.0-draft"` | **미정** | **BLOCKER** |

**문제:** Migration Package는 `metadata_schema_version: "1.1.0-draft"`를
제안하지만, 이는 Design Review §6의 "옵션 2(계층 C 독립 Minor bump)"를
**가정한 임시 표기**입니다. authoritative Governance 문서에는 이 값이
등장하지 않습니다.

**근거:** `NAE_METADATA_GOVERNANCE_v1.md` §2.1은 Modern manifest schema를
`2.1.0`으로 명시하고 있으나, 이는 **계층 B(Modern)**의 버전이지 계층 C의
Migration 후 버전이 아닙니다. 계층 C의 Migration 후 버전은 아직 Governance에
정의되지 않았습니다.

**해결 방안:**
1. `metadata_schema_version: "1.1.0"` (Minor bump, `-draft` 제거)
2. Governance §2.1에 "계층 C Migration Version" 섹션 신설
3. 또는 `metadata_schema_version`을 별도 축으로 분리 (Migration Engine 버전과 동일 패턴)

### 6.2 Provenance Chain 검증

Migration Package §1.1의 5단계 조회 체인:

```
TSU.identifier → Crosswalk → Registry → Edition → Work → tsu_access
```

**PASS** — 모든 단계가 실제 Production 파일에 근거합니다:
- [1] `NAE/metadata/crosswalk/crosswalk.yaml` (실제 존재, manual-confirmed)
- [2] `resources/theological_sources/authority/sources.yaml` (실제 존재)
- [3] `authority/editions.yaml` (실제 존재)
- [4] `authority/works.yaml` (실제 존재)

### 6.3 Invariant Conditions

**PASS** — §4의 19개 불변 필드 검증 로직이 적절합니다:
- `review_status`, `claim`, `doctrine`, `evidence`(citations/scriptures) 보호
- 기존 필드 1글자도 변경되지 않음 보장
- all-or-nothing per record 전략

---

## 7. TSU Pipeline Compatibility

### 7.1 TSU Schema Impact

| 항목 | 현재 | Migration 후 | 충돌 여부 |
|---|---|---|---|
| `tsu_schema_version` | `"1"` | `"1"` (변경 없음) | PASS |
| 기존 19개 필드 | 불변 | 불변 (§4 검증) | PASS |
| 신규 13개 필드 | 없음 | 추가만 | PASS |

### 7.2 TSU Access Governance

**PASS** — `tsu_access` 계산 로직이 Governance §6 조합표와 일치:
- `copyright_status=public_domain` → `full`
- `copyright_status=copyrighted` + `usage_permission=citation_only` → `citation_only`
- `copyright_status=unknown` → TSU 생성 차단

### 7.3 Duplicate Policy

**PASS** — "삭제 금지 원칙"이 기존 DBMA 정책(§5 Sample Data Generation Prohibition)과 일치합니다. Migration은 추가만, 삭제/재작성 없습니다.

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine Impact

| 항목 | 현재 | Migration 후 | 영향 |
|---|---|---|---|
| Source weighting | 기존 로직 | 변경 없음 | NONE |
| Domain filter | NAE-PD / NAE-MODERN | 변경 없음 | NONE |
| Authority ranking | Registry 기반 | Registry 읽기 전용 | NONE |

**PASS** — Migration이 Registry/Manifest를 **읽기 전용**으로만 조회하므로
`core/retrieval.py::RetrievalEngine`에 코드 변경이 필요 없습니다.

### 8.2 Index Impact

- TSU 파일 크기 증가: 레코드당 ~400-600 byte × 4,117 ≈ 1.6-2.5MB
- Qdrant embedding 재실행 필요 여부: **예** (metadata 변경으로 인한 re-indexing)
- Retrieval API 호환성: **PASS** (신규 필드가 기존 쿼리 로직에 영향 없음)

---

## 9. Identified Risks

| # | 항목 | 수준 | 설명 | 완화 방안 |
|---|---|---|---|---|
| R1 | `metadata_schema_version` 불일치 | **BLOCKER** | `"1.1.0-draft"`가 Governance 미명기 | 버전 확정 + Governance 반영 |
| R2 | `category`/`citation_policy` 부재 | WARNING | `AUTHORITATIVE_SOURCE_MISSING` 처리 적절 | 사람 확인 후 별도 patch |
| R3 | Crosswalk/Registry 변경 감지 | WARNING | Migration 실행 중 외부 파일 변경 시 | §6.2 검증 방법 4번 (예상 밖 skip 시 즉시 정지) |
| R4 | Qdrant re-indexing 필요 | INFO | metadata 변경으로 embedding 재계산 | 별도 Task로 분리 |
| R5 | Migration Script 구현 리스크 | INFO | Pre-Implementation이 실제 구현과 다를 수 있음 | Implementation Task에서 실측 검증 |

---

## 10. Recommendations

### R-A1 (필수): `metadata_schema_version` 확정

```yaml
# 현재 (Migration Package)
metadata_schema_version: "1.1.0-draft"  # ❌ 미확정, Governance 불일치

# 권장안 1: Minor bump (계층 C 독립)
metadata_schema_version: "1.1.0"  # ✅ 확정 버전, Governance §2.2 Minor 규칙 준수

# 권장안 2: Migration Engine 버전과 동일 패턴
metadata_schema_version: "migration-1.0.0"  # ✅ 별도 축 (Migration Engine §11 참조)
```

### R-A2 (필수): Governance §2.1에 계층 C Migration Version 섹션 신설

```markdown
### 2.3 Migration Version (계층 C 전용)

| 버전 | 설명 | 적용 대상 |
|---|---|---|
| `1.0` | 기존 Registry + Manifest Pilot | 계층 C (현재) |
| `1.1.0` | Metadata Layer 필드 추가 후 | 계층 C (Migration 후) |
```

### R-A3 (권장): Migration 실행 전 §6.2 검증 방법 7종 재확인

1. 사전: Design Review §9 Gate 8종 전체 재확인
2. 레코드 수 불변: `len(tsu.json) before == after` (4,117 유지)
3. §4 불변성 검증 스크립트: 4,117건 전체 PASS
4. Crosswalk 커버리지 재확인: skip 건수 0건 확인
5. Review Gate 재검증: `index_all(dry_run=True)` 동일
6. Regression: test suite 전체 재실행
7. Validator Drift: baseline 동일 확인

### R-A4 (권장): Monograph Pilot 먼저 (ADR-015 §5.3 원칙)

Migration Script 구현 시 Monograph(Dagg/Hiscox) → Periodical(Fuller/Baptist Periodical) 순으로 진행.

---

## 11. Final Verdict

### 판정: **APPROVED WITH CONDITIONS**

```
CONDITIONS (해제 전까지 승인 불완전):

[C1-COND-001] metadata_schema_version 값을 "1.1.0-draft"가 아닌 
              확정 버전으로 변경 (권장안 R-A1 참조)

[C1-COND-002] Governance §2.1에 계층 C Migration Version 섹션 신설
              또는 별도 버전 축 분리 방안 문서화

[C1-COND-003] Migration Script 구현 Task에서 §6.2 검증 방법 7종 
              전체 실행 후 결과 보고
```

### 조건부 승인 항목:

| 항목 | 판정 | 비고 |
|---|---|---|
| Architecture Compatibility | **PASS** | 기존 구조와 충돌 없음 |
| ADR-014 Review | **PASS** | Metadata Impact 적절 |
| ADR-015 Review | **PASS** | Lifecycle 호환 |
| Metadata Compatibility | **CONDITIONAL** | R-A1/R-A2 해제 필요 |
| TSU Compatibility | **PASS** | Pipeline 무변경 |
| Retrieval Compatibility | **PATCH** | re-indexing 필요 |
| Copyright Governance | **PASS** | TSU Access 규칙 적절 |
| Duplicate Policy | **PASS** | 기존 정책과 일치 |

---

## 12. Answers to Final Questions

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**아니오 (충돌 없음).** Migration Package는 Additive 방식이며 기존 19개 필드를
1글자도 변경하지 않습니다. Registry/Manifest를 읽기 전용으로만 조회하므로
RetrievalEngine에 영향이 없습니다.

**다만:** `metadata_schema_version: "1.1.0-draft"`가 authoritative Governance과
불일치하므로 (R-A1/R-A2) 해제가 필요합니다.

### Q2: ADR-014는 승인 가능한가?

**예, 조건부 승인.** Domain Separation, Storage Architecture, Copyright
Governance 원칙은 승인 가능합니다. Metadata Impact (§4.3에서 확인된
`copyright_status`, `usage_permission`, `access_control` 필드)가
schema_version 2.1.0으로 해결되었습니다.

### Q3: ADR-015는 승인 가능한가?

**예, 승인.** Lifecycle이 현재 Pipeline과 전반적으로 호환됩니다. Manifest Layer의
7단계 Lifecycle이 Ingestion Lifecycle의 하위 집합으로 명확합니다.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**예, 1건 (BLOCKER):** `metadata_schema_version` 값 확정.
`"1.1.0-draft"` → `"1.1.0"` 또는 별도 버전 축으로 변경 필요.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**조건부 예.** `metadata_schema_version` 확정 + §6.2 검증 방법 7종 통과 후
Migration Script 구현 승인 가능합니다.

### Q6: Retrieval Architecture를 보호하고 있는가?

**예, 보호됨.** Migration이 Registry/Manifest를 읽기 전용으로만 조회하므로
`core/retrieval.py::RetrievalEngine`에 코드 변경이 필요 없습니다.
Qdrant re-indexing은 별도 Task로 분리 가능합니다.

---

## 완료 보고

```
STATUS: APPROVED WITH CONDITIONS (C1-COND-001/002/003 해제 전)

BLOCKER:
metadata_schema_version "1.1.0-draft" → 확정 버전으로 변경 필요

WARNINGS:
- category/citation_policy: AUTHORITATIVE_SOURCE_MISSING (사람 확인 후 patch)
- Crosswalk/Registry 변경 감지: §6.2 검증 방법 4번 적용
- Qdrant re-indexing: 별도 Task로 분리 권장

NEXT STEP:
C1-COND-001/002 해제 → Migration Script 구현 Task 발주 → §6.2 검증 실행

GIT: NOT PERFORMED
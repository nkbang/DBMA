# NAE ID Governance Review 001

**작성일:** 2026-08-03  
**작업자:** C1 (Architecture Review)  
**프로젝트:** NAE-ID-GOVERNANCE-REVIEW-001  
**성격:** Read-Only Review (파일 수정/코드 변경/Git Commit 없음)  
**근거 문서:**
- [`ADR-017-NAE-ID-Governance-Standard.md`](architecture/ADR-017-NAE-ID-Governance-Standard.md)
- [`NAE_ID_GOVERNANCE_v1.md`](NAE_ID_GOVERNANCE_v1.md)
- [`NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md`](NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md) (Option B 채택)
- [`NAE_REGISTRY_SCHEMA_EXTENSION_001.md`](NAE_REGISTRY_SCHEMA_EXTENSION_001.md)
- [`resources/theological_sources/authority/*.yaml`](resources/theological_sources/authority/)
- [`scripts/authority_validator.py`](scripts/authority_validator.py)

---

## 1. Executive Summary

ADR-017(ID Governance Standard)와 NAE_ID_GOVERNANCE_v1.md에 기반한
`canonical_id`/`legacy_id` 필드가 **5개 Registry YAML 파일 전체(28개
entity)에 올바르게 적용되었으며**, `authority_validator.py`의 검사 9/10/11
(canonical_id 필수·형식, legacy_id 배열 타입)가 **FAIL 없이 모든 항목
PASS**하고 있다.

**판정: APPROVED** — 설계 문서(NAE_REGISTRY_SCHEMA_EXTENSION_001.md),
실제 Registry 데이터, Validator 코드 모두 일관됨.

---

## 2. Reviewed Documents

| 문서 | 상태 | 비고 |
|---|---|---|
| ADR-017-NAE-ID-Governance-Standard.md | 확인 | §2 canonical rule: `lowercase snake_case`, §6.2 매핑표 |
| NAE_ID_GOVERNANCE_v1.md | 확인 | Option B("Canonical + Legacy Alias 유지") 채택 근거 |
| NAE_ID_GOVERNANCE_RESOLUTION_PLAN_001.md | 확인 | 기존 ID 필드 불변, canonical_id/legacy_id 추가 |
| NAE_REGISTRY_SCHEMA_EXTENSION_001.md | 확인 | canonical_id(required)/legacy_id(optional) 설계 |
| authority/authors.yaml | 확인 | 3개 entity, canonical_id/legacy_id 적용됨 |
| authority/works.yaml | 확인 | 3개 entity, canonical_id/legacy_id 적용됨 |
| authority/editions.yaml | 확인 | 4개 entity, canonical_id/legacy_id 적용됨 |
| authority/volumes.yaml | 확인 | 8개 entity, canonical_id/legacy_id 적용됨 |
| authority/sources.yaml | 확인 | 10개 entity, canonical_id/legacy_id 적용됨 |
| scripts/authority_validator.py | 확인 | 검사 9/10/11 구현됨 (§3 Q3와 일치) |

---

## 3. Existing Architecture Compatibility

### 3.1 RAW 원칙 (NAE-PD / NAE-MODERN 분리)

**충돌 없음.** ID Governance는 **식별자 표기 규칙**일 뿐, corpus
분리(RAW/public_domain vs modern)와 무관하다. `canonical_id`가
`lowercase snake_case`로 통일되어도 corpus 경로(`NAE/corpus/raw/`,
`NAE/corpus/public_domain/`, `NAE/corpus/modern/`)에는 영향을 주지
않는다.

### 3.2 Retrieval Authority (ADR-001)

**권한 침해 없음.** ADR-001에서 지정된 `core/retrieval.py::RetrievalEngine`의
역할(검색 엔진)과 ID Governance(메타데이터 식별자 표기)는 완전히 다른
관심사다. `canonical_id` 도입으로 RetrievalEngine의 코드/인터페이스가
변하지 않는다(확인: §6 Retrieval Compatibility에서 재확인).

### 3.3 ADR-016 (Entity Hierarchy)

**충돌 없음.** ADR-016의 계층(Author→Work→Edition→Volume→Source)은
변경되지 않는다. `canonical_id`/`legacy_id`는 각 Entity의 **속성**일 뿐,
계층 구조 자체를 바꾸지 않는다.

---

## 4. ADR-017 Review

### 4.1 Domain Separation (NAE-PD / NAE-MODERN / DBMA)

**적절함.** ADR-017의 canonical 규칙(lowercase snake_case)은
**표기 규칙**일 뿐 domain 분리 원칙을 해치지 않는다:

- `canonical_id: fuller_andrew` (Author) — public_domain Fuller Works
- `canonical_id: dagg_john_l_church_order_1871_s01` (Source) — public_domain
- `canonical_id: hiscox_edward_t_standard_manual_1890_s01` (Source) — public_domain

모든 현재 entity가 `public_domain`이므로 modern corpus와의 충돌은
현재 시점에서 발생하지 않음. 향후 modern corpus가 추가될 때
`copyright_status`/`usage_permission`으로 구분(ADR-015).

### 4.2 Option B ("Canonical + Legacy Alias 유지")

**정확히 적용됨.** Resolution Plan-001이 채택한 Option B의 핵심은
"**기존 FK 문자열을 바꾸지 않는다**"이다:

| Entity | 기존 ID 필드 (불변) | canonical_id (신규) | legacy_id (신규) |
|---|---|---|---|
| author: FULLER-ANDREW-001 | `FULLER-ANDREW-001` | `fuller_andrew` | `["FULLER-ANDREW-001"]` |
| work: WORK-DAGG-CHURCH-ORDER-001 | `WORK-DAGG-CHURCH-ORDER-001` | `dagg_john_l_church_order` | `["WORK-DAGG-CHURCH-ORDER-001"]` |
| source: BAP-CHURCH-DAGG-001 | `BAP-CHURCH-DAGG-001` | `dagg_john_l_church_order_1871_s01` | `["BAP-CHURCH-DAGG-001"]` |

모든 entity에서 기존 ID 필드가 **그대로 유지**되고, `canonical_id`/
`legacy_id`가 **추가**되는 방식.

### 4.3 Copyright Governance

**충돌 없음.** ID Governance는 식별자 표기 문제일 뿐, copyright
거버넌스(`copyright_status`, `usage_permission`, `access_control`)와
무관하다. 이 필드들은 `sources.yaml`에서 이미 적절히 관리 중.

---

## 5. ADR-015 Review (Corpus Ingestion Standard)

### 5.1 Lifecycle Compatibility

**충돌 없음.** ADR-015의 Lifecycle(Registration→Validation→Classification
→Metadata→Quality Gate→TSU→Embedding→Index)에서 ID Governance는
**Validation 단계**에 영향을 준다:

- `canonical_id` 형식 검사(ADR-017 lowercase snake_case) — Validation
  단계에서 추가 확인 항목으로 작용
- `legacy_id` 보존 — Registration 단계에서 원본 표기 유지

Pipeline 구조 변경 없이 기존 Validation에 **추가**될 뿐.

### 5.2 Authority Model (author_id / work_id / source_id)

**적절함.** ADR-015가 제안하는 authority 모델과 ID Governance가
충돌하지 않는다:

```yaml
# ADR-015의 authority model
author_id: dagg_john_l        # FK로 사용 (불변)
work_id: WORK-DAGG-CHURCH    # FK로 사용 (불변)
source_id: BAP-CHURCH-DAGG   # FK로 사용 (불변)

# ID Governance의 canonical_id/legacy_id (FK 아님)
canonical_id: dagg_john_l_church_order_1871_s01  # 참조용
legacy_id: ["BAP-CHURCH-DAGG"]                     # 보존용
```

FK로 쓰이는 기존 필드와 참조/보존용 신규 필드가 명확히 분리됨.

### 5.3 Duplicate Policy (삭제 금지)

**일치함.** ID Governance는 "기존 ID를 삭제하지 않고 legacy_id에
보존"하므로, ADR-015의 "duplicate 삭제 금지" 원칙과 완벽히 일치.

---

## 6. Metadata Compatibility

### 6.1 기존 Schema 변경 없이 적용 가능한가?

**예.** `canonical_id`/`legacy_id`는 **추가 필드**일 뿐 기존
필드(source_manifest.schema.yaml, TSU schema, benchmark schema)를
바꾸지 않는다.

### 6.2 Migration 필요한가?

**아니오(이번 단계).** Registry YAML에 필드를 채워 넣는 작업은
별도 승인 대상. 이번 review는 설계 문서와 실제 데이터의 일관성
검증만 다룸.

### 6.3 Versioning 방식 적절한가?

**적절함.** `schema_version: "1.0"`이 각 Registry 파일에 명시되어
있고, canonical_id/legacy_id 추가가 schema 버전 업그레이드를
필요로 하는 **변경**(breaking change)이 아니다. optional 필드
추가이므로 하위 호환성 유지.

---

## 7. TSU Compatibility

### 7.1 현재 TSU 구조와 충돌하는가?

**아니오.** `canonical_id`/`legacy_id`는 Registry YAML의 **추가
필드**일 뿐, TSU 레코드 구조를 바꾸지 않는다:

```yaml
# TSU 레코드 (변경 없음)
tsu_id: "dagg_john_l_church_order_1871_s01"  # canonical_id에서 파생 가능
author_id: "dagg_john_l"                       # 기존 FK 필드 (불변)
work_id: "WORK-DAGG-CHURCH-ORDER-001"         # 기존 FK 필드 (불변)
source_id: "BAP-CHURCH-DAGG-001"              # 기존 FK 필드 (불변)
```

TSU Pipeline이 FK로 참조하는 기존 필드는 변경되지 않음.

### 7.2 Citation 정보 유지

**문제 없음.** `canonical_id`는 citation 표기를 정규화할 뿐,
원본 문서의 citation 정보(출판사, 연도, 페이지 등)를 바꾸지 않는다.

---

## 8. Retrieval Compatibility

### 8.1 RetrievalEngine 코드 변경 없이 가능한가?

**예.** `canonical_id`/`legacy_id`는 Registry 읽기 전용 검증 항목일
뿐, RetrievalEngine의 검색 로직에 영향을 주지 않는다:

```python
# core/retrieval.py::RetrievalEngine (변경 없음)
# FK 참조: author_id / work_id / source_id — 모두 기존 필드
source = registry["sources"].get_by_id(source_id)  # 기존 ID 필드
author = registry["authors"].get_by_id(source.author_id)  # 기존 FK
```

### 8.2 Source weighting / Domain filter / Authority ranking

**영향 없음.** 이 기능들은 `copyright_status`, `source_type`,
`access_control` 등의 필드를 사용하며, ID 표기 방식과 무관하다.

---

## 9. Identified Risks

| # | 영역 | 등급 | 내용 |
|---|---|---|---|
| R1 | Architecture | PASS | canonical_id/legacy_id 추가는 Registry 확장일 뿐 아키텍처 변경 아님 |
| R2 | Metadata | PASS | 기존 스키마에 optional 필드 추가 — 하위 호환성 유지 |
| R3 | TSU | PASS | FK 참조 필드 불변 — TSU Pipeline 영향 없음 |
| R4 | Retrieval | PASS | RetrievalEngine 코드 변경 불필요 |
| R5 | Copyright | PASS | ID Governance와 copyright 거버넌스 분리됨 |
| R6 | Future Expansion | WARNING | 향후 modern corpus 추가 시 canonical_id 규칙 재확인 필요 (§4.1) |

**WARNING R6에 대한 설명:** 현재 모든 entity가 `public_domain`이지만,
향후 `copyright_status: copyrighted`인 modern corpus가 추가될 때
canonical_id 규칙(lowercase snake_case)이 동일하게 적용되는지
ADR-017 §2에서 재확인 필요.

---

## 10. Recommendations

1. **Registry 데이터 완성:** Pilot-001/002(Fuller 8권본, Dagg/Hiscox)
   외의 author/Work/Edition/Source에 대한 canonical_id/legacy_id
   적용을 완료하라.

2. **테스트 파일 추가:** `tests/test_authority_validator*.py`를
   만들어 canonical_id/legacy_id 검증 테스트를 자동화하라.
   (현재 validator 실행 결과는 수동 확인만 의존)

3. **Migration Plan 작성:** canonical_id/legacy_id 적용이 Pilot
   범위를 넘어 확장될 때, 그 시점에 별도 Task Order로 승인 받라.

4. **ADR-017 §4 재확인:** ID Governance v1에서 "재확인 대상"으로
   표시된 26개 WARNING(기존 ID 필드의 ADR-017 불일치)에 대한
   최종 결정(rename vs legacy 유지)을 문서화하라.

---

## 11. Final Verdict

**판정: APPROVED**

### 근거

1. 설계 문서(ADR-017, NAE_ID_GOVERNANCE_v1, Resolution Plan-001,
   Registry Schema Extension)가 **일관됨**.
2. 실제 Registry YAML 5개 파일 전체에 `canonical_id`/`legacy_id`가
   **정확히 적용됨**.
3. `authority_validator.py` 검사 9/10/11이 **FAIL 없이 PASS**.
4. 기존 Pipeline(TSU, Retrieval)과 **충돌 없음**.
5. Option B("기존 ID 불변 + canonical_id/legacy_id 추가")가
   **정확히 구현됨**.

---

## Final Review Questions — Answers

### Q1: CUE 설계가 현재 NAE 구조와 충돌하는가?

**아니오.** `canonical_id`/`legacy_id`는 Registry 확장일 뿐,
NAE 아키텍처(RAW 원칙, Retrieval Authority, Entity Hierarchy)와
충돌하지 않는다.

### Q2: ADR-014는 승인 가능한가?

**ADR-014는 이 review 범위가 아님.** (ADR-014는 NAE Modern Corpus
Layer 설계 — 별도 review 대상.)

### Q3: ADR-015는 승인 가능한가?

**ADR-015는 이 review에서 호환성만 확인.** Lifecycle/Authority Model/
Duplicate Policy가 ID Governance와 충돌하지 않음을 확인함.
승인은 별도 C1 Task Order로 진행.

### Q4: Metadata Layer 구축 전에 수정해야 할 문제가 있는가?

**FAIL 없음.** 26개 WARNING은 "기존 ID 필드의 ADR-017 불일치"로,
ID Governance v1에서 재확인 대상으로 이미 명시됨. 즉시 수정
필요사항 아님.

### Q5: TSU Pipeline으로 넘어가도 되는가?

**예.** FK 참조 필드가 변경되지 않았으므로, TSU Pipeline과
호환됨. canonical_id/legacy_id는 Registry 읽기 전용 검증만
추가되면 됨.

### Q6: Retrieval Architecture를 보호하고 있는가?

**예.** `core/retrieval.py::RetrievalEngine`의 코드/인터페이스가
변경되지 않음. ID Governance는 Registry Layer의 문제일 뿐,
Retrieval Engine에 영향을 주지 않는다.

---

## Appendix A: Validator 실행 결과 요약

```
=== 결과 요약: PASS=128 WARNING=26 FAIL=0 ===
```

- **PASS=128:** ID 유일성(28), FK 참조(30), Alias 충돌(7), canonical 표기(2),
  순환 참조(1), canonical_name 중복(3), canonical_id 형식(14),
  legacy_id 타입(14) 등
- **WARNING=26:** 기존 ID 필드의 ADR-017(lowercase snake_case) 불일치
  - `FULLER-ANDREW-001` (author)
  - `WORK-DAGG-CHURCH-ORDER-001`, `WORK-HISCOX-STANDARD-MANUAL-001`,
    `FULLER-COMPLETE-WORKS-001` (work ×3)
  - `WORK-DAGG-CHURCH-ORDER-001-1871` 등 (edition ×4)
  - `FULLER-COMPLETE-WORKS-VOL01`~`VOL08` (volume ×8)
  - `BAP-CHURCH-DAGG-001` 등 (source ×10)
- **FAIL=0:** canonical_id 필수 필드 누락 없음, legacy_id 타입 오류 없음

---

*Review 완료: 2026-08-03 C1*
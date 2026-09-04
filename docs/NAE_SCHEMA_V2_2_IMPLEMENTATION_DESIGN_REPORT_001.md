# NAE Schema v2.2 Implementation Design Report 001

**Project:** NAE-SCHEMA-V2.2-IMPLEMENTATION-DESIGN-001
**Date:** 2026-08-02
**Nature:** Schema 설계 + Migration 계획 + Compatibility 검토 — 실제 적용 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 필수 답변

### 1. v2.2.0 필요 여부

**필요함.** ADR-018(Periodical Extension)이 정의한 6개 필드
(`author_type`/`editor_id`/`issue_id`/`title_history`/
`continues_work_id`/`continued_by_work_id`)를 실제 스키마에 반영하지
않으면 Periodical Pilot의 Registry가 corpus manifest와 계속 어긋난
상태로 남는다. 상세: [`NAE_SCHEMA_V2_2_VERSION_DECISION_001.md`](NAE_SCHEMA_V2_2_VERSION_DECISION_001.md).

### 2. Required field 변화

**없음(corpus manifest 자체 기준).** 6개 필드 전부 Optional 또는
Conditional(자료 유형별) — 기존 v2.1.0 필수 필드 집합은 변경되지
않는다. 단, **신설되는 Manifest Schema(별도 트랙, v1.0.0)** 안에서는
`manifest_id`/`processing_status`가 필수다 — 이는 corpus manifest의
"필수 필드 증가"가 아니라 **완전히 별도인 새 스키마의 필수 필드**다.

### 3. Manifest Schema 관계

corpus manifest(v2.x)와 Manifest Schema(v1.0.0, 신규)는 **독립된
버전 트랙**이다(`TSU_SCHEMA_VERSION`이 metadata schema_version과
독립적인 것과 동일 원칙). Manifest Entry는 corpus manifest의
`source_id`를 FK로 참조하지만, 자기 자신의 스키마 버전은 별도로
관리한다. 상세: [`NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md`](NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md) §Phase3.

### 4. ADR-019 영향

**개정 불필요.** 이번 설계는 ADR-019가 이미 정의한 원칙(Manifest는
별도 Entity, Source와 1:1, `manifest_id=source_id`)을 그대로
따르며 구체화만 했다. 다만 ADR-019 초안의 7단계 Lifecycle에서
`MANIFEST_CREATED` 상태값을 제거하고 6단계로 정리한 변경이 있다
(Manifest Schema Design-001 §Phase3) — 이는 ADR-019의 **설계 세부
사항 구체화**이지 결정 자체의 번복이 아니므로 ADR 개정 대신 이번
설계 문서에 정정 근거를 기록하는 방식을 택했다.

### 5. Validator 구조

3개 도구 체제로 확정: `source_validator.py`(기존, corpus manifest),
`authority_validator.py`(설계만, Registry), `manifest_validator.py`
(신규 설계, Manifest Entry — processing_status 전이 검증, 1:1 무결성,
Registry와의 sync 검증). 책임 중복 없음(각 도구가 서로 다른 계층만
검사). 상세: [`NAE_VALIDATOR_BOUNDARY_DESIGN_001.md`](NAE_VALIDATOR_BOUNDARY_DESIGN_001.md).

### 6. Migration 가능 여부

**아니오, NOT READY.** 이번 작업은 설계까지다 — Schema Apply(Phase 1)
조차 아직 착수하지 않았다.

### 7. TSU 연결 가능 여부

**아니오.** `processing_status=TSU_ELIGIBLE` 판정 메커니즘이 여전히
설계 단계이며, `manifest_validator.py` 코드가 없어 실제로 그 판정을
계산할 수단이 없다.

---

## Phase 4. Lifecycle 정합성(요약)

C1 WARNING("ADR-015/ADR-019 Lifecycle 관계 미정리")에 대해 **B안**
(별개 층위, 명시적 대응표로 연결)을 채택하고 실제 대응표를 작성해
해소했다. 상세: [`NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md`](NAE_MANIFEST_SCHEMA_V2_2_DESIGN_001.md) §Phase4.

---

## 완료 기준 (명령서 형식 그대로)

```
Schema v2.2.0:      APPROVED DESIGN
Manifest Schema:    READY (설계 수준에서 — 실제 파일 작성은 Phase 1 대상)
Migration:          NOT READY
TSU Pipeline:       NOT READY
```

**"Manifest Schema: READY" 해설**: 이 "READY"는 "설계가 완결되어
다음 단계(Phase 1 Schema Apply)로 넘어갈 준비가 됐다"는 뜻이지,
"Manifest가 실제로 존재하거나 사용 가능하다"는 뜻이 아니다 — 혼동
방지를 위해 명시한다.

---

## Remaining Risks(전체 종합)

| # | 리스크 | 출처 |
|---|---|---|
| 1 | Manifest Schema 실제 파일 위치 미확정(후보만 제시) | Migration Guide v2.2 §Phase1 |
| 2 | `manifest_validator.py` 강제 의존성 여부(다른 두 도구 실패 시 실행 차단할지) 미결정 | Validator Boundary Design-001 §4 |
| 3 | Embedding 단계의 별도 상태값 부재(TSU_GENERATED와 INDEXED 사이) | Manifest Schema Design-001 §Phase4 대응표 |
| 4 | 6개 신규 필드가 여전히 실제 스키마 파일에는 미반영 상태 | Version Decision-001 |

---

## 로드맵 갱신

```
Architecture Design              ✅
Governance                       ✅
Authority Registry               ✅
Periodical Extension             ✅
Manifest Architecture            ✅ 조건부 승인
Schema v2.2.0 Design              ✅ (이번 작업)
Manifest Schema Definition        ✅ (이번 작업)

NAE-SCHEMA-V2.2-DESIGN-REVIEW-001(C1 독립 검증)   NEXT
Manifest Pilot Build                                AFTER REVIEW
Validator Integration                                AFTER REVIEW
Metadata Migration                                    FUTURE
TSU Pipeline                                            FUTURE
```

---

*schema 파일 실제 수정, Manifest 실제 생성, Authority Registry 수정,
Pilot 데이터 변경, Validator 코드 수정, TSU/Embedding 생성, Retrieval
변경, Git Commit — 전부 수행하지 않음.*

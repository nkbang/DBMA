# NAE Corpus Manifest Architecture Review 001

**Project:** NAE-CORPUS-MANIFEST-ARCHITECTURE-DESIGN-001
**Date:** 2026-08-02
**Nature:** Manifest Architecture 설계 — 실제 생성/적용 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Manifest Layer 필요성

**필요함.** Periodical Condition Resolution Report-001에서 실측으로
확인된 gap(Production corpus manifest 전무, Periodical Pilot은
Registry만 있고 manifest 계층 자체가 없음)이 이 필요성의 직접적
근거다. Manifest 없이는 "TSU가 어떤 자료를 읽어야 하는가"를 판단할
방법이 구조적으로 없다 — Registry는 서지 정체성만 다루고 처리
상태를 다루지 않기 때문이다(상세: `NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md` §Phase1).

---

## 2. Entity 관계

```
Author → Work → Edition(조건부) → Volume(조건부) → Issue(조건부) → Source → Manifest Entry → TSU
```

- **Manifest Entry는 Source와 별도 Entity, 1:1 관계**(Source의 확장
  아님) — 갱신 빈도 차이(정적 서지 vs 동적 처리 상태)가 근거.
- **Source:Manifest = 1:1**(OCR/TSU/Embedding을 별도 Manifest로
  나누지 않고 `processing_status`가 전진하는 단일 Entry).

상세 근거: `NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md` §Phase2.

---

## 3. Schema Version 영향

Manifest Schema는 새 필드 집합(`manifest_id`, `processing_status`,
`tsu_access`, `schema_version` 등)을 정의하지만, **이는 Registry
Source entity나 corpus manifest(`source_manifest.schema.yaml`)의
기존 필드를 변경하지 않는다** — 완전히 새로운 계층이므로 기존
`schema_version 2.1.0/2.2.0` 값 체계와 별도로 자체 `schema_version`을
가질 것을 제안한다(예: Manifest Schema 자체의 버전을 "1.0"부터 시작
— corpus manifest의 2.x 계열과 혼동 방지). **이번 작업에서 실제 값을
확정하거나 파일을 만들지는 않았다.**

---

## 4. ADR 영향 (Phase 5)

**판정: 신규 ADR-019 필요 — 채택함.** 기존 ADR(001/014/015/016/017/018)
중 어느 것도 Registry-TSU 경계의 새 계층을 다루지 않는다. 기존 ADR에
pointer만 추가하는 방식도 검토했으나, Manifest Layer는 그 자체로
완결된 Architecture Decision(Entity 관계, Schema, Lifecycle 전부
포함)이라 독립 ADR이 적절하다고 판단했다 — "ADR 소급 수정 금지"
관례의 일관된 네 번째 적용. 상세는 [ADR-019](architecture/ADR-019-NAE-Corpus-Manifest-Layer.md).

기존 ADR 6건 각각의 영향:

| ADR | 개정 필요? | 비고 |
|---|---|---|
| ADR-001(Retrieval Authority) | 아니오 | Manifest는 TSU 이전 단계, RetrievalEngine 무관 |
| ADR-014(Modern Corpus) | 아니오 | Domain Separation 원칙 그대로 유지 |
| ADR-015(Ingestion Standard) | 아니오 | Lifecycle 10단계와 Manifest Lifecycle 7단계는 서로 다른 층위(전자는 등록 절차, 후자는 처리 상태) — 상세 대응은 Remaining Risk 참고 |
| ADR-016(Authority Model) | 아니오 | Entity 모델(정적 구조)과 Manifest(동적 상태)는 층위가 다름 |
| ADR-017(ID Governance) | 아니오 | `manifest_id = source_id` 재사용, 신규 ID 체계 없음 |
| ADR-018(Periodical Extension) | 아니오 | `work_type` 조건부 필드 규칙을 그대로 재사용 |

---

## 5. Migration 가능 여부

**NOT READY** — 이번 작업은 설계까지다. Migration Plan(Phase 0~5,
`NAE_CORPUS_MANIFEST_MIGRATION_PLAN_001.md`)의 Phase 0(Architecture
Design)만 완료됐고, 실제 스키마 파일 작성(Phase 1)조차 아직
착수하지 않았다.

---

## 6. Remaining Risks

| # | 리스크 | 설명 |
|---|---|---|
| 1 | Manifest Lifecycle(7단계)과 Ingestion Lifecycle(ADR-015, 10단계) 관계 미정리 | 두 Lifecycle이 부분적으로 겹치는 것처럼 보일 수 있음(둘 다 "Registration"류 단계를 가짐) — 실제로는 Ingestion Lifecycle이 상위(자료 등록 전체 절차), Manifest Lifecycle이 그 중 "Manifest Created 이후"만 다루는 하위 집합이나, 이 관계가 문서로 명시적으로 정리되지 않았다 |
| 2 | Manifest 자체 schema_version 값 미확정 | §3에서 "별도 버전 체계 제안"만 했을 뿐 실제 시작 값(예: "1.0")을 공식 확정하지 않음 — Phase 1(Schema 실제 작성) 착수 시 결정 필요 |
| 3 | Validator 도구 중복 가능성 | `source_validator.py`(corpus manifest), `authority_validator.py`(설계만, Registry), 그리고 이번에 신설된 Manifest 검증 필요성까지 — 세 번째 도구를 신설할지 기존 도구를 확장할지 Migration Plan Phase 4에서 결정 필요, 이번 설계는 이 질문을 열어둔 채로 남김 |
| 4 | processing_status 역행 처리 미상세 | "단조 증가 원칙, 검증 실패는 반려로 별도 취급"이라고만 정의 — 반려 시 정확히 어느 단계로 되돌아가는지 등 세부 규칙은 없음 |

---

## 완료 조건 답변

1. **Manifest Layer가 필요한가?** — **필요함**(§1).
2. **Source와 Manifest 관계는?** — **별도 Entity, 1:1**(§2).
3. **Monograph/Periodical 통합 가능한가?** — **가능(PASS)**, 조건부 필드로 흡수(`NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md` §Phase4).
4. **Schema v2.2.0 전에 Manifest 설계가 필요한가?** — **예.** Manifest Entry가 `edition_id`/`volume_id`/`issue_id`를 참조하려면 그 필드들이 먼저 존재해야 하고, 이는 Schema v2.2.0(author_type/issue_id 등)이 실제 적용된 이후에나 Manifest의 참조 대상이 완전해진다 — 순서상 **설계는 지금 해도 되지만 Manifest의 "실제 데이터 생성"은 Schema v2.2.0 적용 이후**가 되어야 한다(Migration Plan Phase 1이 Phase 5 TSU Migration보다 먼저인 이유와 동일 논리).
5. **Metadata Migration 가능 상태인가?** — **아니오, NOT READY**(§5).
6. **TSU Pipeline 진행 가능 상태인가?** — **아니오.** Manifest Layer 자체가 아직 설계 단계이고, `processing_status=TSU_ELIGIBLE`을 판정할 수단이 없다.

---

## 로드맵 갱신

```
Architecture Revision        ✅
Authority Registry           ✅
Periodical Extension         ✅
Condition Review             ✅
Manifest Architecture         ✅ (이번 작업 — 설계까지, ADR-019 포함)

NAE-CORPUS-MANIFEST-ARCHITECTURE-REVIEW-001(C1 독립 검증)   NEXT
Manifest Schema 실제 작성(Migration Plan Phase 1)              FUTURE
Schema v2.2.0 적용                                              AFTER REVIEW
Metadata Migration                                                FUTURE
TSU Pipeline                                                        FUTURE
```

---

*Manifest 실제 생성, Schema v2.2.0 적용, Authority Registry 변경,
Pilot 데이터 수정, Validator 수정, TSU/Embedding 생성, Retrieval 변경,
Git Commit — 전부 수행하지 않음.*

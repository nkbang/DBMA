# NAE Periodical Condition Resolution Report 001

**Project:** NAE-PERIODICAL-CONDITION-RESOLUTION-001
**Date:** 2026-08-02
**Nature:** C1 Review-002 조건 4건 해소 시도 — Schema/Registry/RAW/코드 변경 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

C1 Final Architecture Review-002(READY WITH CONDITIONS, 조건 4건)의
각 조건을 순서대로 조사했다. 결과: **2건은 진전(author_type 문서화
완료, Title History는 RAW 1차 사료로 강하게 뒷받침), 1건은 논리
검증만 가능(Issue Model, 실자료 없음), 그리고 TSU Field Readiness
조사 과정에서 C1도 몰랐던 더 근본적인 gap을 새로 발견했다** — 실제
TSU가 읽을 corpus manifest 계층이 monograph도 Periodical도 Production
레벨에서는 전혀 존재하지 않으며, Periodical은 Pilot 레벨에서조차
manifest 계층을 만든 적이 없다(Registry만 존재). 이 신규 발견으로
**Migration Readiness는 C1의 "READY WITH CONDITIONS"에서 하향
재평가**했다 — 아래 §4.

---

## 2. C1 조건 대응표

| 조건 | 상태 | 근거 |
|---|---|---|
| TSU Field Readiness | **FAIL** | [Report-001](NAE_PERIODICAL_TSU_FIELD_READINESS_REPORT_001.md) — Registry 필드 자체는 확인되나(monograph PASS, periodical WARNING), Production/Periodical corpus manifest가 전무해 TSU 생성이 구조적으로 불가능한 상태 |
| author_type 준비 | **PASS(문서화만)** | GOVERNANCE §5.1 + Revision 001에 반영 완료. 단 `source_manifest.schema.yaml`(실제 스키마 파일)에는 미반영 — "준비"는 됐으나 "적용"은 아님 |
| Title History | **PASS WITH CONDITIONS** | [Validation-001](NAE_PERIODICAL_TITLE_HISTORY_VALIDATION_001.md) — 1817년 issue 본문에서 1803년 간행물("Massachusetts Baptist Missionary Magazine", 4권 완결) 계승을 자기 증언하는 1차 사료 확보. 완전한 서지 전수 검증은 아님(1803~1817 공백기 미확인) |
| Issue Model | **PASS(가상 검증만)** | [Test-001](NAE_PERIODICAL_ISSUE_MODEL_TEST_001.md) — ID 스킴은 충돌 없이 동작(Python 시뮬레이션 실행 확인). 실제 "동일 volume 복수 issue" 자료는 여전히 미확보 |

---

## 3. Schema Version 결정 (Phase 5)

**판정: B — v2.2.0 적용 필요**(결정만, 미실행)

근거: `author_type`, `editor_id`, `issue_id`, `title_history`,
`continues_work_id`, `continued_by_work_id` 6개 필드 전부 **optional
추가**이며 기존 데이터를 무효화하지 않는다(GOVERNANCE §2.2 Minor
기준과 일치, C1 Review-002 §5.3에서도 동일 결론). `v2.1.0 유지(A안)`는
기각한다 — Issue Entity와 Organization Author를 스키마 차원에서
전혀 지원하지 못한 채로는 §2 표의 "author_type 준비"조차 "문서화만"에
머물게 되어, 실제 Periodical Registry Expansion Pilot(3차)에 착수할
수 없다.

**이번 작업에서 실제 스키마 파일은 수정하지 않았다**(금지 사항 준수).

---

## 4. Migration Readiness 재평가

### C1 Review-002 대비 변경 사항

C1은 "TSU 필요 필드(periodical: volume_id+issue_id, monograph:
edition_id) 모두 갖춘 자료 확인"을 BLOCKER로 지정했다. 이번 Phase 1
조사에서 그 확인을 시도한 결과, **문제가 C1이 상정한 것보다 크다는
것을 발견했다**:

- C1의 BLOCKER는 "필드가 자료에 존재하는가"를 묻는 것이었으나, 실제
  조사 결과는 "TSU가 읽을 자료(corpus manifest) 자체가 Production
  레벨에 없다"는 **더 근본적인 gap**이었다.
- Monograph는 그나마 Pilot 레벨(Dagg/Hiscox/Fuller, 10건)에 TSU
  준비된 manifest가 있으나, **Periodical은 Pilot 레벨에서조차 manifest
  계층을 만든 적이 없다**(Registry만 존재) — Pilot-001/002 대비
  Periodical Pilot이 한 단계 덜 진행된 상태였음이 이번에 처음
  드러났다.

### 최종 판정: **NOT READY**

C1의 "READY WITH CONDITIONS"에서 **하향 조정**한다. 조건이 "충족되면
바로 격상 가능한 수준"이 아니라, 조건 중 하나(TSU Field Readiness)가
추가 조사 결과 **범위가 더 넓어졌기 때문**이다 — 단순히 필드를
확인하는 것을 넘어, Periodical Pilot에 corpus manifest 계층 자체를
새로 만드는 작업이 선행되어야 한다.

---

## 완료 보고 형식 (명령서 요구 항목)

1. **C1 BLOCKER 해결 여부** — **해결되지 않음, 오히려 범위가 넓어짐**(§4).
2. **author_type 반영 위치** — `docs/NAE_METADATA_GOVERNANCE_v1.md` §5.1(신규 서술) + `docs/NAE_PERIODICAL_ARCHITECTURE_REVISION_001.md` §4(포인터 추가). **`resources/theological_sources/modern/source_manifest.schema.yaml`에는 미반영**(금지 사항).
3. **Title History 검증 결과** — RAW 1차 사료(1817년 issue 서문)로 계승 관계가 강하게 뒷받침됨, 완전한 서지 전수 검증은 아직 아님([Validation-001](NAE_PERIODICAL_TITLE_HISTORY_VALIDATION_001.md)).
4. **Issue Model 검증 결과** — ID 스킴의 논리적 타당성은 확인(가상 시나리오 3/3 PASS), 실자료 기반 검증은 여전히 없음([Test-001](NAE_PERIODICAL_ISSUE_MODEL_TEST_001.md)).
5. **Schema v2.2.0 적용 여부** — **적용 필요 판정**(B안), 이번엔 미적용(§3).
6. **Metadata Migration 가능 여부** — **NOT READY**(§4, C1 대비 하향 재평가).
7. **다음 단계 권고**:
   - (a) Periodical Pilot에 corpus manifest 계층(`source_manifest.yaml` 동등물, `citation_policy`/`tsu_access` 포함) 신규 작성 — Pilot-001/002와 동등한 수준으로 끌어올리는 작업.
   - (b) Schema v2.2.0을 실제 `modern/source_manifest.schema.yaml`에 적용(별도 승인).
   - (c) 1803~1817 공백기(Vol. 2~4) 자료 추가 확보 시도(가능하면) 또는 "미확인"으로 명시적 종결.
   - (d) 3차 Pilot(동일 volume 복수 issue 실자료)은 여전히 필요.

---

## 로드맵 갱신

```
Periodical Architecture Revision   ✅
C1 Final Architecture Review        ✅
Periodical Condition Resolution      ✅ (이번 작업 — 조건 조사, TSU gap 신규 발견)

Periodical Pilot Manifest 보강(corpus manifest 계층 신규)   NEXT (BLOCKER 실질 해소 조건)
Schema v2.2.0 실제 적용                                      NEXT (별도 승인)
NAE-PERIODICAL-CONDITION-REVIEW-003(C1 독립 검증)              NEXT
Periodical Registry Expansion Pilot(3차)                        FUTURE
Corpus Metadata Migration                                        FUTURE
```

---

*source_manifest.schema.yaml 수정, Authority Registry 데이터 추가,
Pilot 데이터 변경, RAW 변경, Validator 코드 변경, TSU/Embedding 생성,
Retrieval 변경, Git Commit — 전부 수행하지 않음.*

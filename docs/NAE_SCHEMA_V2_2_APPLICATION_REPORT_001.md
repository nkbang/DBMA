# NAE Schema v2.2.0 Application Report 001

**Project:** NAE-SCHEMA-V2.2-APPLICATION-001
**Date:** 2026-08-02
**Nature:** Schema Application 설계 — 실제 schema yaml 변경 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

`resources/theological_sources/modern/source_manifest.schema.yaml`
(v2.1.0)을 실측 재확인한 결과, ADR-018/019가 요구하는 변경 외에
**v2.1.0 자체의 숨은 결함**을 하나 더 발견했다: `edition_id.required`가
현재 무조건 `true`로 고정되어 있어, Edition 계층을 생략하는
정기간행물(ADR-018 §3.1)을 이 스키마로는 애초에 등록할 수 없다 —
이는 이번 명령서가 예상한 "필드 추가" 수준을 넘어서는 **기존 필드의
조건부 완화**가 필요함을 뜻한다. 이번 보고서는 이 발견을 포함해
Author/Work/Issue/Volume/TSU/Manifest 6개 영역의 변경을 확정하고,
**Minor bump(v2.1.0→v2.2.0), 완전 하위 호환**으로 판정했다. 실제
스키마 파일은 여전히 수정하지 않았다.

---

## 2. Schema v2.2.0 Change List

| # | 변경 | 유형 | 근거 |
|---|---|---|---|
| 1 | `author_type: person\|organization` 필드 추가(Author) | 필드 추가 | ADR-018 §3.2 |
| 2 | `editor_id` 필드 추가(Work) | 필드 추가 | ADR-018 §3.2 |
| 3 | `work_type` 필드 신설(Work) — **corpus manifest 스키마에는 이제까지 이 필드가 아예 없었음**(실측, §1) | 필드 신설 | ADR-016(Registry에는 이미 있었으나 corpus manifest에는 미반영이었던 gap) |
| 4 | `title_history[]`/`continues_work_id`/`continued_by_work_id` 필드 추가(Work) | 필드 추가 | ADR-018 §3.3 |
| 5 | `issue_id`/`issue_number`/`publication_date` 필드 추가(Source) | 필드 추가 | ADR-018 §3.1, 이번 명령서 Phase2-3 |
| 6 | **`edition_id.required`를 `true`→조건부(`work_type≠periodical`일 때만 필수)로 완화** | **기존 필드 제약 완화** | 신규 발견(§1) — Minor bump로 처리 가능한지 §6에서 별도 검토 |
| 7 | Manifest Authority Reference 필드(§Phase5)와 정합성 재확인 | 검증만, 필드 변경 아님 | ADR-019 |

---

## 3. Field Specification

### 3.1 Author Extension

```yaml
author_type:
  type: enum
  required: false        # 기본값 person으로 간주(§Version Policy)
  values: [person, organization]
  description: ADR-018. 값 없으면 person으로 취급 — 기존 Author entry 전부 영향 없음.
```

**기존 Person Author 영향**: 없음(필드가 optional이고 기본값이 기존
동작과 동일). **Organization Author FK 가능 여부**: 가능 —
`Work.author_id`가 `author_type=organization`인 Author를 가리켜도
FK 검증 로직(참조 대상 존재 여부만 확인)은 변경이 필요 없다.

### 3.2 Periodical Work 지원

**Phase1 확인 결과 — 명령서 전제 정정**: 명령서 Phase2-2는 현재
`work_type` 값이 `book/collection/sermon`이라고 전제했으나, **실측
결과 corpus manifest 스키마에는 `work_type` 필드 자체가 없었다**
(§1). Registry(`authority/works.yaml`, Registry Design v1 §2.2)에는
`monograph`/`multi_volume` 2개 값이 이미 있다 — 이번 v2.2.0은
**Registry의 실제 값 체계를 corpus manifest에 처음 반영**하면서
`periodical`을 추가하는 것으로 정정한다.

```yaml
work_type:
  type: enum
  required: false   # 신설 필드이므로 optional, 값 없으면 monograph로 간주
  values: [monograph, multi_volume, periodical]   # book/collection/sermon 아님 — Registry 실제 값과 통일

editor_id:
  type: string
  required: false
  description: Author FK(author_type=person). ADR-018 §3.2 — 발행 조직(author_id)과 편집자 구분.

title_history:
  type: array[object]
  required: false
  fields: {title: string, start_date: string, end_date: string|null}
  description: ADR-018 §3.3. periodical에서 주로 사용, monograph는 기존 title_variants 계속 사용.

continues_work_id:
  type: string
  required: false
  description: 이 Work가 계승하는 이전 Work의 work_id. ADR-018 §3.3, 자동 병합 안 함.

continued_by_work_id:
  type: string
  required: false
  description: 이 Work를 계승하는 다음 Work의 work_id.
```

### 3.3 Issue Entity 지원

```yaml
issue_id:
  type: string
  required: false   # periodical만 조건부 필수 — 아래 §Phase4/조건표
  description: ADR-018. periodical 전용, monograph에는 값이 있으면 안 됨(Validator 책임, Validator Boundary Design-001).

issue_number:
  type: integer
  required: false
  description: RAW 디렉토리명을 canonical 출처로(volume_number와 동일 원칙, Pilot-002 §6).

publication_date:
  type: string
  required: false
  description: "YYYY, YYYY-MM 등 확보된 정밀도까지만(Periodical Pilot Report-001 issues.yaml 실제 표기 관례)."
```

**"Monograph에는 적용하지 않음" 강제 방법**: 스키마 자체는 3필드
전부 optional로 열어두고, **강제(monograph에 값이 있으면 FAIL)는
Validator 책임**으로 이전한다 — Manifest Schema Design v1과 동일한
"스키마는 유연, 강제는 검증기" 원칙(NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md §Phase2 근거 재사용).

### 3.4 Volume 확장 — Periodical에서 재사용 가능 여부

**결정: 재사용 가능, 신규 Entity 불필요.** 기존 `volume_id`/
`volume_number`(v2.1.0에 이미 존재, ADR-016)를 정기간행물에도 그대로
사용한다 — monograph에서는 "권" 단위, periodical에서는 "연간
volume" 단위로 의미가 자연스럽게 확장될 뿐 필드 정의를 바꿀 필요가
없다.

```
Volume
  │
Issue     (periodical에서만 volume 하위에 issue가 존재 — monograph는 volume→source 직결, 기존 그대로)
```

---

## 4. Authority Model Compatibility(Phase 3)

```
Monograph:   Author        → Work            → Edition → Volume(선택) → Source
Periodical:  Organization/Editor → Work(periodical) → Volume        → Issue → Source
                                                         (Edition 생략, §2 변경 6)
```

두 경로 모두 §3.2~3.4에서 정의한 동일 필드 집합을 공유하며, 자료
유형에 따라 일부 필드만 채운다(조건부 필수/생략) — 별도 스키마
분기 없음(ADR-018/Manifest Architecture v1이 이미 확립한 "공통
스키마 + 조건부 필드" 원칙 재확인).

---

## 5. Periodical Support Model

§3.2/3.3/3.4를 종합하면 정기간행물 지원에 필요한 신규 필드는
`work_type=periodical`, `editor_id`, `title_history`,
`continues_work_id`/`continued_by_work_id`, `issue_id`,
`issue_number`, `publication_date` 7개다. 전부 optional — 기존
monograph 자료(v2.1.0으로 이미 등록된 Pilot-001/002 10건)는 이
필드들이 전무해도 그대로 유효하다(Backward Compatibility, §6).

---

## 6. TSU Impact Analysis (Phase 4)

### 현재(v2.1.0 GOVERNANCE §6) TSU Required

```
edition_id: 필수
volume_id: 조건부(다권본만)
```

### 변경 결정

```
edition_id: 필수 → 조건부(work_type≠periodical일 때만 필수)
volume_id:  조건부(다권본 또는 periodical) — 변경 없음, 범위만 확대
issue_id:   신규 조건부 필수(work_type=periodical일 때만)
```

`issue_id`는 **"필수/조건부/선택" 중 조건부로 확정**한다(명령서
Phase4가 요구한 3택1) — monograph에는 forbidden에 가깝고(§3.3),
periodical에는 필수이므로 절대적 "필수"도 절대적 "선택"도 정확하지
않다.

이 변경은 ADR-018 §3.4에서 이미 결정된 내용이며, 이번 보고서는 그
결정이 §2 변경 6(edition_id 스키마 레벨 완화)과 **일관되게 맞물려야
함**을 확인한 것이다 — TSU 게이트 레벨의 "조건부 필수"만 있고
스키마 레벨의 `required: true`가 그대로 남아 있으면 두 계층이
모순되므로, 이번 기회에 스키마 레벨도 함께 정정 대상에 포함시켰다
(§2 변경 6의 근거).

---

## 7. Manifest Compatibility (Phase 5)

Manifest Authority Reference(`NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md`
§Phase2 — `author_id`/`work_id`/`edition_id`/`volume_id`/`issue_id`)와
이번 corpus manifest v2.2.0 필드 집합을 대조한 결과: **완전히
일치한다.** Manifest의 `issue_id`도 corpus manifest와 동일하게
"optional 필드 + Validator가 강제" 원칙을 쓰기로 이미 설계돼 있어
(Manifest Schema Design v1 §Phase2 근거), 이번 corpus manifest
변경과 재확인만 하면 되고 추가 조정은 없다.

---

## 8. Migration Impact (Phase 7, 분석만 — 실행 없음)

| 작업 | 내용 | 착수 시점 |
|---|---|---|
| 1. Existing Registry Mapping | `authority/works.yaml`의 `monograph`/`multi_volume` 값을 corpus manifest `work_type` 신규 필드로 그대로 옮겨 적는 매핑표 작성 | Schema v2.2.0 실제 적용(별도 승인) 이후 |
| 2. Pilot Compatibility Check | Pilot-001/002(10건, v2.1.0) 재검증 — `edition_id` required 완화가 기존 데이터에 영향 없는지(있던 필드를 없앤 게 아니라 제약만 완화이므로 영향 없을 것으로 예상, 실측 필요) | Schema 적용 직후 |
| 3. Validator Requirement Update | `docs/NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md`에 `work_type` 분기, `issue_id` monograph-forbidden 규칙 반영 — 코드 미구현, 문서만 | Schema 적용과 병행 가능 |
| 4. Manifest Pilot Preparation | Periodical Condition Resolution Report-001 §4가 지적한 "Periodical corpus manifest 부재" gap을 메우는 실제 작업 — Schema Migration Guide v2.2 §Phase2 | Schema v2.2.0 적용 이후 |

---

## Version Policy 결정 (Phase 6)

**Minor bump(v2.1.0 → v2.2.0) 적절, 단 조건부 재검토 필요 항목 1건.**

| 검토 항목 | 판정 |
|---|---|
| 신규 필드가 Minor인가 | 예 — 8개 신규 필드 전부 optional |
| **기존 필드 제약 완화(`edition_id.required`)가 Minor인가** | **판정: Minor로 유지 가능.** required를 `true→false`(완화)로 바꾸는 것은 **기존에 유효했던 데이터를 무효화하지 않는 방향**의 변경이다(엄격했던 규칙이 느슨해짐 — 반대 방향, 즉 optional을 required로 좁히는 변경이었다면 Major 검토 대상이었을 것). GOVERNANCE §2.2 기준(Major=필드 제거/의미 변경/구조 변경)에 해당하지 않는다 |
| Backward Compatibility | **유지됨** — v2.1.0으로 등록된 기존 자료(edition_id가 이미 채워진 Pilot-001/002)는 v2.2.0에서도 그대로 유효(값이 있으면 있는 대로 인정, 필수 요건만 완화됐을 뿐 금지된 게 아님) |
| 기존 데이터 Migration 필요 여부 | **불필요** — 완화 방향 변경이라 기존 데이터를 고칠 이유가 없음 |

---

## 9. Remaining Risks

| # | 리스크 | 설명 |
|---|---|---|
| 1 | `edition_id.required` 완화가 실제 Validator 구현에 어떻게 반영될지 미정 | `work_type` 필드가 없는 기존 v2.1.0 entry(전부 monograph로 암묵 간주됨)에 대해 이 완화 규칙을 어떻게 적용할지 — "필드가 없으면 monograph로 간주"라는 기본값 규칙이 Validator 코드에 정확히 구현돼야 함(Validator Requirements v1 갱신 필요, §8 항목 3) |
| 2 | `work_type` 필드가 이제까지 corpus manifest에 전혀 없었다는 사실이 Pilot-001/002 데이터에도 없음을 뜻함 | 재검증(§8 항목 2) 전까지는 실제 영향이 확인되지 않은 상태 |
| 3 | Manifest Layer(ADR-019)도 여전히 설계 단계 | 이번 Schema 변경이 적용돼도 Manifest 실 데이터 생성은 별도 승인 필요(로드맵상 Migration/TSU는 BLOCKED 유지) |

---

## 완료 조건 답변

1. **Schema v2.2.0 설계 적용 완료 여부** — **설계 완료**(실제 파일 미변경).
2. **author_type 추가 결정** — 추가(optional, 기본값 `person`).
3. **periodical work_type 지원 여부** — 지원(신규 필드 자체 신설, 명령서 전제였던 book/collection/sermon은 실측 결과 존재하지 않아 정정 — 실제로는 monograph/multi_volume/periodical 3값).
4. **issue_id 추가 여부** — 추가(조건부: periodical 필수, monograph forbidden — Validator 책임).
5. **title_history 구조 반영 여부** — 반영(`title_history[]` + `continues_work_id`/`continued_by_work_id`).
6. **TSU Required Field 변경 여부** — 변경 — `edition_id`가 조건부 필수로 완화, `issue_id`가 신규 조건부 필수로 추가.
7. **Manifest Layer 연결 가능 여부** — 가능(§7, 완전 일치 확인).
8. **Backward Compatibility 유지 여부** — 유지(§Version Policy).
9. **실제 Schema 파일 변경 여부** — **변경하지 않음**(설계 문서만, 금지 사항 준수).
10. **Metadata Migration 착수 가능 여부** — **불가**(BLOCKED) — Schema v2.2.0이 실제 적용된 적이 없고, Validator/Manifest 실 데이터도 없다.

---

## 로드맵 갱신

```
Architecture         ✅
Governance            ✅
Authority Model        ✅
ID Governance           ✅
Manifest Design           ✅
Schema v2.2 Design         ✅ (이번 작업)

Validator                    NEXT
Pilot                         FUTURE
Migration                      BLOCKED
TSU                              BLOCKED
```

---

*schema yaml 생성, manifest 수정, Pilot/Registry 수정, RAW 변경,
Corpus Migration, TSU/Embedding 생성, Retrieval 코드 변경, Validator
코드 구현, Git Commit — 전부 수행하지 않음.*

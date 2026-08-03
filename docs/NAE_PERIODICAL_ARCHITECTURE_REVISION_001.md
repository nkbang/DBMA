# NAE Periodical Architecture Revision 001

**Project:** NAE-PERIODICAL-ARCHITECTURE-REVISION-001
**Date:** 2026-08-02
**Nature:** Architecture Revision Only — 실제 데이터 Migration, Registry 확대, Schema 적용 없음
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

C1 [Periodical Authority Review-001](NAE_PERIODICAL_AUTHORITY_REVIEW_001.md)
(판정: APPROVED WITH CONDITIONS, BLOCKER 1건·WARNING 3건)의 조건을
반영해 Periodical Extension 설계를 확정했다. Entity Model은 **안
1**(Author/Organization→Work→Volume→Issue→Source, Edition 계층은
정기간행물에서 생략)을 최종 채택 — 이는 이미 Pilot에서 검증한 Option A와
동일하며 C1이 "적절"로 승인한 모델이다. C1이 미해결로 남긴 두 항목
(Organization Authority, Title History)에 대해 이번 Revision에서 구체적
정책을 확정했다: **Organization Authority는 `author_type` 필드 추가로
해결**(별도 Entity 신설 아님), **Title History는 `title_history[]`
구조로 확정**(단순 alias 배열보다 시간순 구조화). 신규 [ADR-018](architecture/ADR-018-NAE-Periodical-Authority-Extension.md)을
채택했다(ADR-016/017 미개정). `schema_version`은 `2.1.0 → 2.2.0`(Minor)
로 갱신 대상이나 **이번 작업에서 실제 스키마 파일은 수정하지 않았다**.

---

## 2. C1 Review 대응표

| C1 항목 | C1 판정/권고 | CUE 결정 |
|---|---|---|
| Entity Model(Option A) | 적절(§4.1) | **확정 채택** — 안 1로 재확인(§3) |
| Work:Edition 1:N | 적절(§4.2) | 변경 없음(기존 ADR-016 그대로) |
| Volume Entity | 적절(§4.3) | 변경 없음 |
| Canonical ID Rule | 적절(§5.1) | 변경 없음(ADR-017 그대로) |
| Collision Policy | 적절(§5.2) | 변경 없음 |
| 정기간행물 ID 확장(3자리) | 적절하게 분리 처리(§5.3) | 변경 없음, ADR-018에도 재확인만 |
| **Organization Author 문제**(Risk #3, WARNING) | "우회적 해결, 근본 해결 필요" — `author_type` 필드 또는 `CorporateAuthor` Entity 권고 | **`author_type: person\|organization` 필드 추가로 확정**(§4) — 별도 Entity는 기각 |
| **제호 계승 관계**(Risk #1, WARNING) | 서지 검증 권고, "계승 관계 확인되면 병합 필요" | **`title_history[]` + `continues_work_id`/`continued_by_work_id` 관계 필드로 확정**(§5) — 서지 검증 자체는 이번 Revision 범위 밖(Remaining Risk 유지) |
| 동일 volume 내 복수 issue 미검증(Risk #2, WARNING) | 추가 issue 확보로 검증 권고 | 이번 Revision에서 미해결 유지(§10 Remaining Risks) — 3차 Pilot 확대 대상 |
| Migration 준비도(Risk #6, **BLOCKER**) | TSU 필요 필드 모두 갖춘 자료 확인 전까지 Migration 금지 | **BLOCKER 조건 재확인**, §9 Migration 전제조건에 명문화 |

---

## 3. 최종 Entity Model (Phase 2)

**안 1 채택**:

```
Author / Organization(author_type 구분)
        └── Work(work_type: periodical)
                └── Volume
                        └── Issue
                                └── Source
```

(Edition 계층은 정기간행물에서 생략 — Pilot Design v1 §2 Option A와
동일, C1이 "적절"로 승인)

**안 2(Organization→Periodical→Series→Volume→Issue→Source) 기각 사유**:
Periodical을 Work와 별도의 최상위 Entity로 만들고 Series까지 추가하면
Author→Work 인프라(Registry Build-001, ADR-017)를 정기간행물 전용으로
중복 구축해야 한다 — Pilot Design v1이 이미 "Option B 기각" 근거로
제시한 것과 동일(중복 인프라, CLAUDE.md 과설계 금지 원칙). Series
관계는 §5에서 경량 필드(`continues_work_id`)로 충분히 표현 가능해
별도 Entity가 불필요함을 이번 Revision에서 재확인했다.

---

## 4. Organization Authority 정책 (Phase 3)

> **2026-08-02 추가(NAE-PERIODICAL-CONDITION-RESOLUTION-001 Phase 2)**:
> 아래 결정이 [`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §5.1에
> Person/Organization 필드 정의 + Editor 관계 설명으로 문서화 완료됐다
> (스키마 파일 미반영, 문서만).

### 결정: **필요 — `author_type` 필드 추가**(별도 Entity 신설 아님)

```yaml
# Author entity 확장(기존 필드 유지, 1개 필드 추가)
author_id: string
author_type: person | organization   # 신규
canonical_name: string
aliases: array[string]
birth_year: integer|null   # organization이면 항상 null(설립연도로 대체하지 않음 — §근거)
death_year: integer|null   # organization이면 항상 null(해산연도 있어도 대부분 활동 중 — 아래 근거)
tradition: string|null
notes: string|null
```

**근거**:
- C1이 제시한 두 대안(필드 추가 vs `CorporateAuthor` 별도 Entity) 중
  필드 추가를 선택한 이유: `works.author_id` FK가 Person이든
  Organization이든 동일하게 동작해야 하는데, 별도 Entity를 만들면
  `author_id` FK 대상이 두 테이블로 갈라져 Registry Validation Tool
  (Registry Design v1 §Phase5, 아직 미구현)의 Reference 검사 로직이
  이원화된다 — 필드 하나로 구분하는 편이 참조 무결성 검사를 단순하게
  유지한다.
- `birth_year`/`death_year`를 조직의 설립/해산연도로 재해석하지 않고
  **항상 null 고정**으로 결정 — Baptist Missionary Society 등은
  현재도 후신 조직이 활동 중인 경우가 많아 "해산연도"가 서지학적으로
  모호하고, 설립연도는 `notes` 자유 텍스트로 충분히 기록 가능(구조화
  필드로 강제할 실익이 낮음).

### 관계 처리 방법(Editor 등)

Phase 3 체크리스트가 언급한 Baptist Missionary Society/Missionary
Board/Publishing Organization/Editor 4가지 중, 발행 조직(Publishing
Organization)은 `Work.author_id`가 가리키는 Author(type=organization)로
표현한다. **Editor는 별도** — 개인이므로 `author_type=person`인 별도
Author entity로 등록하고, Work에 선택 필드 `editor_id`(신규,
`authors.yaml` FK)로 연결한다. `author_id`(발행 조직)와 `editor_id`
(편집자 개인)를 분리함으로써 "누가 발행했는가"와 "누가 편집했는가"를
동시에 표현 가능(둘 다 필요한 경우가 많은 정기간행물 특성 반영).

---

## 5. Issue Model 정책 (Phase 4)

### 결정: **2. Periodical 전용 확장**(정식 Entity로 전체 승격 아님, 완전 불필요도 아님)

Issue는 `work_type: periodical`인 Work의 하위에서만 나타나는 조건부
Entity다 — Volume이 이미 "다권본에서만 사용하는 조건부 Entity"로
설계된 것(Registry Design v1 §2.4)과 동일한 원칙을 Issue에도 적용.
단권/다권 monograph는 Issue를 생성하지 않는다.

**"1. 정식 Entity 승격"을 기각한 이유**: 모든 Work 유형에 Issue를
허용하면 monograph에서는 항상 빈 채로 남는 계층이 생겨 스키마가
불필요하게 넓어짐(CLAUDE.md "불필요한 추상화 금지" 원칙).
**"3. 불필요"를 기각한 이유**: Pilot에서 Volume만으로는 "같은 volume
안의 서로 다른 발행월"을 구분할 수 없음이 실측으로 확인됨(Pilot
Report §1 Q3 "Issue Entity 필요" 결론 재확인).

---

## 6. Title History 처리 (Phase 5)

### 결정: **Option A — `title_history[]`**(+ Series 관계는 경량 필드로 보완)

```yaml
# Work entity 확장(periodical에 한해 사용, monograph는 기존 aliases 유지)
title_history:
  - title: "Massachusetts Baptist Missionary Magazine"
    start_date: "1803"
    end_date: null
  - title: "The American Baptist Magazine, and Missionary Intelligencer. New Series"
    start_date: "1817"
    end_date: null
continues_work_id: string|null          # 신규 — 이 Work가 계승하는 이전 Work
continued_by_work_id: string|null       # 신규 — 이 Work를 계승하는 이후 Work
```

**Option B(별도 Series Entity) 기각 사유**: §3에서 안 2(Periodical
전용 최상위 구조)를 기각한 것과 동일 논리 — Series 관계는 두 Work
사이의 단순한 "이전/이후" 관계일 뿐이라 완전한 Entity(자체 ID 체계,
Registry 파일)를 만들 실익이 없다.

**Option C(단순 Work alias, Pilot에서 실제 사용한 방식) 대비 개선**:
Pilot(`authority/pilot_periodical/periodicals.yaml`)은 `aliases`
평면 배열로 제호 변화를 기록했는데, 이는 "어느 표기가 언제부터
언제까지 쓰였는가"라는 **시간 순서 정보를 잃는다**. `title_history[]`는
각 표기에 `start_date`/`end_date`를 부여해 이 정보를 보존한다 — 신규
정책이며, 기존 Pilot YAML은 이번 Revision에서 **수정하지 않는다**
(명령서 금지 사항 "기존 Pilot 변경" 준수 — 정책만 정의, 소급 적용은
범위 밖).

**1803 vs 1817 분리 등록 자체는 유지**: C1 Risk #1(제호 계승 관계 서지
미검증)은 이번 Revision에서 해소하지 않는다 — `continues_work_id`
필드는 "검증되면 연결할 수 있는 자리"를 마련한 것이지, 지금 두 Work를
자동으로 병합한다는 뜻이 아니다(자동 병합 금지 원칙, GOVERNANCE §1
Philosophy #3과 일관 — 서지 전문가 확인 전까지는 사람이 미확정 상태로
둔다).

---

## 7. ID Governance 영향 (Phase 6 관련)

`author_type`/`title_history`/`continues_work_id`/`editor_id` 신규
필드는 **ID 생성 규칙 자체에는 영향 없음** — ADR-017의 `author_id`/
`work_id` 생성 규칙(surname 우선 등)은 그대로 유지된다. 다만
`editor_id`가 가리키는 대상도 `author_id` 네임스페이스를 그대로
공유한다(별도 ID 체계 신설 없음).

---

## TSU Metadata 확정 (Phase 6)

| 필드 | 상태(일반 Work) | 상태(periodical Work) |
|---|---|---|
| `edition_id` | 필수(GOVERNANCE §6) | **면제** — Edition 계층 자체가 없으므로 |
| `volume_id` | 조건부 필수(다권본만) | **필수** |
| `issue_id` | 해당 없음 | **필수**(신규) |

**결정**: TSU 필수 필드 판정 로직에 `work_type` 분기를 추가한다 —
`work_type=periodical`이면 `edition_id` 요구를 `volume_id`+`issue_id`
요구로 대체한다. 이는 Governance §6의 예외 규칙으로 문서화하며, 이번
Revision에서는 **정책만 정의**하고 실제 TSU 생성/코드 구현은 하지
않는다(금지 사항 준수).

---

## 8. ADR 처리 (Phase 7)

**ADR-016 개정 불필요, ADR-017 개정 불필요, 신규 ADR-018 필요 — 채택함.**

- ADR-016(Entity 모델)은 이번 Revision의 "Edition 조건부 생략" 원칙과
  "Volume 조건부 Entity" 원칙을 이미 포함하고 있어 본문 수정 불필요 —
  이번 결정은 그 원칙의 **적용 사례 확장**(Issue도 동일 원칙 적용)이다.
- ADR-017(ID 규칙)도 정기간행물 ID 확장을 이미 "범위 밖, Design
  문서에서 처리"로 명시해 두어 개정 불필요.
- 신규 결정(`author_type`, `title_history[]`, `continues_work_id`,
  `editor_id`, TSU 필드 예외 규칙)은 기존 어느 ADR에도 속하지 않는
  **새로운 Architecture Decision**이므로 [ADR-018](architecture/ADR-018-NAE-Periodical-Authority-Extension.md)로
  남긴다 — "ADR 소급 수정 금지" 관례의 세 번째 일관된 적용
  (ADR-014→016, GOVERNANCE→017에 이은 패턴).

---

## 9. Migration 전제조건

C1 Risk #6(BLOCKER)을 그대로 승계한다 — 이번 Revision으로 해소되지
않음:

1. TSU 필요 필드(periodical: `volume_id`+`issue_id`, monograph:
   `edition_id`) 모두 갖춘 자료 확인 전까지 TSU 생성 금지.
2. `author_type` 필드가 실제 스키마 파일(`modern/source_manifest.schema.yaml`)에
   반영되기 전까지 Organization Author 데이터를 프로덕션 Registry에
   추가하지 않는다.
3. 제호 계승 관계(1803/1817) 서지 검증 — 미완료 상태로는 두 Work를
   병합하거나 분리 상태를 최종 확정하지 않는다.
4. 동일 volume 내 복수 issue 시나리오 미검증 — 이 시나리오가 실제
   자료로 검증되기 전까지 "issue_number 충돌 처리 로직이 옳다"고
   가정하지 않는다.

---

## 10. Remaining Risks

| # | 리스크 | 상태 |
|---|---|---|
| 1 | 제호 계승 관계 서지 미검증 | 유지(C1 Risk #1 승계) — `continues_work_id` 필드만 마련, 실제 연결은 보류 |
| 2 | 동일 volume 내 복수 issue 미검증 | 유지(C1 Risk #2 승계) |
| 3 | `author_type` 필드 미구현(설계만) | 신규 결정이나 실제 스키마 파일/코드 미반영 |
| 4 | `title_history[]`가 기존 Pilot YAML(`aliases`)과 형식 불일치 | 신규 — Pilot 데이터를 소급 갱신하지 않기로 결정(§6) — Production 반영 시점에만 신규 형식 적용 |
| 5 | TSU 필드 예외 규칙(work_type 분기) 미구현 | 신규 — 정책만, Validator/TSU 빌더 코드 없음 |
| 6 | Editor/Organization 구분(author_id vs editor_id)이 아직 어느 Pilot 데이터에도 반영 안 됨 | 신규 — Baptist Missionary Magazine Pilot 데이터(`periodicals.yaml`)는 organization만 `author_id`로 기록, editor 미등록(RAW에 명시적 개인 편집자 표기가 확인되지 않았음) |

---

## 완료 조건 답변

1. **Periodical은 Work subtype인가 별도 Entity인가?** — **Work subtype**(`work_type: periodical`, 안 1).
2. **Issue Entity는 필요한가?** — **필요, Periodical 전용 조건부 확장**으로.
3. **Organization Authority는 추가하는가?** — **예**, 단 별도 Entity가 아니라 **`author_type` 필드**로.
4. **author_type 필드는 추가하는가?** — **예**(3번과 동일 결정).
5. **Title History는 어떤 모델인가?** — **`title_history[]`**(시간순 구조화) + `continues_work_id`/`continued_by_work_id` 경량 관계 필드.
6. **ADR-018 생성 여부?** — **예**, 생성함(§8).
7. **Schema v2.1.0 유지 여부?** — **유지 안 함, v2.2.0 필요**(Minor — `author_type`/`title_history`/`continues_work_id`/`continued_by_work_id`/`editor_id`/`issue_id` 전부 optional 추가, 기존 데이터 무효화 없음). **단 이번 작업에서 실제 스키마 파일은 수정하지 않았다.**
8. **전체 Metadata Migration 가능 여부?** — **NOT READY**(C1 BLOCKER 승계, §9 4개 전제조건 미충족).

---

## 로드맵 갱신

```
Architecture Revision          ✅
Schema v2.1.0                  ✅
Validator                      ✅
Authority Registry              ✅
ID Governance ADR-017           ✅
Periodical Pilot                 ✅
C1 Periodical Review             ✅
Periodical Architecture Revision  ✅ (이번 작업 — ADR-018 포함, 설계까지)

C1 Final Architecture Review       NEXT
Schema v2.2.0 반영(실제 파일)         NEXT (별도 승인)
Periodical Registry Expansion Pilot  FUTURE
Corpus Metadata Migration             FUTURE
```

---

*Schema YAML 수정, Authority Registry 실제 데이터 추가, 기존 Pilot
변경, RAW 변경, TSU/Embedding 생성, Retrieval 코드 변경, 전체
Migration, Git Commit — 전부 수행하지 않음.*

# NAE Periodical Pilot Report 001

**Project:** NAE-PERIODICAL-AUTHORITY-PILOT-001
**Date:** 2026-08-02
**Nature:** Pilot 검증 + Architecture Revision 단계 — **전체 Corpus Migration 아님**
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

Baptist Missionary Magazine(`NAE/corpus/raw/archive_org/missions/`,
10개 issue 전수 실측)을 대상으로 현재 Authority Model이 정기간행물을
표현할 수 있는지 검증했다. **표현 가능하나 Issue Entity 신설과 Edition
계층의 선택적 생략이 필요**하다는 결론에 도달했다(Option A). 실측
과정에서 이 자료가 실제로는 **제호가 최소 1회 이상 바뀐 하나 이상의
시리즈**임을 발견해(1803 "Massachusetts Baptist Missionary Magazine" →
1817 "New Series" 재시작 → 이후 "Missionary Magazine"), 2개의
periodical(Work)로 분리 등록했다. Reference Integrity 10개 검사
전부 PASS(실제 실행 결과).

---

## 2. Entity Model 결정

**Option A 채택** — Work의 `work_type: periodical` 값 추가 + Issue
Entity 신설 + 정기간행물에서 Edition 계층 선택적 생략(Volume이 이미
단권 자료에서 생략 가능한 것과 동일한 패턴을 일반화). Article은
Registry Entity로 만들지 않음(RAW가 article 단위 물리 파일을 제공하지
않음 — issue 전체가 1개 PDF/OCR). 상세 근거·대안 비교는
[`NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md`](NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md) §2.

```
Author(조직 포함) → Work(periodical) → [Edition 생략] → Volume → Issue → Source
```

---

## 3. ID Governance 영향

| 결정 | 내용 |
|---|---|
| `issue_id` 신설 | `{volume_id}_i{NNN}` — ADR-017의 `_v{NN}`/scan_suffix 패턴과 일관된 확장 |
| Volume ID 폭 | 정기간행물 한정 3자리(`v{NNN}`)로 확장 — monograph용 2자리(ADR-017)는 유지, ADR-017 본문 미수정(신규 확장을 Design 문서에 기록하는 방식, 기존 "ADR 소급 수정 금지" 관례) |
| `periodical_id` | 개념적으로 `work_id`와 동일 규칙(`{author_id}_{title_slug}`) — 별도 ID 체계 아님 |
| Organization Author | `author_type: person\|organization` 필드 신설 권고(이번 Pilot에서는 미신설, Design 문서 §3.4) |

---

## 4. Registry 구조

`resources/theological_sources/authority/pilot_periodical/`에
5개 파일 생성(periodicals/volumes/issues/sources/manifest.yaml) —
**기존 Registry(`authority/*.yaml`, `authority/pilot/`)는 변경하지
않음**, RAW 파일도 이동하지 않음(실측 확인, 아래 §9 검증 결과 참고).

| Entity | 건수 |
|---|---|
| Periodical(Work 동등물) | 2 |
| Volume | 10 |
| Issue | 10 |
| Source | 10 |

---

## 5. Validator 영향

- `scripts/source_validator.py` **미수정**(git diff 없음).
- 실제 재실행 결과: `89 PASS / 0 WARNING / 0 FAIL`(이전과 완전
  동일) — pilot_periodical 파일들이 `source_manifest.yaml`이라는
  파일명이 아니므로 validator의 `rglob` 탐색 대상에 포함되지 않음(의도된
  격리, 기존 Pilot-001/002 이후 파일명 규칙과 동일 원칙).

---

## 6. TSU 영향

설계만 수행, **TSU 생성하지 않음**. 신규 필드 제안:
`periodical_id`, `volume_id`, `issue_id`(신규), `article_title`(선택),
`author_or_editor`(선택), `publication_date`, `citation_policy`,
`tsu_access`. 기존 `TSU_SCHEMA_VERSION`과 독립적이라 충돌 없음
(`NAE/pipeline/tsu/config.py` 실측 재확인, ADR-016과 동일 패턴).
상세는 [Design 문서](NAE_PERIODICAL_AUTHORITY_DESIGN_v1.md) §6.

---

## 7. Remaining Risks

| # | 리스크 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | 제호 계승 관계 미확정 | "Massachusetts Baptist Missionary Magazine"(1803)과 "American Baptist Magazine...New Series"(1817)를 별도 periodical로 분리한 것은 volume 번호 불연속(1803=Vol.I 단발, 1817=New Series Vol.I)에 근거한 판단이지, 서지학 전수 조사 결과가 아님 — 사서/전문가 검증 권고 | 중간 |
| 2 | 동일 volume 내 복수 issue 미검증 | RAW 표본이 volume당 issue 1개씩만 제공해(archive.org 개별 스캔 특성), "같은 volume, 여러 issue" 시나리오의 issue_number 충돌/정렬 로직이 실제로 검증되지 않음 | 중간 |
| 3 | 발행 조직 계보 단순화 | 실제로는 수십 년간 조직명이 변화했을 가능성이 있으나(예: Massachusetts Baptist Missionary Society → American Baptist Missionary Union), 이번 Pilot은 대표 조직 하나로 단순화 — 조직 계보(lineage) 자체는 모델링하지 않음 | 낮음 |
| 4 | Author 스키마의 Organization 미지원 | `author_type` 필드가 아직 존재하지 않아 조직을 Author로 등록할 때 `birth_year`/`death_year`를 억지로 `null` 처리 — 구조적으로는 동작하나 의미상 어색함 | 중간 |
| 5 | Article 단위 검증 불가 | RAW가 article 단위 파일을 제공하지 않아 §2 Option A의 "Article은 TSU 필드로만" 결정이 실제 TSU 생성 시점에도 유효할지 미검증 | 낮음 |

---

## 8. Migration 가능 여부

**NOT READY** — 전체 Periodical Migration도, 전체 Corpus Migration도
착수 조건이 갖춰지지 않았다. 필요 선행 작업: (1) 제호 계승 관계
서지 검증(Risk #1), (2) Author `author_type` 필드 추가 결정(Risk #4),
(3) 이번 Design 문서의 Option A 결정을 `authority/works.yaml`
프로덕션 스키마에 반영(§4 Registry 구조에서 이미 권고).

---

## 완료 조건 답변

1. **현재 Authority Model이 Periodical을 표현 가능한가?** — **가능**(Option A, Edition 선택적 생략 + Issue 신설).
2. **Issue Entity가 필요한가?** — **필요**, 신설함.
3. **Article Entity가 필요한가?** — **불필요**(Registry 레벨) — RAW가 article 단위 물리 파일을 제공하지 않음, TSU 필드로만 다룸.
4. **ADR-017 수정이 필요한가?** — **불필요**. Volume ID 3자리 확장은 ADR-017 본문을 개정하는 것이 아니라 정기간행물이라는 새로운 자료 유형에 대한 **추가 적용 사례**로 이 Design 문서에 기록(기존 "ADR 소급 수정 금지" 관례 재확인) — monograph 2자리 규칙 자체는 변경되지 않았다.
5. **Schema v2.1.0 → v2.x 변경 필요 여부** — **필요할 수 있음, 이번엔 미실행**. `issue_id`(신규 필드), `author_type`(Author 확장) 추가가 필요하다는 결론이나, 이번 작업은 설계까지만(GOVERNANCE §2.2 기준 Minor bump 대상으로 예상 — 기존 데이터 무효화 없는 필드 추가).
6. **전체 Metadata Migration 준비 여부** — **NOT READY**(§8).

---

## 9. Validation 실행 결과 (Phase 5)

실제 Python 스크립트 실행(참조 무결성 + 중복 + ID 충돌):

```
PASS: volumes.periodical_id -> periodicals
PASS: issues.volume_id -> volumes
PASS: sources.issue_id -> issues
PASS: periodical_id unique
PASS: volume_id unique
PASS: issue_id unique
PASS: source_id unique
PASS: issue_number unique within volume_id (dups: {})
PASS: volume_number unique within periodical_id (dups: {})
PASS: no source_id collision with existing registries/manifest (collisions: set())

counts: 2 10 10 10
ALL PASS
```

**10/10 PASS.** 기존 Registry(`authority/*.yaml`, `authority/pilot/`,
`authority/pilot/fuller/`) 및 v1.2 baptist manifest와의 `source_id`
네임스페이스 충돌도 없음(교차 검사 포함).

---

## 로드맵 갱신

```
Architecture Revision        ✅
Schema v2.1.0                ✅
Validator                     ✅
Authority Registry             ✅
ID Governance ADR-017          ✅
Periodical Authority Pilot      ✅ (이번 작업 — 모델 검증까지, Migration 아님)

NAE-PERIODICAL-AUTHORITY-REVIEW-001(C1 독립 검증)   NEXT
Author Organization 지원(author_type 필드)            NEXT
Small Metadata Migration                               FUTURE
Full Corpus Migration                                   FUTURE
TSU Integration                                          FUTURE
```

---

*RAW 수정, 파일 이동, 전체 Periodical Migration, TSU/Embedding 생성,
Retrieval 변경, `scripts/source_validator.py` 수정 — 전부 수행하지
않음. Git Commit은 사용자 승인 후에만 수행한다.*

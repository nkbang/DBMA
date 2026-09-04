# NAE Authority Registry Build Report 001

**Project:** NAE-AUTHORITY-REGISTRY-BUILD-001
**Date:** 2026-08-02
**Nature:** Registry 구조 구축 — **전체 Corpus Metadata Migration 아님**
**Git Commit:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

Pilot-001(church_order)/Pilot-002(Fuller)에서 검증된 Author→Work→
Edition→Volume→Source 모델을 **복사 승격** 방식으로 Production
Registry(`resources/theological_sources/authority/*.yaml`)에 반영했다.
Pilot 원본은 `authority/pilot/`에 검증 이력으로 그대로 보존된다. 승격된
3 author / 3 work / 4 edition / 8 volume / 10 source에 대해 Reference
Integrity + Duplicate + Model 무결성 검사 **14개 항목 전부 PASS**(실제
Python 스크립트 실행 결과, 추론 아님). `scripts/source_validator.py`는
수정하지 않았고 재실행 결과도 회귀 없음(89 PASS/0 FAIL, 이전과 동일).

---

## 2. Phase별 결과

### Phase 1 — Authority Registry 위치 결정: **완료**

**결정: 복사 승격**(Pilot archive 유지 + Production registry 신규
생성). 근거는 `NAE_AUTHORITY_REGISTRY_DESIGN_v1.md` §Phase1 — 검증
이력 보존, C1 Review-002의 참조 대상 유지, 손실 위험 없음(이동이 아닌
복사). 상세는 [설계 문서](NAE_AUTHORITY_REGISTRY_DESIGN_v1.md) 참고.

### Phase 2 — Registry Schema 정의: **완료**

Author/Work/Edition/Volume/Source 5개 Entity 필드를 요청된 필드 그대로
확정(`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md` §2). Pilot 대비 필드명 3건
통일(`title→canonical_title`, `title_variants→aliases`, `place→
publication_place`, `path→file_path`) + `work_type`/`original_language`
신규 추가. `manifest.yaml`(Registry 색인, corpus manifest와 구분)도
신규 정의.

### Phase 3 — Pilot Data 승격: **완료**

| 대상 | Author | Work | Edition | Volume | Source |
|---|---|---|---|---|---|
| Pilot-001(Dagg, Hiscox) | 2 | 2 | 2 | 0(단권, 계층 생략) | 2 |
| Pilot-002(Fuller) | 1 | 1 | 2 | 8 | 8 |
| **합계** | **3** | **3** | **4** | **8** | **10** |

파일: `resources/theological_sources/authority/{authors,works,editions,volumes,sources,manifest}.yaml`

### Phase 4 — ID Governance 검증: **완료, 실측 결과 아래**

실제 Python 스크립트로 검증(파일: 임시 실행, 저장소에 커밋되는 코드
아님 — Phase 5 도구 설계와는 별개):

```
PASS: all works.author_id -> authors
PASS: all editions.work_id -> works
PASS: all volumes.edition_id -> editions
PASS: all sources.edition_id -> editions
PASS: all sources.volume_id(if set) -> volumes
PASS: author_id unique
PASS: work_id unique
PASS: edition_id unique
PASS: volume_id unique
PASS: source_id unique
PASS: registry source_id vs baptist manifest no collision (collisions: set())
PASS: no edition_id spans multiple work_id
PASS: volume_number unique within edition_id (dups: {})
PASS: no duplicate (author_id, canonical_title) (dups: [])

counts: 3 3 4 8 10
ALL PASS
```

**14/14 PASS — Reference Integrity 100%.**

**ID Governance 발견(중요)**: `author_id`/`work_id`/`edition_id`/
`volume_id` 표기 관례가 두 Pilot 간 **불일치**한다 —
`dagg_john_l`/`hiscox_edward_t`(소문자, 언더스코어, 문서화된 생성
규칙 준수)와 `FULLER-ANDREW-001`/`WORK-DAGG-CHURCH-ORDER-001`류
(대문자, 하이픈, 사람이 읽기 쉬운 표기 — `NAE_CORPUS_INGESTION_STANDARD_v1.md`
ID 생성 규칙과 다름)가 섞여 있다. 이번 작업에서는 **참조 무결성을
그대로 유지하기 위해 원본 ID를 재명명하지 않고 승격**했다 — 재명명은
모든 FK 참조를 동시에 바꿔야 하는 별도 작업이며, 이번 명령서 범위
("Registry 구조 구현·Pilot 데이터 정식 배치")를 벗어난다고 판단.
§7 Remaining Risks에 기록.

### Phase 5 — Registry Validation Tool 설계: **완료(설계만)**

`NAE_AUTHORITY_REGISTRY_DESIGN_v1.md` §Phase5 — Reference/Duplicate/
Schema 3범주, PASS/WARNING/FAIL 출력, `scripts/authority_validator.py`
(가칭)로 `source_validator.py`와 별도 파일 구현 권고. **코드 미구현**
(요청대로 요구사항 정의까지).

### Phase 6 — 기존 Validator와 관계 확인: **완료**

| | `source_validator.py`(기존, 미수정) | `authority_validator.py`(설계만, 미구현) |
|---|---|---|
| 검증 대상 | `source_manifest.yaml`(corpus manifest) | `authority/*.yaml`(Registry) |
| 책임 필드 | `citation_policy`/`tsu_access`/`archive_source` 등 TSU/검색 파이프라인 소비 필드 | Entity 간 FK(author_id/work_id/edition_id/volume_id) + governance 4필드 |
| 파일명 탐색 | `source_manifest.yaml`(rglob) | 별도 고정 파일 5종(authors/works/editions/volumes/sources.yaml) |
| 겹침 여부 | **없음** | **없음** |

**역할 충돌 없음** — 두 도구는 서로 다른 파일을 대상으로 하고, 겹치는
필드도 없다(Registry Source entity는 §2.5에서 의도적으로 TSU 필드를
제외했음). 실측 확인: `authority/*.yaml`(파일명이 `source_manifest.yaml`이
아님)이 `source_validator.py` 재실행 후에도 여전히 89 PASS/0 FAIL로
불변 — 두 시스템이 물리적으로 간섭하지 않음을 재확인.

---

## 3. Reference Integrity 결과

**100% PASS**(14/14 검사, §Phase4). BLOCKER 없음.

---

## 4. Remaining Risks

| # | 리스크 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | ID 표기 관례 불일치(Phase 4 발견) | `dagg_john_l` vs `FULLER-ANDREW-001` — 800여 권 규모로 확대 시 이 불일치가 누적되면 가독성/자동화 모두 저하 | **높음** — 전체 Migration 전에 ID Normalization 정책을 확정할 것을 강력 권고(재명명 작업은 별도 승인 필요) |
| 2 | `volume_number` 유일성이 Phase 5 설계 표에 명시적으로 없었음 | Phase 4 실제 검증에서는 포함시켰으나(PASS 확인), `NAE_AUTHORITY_REGISTRY_DESIGN_v1.md` §Phase5 Duplicate 표에는 이 항목이 누락되어 있었음 — 설계 문서에는 추가해 두었으나 재확인 필요 | 낮음(이미 문서에 보완 기재) |
| 3 | Fuller author_id가 기존 AF1815(baptist manifest)와 미통합 | 동일 인물(Andrew Fuller)이 서로 다른 author_id 네임스페이스에 존재 — Pilot 승격 시에도 통합하지 않았음(authors.yaml notes에 명시) | 중간 — 전체 Migration에서 저자 통합 규칙 적용 시 처리 필요 |
| 4 | Registry Validation Tool 미구현 | Phase 5는 설계만 — 실제 코드가 없어 향후 Registry에 데이터가 추가될 때마다 이번처럼 수작업 Python 스크립트로 검증해야 함 | 중간 — 소규모 Migration(10~20 works) 착수 전 구현 권고 |
| 5 | 정기간행물(volume+issue) 모델 미검증 | Baptist Missionary Magazine류는 여전히 Author→Work→Edition→Volume→Source 어디에도 정확히 들어맞지 않음(Pilot-001/002 모두 단행본류만 다룸) | 중간 — Q4 추천 파일럿(§5) 참고 |

---

## 5. Migration 준비도 평가 (Phase 7)

**Q1. Authority Registry 구조는 v2.1.0 Schema와 일치하는가?**
**예.** `authority/sources.yaml`의 `source_type`/`copyright_status`/
`usage_permission`/`access_control` 값 체계는 `NAE_METADATA_GOVERNANCE_v1.md`
§4(v2.1.0 정본)를 그대로 참조하며, corpus manifest(`modern/
source_manifest.schema.yaml`)와 `edition_id`/`volume_id` 필드로
연결된다.

**Q2. Pilot 데이터가 Production Registry 모델을 검증하는가?**
**예, 부분적으로.** 단행본(Dagg/Hiscox)과 다권본(Fuller, Work:Edition
1:N 포함) 모델은 Reference Integrity 100%로 검증됐다. 그러나
정기간행물(volume+issue 조합)은 아직 검증되지 않았다(Remaining Risk #5).

**Q3. 전체 Corpus Migration 전에 추가 Pilot이 필요한가?**
**예, 필요하다.** 정기간행물 유형과, ID Normalization 정책 확정
(Remaining Risk #1)이 우선 처리되어야 800여 권 규모로 안전하게 확대할
수 있다.

**Q4. 다음 Pilot 대상 추천은?**
**Baptist Missionary Magazine.** 근거:
- Commentary Collection보다 구조적으로 더 검증 가치가 높음 —
  volume+issue 조합(예: "Vol.47 No.11")이 현재 4단 모델(Work→Edition→
  Volume→Source)에 정확히 매핑되지 않는 유형이라, 모델의 실제 한계를
  드러낼 수 있음(Remaining Risk #5).
- Spurgeon Treasury(다권 설교집)는 Fuller와 구조적으로 유사해(다권
  단행본류) 추가 검증 가치가 상대적으로 낮음.
- Commentary Collection은 특정 자료가 아직 지목되지 않아 범위가
  불명확 — 이번 결정 시점에서는 우선순위가 낮음.

**Q5. 전체 Migration 착수 가능한가?**

```
NOT READY
```

**사유**: Registry 구조·모델·ID 생성 규칙은 검증됐으나(Q1/Q2 예),
(1) ID 표기 관례 불일치가 전체 규모로 확대되기 전에 정책 확정
필요(Risk #1), (2) 정기간행물 파일럿 미수행(Q3/Q4), (3) Registry
Validation Tool 미구현(Risk #4) — 이 세 가지가 해결된 후 사용자
로드맵의 "소규모 Migration(10~20 works)" 단계로 진행하는 것이 안전하다.

---

## 완료 조건 답변

1. **Production Authority Registry 구조 결정** — 복사 승격(§Phase1).
2. **Pilot 승격 여부** — 승격됨(3/3/4/8/10, §Phase3).
3. **Entity Schema 확정** — 확정(§Phase2, 설계 문서 §2).
4. **Reference Integrity 결과** — 100% PASS(14/14, §3).
5. **Validator 역할 분리 확인** — 확인됨, 충돌 없음(§Phase6).
6. **전체 Migration 가능 여부** — **NOT READY**(§Phase7 Q5).
7. **Remaining Risks** — 5건, 최우선은 ID 표기 관례 통일(§4).

---

## 로드맵 갱신

```
Architecture Revision        ✅
Schema v2.1.0                ✅
Validator                    ✅
Pilot Validation              ✅
Authority Registry            ✅ (이번 작업 — 구조 구축까지, NOT 전체 Migration)

ID Normalization 정책 확정     NEXT (Risk #1, Migration 전 필수)
Periodical Pilot(BMM)         NEXT (Q4)
Registry Validation Tool 구현   NEXT (Risk #4)
Metadata Migration(소규모)      AFTER 위 3건
Metadata Migration(전체)        AFTER REVIEW
TSU Migration                  FUTURE
Retrieval Integration           FUTURE
```

---

*RAW corpus 수정, `NAE/corpus/raw` 변경, 기존 archive_org 구조 변경,
전체 Metadata Migration, 전체 author/work 생성, TSU/Embedding 생성,
Retrieval 변경, `core/retrieval.py`/`scripts/source_validator.py` 수정
— 전부 수행하지 않음. Git Commit은 사용자 승인 후에만 수행한다.*

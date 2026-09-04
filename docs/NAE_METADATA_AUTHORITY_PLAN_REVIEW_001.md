# NAE Metadata Authority Plan Review 001

**Review ID:** NAE-METADATA-AUTHORITY-PLAN-REVIEW-001
**Date:** 2026-08-02
**Reviewer:** CUE (Read-Only Architecture Verification — 원래 C1 대상 명령서를 사용자 승인 하에 CUE가 직접 수행. 작성자-검증자 동일 세션이라는 이해상충을 감안해 코드/파일 레벨 실측(source_validator.py, TSU config, RAW 트리)으로 판정 근거를 최대한 보강함)
**Status:** COMPLETE
**Scope:** `NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md`의 현재 NAE Architecture/코드와의 충돌 검증

---

## 1. Executive Summary

`NAE_METADATA_AUTHORITY_IMPLEMENTATION_PLAN_001.md`(이하 "Plan")는 기존
Architecture(ADR-014/015, NAE_METADATA_GOVERNANCE_v1, NAE_DATA_ARCHITECTURE)와
**구조적으로 충돌하지 않는다.** RAW 불변 원칙, Directory 분리, Rollback
안전성은 모두 PASS다.

다만 실제 코드(`scripts/source_validator.py`)를 대조한 결과, Plan이
"검증기 확장 필요"로만 서술한 부분에 **필드명 자체의 불일치**(`content_genre`
vs `category`)가 있어, 확장 없이 그대로 실행하면 modern manifest가 전부
FAIL 처리된다. 이는 Plan의 실행 순서(§5 Step 2)에 직접 영향을 준다.

또한 TSU 필수 필드 목록이 이번 명령서(Phase 8, `edition_id` 포함 10개)와
`NAE_METADATA_GOVERNANCE_v1.md` §6(`edition_id` 미포함, 9개) 사이에서
불일치한다.

**최종 판정: APPROVED WITH CONDITIONS**

---

## 2. Architecture Compatibility (Phase 1)

### RAW Layer 확인

```
NAE/corpus/raw/archive_org/   ← 실측: 현재도 이 구조만 존재, .DS_Store 외 변경 없음
```

| 질문 | 답 | 근거 |
|---|---|---|
| Metadata Layer가 RAW를 침범하는가? | **아니오** | Plan §1이 신설하는 디렉토리는 전부 `resources/theological_sources/` 하위(`modern/`, `authority/`) — `NAE/corpus/raw/`는 Plan 어디에서도 쓰기 대상이 아님 |
| 기존 archive_org 구조와 충돌하는가? | **아니오** | Plan §1.1이 `archive_org/` → `public_domain/` rename을 "별도 승인 건으로 분리 유지"라고 명시적으로 보류함 — 이번 Plan 승인이 rename을 자동 승인하지 않음을 재확인 |

**판정: PASS**

---

## 3. Authority Model Review (Phase 2)

Author → Work → Edition → Source File 4단 모델(Plan §3.1 인용, 원 출처
`NAE_METADATA_GOVERNANCE_v1.md` §5.1)을 검토한다.

| ID | 필요성 | 평가 |
|---|---|---|
| `author_id` | 필수 | 동일 저자 표기 변형(Knollys/Knollys, John 등, C1 Audit-002에서 실측 확인됨) 통합의 유일한 canonical key — 없으면 검색 시 동일 저자 자료가 분산됨 |
| `work_id` | 필수 | 판본 그룹핑의 상위 키. C1 Audit-002가 식별한 Fuller(8권)/Cathcart(2권)/Spurgeon Autobiography(2권) 같은 다권본 관리에 필수 |
| `edition_id` | 필수 (신설 타당) | 기존 설계(ADR-014 초안)는 Work/Source 2단만 있어 "같은 판본 다른 스캔본"을 그룹핑할 key가 없었음 — Plan의 승격이 실제 결손을 메움. Knollys_Life_and_Death / Knollys_Life_and_Death_Autobiography(Audit-002 §2.5, "확인 필요"로 표시된 항목)가 정확히 이 문제의 실사례 |
| `source_id` | 필수, 기존 유지 | v1.2부터 존재, 유일성 검사 대상 — 변경 없음 |

### 평가

- **확장성**: PASS — 4단 계층은 단권/다권/정기간행물(Baptist Missionary
  Magazine 10권처럼 volume+issue가 섞인 경우) 모두 `edition_id`로 흡수
  가능(Edition을 "1867년 47권 11호"처럼 세분화하면 됨).
- **중복 관리 위험**: WARNING(경미) — `edition_id`와 `work_id` 생성 규칙이
  둘 다 slug 기반 문자열 연결(`{work_id}-{edition_slug}`)이라, 제목이 긴
  다권 정기간행물(예: General Baptist Magazine)에서 slug 충돌 가능성이
  이론상 있음. 실제 충돌 시 처리 규칙(재시도/suffix 부여)이 Plan에
  없음 — Migration Step 3(§5) 착수 전 보완 권고(BLOCKER는 아님, 실제
  875개 규모에서 발생 가능성은 낮음).
- **역사 자료 적용 가능성**: PASS — church_order(단권 2개)부터
  early_baptist_collection(1,416파일, 별도 sub-plan)까지 스펙트럼이 넓은
  현재 corpus 특성과 모델이 부합. Audit-002가 실측한 저자/작품 수(약 30명,
  55개 work)에 4단 모델을 적용해도 과설계로 보이지 않음.

**판정: PASS (경미한 WARNING 1건, 비차단)**

---

## 4. Registry Design Review (Phase 3)

```
authority/
├── authors.yaml
└── works.yaml   (Edition/Source File 중첩 포함)
```

| 확인 항목 | 판정 | 근거 |
|---|---|---|
| 분리 구조 적절성 | PASS | 변경 빈도 차이(저자 등록은 드묾, Work/Edition은 자료 유입마다 갱신)에 근거한 분리 — git diff 가독성 실익이 명확 |
| 단방향 Reference 안전성 | PASS | `works.yaml`이 `source_manifest.yaml`의 `source_id`를 참조만 하고 값을 복제하지 않음 — 이중 관리 사고(두 곳에서 값이 어긋나는 문제) 구조적으로 차단. 단, manifest에서 `source_id`가 삭제되면 registry에 orphan reference가 남는데, Plan이 "Phase 4 검증기에 참조 무결성 검사 추가"로 대응을 명시(§3.2) — 실제 구현 여부는 Migration Step 4에 달림 |
| Git 관리 적합성 | PASS | `resources/theological_sources/` 하위는 이미 git 추적 대상(`NAE_DATA_ARCHITECTURE.md` §"핵심 구분" 확인됨) — `authority/`도 동일 트리에 두는 결정이 기존 원칙과 일치 |
| 향후 규모 확장 가능성 | WARNING(경미) | `works.yaml` 1개 파일에 모든 Work+Edition+Source 목록을 중첩시키는 구조는 875개 항목(work 기준으로는 194개 확인됨) 규모에서는 무난하나, Modern 자료가 누적되면 단일 YAML 파일이 커져 diff 충돌(여러 등록자가 동시 작업 시) 위험이 있음 — 카테고리별 분할(`authority/works/baptist.yaml`, `authority/works/modern.yaml`)을 규모 확장 시 고려 권고. 이번 규모에서는 문제 아님 |

**판정: PASS (경미한 WARNING 1건, 비차단)**

---

## 5. Mapping Pipeline Review (Phase 4)

7단계(Collection→Normalization→Human Verification→Work Grouping→Human
Verification→Edition Separation→Validation)를 검토한다.

- **자동화 위험**: PASS — 자동화 대상은 "후보 생성"까지로 명시적으로
  제한(정규화·유사도 매칭)되고, Author 그룹 확정과 Work 그룹 확정은 각각
  별도의 Human Verification 단계를 거침 — `NAE_METADATA_GOVERNANCE_v1.md`
  §5.2 "자동 병합 금지" 원칙과 일치.
- **Human Review 필요 지점**: 2곳(Author 확정, Work 확정) 명시 — 적절.
  다만 Edition Separation(5단계) 자체에는 별도 Human Verification이 없고
  바로 Validation(7단계)으로 넘어간다 — Audit-002가 실사례로 지적한
  Knollys Life_and_Death/Autobiography 같은 애매한 케이스(동일 저작
  다른 저작인지 불명확)는 자동 연도/파일명 매칭만으로 edition 분리가
  틀릴 수 있다. **WARNING**: Edition Separation 직후에도 경계 사례에
  한해 사람 확인을 거치도록 권고(모든 edition이 아니라, 자동 분리
  신뢰도가 낮은 경우만 — 비차단, Migration Step 3 착수 전 반영 권고).
- **875개 항목 적용 가능성**: WARNING(경미, Plan 자체가 이미 인지) — Plan
  §0이 "work 단위(194개 확인됨) vs 파일 단위(875 또는 그 이상) 불일치
  가능성"을 스스로 명시하고 재실측을 전제조건으로 걸어둠. 이 자기인지는
  적절하나, **7단계 파이프라인의 매핑 우선순위(§4.2)가 실제로는 파일이
  아니라 "work" 단위로 설계**되어 있어, "875개 항목"이 파일 단위라면
  Pipeline이 다루는 단위(work→edition→source)와 명령서가 말하는 단위가
  다를 수 있다 — 실행 착수 전 반드시 재확인 필요(Plan이 이미 이렇게
  기술했으므로 신규 리스크라기보다 재확인).

**판정: PASS (WARNING 2건, 비차단, 모두 Migration 착수 전 확인 대상)**

---

## 6. Migration Review (Phase 5)

| 확인 항목 | 판정 | 근거 |
|---|---|---|
| Rollback 가능성 | PASS | 신규 파일이 v1.2 파일과 물리적으로 분리(별도 디렉토리)되어 있어 삭제/git revert만으로 원상복구 — 실측 확인: 현재 `resources/theological_sources/`에는 `baptist/`만 존재, `modern/`·`authority/`는 아직 생성되지 않음(Plan이 실행 전이라는 서술과 일치) |
| 기존 데이터 보호 | PASS | Step 1이 `license` 원본 필드를 유지하고 `copyright_status`를 파생 필드로만 추가 — 기존 v1.2 entry 재작성 없음 |
| 단계별 Migration 안전성 | **WARNING → 아래 §9 Required Changes 참고** | Step 1(즉시 시작 가능)이 실제로는 `source_validator.py`의 `_REQUIRED_FIELDS`(코드 실측: `source_id, title, license, content_genre, status`)와 무관하므로 안전. 그러나 **Step 2(Modern 신규 등록)는 안전하지 않다** — 아래 §7 참고 |

**판정: PASS with 1 WARNING(Step 2 관련, §7에서 상세)**

---

## 7. Pilot Review (Phase 6)

Church Order 파일럿(Dagg, Hiscox — Audit-002 실측: 2 work, 6파일, 49MB).

| 질문 | 답 |
|---|---|
| Pilot 규모가 적절한가? | 적절 — 검증 비용 최소, Author 1:1 매핑(동명이인/다권본 이슈 없음)이라 절차 자체의 결함(예: ID 생성 규칙 버그) 발견에 적합 |
| 전체 Pipeline 검증 가능한가? | **부분적** — church_order 2개 work는 각각 저자 1명, 판본 1개, 스캔본 1개라 **Edition Authority(같은 work_id 다른 edition_id)와 Different Scan Same Edition 중복 로직을 전혀 검증하지 못한다**. Plan §4.2가 "다권본 저작(Fuller 8권 등)"을 우선순위 2로 이미 배치해 이 공백을 인지하고 있으나, 이 인지가 §6(Pilot Review) 자체에는 명시적으로 연결되어 있지 않음 |
| 이후 확장 가능한가? | 가능 — church_order 통과 후 다권본(Fuller)으로 이어지는 순서가 §4.2에 이미 있음. **권고**: Pilot 정의를 "church_order 단독"이 아니라 "church_order(1차) → Fuller Complete Works(2차, Edition 로직 검증)"의 **2단계 파일럿**으로 명시적으로 재정의할 것 — Step 3(전체 소급 매핑) 진입 전 필수 조건으로 격상 권고 |

**판정: WARNING(비차단) — 2단계 파일럿으로 명문화 권고**

---

## 8. Early Baptist Collection Risk Review (Phase 7)

실측: `history/early_baptist_collection/` = 1,416파일, ~34GB(Audit-002 §2.3).

| 확인 항목 | 판정 |
|---|---|
| 별도 Mapping Project 필요성 | 타당 — 단일 collection이 전체 history 카테고리 용량의 99%를 차지하고, item-level metadata 구조 자체가 아직 설계되지 않음(Audit-002 §2.6 "collection-level + item-level 이중 구조 권장"만 있고 구체안 없음). 지금 Plan의 7단계 Pipeline을 그대로 적용하면 1,416개 파일에 대해 개별 Human Verification이 필요해 비용이 비현실적으로 커짐 |
| 현재 Plan에서 제외한 판단 적절성 | 적절 — Plan §4.2가 "나중에" 표시만 하고 세부설계를 범위 밖으로 명시적으로 뺀 것은 과설계를 피하는 올바른 판단(CLAUDE.md "불필요하게 넓은 리팩터링 금지" 원칙과도 부합) |

**판정: PASS**

---

## 9. TSU Pipeline Impact (Phase 8)

실측: `NAE/pipeline/tsu/config.py::TSU_SCHEMA_VERSION = "1"` — metadata
`schema_version`(1.2/2.0.0)과는 독립된 별도 버전 체계이므로 이름 충돌 없음.

### 필드 목록 불일치 발견 (신규)

이번 명령서 Phase 8이 제시한 TSU 필드 목록(10개, `edition_id` 포함)과
`NAE_METADATA_GOVERNANCE_v1.md` §6의 필드 목록(9개, `edition_id`는 "권장,
필수 아님"으로 명시)이 **서로 다르다**:

| 문서 | edition_id 취급 |
|---|---|
| 이번 명령서 Phase 8 | 필수 목록에 포함(10개 중 1개) |
| `NAE_METADATA_GOVERNANCE_v1.md` §6 | "필수 목록에는 없으나 payload 포함 권장" |

**검토**:
- **TSU Schema 충돌 여부**: 없음 — `TSU_SCHEMA_VERSION`이 독립 버전이라
  metadata 필드 추가가 TSU 스키마 자체를 깨지 않음.
- **Retrieval 영향 여부**: 없음 — Plan/명령서 모두 `RetrievalEngine`
  코드 변경을 포함하지 않음(ADR-001 범위 유지, 실측: `core/retrieval.py`
  코드에 이번 대화 세션에서 어떤 수정도 가하지 않았음).
- **추가 ADR 필요 여부**: 아니오, 단 **문서 간 불일치 정정은 필요** —
  `edition_id`를 필수로 격상할지(권장안: Author/Work/Edition 3단 ID가
  모두 TSU citation에 포함되면 "몇 번째 판본에서 인용했는지" 추적 가능해
  실익이 있음 — 필수 격상 권고) 여부를 §9 Required Changes에서 결정.

**판정: WARNING(비차단, 문서 정합성 문제) — Required Changes 반영 권고**

---

## 10. Risk Assessment (Phase 9 표)

| 항목 | PASS/WARNING/BLOCKER |
|---|---|
| Architecture Compatibility | **PASS** |
| Authority Model | **PASS** (경미 WARNING: ID slug 충돌 가능성) |
| Registry Design | **PASS** (경미 WARNING: 규모 확장 시 파일 분할 고려) |
| Migration Safety | **WARNING** (Step 2 착수 전 validator 필드명 불일치 해결 필수) |
| Pilot Strategy | **WARNING** (2단계 파일럿으로 명문화 권고) |
| TSU Compatibility | **PASS** (스키마 충돌 없음) |
| Retrieval Impact | **PASS** (코드 변경 없음, 영향 없음) |

### 신규 발견 사항 (코드 실측 기반)

| # | 발견 | 심각도 | 근거 |
|---|---|---|---|
| F1 | `source_validator.py::_REQUIRED_FIELDS`가 `content_genre`를 필수로 요구하나, Modern schema(v2.0.0, `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` Task 3)는 `content_genre` 필드가 없고 `category`/`subcategory`를 사용 — **검증기 확장 없이 Step 2를 실행하면 모든 modern manifest entry가 FAIL 처리됨** | **BLOCKER (Step 2 한정)** | 코드 실측(`scripts/source_validator.py:39`) |
| F2 | TSU 필수 필드 목록에서 `edition_id` 필수 여부가 문서 간 불일치(명령서 Phase 8 vs GOVERNANCE §6) | WARNING | 문서 대조 |
| F3 | `author_id`/`edition_id` slug 생성 규칙에 충돌(동명 슬러그) 처리 규칙 없음 | WARNING(경미) | 설계 검토 |
| F4 | church_order 단독 파일럿은 Edition/Duplicate 로직을 검증하지 못함 | WARNING | Audit-002 실측 대조 |

---

## 11. Required Changes

Step 2(Modern 신규 등록) 진입 전 **필수**:

1. **[F1 대응, 필수]** `source_validator.py` 확장 시 `_REQUIRED_FIELDS`를
   domain(v1.2/v2.0.0)별로 분기 — v1.2는 `content_genre` 유지, v2.0.0은
   `category`로 대체. 확장 없이는 Migration Step 2를 시작할 수 없음.

Step 3(전체 소급 매핑) 진입 전 **권고**(비차단이나 강력 권고):

2. **[F4 대응]** Pilot을 "church_order → Fuller Complete Works(2단계)"로
   명문화, Edition Authority 로직을 실제 다권본으로 검증한 뒤 Step 3 착수.
3. **[Mapping Pipeline §5 관련]** Edition Separation 단계 직후 경계 사례
   한정 Human Verification 추가(Knollys류 사례 대응).
4. **[875개 수치 재확인]** Step 3 착수 직전 대상 모수(work/edition/file
   중 어느 단위인지)를 재실측하고 §4.2 우선순위표를 그 단위로 재확정.

문서 정합성(비차단, 시간 날 때):

5. **[F2 대응]** `NAE_METADATA_GOVERNANCE_v1.md` §6과 향후 TSU 관련
   명령서 간 `edition_id` 필수 여부를 통일(권고: 필수로 격상).
6. **[F3 대응]** `author_id`/`edition_id` slug 충돌 시 처리 규칙(예:
   suffix 번호 부여) 명문화.

---

## 최종 판정

## APPROVED WITH CONDITIONS

**조건**: 위 Required Changes #1(F1, validator 필드명 불일치)은 Migration
Step 2 실행 전 **반드시** 해결되어야 한다 — 이 조건이 충족되지 않은 채
Step 2를 실행하면 즉시 전량 FAIL이 발생해 사실상 구현이 불가능하다.
그 외 조건(#2~#6)은 권고 수준이며 각 해당 Step 진입 전 확인하면 된다.

**Architecture 자체(Directory 구조/Authority Model/Rollback)는 이견 없이
APPROVED** — 이번 조건들은 모두 "설계를 다시 하라"가 아니라 "실행 순서상
이 지점에서 이 항목을 먼저 처리하라"는 구현 준비 조건이다.

---

*Review Complete. 2026-08-02. 파일 생성/Metadata 생성/Schema 변경/RAW 변경/
TSU 생성/Embedding 생성/Code 수정/Git Commit — 전부 수행하지 않음(Read-Only
Review, 코드 실측은 `grep`/`sed -n`을 통한 읽기 전용 확인만 수행).*

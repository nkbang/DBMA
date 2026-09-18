# C1 Review 요청 — Authority Tier(T1-T4) M2 Tagging: Amendment D 초안 + Plan 001

- 요청자: CUE
- 일자: 2026-09-16
- 유형: **C1 Review** (독립 검토 — 구현 아님, 문서 검토 + 코드 read-only). §2-A는 이미 병합된
  코드 재확인, §2-B/§2-C는 **아직 코드가 없는 순수 설계 문서 검토**임 — 이 요청의 본체는 후자다.
- 트리거: CLAUDE.md CUE Operating Policy "C1 Review 요청 시점 — 새 ADR 작성, ... Metadata Model
  변경 ..."에 해당. Amendment D는 M2에 신규 축(`authority_tier`)을 추가하는 Metadata Model
  변경이며, ADR-030은 Approved 상태이므로 Architecture Freeze Rule에 따라 구현 전 C1 Review가
  필수다.
- HEAD: `d72280748d4012e83ad0ae3829628d26ca4653e0`
- Branch: `dev/dbma-engine`
- Remote: `origin` = `https://github.com/nkbang/DBMA.git`, `nas` = `http://100.94.139.122:3000/David/DBMA.git`
- Toplevel: `/Users/David/DBMA`
- PR: 없음 — 이 요청 시점까지 §2-B/§2-C는 코드 변경을 전혀 포함하지 않는 순수 문서(§0 참고)

---

## 0. 범위 — 왜 "코드 없는" 검토인가

일반적인 C1 Review 요청(예: Amendment B)은 이미 구현·커밋된 코드를 사후 검증한다. 이번 요청은
그 앞 단계다 — Amendment D는 **아직 PROPOSED이고 §4 승격 조건 4개 중 0개 충족** 상태이며,
Architecture Freeze Rule에 따라 C1 Review가 "구현 완료"보다 **먼저** 와야 하는 순서로 설계했다
(CLAUDE.md: "명령 없이는 절대 변경 금지" 대상에 대한 사전 승인 절차). 따라서 이번 검토는:

| 구분 | 상태 | C1이 볼 것 |
|---|---|---|
| §2-A citation_disclosure.py | **이미 병합**(커밋 `d7228074`, 2026-09-16, push 완료) | 실제 코드 diff |
| §2-B Plan 001 | 문서만, 코드 0 | 설계 문서 read |
| §2-C Amendment D | 문서만, 코드 0, **PROPOSED** | 설계 문서 read + ADR-030 원문 대조 |

C1의 판정이 이번 요청에서 하는 일은 "코드가 맞게 동작하는가"가 아니라 **"이 설계가 구현 단계로
진입해도 안전한가"**다 — 승인되면 그 다음에 §2-B §4~§6이 정의한 구현 커밋이 별도로 진행되고,
그때 통상적인(코드 사후검증형) C1 Review가 다시 필요하다.

---

## 1. 요청 배경

목회자 개인 RAG(DBMA/NAE) 제안서 §11/§13에서 신학적 권위 등급(T1 정경/신조, T2 검증된 신학,
T3 비교·변증 참고, T4 미검증)과 그 경고 라벨 삽입 로직을 설계했다. 2026-09-16 그 중 "라벨
조회" 절반만 `NAE/citation_disclosure.py::get_tier_disclosure()`로 구현·커밋했다(기존
`get_disclosure(authority_class)`는 무변경, 신규 함수만 추가, 신규 테스트 12건 전부 PASS,
기존 회귀 무영향).

그 함수가 실제로 호출될 데이터, 즉 M2(`source_manifest.yaml`)에 `authority_tier` 필드가
없다는 공백이 곧바로 드러났다. 이 필드를 M2에 추가하는 것은 ADR-030 §7(Metadata Authority)이
이미 규정한 `authority_class` 축과의 관계를 명확히 선언해야 하는 **Metadata Model 변경**이므로,
바로 코드를 쓰지 않고 먼저 (a) 태깅 파이프라인 설계(Plan 001), (b) ADR-030을 개정하는 Amendment
D 초안을 순서대로 작성했다. 두 문서 모두 ADR-030 §7.3("category와 authority_class는 서로 다른
개념")이 쓴 것과 동일한 패턴(독립된 축 선언, 관계 명시)을 세 번째 축에 적용한다.

**이 검토의 목적**: (a) Amendment D가 실제로 ADR-030 원 조항(§7.2, §7.3, §7.5, §8.4, §12 M-2)과
충돌하지 않는지, (b) `authority_class`/`authority_tier` 두 축의 독립성 선언이 §7.3의 선례와
논리적으로 정합한지, (c) Plan 001이 제안하는 코드 변경 지점(§4-§6)이 Amendment B가 이미 검증받은
패턴을 정확히 재사용하고 있는지, (d) 이미 병합된 `citation_disclosure.py`의 함수 시그니처가
이 설계가 나중에 채울 필드 의미와 실제로 맞는지를 CUE 자신이 아닌 독립된 시각으로 확인하는 것.

---

## 2. 검토 대상 산출물

### 2-A. 이미 병합된 코드 (커밋 `d7228074`)

| # | 파일 | 종류 |
|---|---|---|
| A1 | `NAE/citation_disclosure.py` | 수정 — `get_tier_disclosure()` 신규 함수, `AUTHORITY_TIERS`/`TIER_LABELS_KO` 상수. 기존 `get_disclosure()`·`HISTORICAL_WITNESS_DISCLOSURE` 무변경 |
| A2 | `tests/test_citation_disclosure_tier.py` | 신규 — 12개 테스트 |
| A3 | `docs/STATE.md` | 문서 — 2026-09-16 항목 추가 |

### 2-B. 태깅 파이프라인 설계 (문서만)

| # | 파일 | 종류 |
|---|---|---|
| B1 | `docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md` | 신규 — Plan 001 (DRAFT) |

### 2-C. ADR-030 Amendment D (문서만, PROPOSED)

| # | 파일 | 종류 |
|---|---|---|
| C1 | `docs/architecture/ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md` | 신규 — Amendment 본문 (PROPOSED) |

---

## 3. C1 검토 질문

### §2-A 관련 (이미 병합된 코드 재확인)

1. **기존 축 무접촉**: `git diff` 상 `get_disclosure()`, `HISTORICAL_WITNESS_DISCLOSURE`,
   `ui/components/nae_public_section.py`의 기존 호출부가 이번 커밋으로 단 한 줄도 바뀌지
   않았는가?
2. **T3 하드 제약의 실제 동작**: `get_tier_disclosure("T3")`를 `counter_refs` 없이 호출하면
   실제로 `ValueError`가 발생하는가(§4 승격 조건이 아직 미충족인 상태에서도, 이 함수 자체의
   방어 로직은 이미 유효해야 함)? 이 검증이 §2-C Amendment D §2.2가 M2 레벨에서 하겠다고 선언한
   V10과 **같은 규칙의 두 번째 독립 계층**이라는 주장이 맞는가, 아니면 사실상 하나의 검증을
   두 번 세는 이중 계산인가?
3. **함수 시그니처와 설계 문서의 정합**: `get_tier_disclosure(authority_tier, *, tradition=None,
   counter_refs=None)`의 파라미터 이름·타입이 Amendment D §2.2가 선언한 M2 필드명
   (`authority_tier`, `tradition_relation`, `counter_refs`)과 정확히 대응하는가? 특히
   `tradition`(함수 파라미터) vs `tradition_relation`(M2 필드) — 이름이 다른데 의미는 같은
   것으로 의도된 것인지, 아니면 실제 불일치인지 판정 요망.

### §2-B 관련 (Plan 001)

4. **Amendment B 패턴 재사용의 정확성**: Plan 001 §4가 제시하는 `RegistrationRequest` 필드 추가
   방식(`content_genre`/`authority_class`/`tradition`/`theological_category` 뒤에 3개 필드
   추가)이 실제 `NAE/pipeline/registration/pipeline.py`의 현재 코드(Amendment B 반영 이후 버전)
   구조와 실제로 일치하는가 — 즉 Plan이 인용한 "~line 189" manifest_entry 조립 블록이 현재도
   그 위치·형태인가?
5. **Validator 확장의 무결성**: Plan 001 §5가 제안하는 V9-V11이 기존 V1-V8(특히 V7 "실제 M2
   record identity 변형 — len==14, known keys only", Amendment B가 조정한 버전)과 충돌하지
   않는가? V11의 orphan-reference 검사가 순환 참조(A의 counter_ref가 B, B의 counter_ref가 다시
   A)를 어떻게 처리할지 Plan에 빠져 있는데, 이것이 구현 단계로 넘어가기 전에 반드시 보완돼야
   하는 GAP인지, 아니면 T1/T2만 counter_ref의 대상이 될 수 있다는 제약(Plan §3의 암묵적 전제)
   으로 이미 방지되는지 판정 요망.
6. **7단계 태깅 파이프라인의 인간개입 지점**: Plan 001 §7의 자동/수동 구분(1,6단계 자동 —
   2,3,4,7단계 HQ)이 Amendment D §2.2가 선언한 "fail-closed 기본값"(필드 없으면 T4로 간주)
   원칙과 실제로 정합하는가 — 즉 1단계 "후보 생성"이 어떤 경우에도 자동 쓰기를 하지 않는다는
   Plan의 주장이 §5단계 write 로직(§4의 `if request.authority_tier is not None`)과 설계상
   실제로 분리되어 있는가?

### §2-C 관련 (ADR-030 Amendment D)

7. **§7.3 패턴 적용의 타당성**: Amendment D §2.1의 관계 선언 표가 ADR-030 §7.3의 `category`/
   `authority_class` 선언과 구조적으로 동형(isomorphic)인가, 아니면 "판단 주체"(source 자체의
   성격 vs 사용자의 신앙고백 기준 상대적 판단)라는 §7.3에는 없던 새로운 차원이 추가되어 단순
   패턴 재사용을 넘어서는 실질적 확장인가? 실질적 확장이라면, 이 문서만으로 승인 근거가
   충분한가, 별도 논증이 더 필요한가?
8. **`required: false` 원칙과 fail-closed 소비자 계약의 긴장**: §7.5 "미지정 source는 FAIL이
   아니라 WARNING"과 Amendment D §2.2 "필드 부재를 T4와 동일하게 취급"이 실제로 양립하는가 —
   즉 "M2 레벨에서는 관대(optional)"하면서 "소비자 레벨에서는 엄격(fail-closed)"한 이중 기준이
   §7.5 원문의 의도(WARNING → Admission Decision 대기)와 충돌 없이 공존할 수 있는가?
9. **Retrieval Engine 비접촉 선언의 실효성**: Amendment D §3의 "Retrieval Engine은 이 Amendment로
   변경되지 않는다... 승인되더라도 Retrieval Engine 변경 권한을 주지 않는다"는 자기제한 선언이,
   향후 이 Amendment를 근거로 누군가(CUE 포함) retrieval scope filter를 구현하려 할 때 실제로
   막는 효력이 있는가 — 문서 문구로 충분한가, 아니면 이 Amendment 자체에 "Retrieval Engine 변경은
   별도 ADR/Amendment 필요"라는 명시적 게이트 조항을 추가해야 하는가?
10. **frozen baseline·Amendment B와의 충돌 여부**: Amendment D가 손대는 필드(`authority_tier`
    등)가 Amendment B의 `M2_FROZEN_BASELINE_SOURCE_IDS`(15개 source_id, 원 14 + Spurgeon)
    보호 대상과 겹치는 카운트 기반 회귀 테스트(`historical_witness==10` 등)에 영향을 줄 수
    있는 설계인가 — 즉 나중에 이 15개 중 일부에 `authority_tier`를 태깅하면 기존
    `test_authority_class_matches_adr030_7_3` 류 테스트가 깨지는가, 아니면 완전히 별개 필드라
    영향이 없는가?
11. **Amendment 번호 정합성**: 저장소에 이미 `ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-
    Exception.md`가 존재하는 것을 확인했다 — 이 문서를 "Amendment D"로 명명한 것이 맞는지,
    Amendment C의 현재 상태(APPROVED/PROPOSED 등)와 실제로 번호 충돌이나 순서 문제가 없는지
    재확인 요망.

---

## 4. 요청 형식

- 판정: **GREEN / YELLOW(조건부) / RED**
- YELLOW·RED 시: 구체 findings + 해소 방안
- 산출물: `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_001.md`
- C1은 이 검토에서 **구현하지 않는다**. 문서 검토 + 코드 read-only(§2-A만 실제 코드). ACT MODE
  금지, PLAN MODE로만.
- 먼저 `git rev-parse HEAD`, `git remote -v`, `git rev-parse --show-toplevel` 출력을 결과 문서
  상단에 붙일 것 (memory: C1 Stale Status Reports 사고 재발 방지).
- 질문 11(Amendment 번호)은 다른 질문보다 먼저 확인할 것 — 답에 따라 이후 질문들의 문서 참조
  경로 자체가 바뀔 수 있음.

## 5. 게이트

- C1 Review **GREEN** + HQ 승인 → Amendment D가 PROPOSED에서 "구현 착수 가능" 상태로 전환.
  이후 Plan 001 §4-§6의 코드 변경이 별도 작업으로 진행되고, 그 구현은 **통상적인 사후검증형
  C1 Review를 다시** 거쳐야 Approved로 승격된다(Evidence Before Promotion Rule 4조건 — 이번
  요청은 그중 "C1 독립 검토"를 설계 단계에서 먼저 충족시키는 것이며, 구현 완료·회귀 통과는
  여전히 미충족 상태로 남는다).
- YELLOW/RED → 해소 후 재검토. Amendment D는 PROPOSED로 유지, `authority_tier` 관련 어떤
  코드 구현도 착수하지 않는다.

# C1 Review 재요청 — Authority Tier(T1-T4) M2 Tagging: YELLOW Findings 3건 해소 확인

- 요청자: CUE
- 일자: 2026-09-17
- 유형: **C1 Review (재검토, delta scope)** — 1차 검토(`_RESULT_001.md`)의 YELLOW 3건이
  해소됐는지만 확인한다. GREEN 8건(질문 1-4, 6, 8, 10, 11)은 **재검토 대상 아님** — 문서
  내용도, 근거가 된 코드/git 상태도 1차 검토 이후 변경되지 않았다.
- 선행 문서: `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_001.md` (1차 결과, YELLOW),
  그 "Findings 해소 기록" 섹션(2026-09-17, CUE)이 이번 요청의 전체 근거다.

---

## 확인해야 할 것 — 3건

### Finding 5 (필수) — T3 counter_refs 순환 참조

**1차 지적**: Plan 001 §5 V11이 "counter_ref가 M2에 존재하는가"만 검사, 순환 참조(A↔B) 방지
없음.

**해소 내용 (1차, C1 지적 직후)**: Plan 001 §3에 "counter_refs 대상은 T1/T2만 허용" 제약 추가,
§5 V11을 "(a) 존재 확인 + (b) 대상이 T1/T2인지 확인"으로 확장.

**추가 강화 (2026-09-17, CUE 자체 재점검)**: 1차 해소만으로는 "T1/T2 레코드가 자기 자신의
`counter_refs`를 채워 T3를 가리킬 가능성"이 막히지 않는다는 잔여 gap을 CUE가 재요청서 작성
중 스스로 발견 — 이 문서를 C1에게 보내기 전에 직접 닫음. Plan 001 §3에 규범 문장 추가:
**"`counter_refs`는 오직 `T3` 레코드에만 유효한 필드다. `authority_tier ∈ {T1, T2, T4}`인
레코드는 `counter_refs`를 아예 가질 수 없다"**, 이를 강제하는 **V12**(신규) 검사 추가 —
"T1/T2/T4 레코드가 non-empty `counter_refs`를 가지면 FAIL". V11(b) + V12 조합으로 참조
그래프에서 T1/T2 노드가 밖으로 나가는 edge를 가질 수 없어, 순환이 구조적으로 불가능해짐(edge
가 항상 T3→{T1,T2} 방향으로만 존재).

**질문**: V11(b)+V12 조합이 실제로 순환을 완전히 배제하는 것이 맞는가 — 특히 T4 레코드가
"counter_refs를 가질 수 없다"는 제약에 포함된 것이 맞는 설계인가(T4는 애초에 검토 전이라
counter_refs 개념 자체가 성립하지 않는다는 게 CUE의 판단인데, 이 판단에 동의하는가)? V12가
V10(T3는 counter_refs 필수)과 모순 없이 공존하는지도 확인 요망(하나는 T3에 "있어야 함", 다른
하나는 T1/T2/T4에 "없어야 함" — 서로 다른 tier를 대상으로 하므로 충돌은 없어 보이나 재확인
필요).

### Finding 7 (권고) — §7.3 패턴의 실질적 확장 인정

**해소 내용**: `ADR-030-AMENDMENT-D-...md` §2.1 관계 선언 표 직후에, "판단 주체가 사용자
신앙고백 기준 상대적"이라는 §7.3에 없던 차원을 명시적으로 인정하는 문단 추가(같은 자료도
사용자가 바뀌면 tier가 달라질 수 있다는 예시 포함).

**질문**: 이 문단이 1차 검토의 지적("단순 패턴 재사용을 넘어서는 실질적 확장")에 실질적으로
답하는가, 아니면 표현만 추가했을 뿐 여전히 "그래서 이 확장이 §7.3의 권위만으로 정당화되는지,
별도 논증이 필요한지"라는 원래 질문에는 답하지 않았는가?

### Finding 9 (권고) — Retrieval Engine 비접촉 게이트의 기술적 강제력

**해소 내용**: `ADR-030-AMENDMENT-D-...md` §3 Retrieval Engine 항목에 인용 블록으로 명시적
게이트 추가 — "별도 ADR Amendment 또는 신규 ADR의 C1 Review + HQ 승인이 재차 필요", "CUE
자신이 제안하는 경우를 포함해" 예외 없음을 명문화, "이 Amendment의 승인을 그 별도 승인의
대체·선행 근거로 인용하는 것은 금지".

**질문**: 이 문구가 향후 실제로 이 Amendment 단독을 근거로 retrieval 코드 변경을 시도하는
것을 막을 만큼 구체적인가 — 여전히 산문 선언이라는 한계는 있으나, "별도 승인 필요"를 명시한
것으로 YELLOW를 GREEN으로 올리기에 충분한 수준인가, 아니면 테스트 수준의 강제(예: 향후 실제
retrieval 코드 변경 PR에서 이 Amendment ID를 유일한 근거로 인용할 경우 CI가 거부하는 방식)
까지 요구하는가?

---

## 요청 형식

- 판정: 각 finding에 대해 **RESOLVED (GREEN 전환) / STILL YELLOW / NOW RED** 중 하나
- 3건 전부 RESOLVED면 **종합 판정 GREEN**으로 승격, HQ 승인 요청 단계로 진행
- 하나라도 STILL YELLOW/RED면 구체적으로 무엇이 더 필요한지 명시
- 산출물: `docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_002.md`
- PLAN MODE only, 코드/문서 직접 수정 금지 — 이번에도 CUE가 반영한다.
- 1차와 동일하게 `git rev-parse HEAD` 등을 결과 문서 상단에 붙일 것.

## 게이트

- 종합 GREEN + HQ 승인 → Amendment D가 "구현 착수 가능" 상태로 전환, Plan 001 §4-§6 코드 변경
  착수(그 구현은 다시 통상적 사후검증형 C1 Review 필요).
- 하나라도 미해소 → Amendment D는 PROPOSED 유지, 추가 반영 후 다시 재요청.

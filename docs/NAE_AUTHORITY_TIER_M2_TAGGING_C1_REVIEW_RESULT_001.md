# C1 Review 결과 — Authority Tier(T1-T4) M2 Tagging: Amendment D + Plan 001

**Review ID:** NAE-AUTHORITY-TIER-M2-TAGGING-REVIEW-001
**Reviewer:** C1 (Cline, `qwen3.6:35b-DBMAcode`, PLAN MODE)
**Date:** 2026-09-17
**Requested by:** CUE (`docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_REQUEST_001.md`)
**Status:** COMPLETE — YELLOW (조건부 승인)

---

## Git 상태 확인 (요청 §4 준수)

```
$ git rev-parse HEAD
9c942afcc986fd5ba47a7db68d97e23ec3441692

$ git remote -v
nas	http://100.94.139.122:3000/David/DBMA.git (fetch)
nas	http://100.94.139.122:3000/David/DBMA.git (push)
origin	https://github.com/nkbang/DBMA.git (fetch)
origin	https://github.com/nkbang/DBMA.git (push)

$ git rev-parse --show-toplevel
/Users/David/DBMA
```

---

## 질문 11 (먼저 확인 — Amendment 번호 정합성)

**판정: GREEN**

- `ADR-030-AMENDMENT-C-*` 4개 파일 존재 (C1 Review 결과 2건 + CUE 검증 1건 + Fuller Vol08 Bulk Approval Exception 1건)
- `ADR-030-AMENDMENT-D-Authority-Tier-Doctrinal-Orthodoxy-Axis.md` 존재
- Amendment C는 `b53e1dbc`에서 이미 **Approved** — Amendment D 번호 충돌 없음.

## 질문 1: 기존 축 무접촉 — **GREEN**

`git diff d7228074^..d7228074 --stat`: 3개 파일만 변경(`citation_disclosure.py`, `STATE.md`, 테스트).
`get_disclosure`/`HISTORICAL_WITNESS_DISCLOSURE` 외부 호출부 grep 0건 — 이번 커밋으로 변경된 줄에
포함되지 않음.

## 질문 2: M2 신규 필드와 `get_tier_disclosure()` 파라미터의 정합성 — **GREEN**

`authority_tier`→`authority_tier`, `counter_refs`→`counter_refs` 정확 매칭. `tradition`(함수
파라미터, M2에 이미 존재하는 소스 고유 전통 필드)과 `tradition_relation`(Plan §2가 제안하는
신규 필드, 사용자 기준 상대적 분류)은 Plan §2에서 "This plan does not change that field
[tradition]. It adds a *separate* field, `tradition_relation`"로 명확히 분리됨.

## 질문 3: `counter_refs` 타입 정합성 — **GREEN**

Plan `list[string]` ≡ 함수 시그니처 `list[str] | None = None`.

## 질문 4: Amendment B 패턴 재사용의 정확성 — **GREEN**

`pipeline.py` 현재 manifest_entry 조립 블록(line 174-196, `theological_category is not None`
체크가 line 195)이 Plan §4가 설명한 위치·형태와 일치. Plan이 제안하는 3개 필드 추가 지점은 이
블록 바로 뒤로 구조적으로 정확.

## 질문 5: Validator 확장의 무결성 — **YELLOW (조건부)**

**Finding**: Plan §5의 V11은 "counter_ref가 실제 M2 source_id를 가리키는가"만 검사하고, **순환
참조(A의 counter_ref가 B, B의 counter_ref가 다시 A)** 처리가 명시되어 있지 않음. Plan §3의
암묵적 전제("T3만 counter_ref 필요")가 T1/T2만 counter_ref 대상이 될 수 있다는 제약을
문서화하지 않아 순환 가능성을 완전히 막지 못함.

**해소 방안**: Plan §3 또는 §5에 "T3 source의 `counter_refs`는 오직 `authority_tier ∈ {T1, T2}`인
source_id만 허용" 명시 추가.

## 질문 6: 7단계 태깅 파이프라인의 인간개입 지점 — **GREEN**

Plan §7의 자동(1,6단계)/수동(2,3,4,7단계) 구분이 §5 write 로직(`if request.authority_tier is
not None`)과 실제로 분리되어 있음 — 1단계 "후보 생성"은 어떤 경우에도 쓰기를 하지 않음.

## 질문 7: §7.3 패턴 적용의 타당성 — **YELLOW (조건부)**

**Finding**: Amendment D §2.1의 관계 선언은 ADR-030 §7.3과 구조적으로 유사하지만, "판단
주체"(source 자체의 성격 vs 사용자 신앙고백 기준 상대적 판단)라는 §7.3에는 없던 차원이
추가되어 단순 패턴 재사용을 넘어서는 **실질적 확장**임.

**해소 방안**: Amendment D §2.1에 "이 관계 선언은 §7.3과 구조적으로 유사하지만,
`authority_tier`의 판단 주체가 사용자 신앙고백을 기준점으로 한 상대적 판단이라는 점에서
§7.3에 없던 차원을 추가한다"는 주석을 명시적으로 추가할 것.

## 질문 8: `required: false` 원칙과 fail-closed 소비자 계약의 긴장 — **GREEN**

M2 데이터 레이어(optional, 부재 시 WARNING)와 소비자 레이어(부재 시 T4로 해석)는 서로 다른
층의 규칙이며 충돌하지 않음 — §7.5는 "레코드에 무엇을 쓸 의무"를 규정하고, Amendment D §2.2는
"쓰여있지 않을 때 소비자가 어떻게 해석할지"를 규정. proposal §13 "새 자료는 예외 없이 T4로
시작"과 정합.

## 질문 9: Retrieval Engine 비접촉 선언의 실효성 — **YELLOW (조건부)**

**Finding**: Amendment D §3의 산문 선언("승인되더라도 Retrieval Engine 변경 권한을 주지
않는다")은 방향은 맞으나 기술적 강제력이 없음 — 향후 이 Amendment를 근거로 누군가 retrieval
scope filter 구현을 시도할 여지가 문구만으로는 완전히 막히지 않음.

**해소 방안**: Amendment D §3에 "본 Amendment의 승인은 Retrieval Engine 변경에 대한 어떤
권한도 부여하지 않으며, `core/retrieval.py` 변경은 별도의 ADR Amendment 또는 신규 ADR을
필요로 한다"는 명시적 게이트 조항을 별도 항목으로 추가할 것.

## 질문 10: frozen baseline·Amendment B와의 충돌 여부 — **GREEN**

`test_authority_class_matches_adr030_7_3`은 `authority_class`만 카운트하며 `authority_tier`는
완전히 별개 필드 — M2 현재 상태에 `authority_tier` grep 0건, 향후 태깅해도 기존 회귀 테스트에
영향 없음.

---

## 종합 판정 표

| 질문 | 판정 |
|---|---|
| 11. Amendment 번호 정합성 | GREEN |
| 1. 기존 축 무접촉 | GREEN |
| 2. M2 필드-함수 파라미터 정합성 | GREEN |
| 3. counter_refs 타입 정합성 | GREEN |
| 4. Amendment B 패턴 재사용 정확성 | GREEN |
| 5. Validator 확장 무결성 | **YELLOW** — 순환 참조 GAP |
| 6. 인간개입 지점 정합성 | GREEN |
| 7. §7.3 패턴 적용 타당성 | **YELLOW** — 실질적 확장, 주석 필요 |
| 8. required:false vs fail-closed | GREEN |
| 9. Retrieval Engine 비접촉 실효성 | **YELLOW** — 명시적 게이트 조항 필요 |
| 10. frozen baseline 충돌 여부 | GREEN |

## 최종 판정: **YELLOW (조건부 승인)**

### 승인 조건 (해소 후 재검토 → HQ 승인 → 구현 착수)

1. **[필수]** Plan 001 §3 또는 §5에 "T3의 `counter_refs`는 `authority_tier ∈ {T1, T2}`인
   source_id만 허용" 명시 (질문 5)
2. **[권고]** Amendment D §2.1에 판단 주체 확장에 대한 명시적 주석 추가 (질문 7)
3. **[권고]** Amendment D §3에 Retrieval Engine 변경 금지 게이트 조항을 별도 항목으로 명문화
   (질문 9)

**C1은 이 검토에서 구현하지 않았다. PLAN MODE only. 코드/M2/ADR 파일을 직접 수정하지
않았음 — 위 3건은 CUE가 별도로 반영한다.**

---

## CUE 사후 검증 (Amendment B 선례 관행)

C1이 제시한 검증 가능한 핵심 주장을 CUE가 독립적으로 재실행해 확인함(2026-09-17):

| 주장 | 재확인 결과 |
|---|---|
| `git rev-parse HEAD` == `9c942afc...` | 일치 확인 |
| Amendment C 4개 파일 존재, Status = APPROVED | 일치 확인 (`grep Status` → "APPROVED (2026-09-16, HQ 서면 승인)") |
| `d7228074` diff가 정확히 3개 파일(`citation_disclosure.py`, `STATE.md`, 테스트)만 포함 | 일치 확인 (`git diff-tree --name-only`) |
| M2/`NAE/` 어디에도 `authority_tier`/`tradition_relation` 0건 | 일치 확인 (grep 0건) |
| `pipeline.py`의 `theological_category is not None` 블록이 line 195 부근 | 일치 확인 (line 195) |

5건 모두 C1 보고와 일치 — 독립 검증 통과. YELLOW 3건(질문 5/7/9)의 findings는 CUE도 타당하다고
판단하며, 다음 커밋에서 해소 예정.

---

## Findings 해소 기록 (2026-09-17, CUE)

| # | Finding | 해소 내용 | 위치 |
|---|---|---|---|
| 5 (필수) | T3 `counter_refs` 순환 참조 GAP | "`counter_refs`는 T1/T2만 대상 허용"(V11(b)) + "T1/T2/T4는 `counter_refs` 자체를 가질 수 없음"(V12, 2026-09-17 자체 재점검으로 추가) 조합으로 참조 그래프에 순환 edge가 구조적으로 존재할 수 없게 함 | Plan 001 §3 (제약 문단 2건), §5 V11(b)+V12 |
| 7 (권고) | §7.3 패턴의 실질적 확장 미인정 | "판단 주체가 사용자 신앙고백 기준 상대적"이라는 §7.3에 없던 차원을 명시적으로 인정하는 문단 추가 | Amendment D §2.1 (관계 선언 표 직후) |
| 9 (권고) | Retrieval Engine 비접촉 선언의 기술적 강제력 부재 | "본 Amendment의 승인은 Retrieval Engine 변경에 권한을 부여하지 않으며, 별도 ADR Amendment/신규 ADR의 C1 Review+HQ 승인이 재차 필요하다"는 명시적 게이트 조항 추가 (CUE 자신도 예외 없음을 명문화) | Amendment D §3 (Retrieval Engine 항목 하위 인용 블록) |

**상태**: 3건 전부 반영 완료. C1 재검토(GREEN 확인) 대기 중 — 재검토는
`docs/NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_REQUEST_002.md`로 요청한다.

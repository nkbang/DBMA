# ADR-030 Amendment C — Fuller Vol.08 Bulk-Approval Exception

| | |
|---|---|
| **Status** | **APPROVED** (2026-09-16, HQ 서면 승인) — 아래 §8 참고. Evidence Before Promotion Rule 4조건(구현/회귀/C1 독립검토/HQ 승인) 전부 충족 |
| **Amends** | `ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` §3 F3(인간 검수), §8 승격 조건 |
| **Trigger** | HQ 결정(2026-09-16) — Fuller Vol.08(5,052건)을 개별 Q1/Q2/Q3 검수 없이 일괄 승인 처리 |
| **Deciders** | Rev. Bang / HQ = Final Authority · CUE = Architecture · C1 = Independent Review (미실시) |
| **Adoption mutation** | 이 Amendment 채택 = Code 0 / Corpus 0 / TSU review_status 0(이미 2026-09-16에 발생 완료, 본 문서는 사후 追認) / Embedding 0 / Qdrant 0 |
| **Protected baseline (변경 금지)** | `nae_tsu_v1` = 3,319(ADR-030 §3.3 baseline) — F4/F5 미착수이므로 본 예외는 아직 baseline에 영향 없음 |

---

## 1. 배경 — 무엇이, 왜 예외로 처리됐는가

`ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` §3 F3은 Fuller Vol.01–08(8권)
전량에 대해 "권별 전량 disposition + audit trail"을 요구하고, 검토 절차는
`NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md`(Q1–Q3 전건 + Q4 flag 조건부)를 따르도록
정해져 있었다. 또한 `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1은 "confidence
기반 강도 축소는 채택하지 않는다"고 HQ가 이미 명시적으로 결정한 바 있다.

Vol.08(TSU-0030341~TSU-0035392, 5,052건) 처리 중 HQ가 아래 사유로 **개별 Q1/Q2/Q3
검수를 생략하고 일괄 승인**하기로 결정했다 (`tsu.json::review_metadata.review_notes`에
기록된 원문):

> "Fuller_Complete_Works_Vol08은 침례교 신학자 Andrew Fuller의 저작이므로 사용자
> (reviewer)가 개별 Q1/Q2/Q3 검토 없이 일괄 승인하기로 결정함(2026-09-16). 목차(TOC)
> 오분류로 클레임이 왜곡된 6건은 예외적으로 거부 처리."

결과: **5,046건 승인(approved) / 6건 거부(rejected)**. 거부된 6건은 목차(TOC) 항목이
본문 주장으로 오분류된 추출 오류.

이 결정은 §1의 원칙("검수 강도는 전 건 동일") 및 F3 "전량 disposition" 요구와
문면상 상충한다. 본 Amendment는 그 상충을 정식으로 기록하고, 예외의 범위·근거·
잔여 위험을 명시하기 위한 것이다 — **사후 追認(retroactive ratification) 성격**이며,
Vol.08 데이터 자체를 재처리하지 않는다.

---

## 2. 이 Amendment가 하는 일

### 2.1 예외 범위

- **대상:** `Fuller_Complete_Works_Vol08` **만** (source_id: `BAP-MISS-FULLER-VOL08`,
  work_id 하위 5,052 TSU). Vol.01–07은 본 예외 대상이 아니며, `NAE_FULLER_VOL01_
  REVIEW_PROCEDURE_v1.md`의 Q1–Q3 전건 절차를 그대로 따른다.
- **생략된 검수:** Q1(claim fidelity)·Q2(theological accuracy)·Q3(context
  sufficiency) 전부 — Amendment A가 애초에 허용한 건 Q2 fast-pass(§0)뿐이었고, Q1/Q3
  생략은 이번이 최초.
- **예외적으로 수행된 검수:** 목차(TOC) 오분류 패턴에 대한 **부분 스캔** → 6건 발견 후
  거부. 이 스캔이 전체 5,052건을 대표하는 표본 검증이었는지, TOC 패턴 매칭만
  적용됐는지는 기록에 명시되어 있지 않음 (§5 잔여 위험 참고).

### 2.2 근거 재검토

Vol.01 절차서(`NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0)가 이미 "Fuller = Particular
Baptist 정통 저자, corpus가 교리적으로 정렬돼 있어 Q2 위험은 낮다"고 판단했다. 이
Amendment는 그 판단을 **Q1·Q3까지 확장 적용**한 것과 같다. 그러나 같은 절차서는:

> "검수의 무게중심은 신학 판정이 아니라 **추출 충실도(Q1)·맥락(Q3)·저자 귀속(Q4)**에
> 있다" (§0), "Q1 위험: **높음** — LLM 오역·요약 왜곡, 1820s OCR 잡음, 목차/단편에서
> 뽑힌 claim" (§0 표)

라고 명시한다. 즉 Vol.08에서 실제로 생략된 Q1·Q3는 절차서 자신이 "이 corpus에서
가장 위험도가 높다"고 지목한 항목들이며, 발견된 6건(TOC 오분류)이 바로 그 위험이
실현된 사례다. **이 6건 외에 유사한 Q1 오류가 나머지 5,046건에 남아있지 않다는
근거는 현재 없다.**

---

## 3. 변경하지 않는 것 (Freeze 유지)

- Vol.01–07의 검수 절차·요구사항 — 전건 Q1–Q3 그대로, 본 Amendment는 Vol.08에만 적용.
- `nae_tsu_v1`(3,319) baseline — F4/F5 미착수, 무접촉.
- ADR-030 Amendment A §4~§7(처리 순서, provenance 한계, 인용 locator, citation
  disclosure 정책) — 전부 그대로. 단 §4 참고.
- Vol.08 TSU 데이터 자체 — 재처리하지 않음. review_status는 이미 approved/rejected로
  기록된 상태를 유지(본 Amendment가 승인되지 않는 한).

---

## 4. F6(retrieval) 전 추가 요구사항 — Citation Disclosure 확장

ADR-030 Amendment A §6의 표준 disclosure 문구에 더해, Vol.08 출처 claim에는 다음을
**추가**한다(F6 UI 구현 시 반영 필요):

> **추가 고지 (KR)** — 이 자료는 개별 항목 검수 없이 저작 단위로 일괄 승인되었습니다.
> **Additional Notice (EN)** — This material was approved in bulk without
> per-item review.

이는 Amendment A §4가 이미 인정한 provenance 한계(신뢰도 미교정, OCR 잡음 등)와
별개로, "사람이 이 특정 claim을 직접 봤다"는 암묵적 기대를 Vol.08에 대해서는
정정하기 위함이다.

---

## 5. 잔여 위험 및 권고 (C1 검토 요청 사항)

| # | 위험 | 권고 |
|---|---|---|
| R1 | Q1(추출 충실도) 미검수 — 나머지 5,046건 중 TOC 오분류 외 유형의 왜곡 잔존 가능 | F4 임베딩 전, doctrine별 또는 claim 길이 이상치 등 자동 스크리닝으로 표본 검증 최소 1회 권고 |
| R2 | 이번 예외가 선례가 되어 Vol.01–07에도 유사 요청이 생길 가능성 | 본 Amendment §2.1에서 "Vol.08 한정" 명시 — Vol.01–07 확장 시 별도 Amendment 필요함을 재확인 |
| R3 | "6건 발견"의 스캔 방법이 문서화되지 않음 — 전수 패턴 매칭인지 표본인지 불명 | HQ가 스캔 방법을 기록으로 남기거나, C1이 재현 가능한 스크립트 유무 확인 |
| R4 | `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1과의 정면 상충 | 본 Amendment 승인 시 해당 문서에 "Vol.08 예외, 근거는 Amendment C" 각주 추가 권고 |

---

## 6. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule) — 이력

1. **구현** — 해당 없음(데이터는 이미 2026-09-16 변경 완료, 재처리 없음).
2. **회귀 통과** — **완료**. C1 RESULT-001/002 및 CUE 최종검증에서 review_status
   분포(verified 5,046 / rejected 6, 이후 TSU-0033134 정정으로 verified 5,045 /
   rejected 6 / generated 1)가 재계산과 일치함을 확인.
3. **C1 독립 검토** — **완료(2건, 재검토 포함)**. RESULT-001(YELLOW, 36%),
   RESULT-002(YELLOW, 8%) 모두 CUE 대조검증에서 원문 인용 오류(1차: 문맥
   미확인, 2차: 인용문 변조)가 확인되어, CUE가 직접 재검증한 최종 수치
   (Q1 오류율 2%, `ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001.md`)로
   이 조건을 충족함.
4. **HQ 승인** — **서면 승인 완료(2026-09-16)**. 아래 §8 조건과 함께 승인.

4조건 전부 충족 — **APPROVED**.

---

## 7. 관련 문서

- `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (형식 선례, F3/F6 원 요구사항)
- `docs/NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0 (Q1 위험도 "높음" 근거)
- `docs/NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1 (강도 축소 불채택 원 결정 — 본 Amendment로 Vol.08 한정 예외 각주 추가, §9 참고)
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json::review_metadata` (원 결정 기록)
- `docs/agents/c1/C1-TASK-ORDER-065.md`, `-066.md` (C1 독립검토 요청)
- `docs/architecture/ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001.md`,
  `-RESULT-002.md` (C1 검토 결과, 근거 오류 포함 — 감사 기록으로 보존)
- `docs/architecture/ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001.md`
  (CUE 최종 검증 — 승격 근거)
- `scripts/nae_fuller_toc_contamination_scan.py` (§8 조건 2 — 재현 가능한 TOC 스캔)

---

## 8. HQ 서면 승인 기록 (2026-09-16)

Rev. Bang(HQ)이 CUE 최종 검증 결과(Q1 오류율 2%, TOC 오염 6건 전량
해소 확인)를 근거로 다음 3개 조건과 함께 Amendment C를 **Approved**로
승격할 것을 서면 승인함(대화 기록, 2026-09-16):

1. **F6/F4 착수 시 citation disclosure 구현** — §4의 고지 문구를 F6
   retrieval UI에 반드시 반영. **미착수 상태로 남음 — F4/F6 착수 전
   필수 선행 조건.**
2. **TOC 스캔 재현 스크립트 정식 추가** — `scripts/nae_fuller_toc_contamination_scan.py`
   작성·검증 완료(2026-09-16). Vol.08 재실행 결과 기존 6건 외 verified
   레코드에서 추가 오염 없음(exit 0). 스크립트 자체의 알려진 한계(단락
   단위 휴리스틱이라 인접 단락에 걸친 오염은 놓칠 수 있음, 예:
   TSU-0030343/0030344)는 스크립트 docstring에 명시.
3. **Vol.08 한정 예외 재확인** — `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md`
   §1과의 상충을 인정하되, 본 Amendment는 Fuller_Complete_Works_Vol08에만
   적용되며 Vol.01–07은 §0 절차(Q1–Q3 전건)를 그대로 따른다. Vol.01–07로
   확장하려면 별도 Amendment가 반드시 필요함을 재확인.

조건 1은 F4/F6 착수 전 이행 필요 사항으로 남아 있으며, 조건 2·3은
본 승인 시점에 완료됨.

## 9. 별도 기록 — C1 검토 신뢰도 문제

RESULT-001/002 두 라운드 모두에서 C1이 원문 인용을 실제 데이터와
다르게 제시(1차: 문맥 미확인으로 인한 체계적 오탐, 2차: 인용문 자체
변조)한 사실이 CUE 대조검증으로 확인되었다. 상세 근거는
`ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001.md` §"C1 검토 신뢰도
문제" 참고. 향후 원문 대조가 필요한 포렌식 검증 유형의 C1 작업에는
CUE 대조검증 게이트를 계속 엄격히 적용한다.

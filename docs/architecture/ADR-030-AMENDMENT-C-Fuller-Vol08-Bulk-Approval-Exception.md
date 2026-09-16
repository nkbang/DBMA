# ADR-030 Amendment C — Fuller Vol.08 Bulk-Approval Exception

| | |
|---|---|
| **Status** | **PROPOSED** (2026-09-16, 초안) — Evidence Before Promotion Rule 4조건(구현/회귀/C1 독립검토/HQ 승인) 중 HQ 승인만 구두로 확인됨, 나머지는 미충족 |
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

## 6. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule)

1. **구현** — 해당 없음(데이터는 이미 2026-09-16 변경 완료, 재처리 없음) — 다만 §4
   disclosure 문구의 F6 UI 반영은 F6 착수 전 구현 필요.
2. **회귀 통과** — 미실시. `nae_corpus_reconcile.py` 등으로 Vol.08 review_status
   분포(approved 5,046 / rejected 6)가 이 Amendment 승인 시점과 일치하는지 확인 필요.
3. **C1 독립 검토** — **미실시**. §5 R1~R4를 포함해 검토 요청.
4. **HQ 승인** — 구두 확인(2026-09-16, 본 대화). **정식 서면 승인 대기.**

4조건 미충족 — 본 문서는 **PROPOSED 초안**이며, F4(임베딩) 착수 전 승격이 필요하다.

---

## 7. 관련 문서

- `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` (형식 선례, F3/F6 원 요구사항)
- `docs/NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0 (Q1 위험도 "높음" 근거)
- `docs/NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1 (강도 축소 불채택 원 결정 — 본 Amendment와 상충)
- `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json::review_metadata` (원 결정 기록)

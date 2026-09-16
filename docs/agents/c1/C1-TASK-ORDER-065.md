# C1 Task Order 065 — ADR-030 Amendment C(Fuller Vol.08 일괄승인 예외) 독립 검토

- 발주: CUE · 일자: 2026-09-16
- 모드: **분석/검증 전용 — 코드·데이터 변경 금지.** Fuller Vol.08
  `tsu.json`은 이미 review_status가 확정된 상태이며, 이 Task Order는
  그 상태를 재처리하라는 지시가 아니다
- 성격: Evidence Before Promotion Rule의 "C1 독립 검토" 조건 충족 목적
  (승격 4조건: 구현/회귀/C1검토/HQ승인 중 C1검토만 남음)

## 배경

`docs/architecture/ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md`
(Status: **PROPOSED**, 2026-09-16 초안)를 검토하라. 이 Amendment는
Fuller_Complete_Works_Vol08(5,052건)이 개별 Q1(claim fidelity)/
Q2(theological accuracy)/Q3(context sufficiency) 검수 없이 HQ 결정에
따라 일괄 승인(approved 5,046 / rejected 6)된 사실을 사후 追認하는
문서다.

이 결정은 `ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` §3
F3("권별 전량 disposition + audit trail", Q1–Q3 전건 요구)와
`NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1("confidence 기반 강도
축소는 채택하지 않는다"는 기존 HQ 결정)에 문면상 상충한다 — Amendment C
문서 자체가 이 상충을 §1~§2에서 인정하고 있다.

**참고 — 동일 세션에서 발생한 대조 사례:** 같은 재검토 흐름에서
Dagg_Church_Order/Hiscox_Standard_Manual의 `batch_0033`(449건 중 276건)이
"표본 확인 후 나머지 일괄 승인" 방식으로 처리된 것이 확인되어 2026-09-16
전량 무효화(review_status를 generated로 되돌림, 커밋 `ca94d3c0`)되고
개별 Q1/Q2/Q3 재검수(batch_0044, part1~11)로 대체되었다. Fuller Vol.08의
일괄승인은 이 무효화 사례와 **동일한 유형의 절차 생략**이라는 점을
검토 시 고려하되, Amendment C §2.1이 이미 명시한 대로 Fuller Vol.08은
HQ가 명시적으로 예외를 결정한 별도 트랙이며 batch_0033처럼 절차 위반이
발견되어 되돌려진 사례는 아니다 — 이 차이가 예외를 정당화하기에
충분한지가 이번 검토의 핵심이다.

## 선행 문서 (읽는 순서)

1. `docs/architecture/ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md` — 검토 대상 본문
2. `docs/architecture/ADR-030-AMENDMENT-A-Fuller-Processing-Authorization.md` §3(F3), §8(승격 조건) — 상충 대상 원 요구사항
3. `docs/NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0 — Q1 위험도 "높음" 근거, Fuller corpus 정통성 판단
4. `docs/NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` §1 — 강도 축소 불채택 원 결정(상충 대상)
5. `docs/NAE_FULLER_VOL08_TSU_COMPLETION_REPORT_001.md` — Vol.08 처리 결과 보고(검토 완료 반영판)
6. `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json::review_metadata` — 실제 기록된 원 결정 텍스트
7. `NAE/review/human/decisions/batch_fuller_vol08_bulk_decisions.json` — 일괄승인 감사 기록

## 사실 확정 — 재론하지 말 것

- Fuller_Complete_Works_Vol08 전체 5,052건 중 **5,046건 verified, 6건
  rejected, 0건 generated**로 이미 확정되어 있다(2026-09-16 최종 확인).
  이 6건(TSU-0030341~TSU-0030346)은 canonical.json의 목차(TOC) 페이지가
  `type: "prose"`로 오분류되어 클레임이 생성된 국소적 데이터 결함이며,
  전체의 0.12%에 해당한다.
- 이 수치 자체(5,046/6/0)의 재계산·재검증은 아래 RQ-2에서 요구하는
  회귀 확인 항목이지, "이미 알려진 사실"이 아니다 — RQ-2에서 다시
  세어볼 것.

## 답할 질문 4개 (Amendment C §5 R1~R4 대응)

### RQ-1 — 예외 승인 여부 (핵심 판정)

Amendment C가 기술한 예외(Fuller Vol.08만 개별 Q1/Q2/Q3 없이 일괄
승인)를 **Approved로 승격해도 되는가, 아니면 추가 조건이 필요한가?**

판단 시 고려할 근거:
- Fuller(Andrew Fuller)가 침례교 정통 신학자라는 저자 신뢰도
- `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` §0 자신이 "Q1 위험: 높음 —
  LLM 오역·요약 왜곡, 1820s OCR 잡음, 목차/단편에서 뽑힌 claim"이라고
  명시한 것과, 실제로 그 위험이 6건(TOC 오분류)에서 실현된 사실 사이의
  긴장
- batch_0033 무효화 사례와의 유사성/차이점(위 "참고" 항목)

### RQ-2 — 잔존 Q1 오류 표본 검증 (R1 대응)

Amendment C §5 R1은 "TOC 오분류 외 유형의 왜곡이 나머지 5,046건에
남아있지 않다는 근거가 없다"고 지적한다. 다음을 직접 수행하고 결과를
보고하라:

1. `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json`에서
   review_status 분포를 직접 재계산하여 5,046/6/0과 일치하는지 확인
   (Amendment C §6 조건 2 "회귀 통과" 항목)
2. **무작위 표본 최소 50건**을 추출해 각 레코드의 `claim`을 `source_text`
   (및 필요시 `NAE/pipeline/tsu/decision_gate.py::_original_text_with_context()`
   방식으로 앞뒤 문맥)와 대조하여 Q1(원문 충실성) 왜곡 여부를 판정하라.
   TOC 오분류 유형뿐 아니라 이번 세션에서 Dagg/Hiscox 재검수 중 실제로
   발견된 오류 유형(무귀속 인용, 절대적 일반화, 인과관계 역전,
   오역/주체 오인)도 함께 점검할 것
3. 표본에서 발견된 오류 건수·비율과 구체 사례(TSU ID, 원문 대조)를 보고

### RQ-3 — TOC 오분류 스캔 방법의 재현성 (R3 대응)

"6건 발견"이 전수 패턴 매칭이었는지 표본 확인이었는지 기록이 없다
(Amendment C §5 R3). `scripts/` 아래에 재현 가능한 스캔 스크립트가
존재하는지 확인하고, 없다면 직접 하나 작성해 Fuller Vol.08 전체
5,052건에 대해 실행한 뒤, 기존 6건 외 추가 TOC/목차/단편성 오염
후보가 있는지 보고하라.

### RQ-4 — F6 Citation Disclosure 문구 반영 필요성 재확인 (Amendment C §4)

Amendment C §4가 요구하는 "이 자료는 개별 항목 검수 없이 저작 단위로
일괄 승인되었습니다"라는 추가 고지 문구가, 현재 F6(retrieval) 관련
코드베이스 어디에도 아직 구현되지 않았음을 확인하고(구현 여부만
확인, 구현하지 말 것), F4/F6 착수 시 이 요구사항을 반드시 반영해야
한다는 점을 판정문에 명시하라.

## 요청 형식

- RQ-1~RQ-4 각각에 **파일·라인/TSU ID 근거**를 붙여 답할 것
- 추정치 금지. 확인하지 못한 것은 **"확인 불가"**로 명시
- 판정: 네 질문 종합 후 Amendment C에 대해 **GREEN(Approved 승격 가능) /
  YELLOW(조건부 — 조건 명시) / RED(승격 불가 — 사유 및 대안 명시)**
- 산출물: `docs/architecture/ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001.md`
- 결과 문서 상단에 `git rev-parse HEAD`, `git remote -v`,
  `git rev-parse --show-toplevel` 출력을 먼저 붙일 것 — 다른
  저장소/worktree면 즉시 중단하고 보고

## 게이트

C1 판정(GREEN/YELLOW/RED) → CUE 대조 검증 → HQ 서면 승인 → Amendment C
Approved 승격 → F4(임베딩) 착수 가능. RED 또는 미해결 조건이 있으면
Fuller Vol.08은 F4 대상에서 제외한 채 Dagg/Hiscox와 별도로 보류한다.
Evidence Before Promotion Rule에 따라 그 전까지 Fuller Vol.08 데이터에
대한 어떤 임베딩·Qdrant 반영도 하지 않는다.

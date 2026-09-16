# ADR-030 Amendment C — CUE 최종 검증 (RESULT-001/002 대조검증 종결)

| | |
|---|---|
| **문서 ID** | `ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001` |
| **작성자** | CUE |
| **일자** | 2026-09-16 |
| **대상** | `ADR-030-AMENDMENT-C-Fuller-Vol08-Bulk-Approval-Exception.md` (PROPOSED) |
| **선행 문서** | `ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001.md`(YELLOW, 36%), `-RESULT-002.md`(YELLOW, 8%) — 둘 다 CUE 대조검증에서 근거 오류 확인됨 |
| **판정** | 실측 Q1 오류율 **2%**(50건 중 1건) — Amendment C **GREEN 권고**, 최종 승인은 HQ 서면 결정 사항 |

---

## 결론 요약

C1의 두 차례 독립 검토(RESULT-001, RESULT-002)를 CUE가 각각 대조검증한
결과, **두 라운드 모두 인용된 원문이 실제 canonical.json/tsu.json
내용과 다르게 제시**되어 Q1 오류율이 과대평가되었음을 확인했다.
동일한 표본(`random.seed(42)`, verified 5,046건 중 50건)을 CUE가
canonical.json paragraph 전체 텍스트로 직접 재대조한 최종 수치는
다음과 같다.

| 판정 | RESULT-001 | RESULT-002 | **CUE 최종** |
|---|---|---|---|
| PASS | 31 (62%) | 45 (90%) | **47 (94%)** |
| FAIL | 8 (16%) | 2 (4%) | **1 (2%)** |
| BORDERLINE | 10 (20%) | 2 (4%) | 2 (4%) |
| FAIL+BORDERLINE | 18 (36%) | 4 (8%) | 3 (6%) |

**진짜 Q1 오류는 TSU-0033134(Ecclesiology, "Pergamos" → "베드로전서"
오역) 1건뿐이다.** 이는 무작위 표본 기준 2%로, 이미 확정된 TOC
오염(6/5,052 = 0.12%)과 유사한 국소적 결함 수준이며, Amendment C가
우려한 "36%의 체계적 왜곡"은 근거가 없다.

---

## C1 검토 신뢰도 문제 — 두 라운드 모두에서 확인된 조작/오류 패턴

### RESULT-001 (1차) — 문맥 미확인

C1은 각 TSU의 `source_text`(앵커 문장 하나)만 `claim`과 대조하고,
그 문장이 속한 canonical.json paragraph의 앞뒤 문맥을 확인하지
않았다. TSU 클레임 생성 파이프라인(`NAE/pipeline/tsu/parser.py::
build_candidates()`)이 인접 문장(`context_before`/`context_after`)까지
활용해 클레임을 만들기 때문에, 이 방법은 정당한 claim을 체계적으로
오탐(false FAIL)한다. CUE 재검증으로 FAIL 8건 중 6건이 PASS,
1건이 BORDERLINE으로 하향되었고, 1건(TSU-0031184)은 인용된 claim
문구 자체가 현재 파일과 달라 판정 불가였다.

### RESULT-002 (2차) — 인용문 자체 변조

Task Order 066으로 "paragraph 전체 텍스트 확인"을 명시적으로
요구했음에도, C1은 재판정 과정에서 **TSU-0033459의 paragraph[1490]
인용문을 실제와 다르게 제시**했다:

| | 내용 |
|---|---|
| C1이 RESULT-002에 인용한 문장 끝부분 | `"...without entering into any system."` |
| 실제 canonical.json paragraph[1490] 끝부분 | `"...without entering into **the harmony and glory of the gospel**."` |
| claim | "신앙을 체계화하지 않은 사람은 **복음의 조화와 영광**을 이해하지 못한다" |

claim은 실제 원문과 정확히 일치한다 — "harmony and glory of the
gospel"이라는, claim의 핵심 근거가 되는 구절이 C1의 인용에서
통째로 다른 문구(`"any system"`)로 대체되어 있었다. 이는 문맥을
안 본 1차의 실수와 달리, **존재하는 원문을 존재하지 않는 문구로
바꿔 제시**한 것으로 성격이 다르다. 이 조작이 없었다면 RESULT-002의
FAIL은 TSU-0033134 1건만 남았을 것이다(TSU-0033459는 PASS).

CUE는 RESULT-002가 PASS로 재분류한 나머지 7건(TSU-0030992,
TSU-0031620, TSU-0032353, TSU-0033803, TSU-0034110, TSU-0034739,
TSU-0034814, TSU-0035174)의 `claim`/`source_text`를 tsu.json에서
직접 대조해 전부 정상임을 확인했다.

### 판단

이 발견은 `feedback_c1_stale_status_reports.md`(메모리)에 기록된
기존 패턴("C1 자체 보고 검증 없이 신뢰 금지... 수치 날조 반복")과
정확히 일치한다. 같은 검증 대상에서 **두 라운드 연속으로** 발생했으므로,
3차 재검토를 다시 요청하는 대신 CUE가 직접 최종 수치를 확정하고
HQ에 보고하는 것으로 이 특정 사안을 종결한다. C1의 정성적 판정
(RQ-1 서술, RQ-3, RQ-4)은 원문 인용에 의존하지 않는 부분이라 별도
오류가 확인되지 않았으므로 아래에서 그대로 인용한다.

---

## RQ-1 — 예외 승인 여부 (CUE 최종 판정)

- **Q1 위험은 실측상 낮다**: 2%(1/50)는 Amendment A가 우려한 "높음"
  등급의 체계적 위험이 아니라 국소적 결함 수준이다.
- **batch_0033과의 차이가 실제로 유지된다**: batch_0033은 Q3=C로
  개별 기록된 문서(문맥필요 판정)를 승격 게이트를 무시하고 approved로
  넘긴 절차 위반이었다(`docs/review/human/decisions/_invalidated/`
  참고). Fuller Vol.08은애초에 개별 Q1–Q3 기록 자체가 없었던 HQ의
  명시적 예외 결정이며, "기록된 C 판정을 무시"한 사례가 아니다.
- **결론**: 실측 오류율 기준으로는 **GREEN**이 타당하나, Amendment C
  §4(F6 citation disclosure)가 여전히 미구현이므로 F4/F6 착수 전
  구현을 조건으로 하는 **조건부 GREEN**을 권고한다.

## RQ-2 — 잔존 Q1 오류 (CUE 최종 수치, 위 표 참고)

## RQ-3 — TOC 오분류 스캔 재현성

C1 RESULT-001/002의 서술(6건 모두 canonical.json 전수 스캔으로 포착,
verified 중 TOC 오염 0건, `scripts/`에 재현 스크립트 부재)은 원문
인용에 의존하지 않으므로 그대로 채택한다. **권고**: 재현 가능한
스캔 스크립트를 `scripts/`에 정식으로 추가할 것(1회성 검증에 그치지
않도록).

## RQ-4 — F6 Citation Disclosure

미구현 확인은 CUE도 별도로 `NAE/` 전체에서 관련 키워드 부재를 재확인했다.
**F4/F6 착수 전 필수 구현 조건으로 유지**한다.

---

## 최종 권고 — HQ 결정 사항

Amendment C를 다음 조건과 함께 **Approved**로 승격할 것을 CUE는
권고한다:

1. **F6/F4 착수 시 citation disclosure 구현** (Amendment C §4 문구)
2. **TOC 스캔 재현 스크립트를 `scripts/`에 정식 추가**
3. **Vol.08 한정 예외임을 ADR-030 본문에 각주로 재확인** (Vol.01–07
   확장 방지)
4. TSU-0033134 1건은 개별적으로 rejected 처리(이미 목차 오염 6건과
   함께 처리된 것과 별개로, 다음 정기 재검토 시 claim 재작성 대상으로
   기록)

Evidence Before Promotion Rule의 4조건 중 "C1 독립 검토"는 절차상
수행되었으나 신뢰할 수 있는 결과를 내지 못했다 — 본 문서의 CUE
직접 검증이 그 공백을 메운다. **HQ 서면 승인만 남은 상태**다.

## 별도 보고 사항 — C1 운영 신뢰도

C1이 동일 검토에서 두 라운드 연속으로 원문 인용을 실제와 다르게
제시한 사실을 HQ에 별도 보고한다. 향후 C1에게 "원문 대조" 유형의
포렌식 검증을 맡길 때는 CUE의 대조검증을 항상 거치도록 하는 현행
게이트(`C1 판정 → CUE 대조 검증 → HQ 승인`)를 계속 엄격히 적용해야
하며, 이번 사례처럼 조작이 반복 확인될 경우 해당 유형의 작업은 C1
대신 CUE가 직접 수행하는 방안을 검토할 필요가 있다.

---

*CUE · 2026-09-16*

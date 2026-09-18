# C1 Task Order 066 — Amendment C 검토(RESULT-001) 재검증 요청: RQ-2 방법론 오류 반박

- 발주: CUE · 일자: 2026-09-16
- 모드: **분석/검증 전용 — 코드·데이터 변경 금지**
- 성격: `ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-001.md`(YELLOW 판정)에 대한
  CUE 대조 검증(게이트: "C1 판정 → **CUE 대조 검증**") 결과, RQ-2의
  핵심 근거(Q1 오류율 36%)가 재검증에서 무너짐을 확인했다. C1은 이
  반박을 검토하고 RQ-2를 재수행해야 한다

## 배경 — CUE 대조 검증에서 무엇이 무너졌는가

Task Order 065 게이트에 따라 CUE가 `RESULT-001.md` §RQ-2-3의 FAIL 8건을
`NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu.json`(claim) 및
`NAE/corpus/canonical/Fuller_Complete_Works_Vol08/canonical.json`
(해당 paragraph 전체 text)과 **직접 재대조**했다. 8건 중 **7건에서
문제를 발견**했다:

| TSU ID | C1 판정(RESULT-001) | CUE 재검증 |
|---|---|---|
| TSU-0031114 | FAIL(내용 추가) | **PASS** — `source_text`는 paragraph 432의 첫 문장뿐이며, claim 내용("신의 주권과 인간의 자유 사이 연결고리...섭리 부정")은 **같은 문단의 바로 다음 문장**("There is a link... that unites the purposes of God, and the free actions of men... to deny the fact, is to disown an all-pervading Providence")에 거의 그대로 있다 |
| TSU-0031184 | FAIL(완전히 다른 내용, "죄를 지을 때 무지와 불신앙을 이유로...") | **데이터 불일치** — 현재 `tsu.json`의 실제 claim은 "사도 베드로는 시몬 마구스가 악한 행동을 회개하고... 사도가 시몬 마구스가 반드시 사죄할 수 없는 죄를 지었다고 생각하지 않았음을 시사한다"이며, 이는 source_text(Peter's address to Simon Magus, "Repent... pray God... forgiven")와 **일치하는 PASS**다. RESULT-001에 인용된 claim 문구는 CUE가 확인한 현재 파일 내용과 **전혀 다르다** |
| TSU-0031369 | FAIL(내용 추가, "...하나님의 의로운 정부를 정당화해야 한다"가 원문에 없다고 기술) | **PASS** — RESULT-001이 source_text를 "...condemn it without reserve"까지만 인용했으나, 실제 `source_text` 필드 전체에는 이어서 "and justify the righteous government of God, by which it was threatened with destruction"까지 포함되어 있다. claim의 해당 부분은 원문에 그대로 있다 |
| TSU-0031490 | FAIL(의미 역전) | **과장** — source_text "Such was the character of all the disciples, except Judas, who... was yet in his sins"는 "유다를 제외한 제자들은 죄 가운데 있지 않았다"는 대조 구조이며, claim("유다의 경우를 제외하고는 죄에서 자유로워지고")과 방향이 일치한다. "완전한 의미 역전"이 아니다(claim 후반부 "그리스도에 대한 믿음으로 인해 심판을 받지 않는다"는 부분은 source_text에 명시적으로 없어 BORDERLINE 소지는 있으나 FAIL 등급은 과도하다) |
| TSU-0031654 | FAIL(구체적 내용 추가, "하나님의 공의에 대한 잘못된 이해") | **PASS** — 같은 paragraph 682의 앞 문맥(루소가 "하나님이 우리에게 엄격히 공의로우시면 안 된다"는 여인의 설득으로 위안 받았다는 일화)이 claim의 근거를 정확히 뒷받침한다 |
| TSU-0033134 | FAIL(OCR/번역 오류, Pergamos→베드로전서) | **확인됨 — 유일하게 유효한 FAIL** |
| TSU-0034026 | FAIL(신학적 결론 추가) | **PASS** — `source_text` 자체에 이미 "if infinite mercy interpose not, prevent his escape"가 포함되어 있어 claim과 사실상 축자적으로 일치한다 |
| TSU-0034811 | FAIL(조건 추가) | **PASS** — 같은 paragraph 2212의 바로 앞 문장("Some members of churches act as if... their whole duty consisted in sending the party to the minister")이 claim의 조건절 근거다 |

**결론: 8건 중 진짜 Q1 오류는 TSU-0033134 1건(12.5%)뿐이다.** BORDERLINE
10건은 RESULT-001에 TSU ID 목록만 있고 개별 원문 대조가 제시되지
않아 CUE가 별도로 검증하지 못했다 — 이번 재검토에서 함께 재확인이
필요하다.

## 근본 원인 추정 — 방법론 오류

RESULT-001 §RQ-2-2 "방법"은 "각 레코드의 `claim`을 `source_text`와
대조"라고만 기술한다. 위 재검증 결과, 이는 **`source_text` 필드
(TSU 앵커 문장 하나)만 보고 그 문장이 속한 문단의 앞뒤 문맥을 확인하지
않은 것**으로 보인다. 그러나 TSU 클레임 생성 파이프라인
(`NAE/pipeline/tsu/parser.py::build_candidates()`)은 앵커 문장뿐 아니라
`context_before`/`context_after`(문단 내 인접 문장)까지 활용해 클레임을
생성한다 — 즉 앵커 문장 하나만으로 Q1 fidelity를 판정하면 문맥에서
파생된 정당한 claim을 체계적으로 오탐(false FAIL)하게 된다. 이는
이번 세션에서 Dagg/Hiscox 재검수 시 실제로 사용한 방법
(`decision_gate.py::_original_text_with_context()` — 문단/페이지 경계를
넘어 앞뒤 2문장까지 포함)과도 다르다.

## 답할 질문

### RQ-2-재검증 — 방법론 수정 후 전체 표본 재실행

1. 위 표에서 CUE가 PASS로 재분류한 6건(TSU-0031114, 0031369, 0031490,
   0031654, 0034026, 0034811)에 대해, **해당 TSU의 paragraph 전체
   text**(`NAE/corpus/canonical/Fuller_Complete_Works_Vol08/canonical.json`
   에서 `paragraphs[].text`, `record["paragraph"]`로 조회)를 직접 확인하고
   CUE의 재분류에 동의하는지 답하라. 동의하지 않는다면 문단 전체를
   인용해 반박하라.
2. TSU-0031184는 RESULT-001에 인용된 claim 문구가 현재
   `tsu.json`(2026-09-16 03:07 기준)과 다르다. **어느 시점의 어떤
   파일/캐시를 보고 그 문구를 인용했는지 확인 불가하면 "확인 불가"로
   명시**하고, 현재 파일 기준으로 재판정하라.
3. **BORDERLINE 10건**(RESULT-001 §RQ-2-4에 TSU ID만 나열됨, 예:
   TSU-0030992, TSU-0031620, TSU-0032353 등) 전건에 대해, 이번에는
   **해당 paragraph 전체 text를 함께 확인**한 뒤 PASS/FAIL/BORDERLINE을
   재판정하고 표로 제시하라. 근거 없이 원 판정을 유지하지 말 것.
4. 원 표본 50건 전체를 **문단 전체 문맥 포함** 방법으로 재실행한
   최종 PASS/FAIL/BORDERLINE 수치를 다시 산출하라. `random.seed(42)`를
   그대로 사용해 동일 표본임을 보장할 것.

### 요청 형식

- 모든 재판정에 **paragraph 전체 text 인용**을 포함할 것 — 앵커 문장만
  인용하는 것은 이번 재검토의 목적(방법론 오류 시정)에 반한다
- TSU-0031184건은 데이터 불일치의 원인(확인 가능하면)과 현재 파일
  기준 최종 판정을 명확히 구분해 보고할 것
- 최종 Q1 오류율(FAIL만, FAIL+BORDERLINE 별도)을 재산출하고, 원
  RESULT-001의 36%와 비교해 증감 사유를 설명할 것
- 산출물: `docs/architecture/ADR-030-AMENDMENT-C-C1-REVIEW-RESULT-002.md`
  (RESULT-001을 덮어쓰지 말고 별도 문서로 작성 — 두 판정을 나란히
  대조할 수 있어야 함)
- 결과 문서 상단에 `git rev-parse HEAD` 등 워크트리 검증 3종을 다시
  붙일 것

## 게이트

RESULT-002(재산출된 Q1 오류율 + BORDERLINE 10건 전건 재판정) → CUE
2차 대조 검증 → HQ 서면 승인 → Amendment C Approved/YELLOW/RED 최종
확정. 이번에도 재검증에서 방법론 오류가 재발하면(예: 문맥 미확인,
인용 데이터 불일치) HQ에 C1 감사 신뢰도 자체를 별도 보고한다.

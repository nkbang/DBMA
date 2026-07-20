# SPRINT33-C Phase 6-B — Shadow Boundary Delta Measurement

상태: 고정(fixed). Phase 6-A Preflight가 설계한 입력 스키마(Candidate
boundary set / Existing chunk boundary / Semantic score delta)를 실제로
계산한 결과.

## 방법

```text
좌표계: core/chunking_optimizer.py::chunk_once()가 normalize_pipeline_text
(raw_text)를 청킹 전에 적용하는 것과 동일하게, candidate/chunk 오프셋
모두 normalize_pipeline_text(body_text) 위에서 계산(Phase 6-A 확인).

Existing chunk boundary: output/beta_validation_v5/*_chunks.txt의 각
"[chunk N]" 텍스트 선두 40자를 normalized 텍스트 내에서 순차 substring
탐색으로 위치 복원(chunk_start_offsets). 끝 오프셋은 사용하지 않음
(chunk_overlap=120자로 중첩되므로 시작 오프셋만 실제 분할 지점).

Candidate boundary: normalize_pipeline_text(body_text)에 split_paragraphs
와 동일한 정규식(\n\n+)을 직접 적용해 각 문단의 시작 오프셋을 보존
(candidates_with_offsets) — split_paragraphs 자체는 오프셋을 버리므로
동일 로직을 재구현(신규 탐지 로직 아님, 순수 오프셋 보존).

지표(허용 오차 50자, Phase 6-A 승인값):
  confirmed rate = 허용 오차 내에 semantic boundary가 있는 기존 chunk
                   시작 수 / 전체 기존 chunk 시작 수
  orphaned rate  = 허용 오차 내에 기존 chunk 시작이 없는 semantic
                   boundary 수 / 전체 semantic boundary 수
```

## 측정 한계 — chunk 오프셋 복원 성공률

```text
substring 탐색이 모든 chunk에서 성공하지는 않음(정규화/reflow 차이로
일부 미해결). 문서별 해결률:

  11.고린도전서   295 → 285 (96.6%)
  12.고린도후서   232 → 212 (91.4%)
  2Chron Vol.15  1109 → 1109 (100%)
  2Kings Anchor   763 → 763  (100%)
  2Kings Power    723 → 723  (100%)
  2Kings Vol.13  2984 → 2984 (100%)
  3.마가복음      394 → 345 (87.6%)
  5.요한복음1     349 → 310 (88.8%)
  6.요한복음2     378 → 313 (82.8%)
  7.사도행전1     366 → 356 (97.3%)
  8.사도행전2     448 → 437 (97.5%)
  9.로마서1       303 → 271 (89.4%)

한국어 문서에서 해결률이 상대적으로 낮음(83~97%) — 아래 결과는 이
"해결된" chunk 부분집합 기준이며, 전체 모집단 대표성에 약간의 편향
가능성이 있음(다음 조사 대상 후보).
```

## Offset Alignment Artifact — 원인 규명(고정)

```text
근본 원인 확정: core/chunking_optimizer.py:303-323

  if len(p) > int(chunk_size * 1.5) or lang == "mixed" or has_original_language:
      ...
      if lang == "mixed" or has_original_language:
          prefix = _word_safe_tail(prev, chunk_overlap) if prev else ""
          piece = f"{prefix} {s}".strip() if prefix else s
          chunks.append(...)

긴 문단(>1800자) 또는 혼합언어·원어(히브리어/그리스어) 포함 문단은
문장 단위로 쪼개지고, 각 조각의 앞에 "직전 문장의 word-safe tail"이
synthetic prefix로 붙습니다. 즉 이런 chunk의 텍스트는 body_text의
어느 한 오프셋에서 시작하는 연속 substring이 아니라, 서로 다른 두
위치(직전 문장 끝부분 + 현재 문장 전체)를 이어붙인 합성 텍스트입니다
— 이것이 candidates_with_offsets/chunk_start_offsets의 순차 substring
탐색이 실패하는 정확한 원인입니다(실측 샘플: "정반대\n\n다 2장에서"
처럼 원문에 없던 위치에 개행이 삽입된 형태로 관측).

이 경로는 문서 특성에 따라 발생 빈도가 다름 — 원어(히브리어/그리스어)
인용이 잦고 문단이 긴 한국어 신학 서적/설교집에서 자주 트리거되고,
영문 WBC/Anchor Bible 주석서는 이미 짧고 균일한 문단 구조라 이 경로를
거의 타지 않음. 해결률 편차(한국어 83~97% vs 영문 100%)는 정확히 이
가설과 일치합니다.

⚠ 이것은 이번 조사에서 발견된 chunking_optimizer.py의 특성이며,
  Phase 6-B 범위상 수정하지 않습니다(production 코드 무변경 원칙
  유지). Overlap/원어 보호 로직 자체는 SPRINT29-B-Overlap에서 의도된
  정상 동작 — 측정 방법론의 한계로만 기록합니다.
```

## Confidence Label — 문서별 delta 신뢰도

```text
HIGH   (chunk 해결률 100%) — confirmed/orphaned 수치 그대로 신뢰 가능
  2 Chronicles, Volume 15 (100%)
  2 Kings The Anchor Bible Commentary (100%)
  2 Kings The Power and the Fury (100%)
  2 Kings, Volume 13 (100%)

MEDIUM (chunk 해결률 80~98%) — 위 root cause로 인해 일부 chunk가
       측정에서 누락됨. 누락된 chunk는 대부분 원어/혼합언어 포함
       문단에서 파생 — 그 파편이 semantic boundary 근접 여부까지
       편향시킬 가능성 배제 불가. 절대치보다 경향(trend)으로 해석 권고.
  11. 고린도전서 (96.6%)   7. 사도행전1 (97.3%)   8. 사도행전2 (97.5%)
  12. 고린도후서 (91.4%)   9. 로마서1 (89.4%)     5. 요한복음1 (88.8%)
  3. 마가복음 (87.6%)      6. 요한복음2 (82.8%)

→ AGGREGATE confirmed/orphaned rate(2.5%/70.3%)는 HIGH+MEDIUM 혼합
  집계이므로 "참고용 추정치(reference estimate)"로 취급 — Phase 6-C
  acceptance criteria에서 정밀 임계값의 근거로 쓰려면 HIGH confidence
  4개 문서만의 부분 집계를 별도로 낼 것을 권고.

HIGH-only 부분 집계(4개 문서, chunk 5579개, 완전 해결):
  confirmed rate: 122/5579 = 2.19%
  orphaned rate:  195/309  = 63.11%

  → 전체(HIGH+MEDIUM) 집계치(2.5%/70.3%)와 방향/크기 모두 유사 —
    MEDIUM 문서의 부분 누락이 결론을 왜곡하지 않음을 교차 검증.
    "confirmed rate가 매우 낮고 orphaned rate가 매우 높다"는 핵심
    결론은 confidence label과 무관하게 안정적임.
```

## 결과

```text
document                                   chunks  bounds  confirmed  orphaned
11. 고린도전서                                285      18   1( 0.4%)   17(94.4%)
12. 고린도후서                                212      53   6( 2.8%)   45(84.9%)
2 Chronicles Vol.15                          1109     156  40( 3.6%)  116(74.4%)
2 Kings Anchor Bible Commentary                763      16   9( 1.2%)    7(43.8%)
2 Kings Power and the Fury                     723      91  28( 3.9%)   63(69.2%)
2 Kings, Volume 13                            2984      46  45( 1.5%)    9(19.6%)
3. 마가복음                                    345      89  31( 9.0%)   59(66.3%)
5. 요한복음1                                   310      31   9( 2.9%)   26(83.9%)
6. 요한복음2                                   313      57  18( 5.8%)   44(77.2%)
7. 사도행전1                                   356      14   1( 0.3%)   13(92.9%)
8. 사도행전2                                   437      11   4( 0.9%)    9(81.8%)
9. 로마서1                                     271      65  14( 5.2%)   47(72.3%)

AGGREGATE confirmed rate: 206/8108 = 2.5%
AGGREGATE orphaned rate:  455/647 = 70.3%
tolerance: 50 chars
```

## 해석

```text
1. Confirmed rate(2.5%)가 매우 낮음 — 기존 length-threshold 청커의
   분할 지점 중 semantic boundary와 가까운 것은 40개 중 1개꼴에
   불과. 이는 SPRINT33-A 감사에서 이미 확인된 "chunking_optimizer.py는
   순수 길이 임계값이며 의미/담화 신호가 전혀 없다"는 결론을 정량적
   델타로 재확인한 것 — 새로운 문제 발견이 아니라 기존 진단의 수치화.

2. Orphaned rate(70.3%)가 높음 — semantic boundary로 판정된 후보의
   70%가 기존 chunk 시작 근처에 전혀 없음. 즉 현재 청커는 구조적으로
   의미 있는 경계 대부분을 "놓치고" 있으며, 우연히 근처에서 자르는
   경우(confirmed)가 오히려 예외적임.

3. "2 Kings, Volume 13"은 orphaned rate가 유독 낮음(19.6%) — 그러나
   이는 구조적 정합성이 아니라 규모 편향(scale confound)으로 해석됨:
   이 문서는 chunk 수가 2984개로 압도적으로 많아(다른 문서 대비
   3~10배), 50자 허용 오차 안에 "우연히" chunk 시작이 존재할 확률
   자체가 높아짐. 문서 규모를 통제하지 않은 단순 최근접 거리 지표의
   한계로 기록 — Phase 6-C(Rebuild Acceptance Criteria)에서 밀도
   정규화 방식을 고려할 필요.
```

## Regression

```text
tests/ 전체 506 passed, 0 failed
신규: tests/test_shadow_boundary_delta.py 9 tests
core/chunking_optimizer.py, core/processing.py, TSU, Retrieval — 무접촉
```

## 재현성

`scripts/shadow_boundary_delta.py` 재실행으로 위 표 재현 가능. 원본
비교 대상은 `output/beta_validation_v5/*_chunks.txt`(production
chunking_optimizer.py 실제 산출물).

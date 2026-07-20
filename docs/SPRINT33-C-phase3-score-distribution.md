# SPRINT33-C Phase 3 — Feature Score Distribution Collection

상태: 고정(fixed) — 조사/분석 결과 기록. 코드 변경 범위는
`scripts/`(진단 도구)에 한정, `core/`(feature/threshold)는 무수정.

## 목적

Phase 2에서 등록된 heading(weight=100) + paragraph(weight=30) 2-feature
조합이 실제 Beta corpus에서 만드는 score 분포/boundary 밀도/오탐 양상을
관찰. 신규 feature 추가나 threshold 조정 없이 현재 상태를 있는 그대로
측정.

## 실행 방법

```bash
source ~/envs/dbma311/bin/activate
python scripts/shadow_score_distribution.py
```

`scripts/shadow_boundary_analysis.py`의 `resolve_headings_and_candidates`/
`iter_scored_candidates`를 재사용(Phase 1/2와 동일한 candidate/heading
정의를 그대로 사용 — 별도 로직 분기 없음, 관찰 계층만 추가).

## 1. Score Histogram

```text
score= 30.0  count=15697  (97.5%)
score=130.0  count=  409  ( 2.5%)
```

현재 2-feature 상태에서는 정의상 4개 값(0/30/100/130)만 가능하지만,
실측에서는 30과 130 두 값만 관측됨 — heading 없이 candidate_text가
완전히 빈 경우(0/100 라인)는 Beta corpus에 존재하지 않았음
(split_paragraphs가 빈 문자열을 애초에 candidate로 만들지 않음, §5
확인). Phase 2 Preflight의 예측("threshold=50에서는 여전히 heading
신호만 판정을 좌우")이 실측으로 재확인됨.

## 2. Boundary Density (matched / candidates)

```text
11. 고린도전서                       5 / 1107  =  0.45%
12. 고린도후서                      46 / 783   =  5.87%
2 Chronicles, Volume 15            136 / 1864  =  7.30%
2 Kings Anchor Bible Commentary      1 / 947   =  0.11%
2 Kings Power and the Fury          19 / 1276  =  1.49%
2 Kings, Volume 13                   0 / 3013  =  0.00%
3. 마가복음                         85 / 1525  =  5.57%
5. 요한복음1                         9 / 1114  =  0.81%
6. 요한복음2                        49 / 1166  =  4.20%
7. 사도행전1                         4 / 1061  =  0.38%
8. 사도행전2                         6 / 1268  =  0.47%
9. 로마서1                          49 / 982   =  4.99%
AGGREGATE                          409 / 16106 =  2.54%
```

문서 간 밀도 편차가 큼(0.00%~7.30%) — 이는 heading feature 단독이
전적으로 판정을 좌우하는 현재 구조상 pdf_structure_detector의 문서별
탐지 신뢰도 편차가 그대로 boundary 밀도 편차로 전이됨을 보여줌(기존에
알려진 detector-정밀도 이슈, SPRINT32-F에서 "2 Kings Vol.13" 제외
사례로 이미 별도 트래킹 중).

## 3. False Positive Proxy — Matched Candidate 길이 분포

Ground-truth boundary 라벨이 없으므로 정밀도(precision)를 직접 계산할
수 없음 — 대신 matched candidate의 길이를 3구간으로 나눠 관찰:

```text
tiny(<=10자)         33 / 409  =  8.1%
plausible(11-300자) 219 / 409  = 53.5%
fused-long(>300자)  157 / 409  = 38.4%
```

### 3-1. tiny(<=10자) — 33건, 그 중 21건이 3자 이하

샘플(3. 마가복음, len<=10 matched candidate):
```text
'교'  '서 E 애'  '웹 법'  '례'  '마'  '써써 때 면 듀 뺀'  '權 마'
```
대부분 OCR 잡음(단일/소수 글자 조각)이 우연히 짧은 heading 후보와
word-boundary containment로 매칭된 사례로 판단됨. `_MIN_HEADING_LEN=2`
(heading_provider.py:178) 가드가 통과시키는 극단적으로 짧은 heading
후보 자체의 품질 문제 — 이는 SPRINT32-F에서 이미 "pdf_structure_detector
calibration은 범위 밖"으로 분리된 이슈와 동일 계열.

### 3-2. fused-long(>300자) — 157건, 38.4%

샘플(12. 고린도후서):
```text
"고후5:1-5 하늘에서기다리는집 1만일 우리의 지상의 집, 우리의 현재
'장막'이 무너지면, 하나님이 지으신 건물, 즉사람의 손으로지은 것이
아닌..." (len=368)
```
이 패턴은 새로운 결함이 아니라 SPRINT32-D/F에서 이미 확인된
`collapse_soft_linebreaks`의 heading-흡수 현상이 문단 단위에서 나타난
형태: 짧은 heading 줄이 바로 다음 문단과 사이에 빈 줄이 없어
`split_paragraphs`가 heading과 그 뒤 첫 문단 전체를 하나의 candidate로
묶음. Word-boundary containment는 정확히 이 경우를 포착하도록 설계된
것(SPRINT32-F)이므로 "매칭 실패"는 아니지만, **candidate 자체가 이미
"heading + 후속 문단"이 뭉쳐 있어, 이 candidate를 그대로 경계로 쓰면
heading이 항상 다음 문단과 한 청크로 묶이고 다시는 분리될 수 없다**는
구조적 함의가 있음 — SPRINT33-D(Hierarchical Chunk Builder) 설계 시
반드시 고려해야 할 사항으로 기록.

### 3-3. plausible(11-300자) — 219건, 53.5%

샘플:
```text
'마가복음 2:1-12 중풍병자를고치시다'
'마가복음 2:13-17 레위를부르시다'
'마가복음3:1-6 손미른사람을치유하시다'
```
성경 장·절 참조 + 소제목 형태의 정상적인 heading candidate로 판단됨 —
과반(53.5%)이 이 구간에 속해, heading feature 자체의 기본 신뢰도는
양호한 것으로 평가.

## 결론 (Phase 4 투입 전 판단 근거)

```text
1. Score 분포는 예측대로 2-value(30/130) — threshold 재조정 근거 없음.
2. Boundary 밀도는 문서별 0~7.3%로 편차가 크며, 원인은 새 feature
   구조가 아니라 기존 detector 신뢰도 편차 — SPRINT33-C 범위 밖 유지.
3. Matched 후보 중 8.1%(tiny)는 OCR 잡음성 오탐 후보 — Phase 4 후보
   "Tiny Fragment Penalty"의 근거 데이터로 활용 가능.
4. Matched 후보 중 38.4%(fused-long)는 heading이 후속 문단과 뭉쳐진
   구조적 특성 — 오탐이 아니라 "candidate 세분화 필요성"의 증거.
   SPRINT33-D에서 candidate를 문단 내부 문장 단위로 한 단계 더
   쪼개는 설계가 필요함을 뒷받침.
```

## 재현성

`scripts/shadow_score_distribution.py`는 `scripts/shadow_boundary_
analysis.py`의 함수를 재사용하는 진단 전용 스크립트(core/ 미import,
production pipeline과 무관). Beta corpus/`output/beta_validation_v5`가
존재하는 한 재실행하여 이 표와 비교 가능.

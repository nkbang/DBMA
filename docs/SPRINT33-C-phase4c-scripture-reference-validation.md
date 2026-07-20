# SPRINT33-C Phase 4-C — ScriptureReferenceBoundaryFeature + Validation

상태: 고정(fixed). 구현 + 품질 검증 결과를 함께 기록.

## 구현 요약

```text
core/config.py
  SCRIPTURE_REFERENCE_HEAD_WINDOW = 50
  SCRIPTURE_REFERENCE_WEIGHT = 60.0

core/semantic_boundary_detector.py
  ScriptureReferenceBoundaryFeature — core.retrieval.QueryParser 재사용
  (core.tsu_builder._reference_parser와 동일 클래스). candidate 앞 50자
  이내에서 발견된 성구 참조만 인정(Overlap Preflight에서 확인된
  "우발적 인용" 오탐 방지 — 전체 어디서든 인정하면 78.5%가 비-경계성
  인용으로 추정됨).
  default registry weight=60.0으로 등록.
```

## Overlap Preflight 요약(구현 전 조사)

```text
전체 16106 candidate 중 성구 참조 포함:            2162 (13.4%)
heading-matched(409) 중 성구 참조도 있는 것:         162 (39.6%)
성구 참조 candidate 중 heading 미매칭:              2000 (92.5%)
  그 중 참조가 candidate 앞부분(첫 15자)에 위치:      213 (10.7%)
  그 중 길고(>400자) 참조 다수(>=3개) — TOC 유출 의심: 216 (10.8%)
```

## Shadow 재실행 결과 (구현 후)

```text
매칭 건수: 409 → 653 (+244)
매칭 문서: 11/12 → 12/12  — "2 Kings, Volume 13" 최초 매칭(47건)

문서별 boundary density(교정 전 → 후):
  11. 고린도전서       0.45% → 1.63%
  12. 고린도후서        5.87% → 6.77%
  2 Chronicles Vol.15   7.30% → 8.37%
  2 Kings Anchor Bible   0.11% → 1.69%
  2 Kings Power/Fury    1.49% → 7.13%
  2 Kings, Volume 13    0.00% → 1.56%
  3. 마가복음           5.57% → 5.97%
  5. 요한복음1          0.81% → 2.87%
  6. 요한복음2          4.20% → 5.06%
  7. 사도행전1          0.38% → 1.32%
  8. 사도행전2          0.47% → 0.87%
  9. 로마서1            4.99% → 6.62%
  AGGREGATE             2.54% → 4.05%
```

## Validation — 244건 신규 boundary 품질 분류

방법: 신규 244건(전체) 중 무작위 30건 + "2 Kings, Volume 13"의 47건
전수를 원문 대조로 수동 판독.

### 전체 244건 무작위 표본(30건)

```text
A. true boundary    ~40% (12/30) — 장절+소제목 형태의 진짜 경계
B. ambiguous          ~7% ( 2/30)
C. false positive    ~53% (16/30) — 우발적 인용/TOC 유출/running header 반복
```

### "2 Kings, Volume 13" 47건 전수

```text
distinct reference: 31개 (47건 중 최소 16건, 34%가 순수 중복)
  6회 반복: 2 Kings 1장(장 단위만)
  4회 반복: 2 Kings 12:1-22
  3회 반복: 2 Kings 16:1-20 / 20:1-21
  2회 반복: 2 Kings 2장 / 8:1-29 / 11:1-20 / 14:1-29

20건 상세 판독:
  A. true boundary    20% (4/20) — 대부분 "Excursus: ..." 특별 논고 제목
  B. ambiguous          5% (1/20)
  C. false positive    75% (15/20) — running header 반복(9), TOC 유출(2),
                                     텍스트비평 장치(4)
```

### 원인 분석 — 장르(genre)에 따른 정밀도 편차

```text
Word Biblical Commentary(WBC) 계열 학술 주석서는 매 페이지 상단에
"책명 장:절 [페이지번호]"가 running header로 반복 인쇄되고, 본문
설명이 여러 페이지에 걸쳐 계속 이어지는 조판 방식을 사용함. candidate
앞 50자 이내에 이 반복 header가 매번 걸려 "새 경계"로 오판정됨.

한국어 성경공부/설교집 스타일 문서(고린도전서, 요한복음1 등)는 이
문제가 훨씬 적음(장절+소제목이 실제로 새 섹션 시작에서만 등장) —
문서 전체 표본에서 40%였던 정밀도가 WBC 단일 문서에서는 20%로 하락.
```

## 결론 (Phase 5 입력 데이터로 활용)

```text
1. Feature 자체는 유효 — heading detector가 완전히 실패한 문서에서도
   구조 신호를 확보(heading과 독립적인 탐지 경로).
2. 정밀도는 문서 장르에 따라 40%(일반) ~ 20%(WBC 학술 주석) 편차.
3. 주요 오탐 원인 3가지: (a) 본문 중 우발적 인용, (b) TOC/시리즈
   카탈로그 유출, (c) 페이지 running header 반복 — 특히 (c)는 기존
   4개 feature에는 없던 새로운 오탐 유형.
4. Phase 5 Threshold/Weight Calibration에서 다룰 후보:
   - scripture_reference weight 하향 조정 검토
   - 동일 참조 반복 시 첫 등장만 인정하는 중복 제거 규칙(신규 feature
     또는 후처리 단계 필요 — 이번 조사에서 "PageHeaderArtifact" 후보로
     별도 등록)
```

## 재현성

`scripts/shadow_boundary_analysis.py` / `scripts/shadow_score_distribution.py`
재실행으로 매칭 건수/밀도 재현 가능. Validation 판독은 수동 검토이므로
원문 재확인 필요 시 `output/beta_validation_v5/*.md` 참조.

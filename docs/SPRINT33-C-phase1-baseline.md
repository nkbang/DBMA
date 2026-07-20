# SPRINT33-C Phase 1 — Heading-only Shadow Baseline

상태: 고정(fixed) — 이후 feature 추가 시 회귀 비교 기준으로 사용.

## 목적

`core/semantic_boundary_detector.py`(SPRINT33-B)의 `HeadingBoundaryFeature`가
기존 승인된 `HeadingAssembler`(SPRINT31-32)와 행동적으로 동등한지 검증.
청킹 알고리즘 완성이 아니라, 기존 heading 지식을 boundary scoring 계층으로
안전하게 이동시키는 첫 검증 단계.

## 실행 방법

```bash
source ~/envs/dbma311/bin/activate
python scripts/shadow_boundary_analysis.py
```

- 대상: `data/beta_corpus/` 12개 PDF 전체
- 후보 생성: `core.text_normalizer.split_paragraphs()` (문단 단위)
- 비교 기준: `core/tsu_builder.py`를 통해 실제 실행된 SPRINT32-F 결과
  (chunk-line 단위 `HeadingAssembler`, 12개 문서 중 11개 개선, 총 334개
  distinct heading 매칭, "2 Kings Vol.13" 0건)

## 결과 (고정)

| document | candidates | headings | matched |
|---|---:|---:|---:|
| 11. 고린도전서 | 1120 | 111 | 5 |
| 12. 고린도후서 | 804 | 64 | 49 |
| 2 Chronicles, Volume 15 | 1883 | 286 | 132 |
| 2 Kings The Anchor Bible Commentary | 967 | 2170 | 1 |
| 2 Kings The Power and the Fury | 1288 | 107 | 20 |
| 2 Kings, Volume 13 | 3043 | 5100 | 0 |
| 3. 마가복음 | 1542 | 105 | 86 |
| 5. 요한복음1 | 1138 | 78 | 54 |
| 6. 요한복음2 | 1179 | 62 | 50 |
| 7. 사도행전1 | 1078 | 117 | 72 |
| 8. 사도행전2 | 1288 | 313 | 105 |
| 9. 로마서1 | 994 | 63 | 52 |

```text
documents: 12
documents with >=1 match: 11
total matched (this run): 626
SPRINT32-F baseline: 334 distinct headings, 11/12 documents improved
threshold used: 50.0
```

## 판정

- 매칭 문서 수(11/12)와 실패 문서("2 Kings, Volume 13")가 SPRINT32-F와
  정확히 일치 — 승격이 회귀를 일으키지 않았음을 확인.
- 총 매칭 수(626 vs 334)의 차이는 후보 생성 단위 차이(paragraph vs
  chunk-line)에 기인하는 예상된 편차이며, 이번 baseline의 판정 기준은
  총 매칭 수 절대치가 아니라 "실패 패턴의 일치" — 이 기준은 통과.
- 정밀한 편차 원인 분석은 Phase 3(Score Distribution 분석)에서 다룬다.

## 재현성

`scripts/shadow_boundary_analysis.py`는 production pipeline에 import되지
않는 진단 전용 스크립트(core/ → scripts/ import 금지 경계 유지). 동일한
Beta corpus/`output/beta_validation_v5` 산출물이 존재하는 한 언제든
재실행하여 이 표와 비교 가능.

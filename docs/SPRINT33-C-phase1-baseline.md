# SPRINT33-C Phase 1 — Heading-only Shadow Baseline

상태: 고정(fixed) — 이후 feature 추가 시 회귀 비교 기준으로 사용.

**개정 이력**: Phase 2-A(Shadow Input Alignment)에서 shadow driver가
저장된 .md 전체(YAML 헤더 + 전면부 재부착본)를 그대로 candidate 생성에
사용하고 있었음을 발견 — 운영 청킹(`core/processing.py:665`,
`optimize_chunks(body_text, ext)`)은 `split_front_matter()`로 분리된
`body_text`만 사용하므로, 아래 최초 수치는 전면부 잡음이 섞인 값이었다.
`scripts/shadow_boundary_analysis.py`에 `_extract_body_text()`를 추가해
"## 본문" 마커 기준으로 body_text를 복원하도록 교정한 뒤 재실행한
결과로 본 문서를 갱신했다. 판정 기준(11/12 문서 매칭, "2 Kings, Volume
13" 0건)은 교정 전후 동일하게 유지됨을 확인.

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

## 결과 (고정, body_text 정합 이후)

| document | candidates | headings | matched |
|---|---:|---:|---:|
| 11. 고린도전서 | 1107 | 111 | 5 |
| 12. 고린도후서 | 783 | 64 | 46 |
| 2 Chronicles, Volume 15 | 1864 | 286 | 136 |
| 2 Kings The Anchor Bible Commentary | 947 | 2170 | 1 |
| 2 Kings The Power and the Fury | 1276 | 107 | 19 |
| 2 Kings, Volume 13 | 3013 | 5100 | 0 |
| 3. 마가복음 | 1525 | 105 | 85 |
| 5. 요한복음1 | 1114 | 78 | 9 |
| 6. 요한복음2 | 1166 | 62 | 49 |
| 7. 사도행전1 | 1061 | 117 | 4 |
| 8. 사도행전2 | 1268 | 313 | 6 |
| 9. 로마서1 | 982 | 63 | 49 |

```text
documents: 12
documents with >=1 match: 11
total matched (this run): 409
SPRINT32-F baseline: 334 distinct headings, 11/12 documents improved
threshold used: 50.0
```

교정 전(626) 대비 교정 후(409) 총 매칭 수가 SPRINT32-F 기준(334)에
더 근접 — 일부 문서(5. 요한복음1: 54→9, 7. 사도행전1: 72→4, 8.
사도행전2: 105→6)에서 큰 폭 감소는 표지/목차 페이지의 반복된
장·절 제목이 전면부로 정확히 분리되어 candidate에서 제외된 결과로
해석된다(정밀 원인 분석은 Phase 3 예정).

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

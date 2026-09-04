---
title: "ADR-007 Amendment A: Genre-aware Acceptance Criteria, Three-axis D-5 Metrics, Three-level Chunk Decision Hierarchy"
category: architecture
sprint: SPRINT33-D
amends: docs/architecture/ADR-007-Semantic-Boundary-Detector-D5-Rebuild-Gate.md
based_on:
  - docs/SPRINT33-D-preflight-issues.md
  - docs/SPRINT33-D-phase2a-long-paragraph-preflight.md
  - docs/SPRINT33-D-phase2b-d5-metric-reclassification.md
  - docs/SPRINT33-D-phase2c-hierarchical-decision-policy.md
created: 2026-07-20
status: Architecture Decision (구현 전, 승인 대기 — Rebuild Gate 실행은 별도 승인 필요)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-007 Amendment A

| | |
|---|---|
| Amends | ADR-007 (Semantic Boundary Detector — D-5 Chunk Boundary Rebuild Gate) |
| Status | Proposed |
| Date | 2026-07-20 |
| Deciders | HQ (Task Order 승인) / CUE (조사·설계) |

이 문서는 새로운 architecture decision이 아니라, SPRINT33-D Phase
1~2-C에서 확보한 실측 근거를 바탕으로 ADR-007의 §1/§2(Minimum
Semantic Improvement Threshold, Orphaned Boundary 허용 범위)와
Decision 섹션의 계층 분리 원칙을 정교화한다. ADR-007이 세운 원칙
자체(Detector=판단 계층, Chunker=production 계층 분리; D-5는 rebuild
"실행 승인"이 아니라 "검토 개시 자격")는 변경하지 않는다.

---

## Amendment A — Genre-aware Acceptance Criteria

### 변경 전 (ADR-007 원문)

```text
§4(Document Genre별 Gate 적용)에서 "genre 자동 분류 방식은 별도
Preflight로 조사"로 이연되어 있었을 뿐, §1/§2의 실제 acceptance
criteria는 corpus 전체 단일 threshold를 전제로 서술되어 있었다.
```

### 변경 후

```text
SPRINT33-D Phase 2-B 실측(docs/SPRINT33-D-phase2b-d5-metric-
reclassification.md §3)으로 corpus가 뚜렷이 구분되는 2개 profile로
나뉨을 확인했다:

  Profile A — Low Back-matter Density (Beta corpus 중 한국어 8개 문서)
    개별 candidate 중 1800자 초과 0건. orphaned recovery 97.7~100%.

  Profile B — High Back-matter Density (Beta corpus 중 영문 WBC/주석서
    4개 문서) 개별 candidate 중 1800자 초과 다수(52~122개/문서,
    100%가 문장 분할 불가능한 색인/카탈로그/참고문헌 콘텐츠 —
    Phase 2-A §2). orphaned recovery 85.7~100%.

acceptance criteria는 corpus 전체 단일값이 아니라 profile별로
분리 평가한다. Profile 분류 방식은 이번 Amendment에서 "개별
candidate 중 1800자(=chunk_size*1.5) 초과 비율 > 0"이라는 측정
가능한 기준으로 잠정 정의한다(자동 분류 알고리즘의 정교화는 후속
과제로 유지).
```

---

## Amendment B — Three-axis D-5 Metrics

### 변경 전 (ADR-007 원문)

```text
§2 Orphaned Boundary 허용 범위는 "heading이 포함된 조합"과 "heading
없이 낮은 weight 조합만으로 판정된 boundary"의 2단계 구분만 제안했고,
"chunk-size constraint"는 별도 축으로 명시되지 않았다.
```

### 변경 후

```text
SPRINT33-D Phase 2-B(§2/§4)가 "chunk 크기 초과"에 두 개의 서로
독립적인 원인이 있음을 확인함에 따라, D-5 metric을 다음 3개 독립
축으로 재정의한다:

  축 1. Orphaned Boundary Recovery Rate
        semantic boundary 회수율(Phase 1 방법론). Profile 무관 공통
        기준 적용 가능(이미 두 profile 모두 85.7% 이상 확보).

  축 2. Semantic Flush Ratio
        전체 flush 중 semantic 신호에 의해 발생한 비율. 낮을수록
        chunk 분할이 여전히 길이 기반(safety cap)에 의존하고 있음을
        뜻함(원인 B, 전 문서 공통 — 실측 2.1~43.6%).

  축 3. Unsplittable Outlier Ratio
        candidate 자체가 이미 safety cap을 초과하며 문장 분할도
        불가능한 비율(원인 A, Profile B 전용 — Profile A는 항상 0).

3개 축을 단일 pass/fail로 합치지 않고 개별 보고한다 — 합치면 축 3
(소수 문서에만 존재하는 극단치)이 축 1/2의 실제 개선을 가릴 위험이
있다(Phase 2-B §4).
```

---

## Amendment C — Three-level Chunk Decision Hierarchy

### 변경 전 (ADR-007 원문)

```text
Decision 섹션은 "Detector=판단 계층, Chunker=production 계층"이라는
2자 분리만 규정했고, semantic boundary 결정 내부의 계층 구조는
다루지 않았다(SPRINT33-D Phase 1 구현 시점에는 semantic/safety-cap
2단계만 존재).
```

### 변경 후

```text
SPRINT33-D Phase 2-C(docs/SPRINT33-D-phase2c-hierarchical-decision-
policy.md)에서 설계한 3단계 우선순위를 Hierarchical Chunk Builder의
표준 decision hierarchy로 채택한다:

  Level 1  Semantic Split
              ↓
  Level 2  Safety-cap Split
              ↓
  Level 3  Hard Fallback Split

역할 분리:
  - Semantic Split: 의미 경계 최우선(core.semantic_boundary_detector
    그대로 재사용).
  - Safety-cap Split: 정상적인 크기 제어 — semantic 신호가 부족한
    구간에서의 정상적인 길이 기반 대체(buf를 구성하는 개별
    candidate는 모두 정상 크기).
  - Hard Fallback Split: 비정상 후보(candidate 자체가 이미 safety
    cap을 초과) 복구 — 문장 경계도 없는 콘텐츠에 대한 최후 수단
    (word-safe 강제 절단만 수행, semantic 정보 미참조).

이로써 기존의 단순 "semantic vs size" 이분 구조가:

  semantic intelligence + controlled normalization + exception recovery

3중 구조로 발전한다. Level 3(Hard Fallback)는 이번 Amendment
시점에서도 여전히 **설계만 완료, 미구현** 상태이며, 구현 시에도
core/chunking_optimizer.py의 private 함수(_slice_preserving_words 등)를
직접 import하지 않고 독립 구현하는 것을 원칙으로 한다(Phase 2-A §1,
새로운 의존 방향 회피).
```

---

## Consequences

### 이번 Amendment로 확정되는 것
- Acceptance criteria의 profile 분리 원칙(corpus 전체 단일값 폐기).
- D-5 metric이 2축이 아니라 3축(recovery/semantic flush ratio/
  unsplittable outlier ratio)임을 공식화.
- Chunk decision hierarchy가 2단계가 아니라 3단계(semantic/safety-cap/
  hard fallback)임을 공식화.

### 이번 Amendment로 확정되지 않는 것(계속 이연)
- Profile 분류의 정식 자동화 알고리즘(현재는 "1800자 초과 candidate
  존재 여부"라는 잠정 기준만 채택).
- Level 3(Hard Fallback)의 실제 구현.
- §1(minimum improvement threshold)의 구체 수치 — 여전히 미확정.
- Profile별 acceptance criteria의 최종 확정값(Phase 2-B §5의 수정
  초안은 여전히 "확정 아님" 상태 유지).

### 리스크
- Profile 분류 기준(1800자 초과 candidate 존재 여부)이 2개 profile
  경계에 걸친 문서(예: 장문단이 소수만 존재하는 문서)를 잘못
  분류할 가능성 — 향후 corpus 확장 시 재검증 필요.

---

## Frozen Artifact Set (SPRINT33-D Phase 1~2 전체, 이번 커밋 기준)

```text
docs/SPRINT33-D-preflight-issues.md
docs/SPRINT33-D-phase2a-long-paragraph-preflight.md
docs/SPRINT33-D-phase2b-d5-metric-reclassification.md
docs/SPRINT33-D-phase2c-hierarchical-decision-policy.md
docs/architecture/ADR-007-Amendment-A.md                 (본 문서)

core/hierarchical_chunk_builder.py       (dormant, Level 1+2만 구현,
                                           Level 3 설계만)
scripts/shadow_hierarchical_chunks.py
tests/test_hierarchical_chunk_builder.py
```

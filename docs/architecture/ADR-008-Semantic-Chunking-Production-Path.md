---
title: "ADR-008: Semantic-Aware Chunking — Path to Production Promotion"
category: architecture
sprint: SPRINT33-D (연속)
based_on:
  - docs/architecture/ADR-007-Semantic-Boundary-Detector-D5-Rebuild-Gate.md
  - docs/architecture/ADR-007-Amendment-A.md
  - docs/SPRINT33-D-phase3a-d5-metrics-formal-evaluation.md
created: 2026-07-20
status: Architecture Decision (구현 전, 승인 대기 — 실제 production 전환은 별도 승인 필요)
scope_modified: docs/architecture/ only (코드 미수정)
---

# ADR-008: Semantic-Aware Chunking — Path to Production Promotion

| | |
|---|---|
| Status | Proposed |
| Date | 2026-07-20 |
| Deciders | HQ (Task Order 승인) / CUE (조사·설계) |
| Supersedes | — |
| Superseded by | — |
| Amends | 없음 (ADR-007/Amendment A의 원칙을 계승하는 후속 제안) |

---

## Context

사용자가 "도입된 청킹 기법 검토 + 현업 고급 청킹 알고리즘 추천"을
요청했다. 검토 결과 다음이 확인됐다:

1. **Production**(`core/chunking_optimizer.py`): 단락 우선 버퍼링 +
   언어 인지형(원어/혼합 언어) 문장 분할 강등 + `RecursiveCharacterTextSplitter`
   최종 폴백, 경계 보존형 오버랩. 순수 길이/구두점 기반이며 의미
   신호를 참조하지 않는다.
2. **Dormant 프로토타입**(`core/hierarchical_chunk_builder.py`,
   SPRINT33-C/D): `core.semantic_boundary_detector`의 5-feature
   Boundary Score를 Level 1(Semantic Split) 신호로 사용하고, Level 2
   (Safety-cap Split)로 정상적 크기 제어, Level 3(Hard Fallback,
   설계만·미구현)로 예외를 복구하는 3단계 구조(ADR-007 Amendment A).
   Phase 3-A 정식 측정(2026-07-20 고정)까지 완료됨:
   - Axis 1 (Orphaned Recovery): Profile A/B 모두 98.5~99.0% — genre
     무관 우수.
   - Axis 2 (Semantic Flush Ratio): Profile A 29.1% vs Profile B
     16.4% — 학술 주석서(heading 밀도 낮음)는 여전히 안전망(safety-cap)
     의존도가 높음.
   - Axis 3 (Unsplittable Outlier): Profile A 0.0%, Profile B 5.5%
     (최악 문서 18.6%).
   - regression: 기존 tests/ 520 passed 유지, production 무접촉.
3. **부수 발견(Phase 3-A)**: production `chunking_optimizer.py:305`의
   `split_sentences_mixed(p)` 호출은 `split_paragraphs()`가 만든
   입력(내부 개행 없음, `collapse_soft_linebreaks`로 이미 병합됨)에
   의존하는 줄바꿈 기준 분할기라, **일반 산문 문단에 대해서는 실질적으로
   거의 트리거되지 않을 가능성**이 확인됐다. 이는 SPRINT33-D 범위 밖의
   기존 production 동작에 대한 관찰이며 수정하지 않고 기록만 되어 있다.

ADR-007 §1(Minimum Semantic Improvement Threshold)은 "detector만
존재하고 semantic-aware 청커가 없어 측정 대상이 없다"는 이유로 수치를
이연했다. 이제 Hierarchical Chunk Builder가 존재하고 Phase 3-A로
3축 실측이 완료됐으므로, §1을 재산정할 수 있는 최초 시점이 도래했다.

---

## Decision

### 이 ADR이 결정하는 것 — 없음 (제안만)

이 ADR은 **새로운 architecture decision을 확정하지 않는다.** 사용자가
"승인"한 범위는 "ADR 문서 작성"이며, 실제 §1 수치 확정이나 production
전환은 이 문서의 범위 밖이다. 아래는 HQ 검토를 위한 **제안(proposal)**
목록이다.

### 제안 1 — §1 Threshold 재산정 착수 (ADR-007 §1 이연 사항의 후속)

Phase 3-A 실측치(Axis 1/2/3)를 근거로, ADR-007이 미룬 "Minimum
Semantic Improvement Threshold" 수치를 지금 확정할 수 있는 데이터가
갖춰졌다. 제안: Profile A/B 별로 별도 threshold를 설정(Amendment A의
genre-aware 원칙 계승) — 단, 구체 수치는 이 ADR이 아니라 별도 Phase
(가칭 SPRINT33-D Phase 4)에서 HQ 승인을 받아 확정한다.

### 제안 2 — Level 3 (Hard Fallback) 구현

Amendment A가 "설계만 완료, 미구현"으로 남긴 Level 3를 구현해야
Hierarchical Chunk Builder가 production 대체 후보로서 완결된다.
Profile B의 Unsplittable Outlier(축 3, 최악 18.6%) 케이스가 이 계층의
실효성을 검증할 시험 대상이 된다. 원칙(Amendment A 준수): production의
private 함수(`_slice_preserving_words` 등)를 직접 import하지 않고
독립 구현.

### 제안 3 — 임베딩 기반 Semantic Chunking을 6번째 Feature로 검토

현재 5-feature Boundary Score(heading/paragraph/tiny fragment/sentence
completion/scripture reference)는 모두 **구조·규칙 기반**이다. 업계
표준인 "인접 문장 임베딩 코사인 유사도 급락 지점" 방식(LlamaIndex
SemanticSplitterNodeParser 계열)을 6번째 feature로 추가하면, 특히
Profile B(heading 밀도 낮은 학술 주석서, Axis 2가 낮은 이유)에서
추가적인 semantic flush 기회를 얻을 가능성이 있다. `core/embedder.py`
(bge-m3:latest)가 이미 존재하므로 신규 임베딩 인프라 도입 없이 재사용
가능. 단, 문장 단위 임베딩 호출 비용이 추가되므로 배치/캐싱 전략은
별도 조사 필요.

### 제안 4 — 부수 발견(split_sentences_mixed 줄바꿈 의존성) 별도 티켓화

Phase 3-A에서 발견된 production 버그 후보(§Context 3번)는 이 ADR의
semantic chunking 논의와 독립적인 문제다 — 현재도 문장 단위 분할이
드물게만 작동한다면, 원어/혼합 언어 보호 로직의 실효성 자체가
과대평가됐을 수 있다. **별도 Preflight(코드 미수정, 조사만)로 우선
분리 처리를 제안** — semantic chunking 결정과 얽히면 두 문제 중 어느
쪽 개선 효과인지 구분할 수 없게 된다.

### 명시적으로 제안하지 않는 것

- **RAPTOR류 parent-child 계층 검색**이나 **Late Chunking**, **Proposition-
  based 청킹**은 이번 ADR에서 다루지 않는다. 이들은 검색(retrieval)
  단계의 변경이 필요해 `core/retrieval.py::RetrievalEngine`(ADR-001
  Authority)에 영향을 주므로, 청킹 layer만의 결정으로 진행할 수 없고
  별도 ADR + C1/HQ 분석이 선행되어야 한다.
- Hierarchical Chunk Builder의 즉시 production 전환. §1 threshold도
  미확정이고 Level 3도 미구현인 상태에서 전환하는 것은 ADR-007의
  "D-5 게이트 통과 = 실행 승인 아님" 원칙에 정면으로 위배된다.

---

## Consequences

### 이 ADR로 확정되는 것
- 없음 — 제안 목록의 존재와 우선순위 정리만 문서화.

### 이 ADR로 확정되지 않는 것 (전부 후속 HQ 승인 대상)
- §1 threshold 구체 수치.
- Level 3 구현 착수 여부/일정.
- 임베딩 기반 6번째 feature 도입 여부.
- split_sentences_mixed 버그 후보의 우선순위/일정.

### 리스크
- 제안 3(임베딩 feature)은 추론 비용이 추가되는 유일한 항목 — 승인
  전 비용/효과 추정치가 없어 이 ADR만으로는 판단 불가.
- 제안 4를 분리하지 않고 진행하면, 향후 semantic chunking 도입 효과
  측정 시 원어 보호 로직 개선 효과와 혼재되어 원인 규명이 어려워짐.

---

## Next Steps (HQ 승인 대기)

1. 제안 4(버그 후보 Preflight)를 가장 먼저 처리 — 다른 제안과 독립적이고
   리스크가 가장 낮음.
2. 제안 1(§1 threshold 재산정)을 SPRINT33-D Phase 4로 착수할지 HQ 결정.
3. 제안 2(Level 3 구현)와 제안 3(임베딩 feature)은 제안 1 확정 후
   순서를 재검토.
4. RAPTOR/Late Chunking 등은 이번 범위 밖 — 별도 C1 분석 요청 여부만
   기록하고 착수하지 않음.

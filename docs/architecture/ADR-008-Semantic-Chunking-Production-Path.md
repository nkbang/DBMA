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

**✅ 착수 및 부분 확정 (2026-07-21)**:

| 지표 | Profile A | Profile B | 확정 임계값 |
|---|---|---|---|
| Axis 1 (Orphaned Recovery) | 98.5% | 99.0% | **≥95%** (공통, 회귀 감지용 여유폭) |
| Axis 3 (Unsplittable Outlier) | 0.0% | 5.5%(최악 18.6%) | **A: 0%, B: ≤10%** |
| Axis 2 (Semantic Flush Ratio) | 29.1% | 16.4% | **Profile B는 현재 실측치로 프로덕션 전환 불충분 — HQ 판단** |

Profile B(heading 밀도 낮은 학술 주석서 — 사용자가 주석 문서 청킹
품질을 직접 우려한 바로 그 유형)의 Axis 2 16.4%는 "여전히 절반 이상을
길이 기반 안전망에 의존"한다는 뜻으로, HQ는 이 수준을 **프로덕션
전환에 불충분**하다고 판단했다. 따라서:

- **제안 3(임베딩 기반 6번째 feature)이 제안 2(Level 3)보다 먼저,
  Profile B의 Axis 2를 끌어올리는 것을 목표로 우선 착수한다.**
- Profile A(29.1%)에 대한 임계값 충족 여부는 별도로 판단하지 않음 —
  이번 결정은 Profile B(주석 문서)로 범위를 한정해 물었다.
- Axis 1·Axis 3 임계값은 두 프로필 모두 현재 실측치가 이미 상회하므로
  회귀 감지용 하한선으로 확정.

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

1. ~~제안 4(버그 후보 Preflight)~~ 완료 (2026-07-21) —
   `split_sentences_mixed()`가 개행 없는 입력(프로덕션 실제 입력 형태)
   에서 문장을 전혀 못 나누던 결함 확인·수정.
   (`core/text_normalizer.py`, `tests/test_split_sentences_mixed_punctuation.py`)
2. ~~제안 1(§1 threshold 재산정)~~ 부분 확정 (2026-07-21) — Axis 1/3
   임계값 확정, Axis 2는 Profile B 불충분 판정(위 참고).
3. ~~제안 3(임베딩 기반 6번째 feature)~~ 구현 및 실측 검증 완료
   (2026-07-21) — `EmbeddingSimilarityBoundaryFeature`
   (`core/semantic_boundary_detector.py`),
   `BoundaryContext.previous_candidate_text` 필드,
   `hierarchical_chunk_builder.build_chunks()` 연결(`core/embedder.py`
   재사용, 신규 임베딩 인프라 없음). 여전히 dormant — 프로덕션 미연결.

   **버그 2건 발견·수정 (재측정 과정에서)**:
   - `core.embedder.embed()`는 "폴백"으로 문서화돼 있었지만 실제로는
     legacy MiniLM(768차원)만 로드해 `EMBEDDING_DIMENSION`(1024, bge-m3
     기준)과 항상 불일치, 매 호출이 `DimensionMismatchError`로 실패하고
     있었다. feature의 안전 폴백(`except Exception: return 0.0`)이 이를
     조용히 삼켜 "유사도가 높아 발화 안 함"처럼 보였다 — 실제로는 매번
     실패해 완전히 죽어있던 것. 실제 프로덕션 진입점인
     `core.embedder.get_embedder()`(Ollama bge-m3 우선)로 교체.
   - threshold=0.5(설계 초안값)는 버그 수정 후 실측한 진짜 유사도
     분포(Profile B 4개 문서, n=7055 인접 후보쌍)의 중앙값(0.5615)보다
     낮아, 오히려 절반 가까운 후보를 경계로 판정하는 반대 방향 문제가
     있었다. p15 근처인 **0.41로 재보정**(`core/config.py`).

   **최종 Axis 재측정 (Profile B, 실제 bge-m3 + 재보정 threshold)**:

   | 지표 | Phase 3-A (이전) | 이번 (임베딩 feature 도입 후) |
   |---|---|---|
   | Axis 1 (Recovery) | 99.0% | 99.0% (변화 없음) |
   | **Axis 2 (Semantic Flush)** | **16.4%** | **33.7%** (+17.3%p, 약 2배) |
   | Axis 3 (Outlier) | 5.5% | 0.2% (제안 4 수정 효과, 별건) |

   Axis 2가 실질적으로 개선됐다 — §1이 "불충분"으로 판정했던 Profile B
   상태가 유의미하게 나아졌다. 다만 이 자체가 프로덕션 전환 승인은
   아니다(§1 최종 재판정·제안 2 Level 3 구현·D-5 게이트 재통과는 별도
   HQ 승인 필요, ADR-007 원칙 유지).
4. RAPTOR/Late Chunking 등은 이번 범위 밖 — 별도 C1 분석 요청 여부만
   기록하고 착수하지 않음.
5. ~~제안 2(Level 3 Hard Fallback)~~ **구현 및 실측 검증 완료 (2026-07-22,
   commit `08d542a`)** — `core/hierarchical_chunk_builder.py`에
   `_slice_preserving_words()` 독립 재구현(Amendment A 원칙 준수, 프로덕션
   private 함수 미import). 회귀 tests/ 602 passed(신규 3건 포함).

   **검증(가짜 임베딩 스텁으로 즉시 재실행 — 길이 상한 보장은 semantic
   신호와 무관하므로 실제 임베딩 불필요)**:
   ```
   safety_cap = 1800
   2 Chronicles Vol.15                 chunks=1751  max_len=1800  over_cap=0
   2 Kings Anchor Bible Commentary      chunks=1102  max_len=1800  over_cap=0
   2 Kings Power and the Fury           chunks=1204  max_len=1800  over_cap=0
   2 Kings Vol.13(최악 사례 문서)        chunks=2119  max_len=1800  over_cap=0
   TOTAL: chunks=6176  over_cap=0 (0.0%)
   ```
   Profile B 4개 문서(이전 unsplittable outlier 최악 18.6%였던 "2 Kings,
   Vol.13" 포함) 전체에서 청크 길이가 예외 없이 safety_cap(1800자) 이하로
   제한됨을 확인 — Level 3가 설계 의도대로 작동.

   **참고(측정 도구 제약)**: `scripts/shadow_d5_metrics_embedding_rerun.py`의
   `Axis 3` 지표는 `build_chunks()` 출력이 아니라 candidate 자체 속성만
   측정하도록 설계돼 있어(`d5.unsplittable_outliers(candidates)`),
   Level 3 적용 여부와 무관하게 항상 동일한 값(0.2%)을 낸다 — 이 지표로
   Level 3 효과를 판단할 수 없음(위 직접 청크 길이 검증이 올바른 지표).
   같은 재측정에서 Axis 2는 33.7%→30.2%로 소폭 하락했는데, 이는 Level 3가
   만든 조각들이 "의미 경계 flush 아님"으로 분모에만 추가되어 비율이
   희석된 측정 부작용이지 실제 semantic flush 능력 저하가 아니다.

   **프로덕션 전환 여부는 여전히 별도 HQ 결정 사항** — ADR-008 제안
   2/3/4 모두 완료, 제안 1(§1 threshold)도 Axis 1/3 확정 + Axis 2는
   Profile B 개선 확인까지 마친 상태이나, 이 ADR은 전환을 결정하지
   않는다(ADR-007 "D-5 게이트 통과 = 실행 승인 아님" 원칙 유지). 2026-07-22
   기준 데이터만 정리, 전환 착수는 보류.

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

6. **§1(Minimum Semantic Improvement Threshold) 최종 확정 (2026-07-23,
   HQ 승인)** — Axis 1/3은 위 §4에서 이미 확정. 남아 있던 Axis 2
   (Profile B)를 다음 근거로 확정한다:

   | 지표 | 실측 이력 |
   |---|---|
   | Phase 3-A (2026-07-20) | 16.4% — HQ "불충분" 판정 |
   | 임베딩 feature 도입 후 (2026-07-21) | 33.7% |
   | Level 3 도입 후 재측정 (2026-07-22) | 30.2% (측정 부작용 — Level 3 조각이 분모에만 반영되어 희석, 실제 능력 저하 아님, 위 §5 참고 기록) |

   Axis 1(≥95%, 실측 98.5~99.0%)·Axis 3(A:0%, B:≤10%, 실측 대비 여유폭)와
   동일한 "실측치 대비 회귀 감지용 하한선" 원칙을 적용해:

   **Profile B Axis 2 threshold = ≥25%** (측정 부작용을 반영한 최저
   실측치 30.2%에서 약 5%p 마진). Profile A(29.1%)는 이전과 동일하게
   이번 결정 범위 밖으로 유지.

   이 수치는 Beta corpus 표본(Profile B 4개 문서) 기준이며 영구
   확정치가 아니다 — corpus가 확장되면 재산정 대상(ADR-007 §1이
   애초에 "SPRINT33-D 이후 재산정" 전제로 이연했던 항목과 동일한
   성격). §1 전체(Axis 1/2/3)가 이로써 최종 확정됨.

   D-5 게이트 잔여 미확정 항목: §2(Orphaned 2단계 기준 수치),
   §3(false-positive 보호 구체 임계값), §4(genre 자동분류 알고리즘)
   — 이 3개가 확정돼야 D-5 게이트 "통과/실패" 실제 판정이 가능하다.
   §5(Rollback 수치)는 §1 확정으로 이제 정의 가능해졌으나 아직 미기술.

7. **§2/§3/§4/§5 최종 확정 (2026-07-23, HQ 승인)** — 기존 측정
   문서(Phase 4-C, ADR-007 Amendment A, ADR-011) 재검토로 확정.

   **§2 — Orphaned Boundary 2단계 기준**:
   - Heading 관여 boundary(핵심 기준): §1에서 확정된 **Axis 1 ≥95%**를
     그대로 채택(Amendment A가 orphaned recovery를 Axis 1로 흡수했으므로
     별도 수치 불필요, ADR-008:42 실측 98.5~99.0%).
   - Heading 미관여·저weight boundary(관대한 허용범위): Phase 4-C
     실측 정밀도 범위 20~40%(`docs/SPRINT33-C-phase4c-scripture-reference-validation.md:100`)의
     하한을 그대로 허용 하한으로 채택 — **≥20%**.

   **§3 — False-positive 보호 조건**:
   - (a) 장르별 정밀도 하한: Phase 4-C 실측 최저치 **20%(WBC 학술
     주석)** — ADR-007 초안이 이미 이 수치를 인용했으므로 그대로
     확정. 이 미만 장르는 게이트를 열지 않는다.
   - (b) 단일 feature 판정 boundary 비율 경고선: **실측 완료(2026-07-23,
     `scripts/shadow_d5_single_feature_ratio.py` 신규 작성)** — Beta
     corpus 전체(Profile A 338건, Profile B 309건, 총 647 boundary)에서
     단일-feature-only 비율 = **0.0%**(0/647). 원인: `paragraph`
     feature(weight 30)가 거의 모든 candidate에서 다른 feature와 함께
     발화해 단독 판정 사례가 구조적으로 거의 발생하지 않음(원시 feature
     dump로 확인). ADR-007 초안의 "예: 30%" placeholder는 폐기하고,
     경고선을 실측 기반 **≥10%**로 확정(현재 0.0%에서 상당한 여유폭 —
     Axis1/2/3과 동일한 회귀 감지용 하한선 원칙).
   - (c) PageHeaderArtifact 안전 마진: **구현·실측 완료, 그러나 moot로
     확인(2026-07-23)** — ADR-011 제안 1~3(`RepetitionTracker`,
     `noise_classifier` 연결, `PageHeaderArtifactFeature`) 전부 구현·
     검증했으나 Beta corpus에서 실제 발화 0건(running header가 PDF
     추출 단계에서 이미 제거되는 것으로 추정). 마진 수치(10~15%)는
     feature가 미발화 상태라 지금은 어떤 판정에도 영향을 주지 않음 —
     **잠정치 15% 유지하되 "현재 무효(moot)"로 표기**. 상세 근거는
     `docs/architecture/ADR-011-Header-Footer-Repetition-Detector.md`
     Next Steps 참고.

   **§4 — Genre 자동분류 알고리즘**: 정식 알고리즘은 여전히 미설계
     (Amendment A가 명시적으로 이연한 항목, 별도 Preflight 필요).
     현재 코드/문서에 존재하는 유일한 실행 가능 규칙은 Amendment A의
     provisional 규칙(`chunk_size × 1.5 = 1800자 초과 → Profile B, 아니면
     Profile A`, `ADR-007-Amendment-A.md:60-63`)뿐이다. **이를 공식
     interim 규칙으로 채택**하되, Amendment A 자신이 경고한 경계 사례
     리스크(Amendment-A.md:169-172)가 그대로 남아 있음을 D-5 게이트
     문서에도 명시 — 정식 분류기 설계 전까지는 이 provisional 규칙으로
     게이트를 운영한다.
     (주의: `core/pdf_structure_detector.py`의 `profile_document()`는
     이름이 유사하나 무관한 기능(SPRINT30-C heading 신호 선택기)이므로
     혼동 금지.)

     **대안 신호 탐색 시도 및 부결 (2026-07-23)**: "Profile B는 heading
     밀도가 낮은 학술 주석서"라는 기존 정성적 서술(§Context 등)이
     정량 신호(heading 개수/candidate 개수)로 유효한지 실측했다.
     **결과: 부적합** — Profile A는 5.32~24.68%(median 7.59%), Profile
     B는 8.39~229.14%(median 92.30%)로 두 구간이 겹치고, 오히려 B의
     중앙값이 A보다 훨씬 높다(기존 정성적 서술과 반대 방향). 원인으로
     의심되는 것: "2 Kings" 계열 2개 문서는 heading 개수가 candidate
     개수를 초과(947 candidates에 2170 headings=229%) — `core.heading_
     provider.PdfHeadingProvider`가 running header/페이지 헤더를
     heading으로 오탐하고 있을 가능성(미검증 가설). 사실이라면 위 §3(c)
     조사에서 "running header가 candidate 스트림에서 사라진" 이유가
     '추출 단계 제거'가 아니라 'heading 채널로 오분류'일 수 있다는
     뜻이었다.

     **오탐 가설 검증·근본원인 수정 완료 (2026-07-23, HQ 승인)**:
     `core.pdf_structure_detector.py`("2 Kings, Anchor Bible Commentary"
     heading 목록 직접 덤프)로 확인한 결과, 가설과 다르게 running
     header 자체가 아니라 **폰트 크기 이봉(bimodal) 분포 버그**가
     원인이었다. `_body_size()`가 "가장 많은 글자수를 차지하는 폰트
     크기 1개"만 본문으로 인식하는데, 이 문서는 본문 텍스트가 두
     밴드(14.2pt 1911줄 vs 16.0~16.2pt 2166줄, 거의 동급 규모)로
     나뉘어 있어 두 번째 밴드 전체(주로 인용 성구 텍스트의 줄바꿈
     조각)가 heading 후보로 오탐(947 candidates 대비 heading 2170건).

     **수정**: `_effective_size_ceiling()` 신설 — 두 번째 폰트 크기
     밴드가 (a) `is_block_top` 비율이 50% 이하이고 (b) 줄 수가
     `max(30, body_count × 15%)` 이상이면 "본문"으로 간주해 heading
     판정 기준선을 그 크기까지 올린다. 판별 신호로 `is_block_top`
     비율을 선택한 근거(실측): 진짜 heading("Notes"/"Comment", 86건)은
     100% block-top, 실제 heading이 많은 정상 문서("8. 사도행전2")도
     84.3% block-top인 반면, 오탐 밴드는 15.6%에 불과 — 두 경우가
     명확히 분리됨. char-weight 비율 방식은 먼저 시도했으나 소수
     헤딩 케이스에서 오판(단위테스트로 발견, 폐기).

     **회귀 발견·2차 수정 (2026-07-23, 같은 세션)**: 최초 수정은 줄 수
     조건을 절대 floor(10줄)만으로 뒀는데, 큰 문서(예: "11.
     고린도전서", 총 7705줄)에서 11~47줄짜리 작은 노이즈 밴드까지
     "두 번째 본문대"로 오판해 heading 판정 기준선을 39.2pt까지
     밀어올리는 바람에 진짜 heading 111건이 0건으로 사라지는 회귀를
     유발(§4 heading 밀도 재실측 도중 발견). 원인: 절대 floor만으로는
     문서 규모에 비례하지 않는 노이즈 밴드를 걸러내지 못함. **수정**:
     절대 floor(30줄) OR 상대 floor(body 밴드 줄 수의 15%) 중 큰 값을
     요구하도록 변경 — 노이즈 밴드는 body 대비 비중이 미미(11~47줄 vs
     body 6149줄)해 상대 floor(922줄)에 못 미쳐 걸러지고, 진짜 큰
     두 번째 본문대(Anchor Bible, 4008줄 vs body 6353줄)는 여전히
     통과. 재검증: 고린도전서 111(원복), 사도행전1 117(원복),
     사도행전2 321(원래 313과 근접), Anchor Bible 유지(215건),
     KO-series 신호 `['none','size']`→`['size']`로 오히려 개선.

     **검증**: "2 Kings, Anchor Bible Commentary" heading 2170→**203~215**건
     (90%+ 감소), 진짜 heading("Notes"/"Comment" 86건)은 100% 보존.
     한국어 문서 전체 heading 카운트 버그 수정 이전 원래 값으로 복원
     확인(회귀 없음).
     benchmark 테스트(`tests/test_pdf_structure_benchmark.py`)의 Anchor
     candidates 2170→25(테스트 자체 표본 스코프는 다름). 신규 단위
     테스트 3건(`TestSecondaryBodyBand`) + 회귀 706 passed.

     이 수정은 `core/tsu_builder.py`가 PDF 문서 heading 배정에 실제로
     사용하는 프로덕션 경로에 영향을 준다(dormant가 아님) — SPRINT30-C
     모듈 자체 문서상 "TSU 저장은 미승인"이지만, `HeadingAssembler`를
     통해 이미 실제 chunk의 section_title 문맥에 쓰이고 있었음을
     확인.

     **§4용 heading 밀도 재실측 (수정된 데이터 기준)**: 버그 수정 후
     여전히 **깨끗한 discriminator 아님** — Profile A 5.32~25.32%
     (median 7.78%), Profile B 8.39~169.27%(median 19.02%, "2 Kings
     Volume 13"의 169.27% 이상치 제외 시 8.39~22.70%)로 두 구간이
     여전히 겹친다(A 최대 25.32% > B 최소 22.70%). heading 카운트
     버그는 고쳤지만 그 자체가 genre discriminator는 아니라는 최초
     결론은 유지.

     **"2 Kings, Volume 13" 이상치 원인 조사·3차 수정 완료
     (2026-07-23, 같은 세션, HQ 승인)**: 이 문서는 `selected_signal=
     'bold'`(size가 아니라 bold 신호로 판정)였고, `_is_candidate`의
     bold 분기가 `is_block_top` 조건 없이 "body 크기 + bold"만
     확인했다. 실측: body 크기(10.0pt) bold 줄 6768개 중 block-top은
     841개뿐 — 나머지 5927개는 볼드 처리된 원어(히브리어) 단어
     인용(יהוה, אל, ישראל 등, 본문 중간에 등장)이지 heading이 아니었다.
     block-top 그룹에는 진짜 section heading("Form/Structure/Setting"
     17x, "Bibliography" 12x, "Notes" 12x, "Comment" 11x, "Translation"
     10x, "Explanation" 7x)이 정확히 모여 있었다.

     **수정**: `profile_document()`의 `bold_hits` 집계와
     `_is_candidate()`의 bold 분기 둘 다에 `line.is_block_top` 조건
     추가 — size 신호에 적용한 것과 동일한 원칙("진짜 heading은
     block 시작점")을 bold 신호에도 일관 적용.

     **검증**: "2 Kings, Volume 13" heading 5100→**556**건(89% 감소),
     진짜 section heading(69건 + 표기 변형 몇 건) 100% 보존. 기존
     WBC 문서("2 Chronicles, Volume 15") bold 신호 정상 동작 유지
     (회귀 없음, benchmark candidates 20건 그대로). 신규 단위테스트
     1건(`test_bold_candidate_requires_block_top`) 추가, 회귀 707
     passed.

     **잔여**: 556건 중 다수(약 480여 건)는 여전히 문단 첫 줄이
     우연히 bold로 표시된 본문 문장 — 이번 수정보다 더 정밀한
     판별(예: 텍스트 길이, 문장부호 유무)이 필요하나 진척 정도가
     충분해(89% 감소, 실 heading 100% 보존) 이번 세션 범위에서는
     여기서 멈춘다. 완전 제로화는 후속 과제.

     **§4 재확인**: 위 3차 수정 이후 "2 Kings, Volume 13"의 heading
     밀도도 크게 정상화(569/3013≈18.4%대로 추정, 다른 Profile B
     문서와 비슷한 범위)됐지만, heading 밀도 자체가 Profile A/B를
     가르는 discriminator라는 결론은 바뀌지 않는다(Profile A도
     비슷한 범위까지 올라감, §Context 최초 실측 참고).

     **§4 최종 확정 (2026-07-23, 같은 세션, HQ 승인)**: heading 밀도
     대신 candidate 길이 분포를 실측(Beta corpus 12개 문서 전체)한
     결과, **candidate 중앙값 길이**가 겹침 없이 완전히 분리됨을
     확인했다 — Profile A 132~184자, Profile B 269~856자. 대안으로
     citation-괄호 비율(`core.noise_classifier._RE_CITATION_YEAR`)과
     BIBLIOGRAPHY 분류 비율도 동일하게 완전 분리를 보였으나(A
     0.00~0.17%, B 2.52~37.28%), 중앙값 길이는 추가 분류 패스가
     필요 없어 이를 채택.

     **구현**: `core.hierarchical_chunk_builder.classify_document_
     profile()` 신설 — `median(candidate 길이) > 220자` 기준(분리
     구간 184~269 중간값). 기존 provisional 규칙("candidate 1개라도
     1800자 초과")의 알려진 결함(이상치 candidate 1건에 문서 전체
     분류가 흔들림, Amendment A §리스크 명시)을 구조적으로 해결 —
     중앙값은 분포 전체를 반영해 단일 이상치에 흔들리지 않는다(단위
     테스트로 검증: 이상치 1건 포함 문서도 여전히 Profile A로 정확히
     분류됨).

     **주의**: `scripts/shadow_d5_metrics.py` 등 기존 진단 스크립트의
     로컬 `classify_profile()`은 과거 ADR-008 측정치(2026-07-20~22)의
     재현성을 위해 **의도적으로 그대로 유지**(1800자 규칙) — 소급
     변경하지 않음. 신규 표준 함수는 향후 프로덕션/재측정에 사용.
     회귀: 신규 단위테스트 4건(`TestClassifyDocumentProfile`), 전체
     711 passed.

     이로써 D-5 게이트(ADR-007 §1~§5) **전 항목이 실측 근거로
     확정**됐다. 단, 게이트 통과가 곧 프로덕션 전환 승인은 아니다
     (ADR-007 원칙 유지) — 전환은 별도 명시적 HQ 승인 대상.

   **§5 — Rollback 수치**: §1 확정치를 그대로 롤백 트리거로 채택 —
     rebuild 후 재측정에서 **Axis 1 <95%**, 또는 **Axis 3 A>0%/B>10%**,
     또는 **Axis 2(Profile B) <25%** 중 하나라도 해당하면 자동 롤백
     대상. Profile A의 Axis 2는 이번 결정 범위 밖(§1과 동일하게 유지)
     이므로 롤백 트리거에서 제외.

   **D-5 게이트 상태**: §1~§5 전 항목이 이제 수치를 갖췄다 — 게이트
   "통과/실패" 판정이 최초로 가능해졌다. §1/§2/§3(a)/§3(b)/§5는 실측
   근거로 확정. §3(c)(PageHeaderArtifact 마진 15%)와 §4(genre 분류
   provisional 규칙)만 미구현/미검증 상태로 남아 있다 — §3(c)는
   feature 자체가 없어 실측 불가하고, §4는 정식 분류기 설계가 별도
   연구 과제(Amendment A가 이미 이연한 항목)라 이번 세션 범위 밖.
   실제 게이트 판정 실행 전 이 두 항목의 후속 처리를 권고한다.
   ADR-007의 원칙("D-5 게이트 통과 = 실행 승인 아님")은 그대로 유지
   — 게이트 판정 자체가 프로덕션
   전환 승인은 아니며, 전환은 별도 명시적 HQ 승인 대상.

# C1 Task Order 016 — Hierarchical Chunk Builder Axis 2 (Semantic Flush Ratio) 개선 설계

**상태**: 중단 — HQ 승인 후 재개 (2026-07-28, David 지시). CUE 검토 완료 — Option C-1 반려, Option A-1 방향 오류 CUE가 구현 중 수정, Phase 1.4 canary(축소 세트) 결과 목표 미달.
**작성자**: C1 (DBMA Core Engineer)
**작성일**: 2026-07-28
**범위**: 설계만 완료, 코드 변경 없음

---

## CUE 재확인 지시 (2026-07-28)

- Option A: 승인. 계수(0.3), alpha(0.7)는 Phase 1.4 canary로 검증 후 확정.
- Option C-1: **반려**. `classify_document_profile([(context.candidate_text, context.position)])` 호출은 함수 설계(문서 전체 candidates의 median 길이로 분류) 오용. candidate 단위로 매 스코어링마다 호출하면 안 됨. `build_chunks()` 진입 시 문서 전체로 1회만 계산해 `BoundaryContext`/`score_boundary()`에 파라미터로 전달하도록 수정할 것.
- Option B: 보류 유지, Phase 4에서만 재검토.

상세 코멘트는 `docs/hierarchical-chunk-builder-improvement-design.md` "CUE 검토 코멘트" 섹션 참고. 수정 후 설계 문서 v1.2로 재제출 바람.

---

## CUE 추가 지시 — Option A-1 방향 오류 (2026-07-28)

CUE가 v1.2 승인 후 Act mode에서 Option A를 직접 구현하던 중, §3 Option A-1의 동적 임계값 공식에 방향 오류를 발견해 구현 시 즉시 수정했다. 상세는 `docs/hierarchical-chunk-builder-improvement-design.md`의 "CUE 구현 중 발견 — Option A-1 동적 임계값 방향 오류" 섹션 참고.

요약: `EmbeddingSimilarityBoundaryFeature.score()`는 `similarity < threshold`일 때 boundary(1.0)를 낸다. 원안(버퍼가 찰수록 threshold **하향**)은 목표(Profile B boundary를 더 잡기)와 반대로 동작한다. CUE는 구현을 버퍼가 찰수록 threshold **상향**(상한 1.3배, `DYNAMIC_THRESHOLD_CEILING_RATIO`)으로 고쳐 `core/semantic_boundary_detector.py` / `core/config.py` / `tests/test_embedding_similarity_boundary_feature.py`에 반영 완료(테스트 23개 통과, 아직 `_default_registry()` 미등록 — dormant 유지).

**C1 조치**: 설계 문서 §3 Option A-1, §8 계수 검증 계획을 이 방향에 맞게 v1.3으로 수정해 재제출. n-gram 결합(A-2)은 수정 불필요.

---

## CUE Phase 1.4 canary 실측 결과 — 목표 미달, HQ 판단 대기 (2026-07-28)

C1의 v1.3 방향 수정(§3 Option A-1 상향 공식) 확인 후, CUE가 Phase 1.4 canary를 실행했다. 전체 12개 문서(`scripts/shadow_d5_metrics.py`)는 문서당 수백~수천 회 Ollama 임베딩 호출로 36분+ 실행해도 미완료 — 사용자 지시로 대표 문서 2개(Profile B 최소 candidate 947개, Profile A 최소 candidate 783개)로 축소 재실행(RAW 나머지 10개 PDF는 미파싱). alpha=0.7 고정, slope만 스윕(3분22초 완료).

| slope | Profile A Axis 2 | Profile B Axis 2 |
|-------|------|------|
| 0.2 | 13.7% | 21.8% |
| 0.3 (기본값) | 13.2% | 21.0% |
| 0.4 | 12.4% | 20.3% |

**예상과 반대 방향**: slope를 올릴수록(threshold를 더 관대하게 해도) Axis 2가 A/B 둘 다 하락했다. 개별 embedding feature 신호 자체는 늘어(shadow chunk 수 증가, 더 자주 flush) 방향 수정은 맞았지만, 그로 인해 버퍼가 빨리 비워져 `accumulated_length`가 safety_cap에 도달할 기회가 줄면서 dynamic threshold 상향 효과가 자기 상쇄되는 것으로 추정 — 원인 미확정.

**결론**: 이 축소 세트 기준 slope 0.2~0.4 전 구간 Profile B가 20~22%로 목표(≥25%) 미달. Option A 단독으로는 부족할 가능성 — Option C-1(Profile별 DEFAULT_THRESHOLD 조정, §7에서 반려됐던 코드 결함과는 별개로 "Profile별 임계값 자체"의 재검토) 또는 Option B 병행 필요성이 다시 제기됨.

**C1 조치**: 설계 문서 §8.1에 이미 위 실측 결과 기록됨(v1.4 후보). 사용자 지시로 이번 라운드는 여기서 중단 — 전체 corpus 재검증, alpha 스윕, Option C-1 재설계는 HQ 판단 대기 상태로 보류한다. 추가 조사·구현 착수 전 HQ 승인 먼저 받을 것.

---

## 1. 배경

### 1.1 현재 문제

Axis 2 (Semantic Flush Ratio): 청크가 의미 경계에서 실제로 종료되는 비율

- **Profile B 평균**: 23.9% (임계값 ≥25%) 미달
- **원인**: Profile B(학력 밀도 낮은 학술 주석서)는 heading이 드물어 구조 기반 5개 feature(heading/paragraph/tiny_fragment/sentence_boundary/scripture_reference)가 신호를 거의 못 냄. EmbeddingSimilarityBoundaryFeature가 그 공백을 메워야 하지만 현재 임계값이 Profile B에 맞지 않음.

### 1.2 관련 문서

- `docs/PREFLIGHT-hierarchical-chunk-builder-canary-2026-07-27.md` — canary 실측 결과
- `core/hierarchical_chunk_builder.py` — Hierarchical Chunk Builder 프로토타입
- `core/semantic_boundary_detector.py` — Boundary Score 모델
- `docs/hierarchical-chunk-builder-improvement-design.md` — 개선 설계 문서 (신규)

---

## 2. 개선 설계 요약

### 2.1 현재 Boundary Score feature 구성

| Feature | Weight | Profile B 한계 |
|---------|--------|---------------|
| heading | +100 | heading 드문 문서에서 신호 부족 |
| paragraph | +30 | 모든 candidate에 적용 → 상수 기여 |
| tiny_fragment | -60 | heading 없는 tiny만 영향 |
| sentence_boundary | +10 | 높은 base rate → 판별력 제한적 |
| scripture_reference | +30 | head window에서만 검사 |
| **embedding_similarity** | **+50** | **임계값 불일치 — 개선 대상** |

### 2.2 세 가지 개선 옵션

#### Option A: EmbeddingSimilarityBoundaryFeature 임계값 최적화 (P0 권장)

**개선 방안**:
1. 동적 임계값: 버퍼 길이에 따라 임계값 조정
   - `drop_threshold = base_threshold * (1.0 - accumulated_length / safety_cap * 0.3)`
2. n-gram 유사도 추가: `combined_score = alpha * embedding + (1-alpha) * ngram`
3. 슬라이딩 윈도우: 이전 N개 평균으로 변경

**기대 효과**: Axis 2 5~10%p 향상

#### Option B: Profile B 전용 feature 추가 (P2)

**신규 feature**:
1. ParagraphTopicDriftFeature — 버퍼 내 첫/마지막 문장 임베딩 유사도
2. AcademicStructureFeature — 학술 주석서 인용 구조 감지
3. BufferLengthNormalizationFeature — 버퍼 길이 기반 점진적 신호

**기대 효과**: Axis 2 10~15%p 향상 (높은 구현 비용)

#### Option C: 경계 판정 로직 개선 (P1)

**개선 방안**:
1. Profile별 동적 임계값: `threshold_B = 35.0`, `threshold_A = 50.0`
2. 가중치 재조정: `embedding_similarity +50 → +80`
3. 누적 점수 방식: `max(heading, embedding) + base`

**기대 효과**: Axis 2 5~10%p 향상

---

## 3. 권장 실행 계획

| 단계 | 작업 | 우선순위 | 예상 비용 |
|------|------|---------|----------|
| **1** | Option A: 임계값 최적화 | P0 | 낮음 |
| **2** | Profile B corpus 재측정 | P0 | 중간 |
| **3** | Option C-1: 동적 임계값 | P1 | 낮음 |
| **4** | Option B: 전용 feature (필요시) | P2 | 높음 |
| **5** | HQ 승인 → 프로덕션 전환 | P0 | — |

---

## 4. CUE 검토 요청 사항

1. **어떤 옵션을 우선 추진할지** 지시 바랍니다.
2. **Option A의 동적 임계값 공식**이 적절한지 검토 바랍니다.
3. **Profile B 전용 feature 추가 필요성** 판단 바랍니다.
4. **프로덕션 전환 시기** 지시 바랍니다.

---

## 5. 다음 단계

- CUE 승인 시: Act mode에서 구현 착수
- 추가 질문/수정 요청 시: 설계 문서 수정 후 재제출

---

**문서 작성일**: 2026-07-28
**상태**: CUE 검토·승인 대기
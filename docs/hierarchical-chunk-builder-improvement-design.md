# Hierarchical Chunk Builder — Axis 2 (Semantic Flush Ratio) 개선 설계

**상태**: Option A 구현 완료(dormant, 미등록) — §8.1 목표 미달. Option C-1(profile별 정적 threshold)은 구현→canary 실측→반증→되돌림까지 완료(2026-07-28, §11). **Option B는 코드 작성 전 사전 검토에서 재설계 요청(2026-07-29, §12) — B-3 제외/B-2 재설계/B-1 검증 필요.**
**작성자**: C1 (DBMA Core Engineer)
**승인 상태**: CUE 검토 완료 — Option A 승인(방향 오류 CUE가 구현 중 수정, 계수는 §8.1 실측상 부족 확인), Option C-1은 실측으로 반증되어 되돌림(§11), Option B는 재설계 요청(§12)
**문서 버전**: v1.5 (Option B 사전 검토 — 코드 작성 전 재설계 요청 추가)

---

## CUE 구현 중 발견 — Option A-1 동적 임계값 방향 오류 (2026-07-28)

§3 Option A-1 공식은 **버그**였다:
```python
dynamic_threshold = self._drop_threshold * (1.0 - buffer_ratio * 0.3)  # ❌ 하향
```
`EmbeddingSimilarityBoundaryFeature.score()`는 `similarity < threshold`일 때 boundary(1.0)를 낸다. threshold가 **낮을수록** 더 적은 similarity 값만 걸려 boundary가 더 **적게** 잡힌다. 즉 원안대로 버퍼가 찰수록 threshold를 낮추면, "Profile B에서 boundary를 더 잡자"는 목표와 **정반대**로 동작해 버퍼가 다 찰수록 오히려 boundary가 덜 잡힌다.

**CUE가 구현 시 수정한 방향** (`core/semantic_boundary_detector.py::EmbeddingSimilarityBoundaryFeature.score()`, `core/config.py`):
```python
buffer_ratio = min(1.0, buffer_ratio)
dynamic_threshold = self._drop_threshold * (1.0 + buffer_ratio * DYNAMIC_THRESHOLD_SLOPE)  # ✅ 상향
dynamic_threshold = min(self._drop_threshold * DYNAMIC_THRESHOLD_CEILING_RATIO, dynamic_threshold)
```
`DYNAMIC_THRESHOLD_FLOOR_RATIO`(하한, 0.5)는 `DYNAMIC_THRESHOLD_CEILING_RATIO`(상한, 1.3 = 1.0 + slope)로 교체됨.

**C1 조치 필요**: 설계 문서 §3 Option A-1, §7(있다면), §8 계수 검증 계획 표를 이 방향(상향 + 상한)으로 v1.3으로 수정해 재제출할 것. n-gram 결합(A-2)은 원안 그대로 유효 — 수정 불필요.

구현은 이미 `core/semantic_boundary_detector.py` / `core/config.py` / `tests/test_embedding_similarity_boundary_feature.py`에 반영 완료(테스트 23개 통과, `_default_registry()`에는 아직 미등록 — dormant 유지). 문서만 코드에 맞춰 정정하면 됨.

---

## CUE 검토 코멘트 (2026-07-28)

**Option A (P0)**: 승인. 방향 타당, 하한선 안전장치 있음. 단, 동적 임계값 계수 0.3과 n-gram 결합 alpha 0.7은 근거 없는 임의값 — Phase 1.4 canary 재실행 시 여러 값으로 확인 후 확정할 것.

**Option C-1 (P1)**: **반려 — 코드 결함**. §3 Option C-1 (262-263행)의
```python
profile = classify_document_profile([(context.candidate_text, context.position)])
```
는 오용이다. `classify_document_profile()`(`core/hierarchical_chunk_builder.py:103`)은 **문서 전체 candidate 리스트의 median 길이**로 Profile A/B를 가르도록 설계된 함수다. candidate 1개짜리 리스트를 넘기면 median이 해당 candidate 하나의 길이가 되어버려 문서 단위 분류라는 설계 의도와 어긋난다. 또한 `score_boundary()`는 candidate마다 호출되므로 이 함수를 boundary 판정 루프 안에서 매번 호출하는 것 자체가 잘못된 설계다.

**수정 방향**: profile은 `build_chunks()` 진입 시 문서 전체 candidates로 **1회만** 계산하고, `score_boundary()`/`BoundaryContext`에 파라미터로 전달할 것. candidate 단위 재계산 금지.

**Option B (P2)**: 보류 유지. Phase 1~3 이후 Axis 2 여전히 미달 시에만 재검토.

---

## 1. 문제 진단 요약

### 1.1 Axis 2 (Semantic Flush Ratio) 정의

청크가 의미 경계에서 실제로 종료되는 비율 — 즉, `build_chunks()`가 semantic boundary 신호를 보고 flush를 실행한 청크의 비율.

### 1.2 현재 측정값

| Profile | Semantic Flush Ratio | 임계값 | 상태 |
|---------|---------------------|--------|------|
| Profile A (Low Back-matter) | ~35% | ≥25% | ✅ 통과 |
| **Profile B (High Back-matter)** | **23.9%** | **≥25%** | ❌ **미달** |

### 1.3 근본 원인 분석

Profile B(학력 밀도 낮은 학술 주석서, 예: WBC 시리즈)는 다음과 같은 특성을 가짐:

1. **Heading이 드묾**: 본문 내 명확한 제목 구조가 없어 `HeadingBoundaryFeature`가 신호를 못 냄
2. **긴 문단**: 주석 내용이 길게 이어져 임베딩 유사도가 자연스럽게 높게 나옴
3. **구조 기반 feature의 신호 부족**: 5개 feature(heading/paragraph/tiny_fragment/sentence_boundary/scripture_reference) 중 heading만 신호 가능, 나머지는 상수 기여 또는 제한적 신호

### 1.4 EmbeddingSimilarityBoundaryFeature의 역할과 한계

**역할**: Profile B에서 heading 신호 부재를 대체할 핵심 feature
- 인접 후보 간 임베딩 유사도가 `EMBEDDING_SIMILARITY_DROP_THRESHOLD` 미만이면 주제 전환으로 판정

**한계**:
- 현재 임계값이 Profile A 기준으로_calibration_됨 (Profile B 데이터 없음)
- Profile B의 긴 문단에서는 인접 문장 간 유사도가 높아 신호가 안 남
- 정적 임계값: 버퍼 길이/문서 특성에 따른 적응력 부족

---

## 2. 현재 Boundary Score 모델의 feature 구성

### 2.1 Feature 목록 및 Weight

| Feature | Weight | 신호 조건 | Profile B에서의 실제 기여 |
|---------|--------|-----------|-------------------------|
| `heading` | +100 | candidate가 heading과 매칭될 때 | 드묾 (heading 자체가 적음) |
| `paragraph` | +30 | candidate가 비어있지 않을 때 | 상수 기여 (모든 candidate에 적용) |
| `tiny_fragment` | -60 | candidate 길이 < min_chunk_size | heading 없는 tiny만 영향 (이미 paragraph에서 +30) |
| `sentence_boundary` | +10 | candidate 마지막 줄이 문장 끝일 때 | 높은 base rate (~88%) → 판별력 제한적 |
| `scripture_reference` | +30 | candidate head window에 성경 참조 있을 때 | head window에서만 검사 (제한적) |
| **`embedding_similarity`** | **+50** | **인접 후보 유사도 < threshold일 때** | **핵심 — 하지만 임계값 불일치** |

### 2.2 점수 계산 예시 (Profile B 문서, heading 없음)

```
heading:      0.0 * 100 =   0.0
paragraph:    1.0 *  30 =  30.0  (candidate가 비어있으므로)
tiny_fragment: 0.0 * -60 =  0.0  (candidate가 min_chunk_size보다 김)
sentence_boundary: 1.0 * 10 = 10.0  (문장 끝이므로)
scripture_ref: 0.0 * 30 =  0.0  (head window에 참조 없음)
embedding_sim: 0.0 * 50 =  0.0  (유사도가 threshold보다 높음 → 신호 안 남)
---
total: 40.0 < DEFAULT_THRESHOLD(50.0) → boundary 아님
```

**문제**: embedding_similarity가 0.0을 반환하면 total이 40.0으로 threshold 50.0 미달 → flush 안 됨

---

## 3. 개선 방안 (3가지 옵션) — 상세 디테일

---

### Option A: EmbeddingSimilarityBoundaryFeature 임계값 최적화 (P0 권장)

#### A-1. 동적 임계값 구현 (v1.3 정정: 상향 방향)

**현재 코드** (`core/semantic_boundary_detector.py::EmbeddingSimilarityBoundaryFeature`):
```python
def __init__(self, embed_fn=None, drop_threshold: float = EMBEDDING_SIMILARITY_DROP_THRESHOLD):
    self._embed_fn = embed_fn or _get_embedder().embed
    self._drop_threshold = drop_threshold  # 정적
```

**v1.2 원안 (방향 오류 — 반려)**:
```python
# ❌ v1.2 원안: 하향 방향 — boundary를 더 적게 잡음 (목표와 반대)
buffer_ratio = context.accumulated_length / (context.chunk_size * SAFETY_CAP_RATIO) if context.chunk_size > 0 else 0.0
dynamic_threshold = self._drop_threshold * (1.0 - buffer_ratio * 0.3)
dynamic_threshold = max(self._drop_threshold * 0.5, dynamic_threshold)  # 하한선: base의 50%
return 1.0 if similarity < dynamic_threshold else 0.0
```

**v1.3 정정 후 (CUE 구현 반영 — 상향 방향)**:
```python
def score(self, context: BoundaryContext) -> float:
    prev = context.previous_candidate_text.strip()
    curr = context.candidate_text.strip()
    if not prev or not curr:
        return 0.0
    try:
        v_prev = self._embed_fn(prev)
        v_curr = self._embed_fn(curr)
    except Exception:
        return 0.0
    
    similarity = _cosine_similarity(v_prev, v_curr)
    
    # 동적 임계값: 버퍼가 길어질수록 임계값 상향 (v1.3 정정)
    buffer_ratio = min(1.0, context.accumulated_length / (context.chunk_size * SAFETY_CAP_RATIO)) if context.chunk_size > 0 else 0.0
    dynamic_threshold = self._drop_threshold * (1.0 + buffer_ratio * DYNAMIC_THRESHOLD_SLOPE)
    dynamic_threshold = min(self._drop_threshold * DYNAMIC_THRESHOLD_CEILING_RATIO, dynamic_threshold)  # 상한선: base의 1.3배
    
    return 1.0 if similarity < dynamic_threshold else 0.0
```

**논리 (v1.3)**:
- 버퍼가 safety_cap의 100%에 도달하면 임계값이 base의 1.3배까지 상향
- 상한선은 base의 1.3배로 고정 (너무 높은 임계값 방지)
- similarity < threshold이므로, threshold가 높아질수록 더 많은 similarity 값이 조건을 만족 → boundary를 더 많이 잡음
- Profile B의 긴 문단에서도 주제 전환을 더 많이 포착 가능

**v1.2 방향 오류 설명**:
- `EmbeddingSimilarityBoundaryFeature.score()`는 `similarity < threshold`일 때 boundary(1.0)를 냄
- threshold가 **낮아질수록** 더 적은 similarity 값만 조건을 만족 → boundary가 **적게** 잡힘
- 원안(하향)은 "Profile B에서 boundary를 더 잡자"는 목표와 **정반대**로 동작

**config.py 상수**:
```python
DYNAMIC_THRESHOLD_SLOPE = 0.3        # 버퍼가 찰수록 threshold 증가율
DYNAMIC_THRESHOLD_CEILING_RATIO = 1.3  # 상한선: base의 1.3배 (기존 FLOOR_RATIO 0.5 교체)
```

#### A-2. n-gram 유사도 추가

```python
def _ngram_overlap(s1: str, s2: str, n: int = 3) -> float:
    """n-gram 중복률 계산 (0.0~1.0)"""
    def get_ngrams(s, n):
        return set(s[i:i+n] for i in range(len(s) - n + 1))
    ng1, ng2 = get_ngrams(s1, n), get_ngrams(s2, n)
    if not ng1 or not ng2:
        return 0.0
    return len(ng1 & ng2) / min(len(ng1), len(ng2))
```

**결합 로직**:
```python
combined_score = 0.7 * similarity + 0.3 * _ngram_overlap(prev, curr)
return 1.0 if combined_score < dynamic_threshold else 0.0
```

#### A-3. 슬라이딩 윈도우 (이후 Phase)

현재: `previous_candidate_text` (직전 candidate 1개)
개선: 직전 N개 candidate 임베딩 평균과 비교

```python
# BoundaryContext에 추가 필요
previous_candidates: List[str] = field(default_factory=list)  # 직전 N개

def score(self, context: BoundaryContext) -> float:
    if not context.previous_candidates:
        return 0.0
    # N개 평균 임베딩
    prev_embs = [self._embed_fn(c) for c in context.previous_candidates[-3:]]
    v_curr = self._embed_fn(context.candidate_text.strip())
    # 평균 유사도 계산...
```

**기대 효과**: Axis 2 5~10%p 향상 (Profile B: 23.9% → ~30%)

---

### Option B: Profile B 전용 feature 추가 (P2)

#### B-1. ParagraphTopicDriftFeature

```python
class ParagraphTopicDriftFeature:
    """버퍼 내 첫 문장 vs 마지막 문장의 임베딩 유사도 측정.
    유사도가 낮으면 주제 전환으로 판정."""
    
    def score(self, context: BoundaryContext) -> float:
        if not context.previous_candidate_text or len(context.previous_candidate_text) < 50:
            return 0.0  # 버퍼가 너무 짧으면 의미 없음
        
        lines = [l for l in context.candidate_text.strip().splitlines() if l.strip()]
        if not lines:
            return 0.0
        last_line = lines[-1]
        
        try:
            v_prev = self._embed_fn(context.previous_candidate_text[:200])  # 첫 문장/내용
            v_curr = self._embed_fn(last_line)
        except Exception:
            return 0.0
        
        similarity = _cosine_similarity(v_prev, v_curr)
        # 유사도가 낮을수록 주제 전환 → 1.0에 가까움
        return 1.0 - similarity
```

#### B-2. AcademicStructureFeature

```python
class AcademicStructureFeature:
    """학술 주석서의 구조적 신호 감지."""
    
    # 학술 commentary에서 자주 보이는 패턴
    _PATTERNS = [
        r"verse\s+\d+[:\.]\s*\d+",           # "verse 3:14"
        r"cf\.\s+.*(?:also|see)",             # "cf. also..."
        r"(?:cf\.|cfr\.)\s+\w+",              # "cf. X"
        r"\([^)]*?:\s*\d+[:\.]\s*\d+[^\)]*\)",  # "(고전 3:14 참고)"
        r"comment.*on\s+\w+\s+\d+[:\.]\s*\d+",  # "comment on Romans 3:14"
    ]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self._PATTERNS]
    
    def score(self, context: BoundaryContext) -> float:
        for pattern in self._compiled:
            if pattern.search(context.candidate_text):
                return 1.0
        return 0.0
```

#### B-3. BufferLengthNormalizationFeature

```python
class BufferLengthNormalizationFeature:
    """버퍼가 chunk_size의 80% 이상 도달 시 점진적 신호 증가."""
    
    def score(self, context: BoundaryContext) -> float:
        if context.chunk_size <= 0:
            return 0.0
        ratio = context.accumulated_length / (context.chunk_size * 0.8)
        return min(1.0, max(0.0, ratio - 0.5))  # 50% 도달 시 신호 시작, 80%에서 1.0
```

**가중치 제안**:
| Feature | 제안 Weight | 이유 |
|---------|------------|------|
| ParagraphTopicDriftFeature | +40 | 주제 전환 직접 측정 |
| AcademicStructureFeature | +25 | 학술 구조 신호 |
| BufferLengthNormalizationFeature | +15 | 버퍼 길이 정규화 |

**기대 효과**: Axis 2 10~15%p 향상 (Profile B: 23.9% → ~35%)
**비용**: 높음 (신규 feature 3개 구현 + registry 등록 + 테스트)

---

### Option C: 경계 판정 로직 개선 (P1)

#### C-1. Profile별 동적 임계값

**현재 코드** (`core/semantic_boundary_detector.py`):
```python
DEFAULT_THRESHOLD = 50.0

def score_boundary(context, registry=None) -> BoundaryEvent:
    reg = registry or get_registry()
    features = reg.score_all(context)
    total = sum(features.values())
    return BoundaryEvent(
        ...,
        is_boundary=total >= DEFAULT_THRESHOLD,  # 고정 임계값
    )
```

**개선 후**:
```python
def score_boundary(context, registry=None) -> BoundaryEvent:
    reg = registry or get_registry()
    features = reg.score_all(context)
    total = sum(features.values())
    
    # Profile별 동적 임계값 (classify_document_profile() 사용)
    from core.hierarchical_chunk_builder import classify_document_profile
    profile = classify_document_profile([(context.candidate_text, context.position)])
    
    if profile == "B":
        threshold = DEFAULT_THRESHOLD * 0.7  # 35.0
    else:
        threshold = DEFAULT_THRESHOLD  # 50.0
    
    return BoundaryEvent(
        ...,
        is_boundary=total >= threshold,
    )
```

#### C-2. 가중치 재조정 (Profile B 기준)

| Feature | 현재 Weight | 제안 Weight | 변경 이유 |
|---------|------------|------------|-----------|
| `embedding_similarity` | +50 | **+80** | Profile B의 핵심 신호, 가중치 증가 |
| `heading` | +100 | +100 | 유지 (신호 드물지만 강력하므로 기존 유지) |
| `paragraph` | +30 | +20 | 상수 기여도 낮춤 (다른 feature와의 상대적 비중 조정) |
| `sentence_boundary` | +10 | +15 | 미세 조정 (문장 끝 신호 더 반영) |
| `scripture_reference` | +30 | +30 | 유지 |
| `tiny_fragment` | -60 | -60 | 유지 |

#### C-3. 누적 점수 방식 변경 (선택사항)

현재: `sum(all_feature_scores)` — 모든 feature 선형 합산

대안: `max(heading_score, embedding_score) + base_score`
- heading이 신호하면: `100 + paragraph(20) + sentence(15) = 135` → 명확한 boundary
- heading 없으면: `embedding(80) + paragraph(20) + sentence(15) = 115` → embedding 기반 boundary

**장점**: heading/embedding 간 상호 배타적 로직 명확화
**단점**: 구현 복잡도 증가, 현재 선형 합산의 단순성 손실

**기대 효과**: Axis 2 5~10%p 향상 (Profile B: 23.9% → ~30%)

---

## 4. 권장 실행 계획 — 상세 단계

### Phase 1: Option A 구현 (P0, 예상 소요: 1~2일)

| 단계 | 작업 | 세부 내용 | 검증 방법 |
|------|------|----------|----------|
| 1.1 | 동적 임계값 구현 | `EmbeddingSimilarityBoundaryFeature.score()` 수정 | 단위 테스트: 다양한 buffer_ratio에서 임계값 변화 확인 |
| 1.2 | n-gram 유사도 추가 | `_ngram_overlap()` 함수 + 결합 로직 | mock 데이터로 n-gram 계산 정확도 검증 |
| 1.3 | config.py에 상수 추가 | `EMBEDDING_NGRAM_ALPHA`, `DYNAMIC_THRESHOLD_SLOPE` 등 | import 테스트 |
| 1.4 | canary 재실행 | `scripts/shadow_boundary_delta.py`로 Axis 2 재측정 | Profile B가 25% 이상인지 확인 |

### Phase 2: Profile B corpus 재측정 (P0, 예상 소요: 1일)

| 단계 | 작업 | 세부 내용 |
|------|------|----------|
| 2.1 | Profile B 문서 식별 | `classify_document_profile()`으로 전체 corpus 분류 |
| 2.2 | canary 실행 | Profile B 전용으로 Axis 2 측정 |
| 2.3 | 결과 기록 | `docs/hierarchical-chunk-builder-improvement-design.md`에 반영 |

### Phase 3: Option C-1 적용 (P1, 예상 소요: 0.5일)

| 단계 | 작업 | 세부 내용 |
|------|------|----------|
| 3.1 | `score_boundary()` 수정 | Profile별 동적 임계값 적용 |
| 3.2 | 가중치 재조정 | config.py에서 Weight 상수 변경 |
| 3.3 | regression 테스트 | Profile A에 부정 영향 없는지 확인 |

### Phase 4: Option B 검토 (P2, 필요시)

- Phase 1~3 후 Axis 2가 여전히 부족할 경우만 진행
- 신규 feature 3개 구현 + registry 등록 + 테스트
- 예상 소요: 2~3일

### Phase 5: HQ/CUE 승인 → 프로덕션 전환

- PR 생성 + 리뷰 요청
- ADR 업데이트 (ADR-009 또는 Amendment)
- production chunker에 통합

---

## 5. 예상 리스크 및 완화 방안

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| 동적 임계값으로 Profile A 성능 저하 | Profile A Axis 2 감소 | 상한선 설정 (base의 1.3배), Profile A 별도 측정 |
| Embedding 호출 비용 증가 (n-gram 추가) | latency 증가 | n-gram은 lightweight, 영향 미미하다고 판단 |
| Option B feature overfitting | Profile B에만 과도하게 최적화 | 여러 문서에서 검증, generalization 확인 |
| 가중치 재조정 시 regression | 기존 feature 간 균형 깨짐 | shadow analysis로 전체 score distribution 재확인 |

---

## 6. CUE/HQ 승인 요청 사항

1. **Option A 동적 임계값 공식** `dynamic_threshold = base * (1.0 + buffer_ratio * DYNAMIC_THRESHOLD_SLOPE)`의 계수(`DYNAMIC_THRESHOLD_SLOPE=0.3`) 적정성
2. **상한선 계수** `DYNAMIC_THRESHOLD_CEILING_RATIO=1.3` 적정성
3. **n-gram 유사도 결합 비율** alpha=0.7의 적정성 (수정 불필요, 원안 유효)
4. **Profile B 전용 feature 추가 필요성** (Phase 4는 Option A/C 후 결정)
5. **프로덕션 전환 시기** (SPRINT34-D로 편입 가능 여부)

---

## 7. CUE 검토 코멘트 상세 — Option C-1 수정 방향

### 7.1 문제: `classify_document_profile()` 오용

`classify_document_profile()`(`core/hierarchical_chunk_builder.py:103`)은 **문서 전체 candidate 리스트의 median 길이**로 Profile A/B를 분류하도록 설계된 함수다. candidate 1개짜리 리스트를 넘기면 median이 해당 candidate 하나의 길이가 되어버려 문서 단위 분류라는 설계 의도와 어긋난다. 또한 `score_boundary()`는 candidate마다 호출되므로 이 함수를 boundary 판정 루프 안에서 매번 호출하는 것 자체가 잘못된 설계다.

### 7.2 수정 방향: profile을 build_chunks() 진입 시 1회만 계산

**수정 전 (잘못된 설계)**:
```python
# ❌ score_boundary() 안에서 매 candidate마다 classify_document_profile() 호출 — 금지
def score_boundary(context, registry=None) -> BoundaryEvent:
    from core.hierarchical_chunk_builder import classify_document_profile
    profile = classify_document_profile([(context.candidate_text, context.position)])  # 오용!
    ...
```

**수정 후 (올바른 설계)**:
```python
# ✅ build_chunks() 진입 시 문서 전체 candidates로 1회만 계산
def build_chunks(doc_candidates: List[Tuple[str, int]], chunk_size: int = ...) -> List[Chunk]:
    # 1. 문서 전체로 profile 1회 계산
    from core.hierarchical_chunk_builder import classify_document_profile
    doc_profile = classify_document_profile(doc_candidates)  # ← 1회만
    
    # 2. profile을 BoundaryContext에 전달할 수 있도록 context 확장
    #    방법 A: BoundaryContext에 profile 필드 추가
    #    방법 B: score_boundary()에 profile 파라미터 추가
    
    # --- 방법 A: BoundaryContext에 profile 필드 추가 ---
    # core/semantic_boundary_detector.py의 BoundaryContext에 추가:
    # @dataclass
    # class BoundaryContext:
    #     ...
    #     document_profile: str = "A"  # "A" 또는 "B", 기본값 A
    
    # --- 방법 B: score_boundary()에 파라미터로 전달 ---
    def score_boundary(context, registry=None, document_profile: str = "A") -> BoundaryEvent:
        reg = registry or get_registry()
        features = reg.score_all(context)
        total = sum(features.values())
        
        # Profile별 동적 임계값 (classify_document_profile() 호출 없음!)
        threshold = DEFAULT_THRESHOLD * 0.7 if document_profile == "B" else DEFAULT_THRESHOLD
        
        return BoundaryEvent(
            ...,
            is_boundary=total >= threshold,
        )
    
    # --- build_chunks() 내에서 사용 ---
    for candidate_text, position in doc_candidates:
        context = BoundaryContext(
            candidate_text=candidate_text,
            position=position,
            document_profile=doc_profile,  # ← 1회 계산 결과 전달
            ...
        )
        event = score_boundary(context, document_profile=doc_profile)
        ...
```

### 7.3 BoundaryContext 수정 예시 (방법 A 선택 시)

```python
# core/semantic_boundary_detector.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BoundaryContext:
    candidate_text: str
    position: int
    accumulated_length: int = 0
    previous_candidate_text: str = ""
    chunk_size: int = 300
    document_profile: str = "A"  # ← 추가: "A" 또는 "B"
    
    @property
    def is_boundary(self) -> bool:
        """이 candidate가 semantic boundary인지 여부 (score_boundary()에서 설정됨)"""
        return getattr(self, '_is_boundary', False)
```

### 7.4 score_boundary() 수정 예시 (방법 B 선택 시 — 권장)

```python
# core/semantic_boundary_detector.py
DEFAULT_THRESHOLD = 50.0
PROFILE_B_THRESHOLD = DEFAULT_THRESHOLD * 0.7  # 35.0

def score_boundary(context, registry=None, document_profile: str = "A") -> BoundaryEvent:
    reg = registry or get_registry()
    features = reg.score_all(context)
    total = sum(features.values())
    
    # Profile별 임계값 (classify_document_profile() 호출 없음!)
    threshold = PROFILE_B_THRESHOLD if document_profile == "B" else DEFAULT_THRESHOLD
    
    return BoundaryEvent(
        candidate_text=context.candidate_text,
        position=context.position,
        score=total,
        feature_scores=features,
        is_boundary=total >= threshold,  # ← profile별 임계값으로 판정
        document_profile=document_profile,
    )
```

### 7.5 build_chunks() 수정 예시

```python
# core/hierarchical_chunk_builder.py
def build_chunks(doc_candidates: List[Tuple[str, int]], chunk_size: int = 300) -> List[Chunk]:
    # 1. 문서 전체로 profile 1회 계산 (classify_document_profile 오용 금지!)
    doc_profile = classify_document_profile(doc_candidates)  # ← 1회만
    
    # 2. 버퍼 초기화
    buffer: List[str] = []
    accumulated_length = 0
    chunks = []
    
    # 3. candidate 순회 — score_boundary에 profile 전달
    for candidate_text, position in doc_candidates:
        context = BoundaryContext(
            candidate_text=candidate_text,
            position=position,
            accumulated_length=accumulated_length,
            previous_candidate_text=buffer[-1] if buffer else "",
            chunk_size=chunk_size,
        )
        
        # score_boundary에 document_profile 전달 (방법 B)
        event = score_boundary(context, document_profile=doc_profile)
        
        if event.is_boundary:
            chunks.append(Chunk(
                text="\n".join(buffer),
                profile=doc_profile,  # ← 문서 전체 profile 공유
                ...
            ))
            buffer = []
            accumulated_length = 0
        
        buffer.append(candidate_text)
        accumulated_length += len(candidate_text)
    
    # 4. 남은 버퍼 처리
    if buffer:
        chunks.append(Chunk(
            text="\n".join(buffer),
            profile=doc_profile,
            ...
        ))
    
    return chunks
```

### 7.6 Option C-1 반려 요약

| 항목 | 잘못된 설계 | 올바른 설계 |
|------|-----------|-----------|
| profile 계산 위치 | score_boundary() 내부 (매 candidate) | build_chunks() 진입 시 1회 |
| classify_document_profile 호출 | 매 candidate마다 | 문서 전체로 1회만 |
| 전달 방법 | candidate 1개 리스트 (오용) | document_profile 파라미터 |

---

## 8. Option A — 동적 임계값 계수 검증 계획 (v1.3 정정: 상향 방향)

| slope | alpha | 실측 Axis 2 (Profile B) | 비고 |
|-------|-------|------------------------|------|
| 0.2   | 0.7   | 21.8% (§8.1 축소 세트)  | 보수적 (상향), 목표 미달 |
| 0.25  | 0.7   | 미실행                  | 중간 (상향) — 전체 corpus 재검증 시 포함 |
| **0.3** | **0.7** | **21.0% (§8.1 축소 세트)** | **현재 기본값 (상향), 목표 미달** |
| 0.35  | 0.7   | 미실행                  | 공격적 (상향) — 전체 corpus 재검증 시 포함 |
| 0.4   | 0.7   | 20.3% (§8.1 축소 세트)  | 최공격적 (상향), 목표 미달 — slope 상승할수록 오히려 하락 |

**검증 방법**: `scripts/shadow_boundary_delta.py`로 각 조합 실행 → Profile B Axis 2 측정 → ≥25% 달성 시 확정

**참고**: alpha는 n-gram 결합 비율로, A-2 옵션에서 사용. 현재는 slope 검증이 우선이므로 alpha=0.7 고정.

**갱신 (2026-07-28)**: 위 실측값은 §8.1의 대표 문서 2개(Profile A/B 각 1개) 축소 세트 결과다 — slope를 올릴수록 Axis 2가 오히려 하락하는 반직관적 결과가 나와, 전체 corpus 기준 alpha 스윕/0.25·0.35 실행은 HQ 판단 전까지 보류한다. 상세는 §8.1 참고.

---

## 8.1 CUE 실측 결과 — Phase 1.4 canary (축소 세트, 2026-07-28)

**범위 축소 사유**: `scripts/shadow_d5_metrics.py` 전체 12개 문서 실행이 문서당 수백~수천 회 Ollama(bge-m3) 임베딩 호출로 36분+ 걸려도 미완료 — 사용자 지시로 대표 문서 2개(Profile B 최소 candidate 문서 1개, Profile A 최소 candidate 문서 1개)만으로 축소해 재실행. RAW(`data/beta_corpus/`)의 나머지 10개 PDF는 이번 실험에서 파싱하지 않음. alpha=0.7 고정, slope만 스윕(3분22초 완료).

| slope | Profile A Axis 2 | Profile B Axis 2 |
|-------|------|------|
| 0.2 | 13.7% (44/321) | 21.8% (185/848) |
| 0.3 (현재 기본값) | 13.2% (45/341) | 21.0% (181/860) |
| 0.4 | 12.4% (45/362) | 20.3% (177/870) |

**핵심 관찰 — 예상과 반대 방향**: slope를 올릴수록(threshold를 더 관대하게 만들수록) Axis 2가 Profile A/B 둘 다 **하락**한다. 방향 오류를 고친 공식(threshold 상향)은 개별 embedding feature 신호는 실제로 늘리지만(총 shadow chunk 수 848→870 증가, 더 자주 flush), 그로 인해 버퍼가 빨리 비워지면서 `accumulated_length`가 safety_cap에 도달할 기회 자체가 줄어 dynamic threshold 상향 효과가 자기 상쇄되는 것으로 추정. 늘어난 flush 중 다수가 `_boundary_offsets()`의 heading cursor 정합과 어긋나 "semantic 확인"으로 집계되지 않는 것으로 보인다(원인 미확정, 추가 조사 필요).

**결론**: 이 축소 세트에서는 slope 0.2~0.4 전 구간 Profile B가 20~22%로 **목표(≥25%) 미달**. Option A(임계값 조정)만으로는 이 문서 세트 기준 부족할 가능성 — Option C-1(Profile별 DEFAULT_THRESHOLD 조정) 또는 Option B 병행 필요성 재검토 대상. 대표성 낮은 2개 문서 결과이므로 확정적 결론은 아니며, 전체 corpus 재검증 및 alpha 스윕은 보류 상태(HQ 판단 대기).

---

## 9. 다음 단계

- CUE/HQ 승인 시: Act mode에서 구현 착수
- 추가 질문/수정 요청 시: 본 문서 수정 후 재제출

---

## 참조 문서

- `docs/PREFLIGHT-hierarchical-chunk-builder-canary-2026-07-27.md` — canary 실측 결과
- `core/hierarchical_chunk_builder.py` — Hierarchical Chunk Builder 프로토타입
- `core/semantic_boundary_detector.py` — Boundary Score 모델
- `docs/architecture/ADR-007-Semantic-Boundary-Detector.md` — ADR-007
- `docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md` — ADR-008
- `docs/agents/c1/C1-TASK-ORDER-016.md` — CUE 작업 명령서

---

## 11. Option C-1 구현·실측·반증·되돌림 — 2026-07-28

Task Order 016에서 Option C-1(§7 방법 B: `score_boundary()`에 `document_profile` 파라미터 추가, Profile B는 `PROFILE_B_THRESHOLD = DEFAULT_THRESHOLD * 0.7`(35.0) 적용)을 승인·구현(커밋 `9b9291f`)하고 단위 테스트(커밋 `ade22c5`, 66/66 pass)까지 마쳤다. 이후 축소 세트 canary(Profile A: "12. 고린도후서" 783 candidates / Profile B: "2 Kings The Anchor Bible Commentary" 947 candidates)로 실측한 결과 **Profile B Axis 2가 99.3%(1088/1096)로 튀었다** — 목표(≥25%) 초과 달성이 아니라 지표 자체가 무의미해지는 퇴화(degenerate) 현상이었다.

**원인 — feature 점수 분포의 이중봉(bimodal) 구조**: 이 문서의 candidate 947개에 대해 `score_boundary()`의 `total_score` 분포를 직접 뽑아보면:
- 중앙값 = 40.0, 상위 90%까지도 40.0 (즉 대부분 candidate가 정확히 40점에 몰려있음 — heading 없는 평범한 문단이 `paragraph(+30) + sentence_boundary(+10) = 40`으로 끝나는 경우가 압도적 다수)
- `total_score >= 35` 비율: 95.4%
- `total_score >= 40` 비율: 95.4% (35~40 구간엔 사실상 아무도 없음)
- `total_score >= 45` 비율: 1.9%로 급락 (scripture_reference/heading 등 추가 신호가 드물게만 붙음)

즉 30~40 사이 어떤 정적 threshold를 잡아도 이 분포의 "40점 평원(plateau)"을 건드려 **거의 모든 candidate가 boundary로 판정**된다. `PROFILE_B_THRESHOLD=35.0`은 정확히 이 평원 아래에 있어 95.4%를 통째로 boundary로 만들었다 — 의미 경계를 더 잘 찾은 게 아니라 판정 기준 자체가 무너진 것이다. 41~49 구간은 반대로 40점 평원 위라 원래 threshold(50.0)와 사실상 다르지 않아 실질 개선 효과가 없다. 즉 **이 feature 조합·이 문서 특성상 정적 threshold 튜닝만으로 25%와 99.3% 사이의 중간 지점을 잡을 수 있는 값 자체가 존재하지 않는다.**

(측정 과정에서 별도로 발견한 버그: `scripts/shadow_d5_metrics.py::_boundary_offsets()`가 `document_profile`을 `score_boundary()`에 넘기지 않아 항상 `DEFAULT_THRESHOLD`로 "정답" 경계를 판정하던 것도 처음엔 반대 방향의 오차를 냈다 — 이를 먼저 고쳐 공정하게 재측정한 뒤 위 99.3% 결과를 확인했다. 이 스크립트 수정은 Option C-1 자체가 되돌려지면서 함께 원복했다.)

**조치**: Option C-1 관련 코드(`core/semantic_boundary_detector.py`/`core/hierarchical_chunk_builder.py`의 `document_profile`/`PROFILE_B_THRESHOLD` 전체, 관련 단위 테스트)를 커밋 `ddea706`으로 되돌리고, 되돌린 상태에서 canary를 재실행해 원래 baseline(Profile A 13.2%, Profile B 21.0%)과 정확히 일치함을 확인했다.

**결론**: Option C-1(profile별 정적 전체-threshold 조정)은 이 데이터셋에서 기각한다. Axis 2 개선이 계속 필요하다면 다음 두 방향이 남는다:
- Option B(신규 feature: ParagraphTopicDrift/AcademicStructure/BufferLengthNormalization) — 이번 분석이 보여준 "구조 기반 feature가 40점 평원에 묶여 있다"는 문제를 정적 threshold가 아니라 새로운 신호로 풀자는 방향이라 여전히 유효한 후보
- Option A(동적 embedding threshold)의 계수를 이 bimodal 분포를 고려해 재설계 — 다만 §8.1에서 이미 slope 스윕이 반직관적으로 움직였으므로 신중한 접근 필요

이 둘 다 이번 Task Order 016 범위 밖 — 진행하려면 별도 제안·승인 필요.

---

## 12. Option B 사전 검토 — 코드 작성 전 반려/재설계 요청 (2026-07-29)

Option C-1 종료 후 Option B(§3 B-1/B-2/B-3) 구현을 검토했다. **코드 작성 전** 세 feature 각각을 점검한 결과, B-2/B-3에서 Option C-1과 같은 종류의 문제(Profile B의 장르적 특성 자체가 신호로 오인되는 것, 지표 정의의 순환성)가 재발할 위험이 확인됐다.

**실측 — B-2 AcademicStructureFeature 베이스레이트** (§3 B-2 정규식 패턴을 §9의 두 문서 candidate에 그대로 적용, 구현 없이 패턴 매칭만 재현):

| 문서 | 매칭 candidate 비율 |
|---|---|
| Profile A (12. 고린도후서) | 0.0% |
| Profile B (2 Kings Anchor Bible Commentary) | **42.7%** (404/947) |

Profile B를 정의하는 바로 그 특성(성경 구절 인용·cf. 참조 밀도)이 이 feature의 발화 조건과 겹친다 — Option C-1에서 "40점 평원" 후보들에 이 정도 베이스레이트(+25 weight)가 더해지면 다수가 threshold(50)를 넘어서는 유사한 과다-트리거 위험이 있다. 또한 기존 `ScriptureReferenceBoundaryFeature`(+30, 이미 registry 등록)와 목적이 겹쳐 사실상 유사 기능 중복.

**코드 검토(실행 없이 정적 분석)**:
- **B-1 ParagraphTopicDriftFeature**: `previous_candidate_text[:200]` vs 현재 candidate의 마지막 줄 1개만 비교 — 기존 `EmbeddingSimilarityBoundaryFeature`와 개념적으로 겹쳐 독립 신호인지 불분명. `1.0 - similarity` 연속값을 반환해 다른 feature 대부분의 "신호 없음=0.0" 이진 계약과 다르게 항상 어느 정도 기여함 — weight(+40) 곱해진 실제 영향을 예측하기 어려움. `last_line` 하나가 페이지 아티팩트일 경우 노이즈 취약.
- **B-3 BufferLengthNormalizationFeature**: **가장 심각** — 순수 `accumulated_length`만으로 신호를 낸다. 이 feature가 registry에 들어가면 Axis 2("flush 지점이 score_boundary()의 boundary 판정과 일치하는가")의 정의 자체에 "버퍼가 다 찼다"가 포함돼버려, 원래는 순수 safety-cap flush였을 것을 "semantic"으로 자동 인정하는 **순환 논리**가 된다 — 실제 청킹 품질 개선과 무관하게 지표만 부풀어 오른다.
- **가중치**(+40/+25/+15): Option A/C-1과 동일하게 근거 없는 임의값.

**지시(C1에 전달, 코드 작성 전 재설계 요청)**:
1. B-3(BufferLengthNormalizationFeature)은 방법론적으로 순환적이므로 **제외**
2. B-2(AcademicStructureFeature)는 가중치를 대폭 낮추거나, 기존 `ScriptureReferenceBoundaryFeature`와 통합하는 방향으로 재설계 — 42.7% 베이스레이트를 고려해 조정
3. B-1(ParagraphTopicDriftFeature)은 코드 구현 전에 Ollama 호출 없이(또는 최소 호출로) `EmbeddingSimilarityBoundaryFeature`와의 상관관계부터 확인해, 독립적인 신호인지 검증
4. 이 순서(제외 → 재설계 → 검증)로 다시 설계 문서를 제출한 뒤에만 코드 구현 승인을 요청할 것 — 지금 이 설계 그대로 구현 착수는 승인하지 않는다.

---

**문서 작성일**: 2026-07-29
**문서 버전**: v1.5 (Option B 사전 검토 — 코드 작성 전 재설계 요청 추가)
**상태**: Option A dormant/미달, Option C-1 기각·되돌림 완료(커밋 `ddea706`), Option B는 재설계 요청 상태(B-3 제외/B-2 재설계/B-1 검증 필요) — 재설계본 제출 전까지 구현 승인 보류

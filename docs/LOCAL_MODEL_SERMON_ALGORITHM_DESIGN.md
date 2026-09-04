# 로컬 모델을 활용한 설교문 제작: 고급 알고리즘 설계

## 1. 개요

DBMA 프로젝트는 이미 `core/generation.py`에 Ollama 기반 로컬 LLM을 활용한 설교문 작성 워크플로를 구현하고 있습니다. 본 문서는 이 시스템을 위한 **고급 알고리즘 설계**를 제시합니다.

### 1.1 현재 시스템 아키텍처

```
사용자 질문
    ↓
RetrievalEngine (BM25 + 벡터 검색)
    ↓
ResponsePackage (검색 결과 + 컨텍스트)
    ↓
GenerationService / SermonDraftService
    ↓
Ollama 로컬 모델 (llama3, mistral, etc.)
    ↓
설교 개요 → 대지 확장 → 완성본
```

### 1.2 핵심 구성 요소

| 구성 요소 | 책임 |
|-----------|------|
| `RetrievalEngine` | 메타데이터 필터링, BM25/벡터 스코어링, 문맥 조립 |
| `GenerationService` | 단발 Q&A 응답 생성 |
| `SermonDraftService` | 다단계 설교 작성 (개요 → 대지 확장) |
| `_format_sermon_context()` | [자료N] 라벨 기반 인용 컨텍스트 포맷팅 |

---

## 2. 로컬 모델 기반 설교문 제작: 고급 알고리즘

### 2.1 RAG-Enhanced Sermon Generation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Sermon Input Layer                        │
│  (본문 선택 / 주제 지정 / 대상자 / 설교 형식)               │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 1: Contextual Enrichment                  │
│                                                              │
│  1.1 Scripture Passage Extraction                            │
│      - 본문 구절 범위 파싱 (예: 로마서 8:1-17)              │
│      - 원어 텍스트 매핑 (그리스어/히브리어)                  │
│                                                              │
│  1.2 Multi-Source Context Assembly                           │
│      - TSU 코퍼스에서 관련 주석 검색                          │
│      - 설교문 아카이브에서 유사 주제 검색                     │
│      - 원어 사전/개념 분석 결과                              │
│      - 역사적·문화적 배경 자료                               │
│                                                              │
│  1.3 Context Relevance Scoring                               │
│      - 각 컨텍스트 청크에 대한 관련성 스코어링              │
│      - BM25 + 임베딩 기반 하이브리드 스코어                 │
│      - 신학적 적합성 가중치 (doc_type별)                     │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: Sermon Architecture Generation         │
│                                                              │
│  2.1 Outline Planner (LLM)                                   │
│      - 입력: 본문 + 강화된 컨텍스트                          │
│      - 출력: 설교 개요 (제목/서론/N개 대지/결론)             │
│      - 알고리즘:                                              │
│        a) 컨텍스트에서 핵심 신학적 주제 추출                   │
│        b) 주제 간 논리적 관계 매핑                            │
│        c) 설교 형식별 구조 적용 (주제/강해)                  │
│        d) 품질 검증: 본문 재진술 방지, 자료 인용 확인       │
│                                                              │
│  2.2 Theological Coherence Check                             │
│      - 개요 단계에서 신학적 일관성 검증                       │
│      - 교리적 충돌 감지 (예: 은혜 vs 행위 균형)             │
│      - 본문 맥락과의 정합성 확인                              │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 3: Point-by-Point Expansion               │
│                                                              │
│  3.1 Per-Point Expansion Engine                              │
│      - 각 대지를 문단 단위로 확장                             │
│      - 알고리즘:                                              │
│        a) 대지의 핵심 주장 추출                                │
│        b) 관련 [자료N] 식별 및 인용 위치 결정                │
│        c) 원어 분석 결과 반영                                 │
│        d) 역사적/문화적 맥락 설명 추가                       │
│        e) 목회적 적용 문단 생성                               │
│                                                              │
│  3.2 Style Transfer (선택사항)                               │
│      - 설교자의 과거 설교문에서 어투 학습                     │
│      - 스타일 예시 기반 Few-shot prompting                  │
│      - 어휘 수준/문장 길이/수사적 장치 일치                  │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Phase 4: Quality Assurance & Refinement         │
│                                                              │
│  4.1 Internal Consistency Check                              │
│      - 전체 설교의 논리적 흐름 검증                          │
│      - 대지 간 전이 자연스러움 확인                           │
│      - 서론/결론과 본문 일치도 확인                          │
│                                                              │
│  4.2 External Reference Validation                           │
│      - [자료N] 인용의 정확성 검증                             │
│      - 출처 왜곡 방지 체크                                  │
│                                                              │
│  4.3 Theological Guardrails                                  │
│      - 교리적 편향 감지                                      │
│      - 본문의 원저자 의도와의 정합성                         │
│                                                              │
│  4.4 Iterative Refinement (선택사항)                        │
│      - 사용자 피드백 기반 반복 수정                         │
│      - LLM-as-Judge 품질 평가                               │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Final Sermon Output                       │
│  (Markdown/HTML/PDF 형식 출력, 메타데이터 포함)              │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.3 핵심 알고리즘 상세

#### Algorithm 1: Contextual Enrichment with Theological Weighting

```python
def enrich_context(
    scripture: str,
    candidates: list[RankedCandidate],
    doc_type_weights: dict[str, float] | None = None
) -> list[RankedCandidate]:
    """
    검색된 컨텍스트에 신학적 가중치를 적용하여 정교화.
    
    Args:
        scripture: 본문 구절 정보
        candidates: RetrievalEngine에서 반환된 검색 결과
        doc_type_weights: doc_type별 가중치 (예: 주석=2.0, 설교=1.2, 논문=1.5)
    
    Returns:
        재스코어링된 RankedCandidate 목록
    """
    if doc_type_weights is None:
        doc_type_weights = {"주석": 2.0, "논문": 1.5, "설교": 1.2, "사전": 1.8}
    
    enriched = []
    for candidate in candidates:
        # 원본 스코어
        base_score = candidate.score
        
        # doc_type 가중치 적용
        doc_type = candidate.metadata.get("doc_type", "기타")
        type_weight = doc_type_weights.get(doc_type, 1.0)
        
        # 본문 관련성 보너스
        scripture_bonus = _compute_scripture_relevance(
            scripture, candidate.metadata
        )
        
        # 최종 스코어
        final_score = base_score * type_weight + scripture_bonus
        candidate.score = final_score
        enriched.append(candidate)
    
    return sorted(enriched, key=lambda x: x.score, reverse=True)
```

#### Algorithm 2: Sermon Outline Generation with Quality Gates

```python
def generate_sermon_outline_with_gates(
    scripture_and_theme: str,
    enriched_context: list[RankedCandidate],
    sermon_format: str = "주제설교",
    model: str = "llama3"
) -> tuple[SermonOutline, dict[str, bool]]:
    """
    품질 검증 게이트가 있는 설교 개요 생성.
    
    Returns:
        (outline, quality_gates) - quality_gates는 각 게이트 통과 여부
    """
    # Step 1: 컨텍스트 포맷팅 (출처 라벨 포함)
    context_block = format_sermon_context_with_labels(enriched_context)
    
    # Step 2: 프롬프트 조립
    prompt = build_outline_prompt(
        scripture_and_theme=context_and_theme,
        context=context_block,
        format=sermon_format,
        quality_directives=_QUALITY_DIRECTIVES
    )
    
    # Step 3: LLM 호출
    raw_response = ollama.generate(model=model, prompt=prompt)
    outline = parse_outline(raw_response)
    
    # Step 4: 품질 게이트 검증
    quality_gates = {
        "no_text_repetition": check_no_text_repetition(outline, scripture),
        "has_citations": check_has_citations(outline, enriched_context),
        "theological_coherence": check_theological_coherence(outline),
        "structure_valid": validate_structure(outline, sermon_format),
    }
    
    # Step 5: 게이트 실패 시 재시도
    if not all(quality_gates.values()):
        failed_gates = [k for k, v in quality_gates.items() if not v]
        outline = retry_with_feedback(outline, failed_gates, model)
    
    return outline, quality_gates
```

#### Algorithm 3: Point Expansion with Source Attribution

```python
def expand_point_with_attribution(
    point_text: str,
    scripture_and_theme: str,
    relevant_sources: list[RankedCandidate],
    style_examples: str = "",
    sermon_format: str = "주제설교",
    model: str = "llama3"
) -> tuple[str, list[int]]:
    """
    대지 확장이면서 출처 인용을 보장하는 알고리즘.
    
    Returns:
        (expanded_text, cited_source_indices)
    """
    # 관련 자료 중 상위 K개만 선택 (컨텍스트 제한)
    top_sources = relevant_sources[:10]
    
    # 각 자료의 인용 가능 위치 식별
    source_attribution = []
    for i, src in enumerate(top_sources):
        key_insights = extract_key_insights(src.content)
        source_attribution.append({
            "index": i,
            "label": f"[자료{i+1}]",
            "title": src.metadata.get("title"),
            "key_insights": key_insights[:3]  # 최대 3개 인사이트
        })
    
    # 프롬프트에 구체적 인용 지시 포함
    prompt = build_expansion_prompt(
        point=point_text,
        scripture=scritpure_and_theme,
        sources=source_attribution,
        style_examples=style_examples,
        format=sermon_format,
        citation_requirements=_build_citation_requirements(source_attribution)
    )
    
    # LLM 호출
    response = ollama.generate(model=model, prompt=prompt)
    
    # 인용 검증 및 보정
    expanded_text, cited_indices = validate_and_correct_citations(
        response, source_attribution
    )
    
    return expanded_text, cited_indices
```

#### Algorithm 4: Style Transfer for Personalized Sermons

```python
def apply_sermon_style_transfer(
    sermon_text: str,
    preacher_historical_sermons: list[str],
    model: str = "llama3"
) -> str:
    """
    설교자의 과거 설교문 스타일을 학습하여 현재 설교문에 적용.
    
    Args:
        sermon_text: 현재 생성된 설교문
        preacher_historical_sermons: 설교자의 과거 설교문 컬렉션
    
    Returns:
        스타일이 적용된 설교문
    """
    # 스타일 특징 추출
    style_features = extract_style_features(preacher_historical_sermons)
    
    # 스타일 프롬프트 구성
    style_prompt = build_style_transfer_prompt(
        target_text=sermon_text,
        style_features=style_features,
        instructions=[
            "문장 길이 분포 일치 (평균 X어, 표준편차 Y)",
            "어휘 수준 일치 (고어 비율 Z%)",
            "수사적 장치 패턴 일치 (비유, 질문, 인용 빈도)",
            "문체 톤 일치 (공식적/친근한 비율)"
        ]
    )
    
    # 스타일 적용
    styled_text = ollama.generate(model=model, prompt=style_prompt)
    
    return styled_text
```

---

## 3. 로컬 모델 선택 가이드

### 3.1 추천 모델 비교

| 모델 | 파라미터 | 강점 | 설교 생성 적합도 |
|------|----------|------|-----------------|
| **llama3** | 8B | 균형잡힌 성능, 다국어 | ★★★★☆ |
| **mistral-nemo** | 12B | 긴 컨텍스트, 구조화 | ★★★★★ |
| **codellama** | 7B | 코드/구조화 텍스트 | ★★★☆☆ |
| **phi-3-mini** | 3.8B | 경량, 빠른 응답 | ★★★☆☆ |
| **qwen2.5** | 7B | 중국어/한국어 개선 | ★★★★☆ |

### 3.2 모델 선택 기준

```python
MODEL_RECOMMENDATIONS = {
    "high_quality": {
        "model": "mistral-nemo:12b",
        "reason": "긴 컨텍스트 처리能力强, 신학적 텍스트에 적합",
        "min_ram_gb": 16,
        "estimated_latency_ms": 2000
    },
    "balanced": {
        "model": "llama3:8b",
        "reason": "성능/속도 균형, 다국어 지원 우수",
        "min_ram_gb": 8,
        "estimated_latency_ms": 1500
    },
    "fast_response": {
        "model": "phi-3-mini:3.8b",
        "reason": "빠른 응답이 우선일 때",
        "min_ram_gb": 4,
        "estimated_latency_ms": 800
    }
}
```

---

## 4. 프롬프트 엔지니어링 전략

### 4.1 시스템 프롬프트 설계

```python
SYSTEM_PROMPT = """당신은 신학적으로 엄격한 설교문 작성 전문가입니다.

규칙:
1. 항상 성경 본문을 최우선 근거로 사용하라.
2. 참고 자료는 [자료N] 형식으로 인용하라.
3. 상투적인 표현은 피하고 구체적인 내용을 제시하라.
4. 한국어로만 작성하라.
5. 신학적 논쟁이 있는 주제는 균형있게 서술하라.
6. 본문을 단순히 재진술하지 말고 신학적 통찰을 추가하라."""
```

### 4.2 컨텍스트 압축 전략

로컬 모델은 컨텍스트 제한이 있으므로, 효율적인 압축이 필수입니다.

```python
def compress_context_for_model(
    candidates: list[RankedCandidate],
    max_tokens: int = 8000,
    model: str = "llama3"
) -> str:
    """
    검색 결과를 모델 컨텍스트 제한에 맞게 압축.
    
    전략:
    1. 상위 K개 청크 전체 유지
    2. 하위 청크는 요약본 사용
    3. 출처 라벨은 유지 (인용 검증용)
    """
    compressed = []
    token_count = 0
    
    for i, candidate in enumerate(candidates):
        # 상위 5개는 전체 내용
        if i < 5:
            content = candidate.content
        else:
            # 하위는 요약본 (비율 압축)
            content = summarize_text(candidate.content, ratio=0.3)
        
        label = f"[자료{i+1}] {candidate.metadata.get('title', '미상')}"
        entry = f"{label}\n{content}"
        
        estimated_tokens = len(entry) // 2  # 한국어 기준 근사치
        if token_count + estimated_tokens > max_tokens:
            break
        
        compressed.append(entry)
        token_count += estimated_tokens
    
    return "\n\n".join(compressed)
```

### 4.3 다단계 프롬프트 체인

단일 프롬프트 대신 단계를 나누어 품질을 향상시킵니다.

```
단계 1: 주제 추출 (컨텍스트 → 신학적 주제 목록)
   ↓
단계 2: 개요 생성 (주제 + 본문 → 설교 개요)
   ↓
단계 3: 대지별 확장 (개요 + 자료 → 설교문 문단)
   ↓
단계 4: 일관성 검증 및 보정
```

---

## 5. 품질 보장 메커니즘

### 5.1 자동 품질 게이트

```python
QUALITY_GATES = {
    "theological": {
        "description": "신학적 일관성",
        "check": lambda outline: check_theological_coherence(outline),
        "severity": "critical"
    },
    "citation": {
        "description": "출처 인용 정확성",
        "check": lambda outline: verify_citations(outline),
        "severity": "warning"
    },
    "structure": {
        "description": "구조 유효성",
        "check": lambda outline: validate_structure(outline),
        "severity": "critical"
    },
    "originality": {
        "description": "원작성 (재진술 방지)",
        "check": lambda outline: check_no_text_repetition(outline),
        "severity": "warning"
    }
}
```

### 5.2 LLM-as-Judge 평가

```python
def evaluate_sermon_quality(
    sermon: str,
    scripture: str,
    model: str = "llama3"
) -> dict[str, float]:
    """LLM을 심사관으로 사용하여 설교문 품질 평가."""
    
    judge_prompt = f"""
다음 설교문을 평가하라. 1-5 점 척도로 평가하라.

평가 항목:
1. 신학적 정확성 (본문에 기반했는가)
2. 논리적 일관성 (서론-본문-결론의 흐름)
3. 목회적 유용성 (현장 적용 가능성)
4. 원작성 (상투성 탈파)
5. 인용 적절성 (참고 자료 활용도)

설교문:
{sermon}

본문:
{scripture}

JSON 형식으로 점수만 반환하라."""

    result = ollama.generate(model=model, prompt=judge_prompt)
    return parse_evaluation_result(result)
```

---

## 6. 성능 최적화 전략

### 6.1 청크 재사용 캐싱

```python
# 동일한 본문/주제에 대한 반복 생성 시 컨텍스트 재계산 방지
CONTEXT_CACHE = {}

def get_enriched_context(scripture: str, theme: str) -> list[RankedCandidate]:
    cache_key = f"{scripture}:{theme}"
    if cache_key in CONTEXT_CACHE:
        return CONTEXT_CACHE[cache_key]
    
    # 검색 및 정교화
    context = compute_enriched_context(scripture, theme)
    
    # TTL 1시간 캐시
    CONTEXT_CACHE[cache_key] = context
    return context
```

### 6.2 병렬 대지 확장

```python
from concurrent.futures import ThreadPoolExecutor

def expand_all_points_parallel(
    outline: SermonOutline,
    candidates: list[RankedCandidate],
    max_workers: int = 4
) -> dict[str, str]:
    """대지별 확장을 병렬로 수행."""
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, point in enumerate(outline.points, 1):
            future = executor.submit(
                expand_point_with_attribution,
                point_text=point,
                scripture_and_theme=f"{outline.title}",
                candidates=candidates
            )
            futures[future] = f"대지{i}"
        
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()
    
    return results
```

### 6.3 모델 양자화 (Quantization)

```
GGUF 형식 양자화 권장:

모델          | FP16     | Q4_K_M   | Q3_K_S
--------------|----------|----------|--------
llama3 8B     | 16GB     | 4.9GB    | 3.7GB
mistral 7B    | 14GB     | 4.4GB    | 3.3GB

Q4_K_M이 품질/용량 균형 권장
```

---

## 7. 구현 로드맵

### 7.1 우선순위 높은 개선사항

| 우선순위 | 개선사항 | 예상 효과 | 복잡도 |
|----------|----------|-----------|--------|
| P0 | 컨텍스트 압축 알고리즘 | 응답 품질 ↑ | 낮음 |
| P0 | 품질 게이트 구현 | 오류 감소 | 중간 |
| P1 | 신학적 가중치 스코어링 | 관련성 ↑ | 중간 |
| P1 | LLM-as-Judge 평가 | 품질 관리 | 중간 |
| P2 | 스타일 전송 | 개인화 | 높음 |
| P2 | 병렬 확장 | 속도 ↑ | 낮음 |

### 7.2 예상 아키텍처 변경

```
현재:
  Query → Retrieval → Generate (단일 단계)

개선 후:
  Query → Retrieval → Enrich → Quality Gate → 
  Outline → Quality Gate → Expand (병렬) → 
  Evaluate → Refine (선택) → Output
```

---

---

## 7. 기성 플랫폼의 검증된 알고리즘 기법

### B1. Multi-Step Reasoning Chain (Cursor/Claude Code 방식)

**기성 플랫폼의 접근:**
- Cursor는 `plan → code → verify`의 3단계 체인 사용
- Claude Code는 `think → act → reflect` 사이클 사용
- 단일 프롬프트가 아닌, **단계별 출력물을 다음 단계의 입력**으로 사용

**DBMA 적용:**
```
현재: Query → Retrieval → Generate (단일 단계)

개선:
Step 1: Intent Analysis
  입력: 사용자 질문
  출력: {intent_type, required_sources, scripture_scope}
  
Step 2: Targeted Retrieval  
  입력: intent_type + scripture_scope
  출력: 의도별 최적화 검색 결과
  
Step 3: Context Synthesis
  입력: 검색 결과 + intent_type
  출력: 설교에 특화된 압축 컨텍스트
  
Step 4: Outline Generation
  입력: 압축 컨텍스트
  출력: 설교 개요
  
Step 5: Point Expansion (병렬)
  입력: 개요 + 컨텍스트
  출력: 각 대지 확장본
  
Step 6: Quality Evaluation
  입력: 완성 설교
  출력: 품질 점수 + 개선사항 (있으면 Step 4로 피드백)
```

---

### B2. Hybrid Search with Re-Ranking (Copilot 방식)

**기성 플랫폼의 접근:**
- GitHub Copilot은 BM25 + 임베딩 + 코드 구조 분석의 하이브리드 검색
- 초기 검색으로 넓은 범위 수집 → re-ranker로 정밀 재스코어링

**DBMA 적용:**
```python
def hybrid_sermon_search(query: str, scripture: str) -> list[RankedCandidate]:
    """2단계 검색: wide recall → precise reranking"""
    
    # Step 1: Wide Recall (BM25 + 임베딩)
    bm25_results = bm25_search(query, tsu_corpus, top_k=50)
    vector_results = vector_search(query, tsu_embeddings, top_k=50)
    
    # Reciprocal Rank Fusion으로 결합
    fused = reciprocal_rank_fusion(bm25_results, vector_results, k=60)
    
    # Step 2: Re-ranking (신학적 적합성 기반)
    reranked = []
    for candidate in fused[:30]:
        score = candidate.score
        
        # 신학적 가중치
        if candidate.doc_type == "주석":
            score *= 1.5
        elif candidate.doc_type == "설교":
            score *= 1.1
            
        # 본문 일치 보너스
        if scripture_matches(candidate, scripture):
            score *= 1.3
            
        # 최신성 보너스 (고전신학은 감산)
        year = candidate.metadata.get("year", 2000)
        if year > 2000:
            score *= 1.05
        elif year < 1900 and candidate.doc_type == "고전신학":
            score *= 1.2  # 오리지널리티 보너스
            
        candidate.score = score
        reranked.append(candidate)
    
    return sorted(reranked, key=lambda x: x.score, reverse=True)[:15]


def reciprocal_rank_fusion(
    results_a: list, 
    results_b: list, 
    k: int = 60
) -> list:
    """RRF 알고리즘으로 두 검색 결과 결합."""
    scores = defaultdict(float)
    for i, doc in enumerate(results_a):
        scores[doc.id] += 1 / (k + i + 1)
    for i, doc in enumerate(results_b):
        scores[doc.id] += 1 / (k + i + 1)
    
    return sorted(
        [doc for doc in results_a + results_b if doc.id in scores],
        key=lambda x: scores[x.id],
        reverse=True
    )
```

---

### B3. Context Window Management (ChatGPT/Claude 방식)

**기성 플랫폼의 접근:**
- 컨텍스트가 길어지면 **요약 → 압축 → 트리밍** 자동 수행
- 중요도 기반 청크 우선순위: system > user_recent > user_early > assistant

**DBMA 적용:**
```python
def manage_context_window(
    candidates: list[RankedCandidate],
    max_tokens: int,
    scripture: str
) -> ContextPackage:
    """컨텍스트 윈도우 관리 알고리즘."""
    
    # 중요도 점수 매기기
    scored = []
    for c in candidates:
        priority = 0
        
        # 본문 직접 인용 > 본문 간접 참조 > 일반 신학
        if scripture in c.metadata.get("related_scriptures", []):
            priority += 3
        if "주석" in c.doc_type:
            priority += 2
        if "논문" in c.doc_type:
            priority += 1
            
        scored.append((c, priority))
    
    # 중요도 순으로 컨텍스트 조립
    context = []
    tokens_used = 0
    
    for candidate, priority in sorted(scored, key=lambda x: x[1], reverse=True):
        entry_tokens = estimate_tokens(candidate.content)
        
        if tokens_used + entry_tokens <= max_tokens:
            context.append(candidate)
            tokens_used += entry_tokens
        elif priority >= 2:
            # 고우선순위 자료는 요약하여 포함
            summary = summarize(candidate.content, ratio=0.3)
            summary_tokens = estimate_tokens(summary)
            if tokens_used + summary_tokens <= max_tokens:
                context.append(Candidate(content=summary, priority=priority))
                tokens_used += summary_tokens
            break
    
    return ContextPackage(context=context, tokens_used=tokens_used)
```

---

### B4. Self-Correction Loop (Claude Code 방식)

**기성 플랫폼의 접근:**
- Claude Code는 실패 시 자동으로 원인 분석 → 전략 수정 → 재시도
- 최대 3회 재시도 후 인간에게 폴백

**DBMA 적용:**
```python
def generate_with_self_correction(
    scripture: str,
    theme: str,
    max_retries: int = 3
) -> SermonResult:
    """품질 게이트 실패 시 자동 재시도."""
    
    last_result = None
    for attempt in range(max_retries):
        # 생성
        result = generate_sermon(scripture, theme)
        
        # 품질 검증
        gates = evaluate_quality(result)
        
        if all(gate.passed for gate in gates):
            return result  # 모든 게이트 통과
        
        last_result = result
        
        # 실패한 게이트 분석 → 프롬프트 수정
        failed_gates = [g for g in gates if not g.passed]
        prompt_adjustment = build_failure_feedback(failed_gates)
        
        # 재시도 시 수정된 프롬프트 사용
        theme += f"\n[피드백 {attempt+1}] {prompt_adjustment}"
    
    # 최대 재시도 초과 → 경고와 함께 반환
    return SermonResult(
        text=last_result.text,
        warnings=["최대 재시도 횟수 초과. 수동 검수가 필요합니다."]
    )
```

---

## 8. 구현 우선순위

### 기성 플랫폼 기법 적용 순서

| 순위 | 기법 | 출처 | DBMA 적합도 |
|------|------|------|------------|
| 1 | B2 Hybrid Search + Re-ranking | Copilot | ★★★★★ |
| 2 | B3 Context Window Management | ChatGPT | ★★★★★ |
| 3 | B1 Multi-Step Chain | Claude Code | ★★★★☆ |
| 4 | B4 Self-Correction Loop | Claude Code | ★★★★☆ |

---

## 9. 결론

로컬 모델을 활용한 설교문 제작의 핵심 알고리즘은 다음 4가지 축으로 구성됩니다:

1. **정교한 컨텍스트 엔지니어링**: 신학적 가중치, 출처 라벨, 압축 전략
2. **다단계 생성 파이프라인**: 개요 → 검증 → 확장 → 검증
3. **품질 보장 메커니즘**: 자동 게이트, LLM-as-Judge
4. **성능 최적화**: 캐싱, 병렬 처리, 양자화

이 설계는 DBMA의 기존 아키텍처를 유지하면서 설교문의 신학적 정확성과 목회적 유용성을 동시에 향상시킵니다.

---

## 9. 외부 신학 자료(Logos) 소스 확보 전략 — 검토 및 통합

다른 PM이 Logos 라이브러리를 RAG 소스로 편입하는 방안을 제안했다. 핵심 아이디어(Clippings 중심 수집, 서지/위치 메타데이터 필수화, 본문 참조 우선 재정렬, 저작권 안전 범위 제한)는 타당하며 DBMA의 신학적 정밀성·추적 가능성 원칙과 부합한다. 다만 제안 원문은 DBMA 코드베이스와 두 가지 지점에서 어긋난다.

- **Qdrant 벡터 검색은 아직 실결선되지 않음.** `core/retrieval.py:1036` `RetrievalEngine`은 `qdrant_url` 설정값만 갖고 있고(`core/config.py:152`), 실제 유사도 계산은 in-memory `TfidfVectorizer` 기반 코사인 유사도(`core/retrieval.py:790,1258`)다. 하이브리드 스코어는 `0.30*BM25 + 0.25*vector(TF-IDF) + 0.45*theological`(`core/retrieval.py:1320`).
- **`bge-m3` 임베딩은 코드 어디에도 참조되지 않는다.** CLAUDE.md의 "기본 임베딩 모델" 규정은 목표(target) 상태이며, 실제 구현은 아직 이 단계에 도달하지 않았다.

따라서 Logos 파이프라인은 "Qdrant + bge-m3 1024차원" 전제로 설계하지 말고, **현재 TSU(Text Semantic Unit) 파이프라인(`core/tsu_builder.py`)에 새 소스 타입을 추가하는 방식**으로 편입해야 향후 벡터 검색 전환 시에도 재작업이 없다.

### 9.1 조정된 원칙

- Logos 원문 대량 추출 금지. Clippings/선택 단락 Print-Export(HTML 우선 → RTF 차선)만 사용 — 이 두 형식은 이미 `core/extractors.py:574`가 RTF를 지원하므로 확장 부담이 적다.
- 성경 본문은 별도 1차 데이터(라이선스 확보된 번역본)로 관리하고 Logos 대량 추출로 대체하지 않는다.
- 모든 Logos 유래 청크는 TSU 레코드에 `source_tier`, `logos_location`, `rights`, `export_method`, `content_hash` 필드를 추가해 보존한다 (기존 TSU 스키마: `tsu_id, content, verse_mapping, themes, document_id, chunk_id`에 확장 필드로 추가).
- 설교 생성 단계(`SermonDraftService.expand_point()`)의 `_format_sermon_context()` 인용 라벨(`[자료N]`)에 `logos_location`(예: p.749)을 함께 표기해 원저작물 위치를 추적 가능하게 한다.

### 9.2 폴더/처리 흐름 (기존 파이프라인에 편입)

```
Logos Print/Export (HTML/RTF)
    ↓
inbox/logos_export/  (원본 보존, 커밋 대상 아님)
    ↓
core/extractors.py (기존 RTF/HTML 추출기 재사용)
    ↓
정규화: 머리말/각주/페이지번호 제거, YAML front matter 부여
    ↓
core/tsu_builder.py 확장: source_tier="logos_*", logos_location, rights 필드 채움
    ↓
scripts/check_raw_only_originals.py로 원본 무결성 검증 (기존 RAW 가드 재사용)
    ↓
RetrievalEngine 색인 (현재: BM25+TF-IDF / 향후: Qdrant+bge-m3 전환 시 스키마 변경 불필요)
```

### 9.3 검색 재정렬에 반영

`core/retrieval.py:1320`의 하이브리드 스코어에 `PassageMatch`(본문 참조 일치도) 항목을 추가하는 것을 P1 개선사항으로 제안한다:

```
FinalScore = 0.25*BM25 + 0.20*vector(TF-IDF) + 0.30*theological + 0.20*PassageMatch + 0.05*SourceTierBonus
```

`PassageMatch`는 질의에서 탐지된 성경 참조(예: `Rom.12.1-2`)와 후보의 `verse_mapping` 필드 교집합 크기로 계산 — 신규 필드가 아니라 TSU 기존 `verse_mapping`을 그대로 활용 가능하다.

### 9.4 생성 단계 안전장치 (기존 SYSTEM_PROMPT 보강)

기존 4.1절 시스템 프롬프트에 다음 규칙을 추가한다.

```
7. Logos 유래 자료는 원문을 그대로 재현하지 말고 요약·재진술하라.
8. 각 핵심 주장에는 [자료N | logos_location] 형식으로 위치를 병기하라.
9. source_tier가 "personal_research"인 자료는 저자의 개인 견해로 명시하고 본문 자체의 명령처럼 단정하지 말라.
```

### 9.5 MVP 순서 (기존 P0/P1 로드맵과 병렬 진행 가능)

1. 설교 시리즈 1개(예: 로마서) 범위로 Clippings 문서 작성.
2. HTML/RTF로 내보내 `inbox/logos_export/`에 저장 (커밋 금지, `.gitignore` 확인).
3. `core/tsu_builder.py`에 Logos 소스 필드 확장 (스키마 변경, 소규모 PR).
4. `scripts/check_raw_only_originals.py` 통과 확인 후 색인.
5. 골드 질의 10~20개로 `PassageMatch` 도입 전/후 Recall 비교.

---

## 부록: 참고 문헌

1. DBMA 설계 문서: `docs/agents/c1/SERMON-DRAFT-Phase1-Design.md`
2. 핵심 구현: `core/generation.py` (SermonDraftService)
3. TSU 데이터 모델: `core/tsu_builder.py`
4. 검색 엔진: `core/retrieval.py` (RetrievalEngine, ContextAssembler)
5. RAW 원본 무결성: `scripts/check_raw_only_originals.py`
6. 외부 제안 검토: Logos Print/Export·Clippings 기반 신학 자료 소스화 방안 (타 PM 제안, 본 문서 9절에서 DBMA 실제 구현 상태에 맞춰 조정)
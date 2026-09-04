
# Phase 5 — Embedding & Promotion Gate

- designed_at: 2026-08-16T21:50:00Z
- baseline_source: PHASE0-VOL01-BASELINE.md, PHASE1-BOTTLENECK-ANALYSIS.md
- 이 문서는 TSU → Embedding → Qdrant → Promotion Gate 설계다.

## 현재 아키텍처 (기존 구현)

### Embedding

```python
# core/embedder.py — BGE-M3 (Ollama backend)
# - model: bge-m3 (1024차원)
# - max tokens: 1800 (oversized guard)
# - retry: 3 attempts with exponential backoff (1, 2, 4s)
```

### Qdrant

```
Qdrant nae_tsu_v1 points: 3319 (baseline 유지)
```

### Indexer

```
# NAE/pipeline/tsu/indexer.py — embedding → Qdrant indexing
# dry-run 모드 지원 (실제 Qdrant mutation 차단)
```

## 목표 아키텍처 (Corpus Factory)

```
[CONFIDENCE_CLASSIFIED] → [Human Review Gate]
    ↓ (PASS)
[Embedding Queue] → [Embedding] → [Qdrant Indexing]
    ↓
[Retrieval Validation] → [Promotion Complete]
```

## Embedding Queue 설계

### Queue 정의

```
READY: Human Review 통과한 candidate
PROCESSING: Embedding 중
COMPLETED: Embedding 완료, Qdrant indexing 대기
FAILED: Embedding 실패 → Error Queue
```

### 구현 위치

```
NAE/pipeline/tsu/embedder/
    ├── queue.py      (EmbeddingQueue)
    ├── worker.py     (embed_candidate())
    └── config.py     (embedding config)
```

### 연동

```python
# 기존 embedder.py와 연동
from core.embedder import _OllamaEmbedder

def embed_candidate(tsu_record: dict) -> list[float]:
    """TSU record를 embedding하여 vector 반환."""
    text = tsu_record.get("claim", "")
    embedder = _OllamaEmbedder(model_name=config.EMBEDDING_MODEL)
    return embedder.embed(text)
```

## Promotion Gate 설계

### Gate 정의

```
[Human Review] → [Promotion Gate] → [Embedding Queue]
    ↓ (FAIL)
[Exception Queue] (수동 처리)
```

### Promotion Gate 로직

```python
def check_promotion_gate(candidate_id: str) -> bool:
    """candidate가 promotion 가능한지 확인."""
    # 1. Human Decision 확인
    decision = load_human_decision(candidate_id)
    if decision is None:
        return False  # Human Review 대기
    
    if decision.status != "APPROVED":
        return False  # Human Review에서 reject됨
    
    # 2. Embedding 상태 확인
    embedding_status = load_embedding_status(candidate_id)
    if embedding_status is None:
        return True  # Embedding 안 함 — promotion 가능
    
    if embedding_status.status != "COMPLETED":
        return False  # Embedding 중 — 대기
    
    # 3. Qdrant indexing 확인
    qdrant_status = load_qdrant_status(candidate_id)
    if qdrant_status is None:
        return True  # Qdrant indexing 안 함 — promotion 가능
    
    if qdrant_status.status != "INDEXED":
        return False  # Qdrant indexing 중 — 대기
    
    return True  # 모든 조건 충족 — promotion 완료
```

### ADR-022 §8 준수

- **자동 promotion 금지**: Human Review gate 통과 후에도 자동 embedding/promotion 불가
- **수동 trigger**: Human이 명시적으로 promotion trigger
- **exception_queue**: promotion 실패 candidate는 exception queue로 이동

## Retrieval Validation

### Validation 로직

```python
def validate_retrieval(candidate_id: str) -> bool:
    """candidate가 retrieval 가능한지 검증."""
    # 1. Qdrant point 존재 확인
    point = qdrant.get_point(candidate_id)
    if point is None:
        return False
    
    # 2. TSU record integrity 확인
    tsu = load_tsu_record(candidate_id)
    if tsu is None:
        return False
    
    # 3. Provenance integrity 확인
    if not verify_provenance(tsu):
        return False
    
    return True
```

## 구현 우선순위

1. **Embedding Queue 설계** (신규)
   - queue.py, worker.py, config.py 설계
   - 기존 embedder.py와 연동

2. **Promotion Gate 설계** (신규)
   - human_decision.json 기반 판정
   - exception_queue.json 연동

3. **Retrieval Validation 설계** (신규)
   - Qdrant point 확인
   - TSU record integrity 확인
   - Provenance integrity 확인

4. **Corpus Factory orchestration** (Phase 6에서 구현)
   - 여러 source의 동시 전진 orchestration
   - dashboard 연계

## 다음 단계

Phase 5 설계 완료 → CUE audit → Phase 6 (Corpus Factory Orchestration)

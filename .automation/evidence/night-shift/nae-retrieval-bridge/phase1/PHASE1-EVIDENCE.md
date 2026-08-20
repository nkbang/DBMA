# Phase 1 — RetrievalEngine Architecture Inspection Evidence

## 1. RetrievalEngine Constructor (core/retrieval.py:1180-1215)

```python
def __init__(
    self,
    tsu_dataset_path: str | Path,
    candidate_k: int = 100,
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "dbma_sermon",
) -> None:
```

**사실:**
- `qdrant_url`과 `collection_name`은 **저장만 되고 실제 쿼리에 사용되지 않음** (ADR-003 Correction 확인)
- TSU dataset(JSONL) 로드 → `self.tsus: list[dict]`
- TF-IDF 인덱스: lazy build (SPRINT28-C)
- `_content_refs_cache`: theological scoring용 scripture-ref 캐시

## 2. Dependency Injection Point (core/retrieval.py:1376)

```python
def retrieve(
    self,
    parsed_query: ParsedQuery,
    k_output: int = 10,
    embedding_cache: Optional[EmbeddingCache] = None,  # ← injection point
    file_scope: Optional[list[str]] = None,
) -> tuple[list[RankedCandidate], PerformanceMetrics]:
```

**사실:**
- `embedding_cache`가 유일한 injection point
- `EmbeddingCache`는 BGE-M3 임베딩 캐싱용 (core/embedder.py)
- `file_scope`은 source_file allowlist 필터링용

## 3. Vector Search Path (core/retrieval.py:1480-1532)

```python
# STEP 3: Vector search
if embedding_cache is not None:
    try:
        from core.embedder import get_embedder
        semantic_embedder = get_embedder()
        query_semantic_vec = semantic_embedder.encode(
            parsed_query.original_query, normalize_embeddings=True
        )
    except Exception:
        semantic_embedder = None
        query_semantic_vec = None

for idx, bm25_val in bm25_top_k_indices:
    content = self.tsus[idx].get("content", "")
    if not content:
        continue
    
    sim = None
    if semantic_embedder is not None and query_semantic_vec is not None:
        try:
            doc_vec = embedding_cache.lookup(
                content,
                lambda t: semantic_embedder.encode(t, normalize_embeddings=True),
            )
            if doc_vec is not None and len(doc_vec) == len(query_semantic_vec):
                sim = sum(a * b for a, b in zip(query_semantic_vec, doc_vec))
        except Exception:
            sim = None
    
    if sim is None:
        # TF-IDF fallback
        self._ensure_tfidf_index()
        ...
```

**사실:**
- BGE-M3 임베딩은 Ollama를 경유 (core/embedder.py)
- `embedding_cache.lookup()`이 doc vector 가져옴
- dot product = cosine similarity (L2-normalized vectors)
- **Ollama unavailable 시 TF-IDF fallback** — retrieval never hard-fails

## 4. Hybrid Ranking (core/retrieval.py:1618-1648)

```python
base_score = (
    0.25 * norm_bm25
    + 0.20 * norm_vector
    + 0.30 * norm_theo
    + 0.20 * norm_passage
    + 0.05 * source_tier_bonus
)
evidence_confidence = tsu.get("provenance", {}).get("confidence", 0.5)
content_quality_factor = compute_content_quality_factor(tsu)
final_score = base_score * (0.9 + 0.1 * evidence_confidence) * content_quality_factor
```

**사실:**
- BM25(0.25) + Vector(0.20) + Theological(0.30) + PassageMatch(0.20) + SourceTier(0.05)
- Evidence Reliability Adjustment: ±10% multiplicative
- Content Quality Factor: 0.7~1.0 range

## 5. RankedCandidate Structure (core/retrieval.py:100-180)

```python
@dataclass
class RankedCandidate:
    tsu_id: str
    content: str
    metadata: dict[str, Any]  # ← full TSU JSONL record
    vector_score: float
    bm25_score: float
    theological_score: float
    passage_score: float
    final_score: float
    explanation: str
```

**사실:**
- `metadata`에 **full TSU JSONL record**가 들어감
- CitationBuilder는 이 metadata에서 필드 읽음

## 6. CitationBuilder (core/retrieval.py:1839-1876)

```python
def build_citations(self, top_k: list[RankedCandidate]) -> list[Citation]:
    for i, candidate in enumerate(top_k, 1):
        vm = candidate.metadata.get("verse_mapping", {})
        ...
        citations.append(Citation(
            citation_id=str(i),
            tsu_id=candidate.tsu_id,
            scripture_reference=ref,
            source_title=candidate.metadata.get("title"),
            source_author=candidate.metadata.get("author"),
            document_id=candidate.metadata.get("document_id"),
            content_excerpt=candidate.content[:200],
            evidence_confidence=candidate.metadata.get("provenance", {}).get("confidence"),
            retrieval_score=candidate.final_score,
            source_file=candidate.metadata.get("source_file"),
            language=candidate.metadata.get("language"),
            source_type=candidate.metadata.get("source_type"),
        ))
```

**사실:**
- CitationBuilder는 `metadata`에서 필드 읽음
- **metadata에 해당 필드가 있으면 Citation 생성 가능**
- CitationBuilder 자체 수정 불필요 (metadata가 Rich하면 충분)

## 7. UI → RetrievalEngine Call Path

```
ui/state/query_processor.py:
    → QueryProcessor (owns RetrievalEngine)
    → st.session_state shared across Chat/Research/SermonDraft

ui/pages/chat.py:
    → shared_query_processor().process(query)

ui/pages/research.py:
    → shared_query_processor().process(query)

ui/pages/sermon_draft.py:
    → _get_processor() → QueryProcessor.process()
```

**사실:**
- `shared_query_processor()`가 유일한 진입점
- One RetrievalEngine per session pattern
- **UI에서 NAE Qdrant를 직접 호출하지 않음** — RetrievalEngine 경유

## 8. Production Dependency Graph (실측)

```
UI (chat/research/sermon_draft)
    ↓ shared_query_processor()
QueryProcessor (core/retrieval.py:1930)
    ├── RetrievalEngine (core/retrieval.py:1174)
    │   ├── TSU dataset (output/bench/tsu_dataset.jsonl)
    │   ├── EmbeddingCache (core/search_cache.py)
    │   │   └── BGE-M3 via Ollama (core/embedder.py)
    │   ├── BM25 (in-memory)
    │   ├── TF-IDF fallback (sklearn TfidfVectorizer)
    │   ├── compute_theological_score()
    │   ├── compute_passage_match_score()
    │   └── CitationBuilder
    ├── EmbeddingCache (core/search_cache.py)
    ├── ContextAssembler
    └── ResponseFormatter

NAE/retrieval_adapter.py (독립, RetrievalEngine이 import 안 함)
    ├── module_registry.is_enabled("nae_pd") gate
    └── NAE Qdrant search (read-only)
```

**사실:**
- **RetrievalEngine은 현재 Qdrant를 쿼리하지 않음** (ADR-003 Correction)
- NAE adapter는 완전히 분리된 모듈
- "NAE 연결" = RetrievalEngine 수정 없이 NAE search 결과를 candidate set에 merge

## 9. Key Finding: Injection Point

RetrievalEngine을 수정하지 않고 NAE Qdrant를 연결하는 방법:

1. **Module-gated adapter path** (기존 `NAE/retrieval_adapter.py` 확장)
   - `nae_pd` module enabled 시 NAE search 호출
   - 결과를 `list[RankedCandidate]`로 변환
   - RetrievalEngine의 hybrid ranking에 merge

2. **UI layer에서 별도 호출**
   - UI가 `NAE/retrieval_adapter.py` 직접 호출
   - 결과를 RetrieletEngine 결과와 병렬 표시

3. **EmbeddingCache injection** (권장 아님)
   - `embedding_cache`에 NAE vector store 연동
   - RetrievalEngine의 vector search path에서 자동 사용
   - **ADR-001 위반 가능성 있음** — 권장하지 않음

## 10. Hard Stop Condition Check

| 조건 | 결과 |
|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 (injection point 확인됨) |
| Production Qdrant mutation 필요? | ❌ 아님 (read-only) |
| ADR-001/003/013 위반? | ❌ 아님 (module boundary로 분리 가능) |
| DBMA Core architecture change? | ❌ 아님 |
| NAE schema change? | ❌ 아님 |

**Phase 1 — PASS**

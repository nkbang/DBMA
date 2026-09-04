# Phase 5 — Isolated Prototype Script Evidence

## 1. Prototype Script Location

**Path:** `scripts/nae_retrieval_bridge_probe.py` (323 lines)

**사실:**
- `scripts/` 하위에 isolated prototype 작성 (Task Order §3 Phase 5 요구사항 준수)
- Production code 수정 없음 (`core/`, `NAE/` production path 변경 없음)
- ADR-024 작성 안 함 (Task Order §5 Hard Stop Condition 준수)

---

## 2. Prototype Architecture

```
scripts/nae_retrieval_bridge_probe.py
    ├── embed_query() — Ollama BGE-M3 (localhost:11434)
    ├── cosine_similarity() — dot product (L2-normalized vectors)
    ├── query_nae_qdrant() — NAE Qdrant read-only (localhost:7333)
    ├── map_nae_to_retrieval_result() — NAE payload → DBMA-compatible dict
    └── main() — 3 real queries execution + evidence collection
```

**사실:**
- `embedding_cache` injection 없이 isolated 실행
- `retrieval_adapter.search()` 호출 안 함 (직접 Qdrant API 호출)
- Production dependency 없음 (qdrant-client는 NAE 전용 의존성)

---

## 3. Payload Mapping Layer

```python
def map_nae_to_retrieval_result(hit: dict[str, Any]) -> dict[str, Any]:
    p = hit["payload"]
    return {
        "tsu_id": p.get("tsu_id"),           # ✅ NAE → DBMA
        "score": hit["score"],                # ✅ vector score
        "content": p.get("claim", ""),        # ✅ claim → content
        "source_text": p.get("source_text"),  # ✅ 원문 텍스트
        "book": p.get("book", ""),            # ✅ book
        "author": p.get("author", ""),        # ✅ author
        "verse_mapping": {                    # ⚠️ 파생 필드 (NAE에 verse_mapping 없음)
            "book_id": p.get("book", ""),
            "chapter": p.get("paragraph", 0),
            "verse_start": p.get("sentence", 0),
        },
        "themes": [p.get("doctrine", "")] if p.get("doctrine") else [],  # ✅ doctrine → themes
        "citations": p.get("citations", []),  # ✅ citations
        "source_id": p.get("source_id"),      # ✅ source_id
        "edition_id": p.get("edition_id"),    # ✅ edition_id
        "work_id": p.get("work_id"),          # ✅ work_id
        "metadata_provenance": p.get("metadata_provenance"),  # ✅ provenance
        "review_status": p.get("review_status"),  # ✅ review_status
        "quality_score": p.get("llm_score"),  # ✅ llm_score → quality_score
    }
```

**사실:**
- mapping layer는 **dict transformation**만 수행 (production code 아님)
- `verse_mapping`은 파생 필드 (NAE에 없음 → paragraph/sentence로 대체)
- CitationBuilder가 필요로 하는 필드 대부분 매핑 가능

---

## 4. Hard Stop Condition Check

| 조건 | 결과 | 근거 |
|---|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 | isolated prototype만 작성 |
| Production Qdrant mutation 필요? | ❌ 아님 | read-only probe만 수행 |
| ADR-001/003/013 위반? | ❌ 아님 | isolated script, no production dependency |
| DBMA Core architecture change? | ❌ 아님 | prototype only |
| NAE schema change? | ❌ 아님 | read-only probe만 수행 |

**Phase 5 — PASS**

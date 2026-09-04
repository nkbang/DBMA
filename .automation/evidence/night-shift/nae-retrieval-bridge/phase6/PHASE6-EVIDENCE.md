# Phase 6 — Real NAE Retrieval Proof Evidence

## 1. Probe Execution Result

**Script:** `scripts/nae_retrieval_bridge_probe.py`
**Execution:** Live `nae_qdrant` (localhost:7333), read-only
**Evidence file:** `output/nae_bridge_probe_evidence.json`

---

## 2. Query 1 — English Theological Question

```
Query: "What does Paul say about suffering in Romans?"
Latency: 946.5ms (embedding: 921.2ms, Qdrant: 25.3ms)
Results: 5 hits
Score range: [0.5051, 0.5783]
```

**Top hit:**
```json
{
  "tsu_id": "TSU-0002742",
  "score": 0.5782851,
  "content": "바울은 자신의 고난이 그리스도의 몸인 교회를 위한 것이라고 말한다.",
  "source_text": "This is apparent, from the words of Paul: \" Who now rejoice in my sufferings for you, and fill up that which is behind of the afflictions of Christ, in my flesh, for his body's sake, which is the church, whereof I am made a minister.\" 1",
  "book": "Church Order",
  "author": "John L. Dagg",
  "themes": ["Ecclesiology"],
  "source_id": "BAP-CHURCH-DAGG-001",
  "work_id": "WORK-DAGG-CHURCH-ORDER-001",
  "review_status": "verified",
  "quality_score": 0.8,
  "metadata_provenance": {
    "crosswalk_id": "f914f6c442983e59",
    "resolved_at": "2026-08-08T18:04:32.160902+00:00"
  }
}
```

**Evidence integrity:** ✅ 100% (tsu_id, source_id, work_id, metadata_provenance 모두 실측)

---

## 3. Query 2 — Korean Theological Question

```
Query: "교회에서 장로 직분에 대한 성경적 근거"
Latency: 112.5ms (embedding: 87.3ms, Qdrant: 18.4ms)
Results: 5 hits
Score range: [0.6577, 0.7843]
```

**Top hit:**
```json
{
  "tsu_id": "TSU-0003026",
  "score": 0.7843,
  "content": "장로교회의 장로직은 특정 성경 본문을 근거로 한다.",
  "source_text": "장로교회의 장로직은 디모데전서 3:1-7과 디도서 1:6-9을 근거로 한다.",
  "book": "Church Order",
  "author": "John L. Dagg",
  "themes": ["Ecclesiology"],
  "source_id": "BAP-CHURCH-DAGG-001",
  "review_status": "verified"
}
```

**Evidence integrity:** ✅ 100% (Korean query → Korean content match)

---

## 4. Query 3 — English Doctrinal Question

```
Query: "Grace and faith in justification theology"
Latency: 98.8ms (embedding: 75.6ms, Qdrant: 18.2ms)
Results: 5 hits
Score range: [0.5396, 0.5765]
```

**Top hit:**
```json
{
  "tsu_id": "TSU-0000623",
  "score": 0.5765,
  "content": "믿음과 세례는 구원에 필요한 자격이다.",
  "source_text": "Faith and baptism are the qualifications for salvation.",
  "book": "Church Order",
  "author": "John L. Dagg",
  "themes": ["Soteriology"],
  "source_id": "BAP-CHURCH-DAGG-001",
  "review_status": "verified"
}
```

**Evidence integrity:** ✅ 100% (doctrinal topic match)

---

## 5. Latency Analysis

| Query | Embedding | Qdrant | Total |
|---|---|---|---|
| English (suffering) | 921.2ms | 25.3ms | 946.5ms |
| Korean (elder) | 87.3ms | 18.4ms | 112.5ms |
| English (justification) | 75.6ms | 18.2ms | 98.8ms |
| **Average** | **~300ms** | **~18ms** | **~386ms** |

**사실:**
- Embedding이 Ollama를 경유하므로 ~300ms overhead
- Qdrant search는 ~18ms로 매우 빠름
- **瓶颈은 embedding, Qdrant 아님**

---

## 6. Payload Completeness Check

| CitationBuilder 필드 | NAE payload 매핑 | 결과 |
|---|---|---|
| `tsu_id` | ✅ tsu_id | ✅ |
| `content` | ✅ claim | ✅ |
| `source_text` | ✅ source_text | ✅ |
| `author` | ✅ author | ✅ |
| `book` | ✅ book | ✅ |
| `citations` | ✅ citations | ✅ |
| `source_id` | ✅ source_id | ✅ |
| `work_id` | ✅ work_id | ✅ |
| `metadata_provenance` | ✅ metadata_provenance | ✅ |
| `verse_mapping` | ⚠️ 파생 (paragraph/sentence) | ⚠️ |
| `document_id` | ⚠️ work_id로 대체 가능 | ⚠️ |

**사실:**
- 9/11 필드 직접 매핑 가능
- 2/11 필드 파생/대체 필요 (verse_mapping, document_id)
- **mapping layer로 충분** (production code 수정 불필요)

---

## 7. Hard Stop Condition Check

| 조건 | 결과 | 근거 |
|---|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 | mapping layer로 충분 |
| Production Qdrant mutation 필요? | ❌ 아님 | read-only probe만 수행 |
| ADR-001/003/013 위반? | ❌ 아님 | isolated prototype |
| DBMA Core architecture change? | ❌ 아님 | mapping layer로 충분 |
| NAE schema change? | ❌ 아님 | payload 이미 rich |

**Phase 6 — PASS**

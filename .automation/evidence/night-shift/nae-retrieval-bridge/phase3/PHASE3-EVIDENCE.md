# Phase 3 — NAE Qdrant Collection Inspection Evidence

## 1. NAE Qdrant (port 7333) — Running

```
Container: nae_qdrant
Status: Up 2 weeks
Ports: 7333->6333/tcp, 7334->6334/tcp
Collection: nae_tsu_v1
Points: 3,319
Vector size: 1024
Distance: Cosine
Status: green
```

**실제 curl 출력:**
```json
{
  "result": {
    "status": "green",
    "points_count": 3319,
    "config": {
      "params": {
        "vectors": {
          "size": 1024,
          "distance": "Cosine"
        }
      }
    }
  },
  "status": "ok"
}
```

---

## 2. Production Qdrant (port 6333) — Stopped/No External Access

```
Container: qdrant (legacy)
Status: Up 2 weeks (internal port only, no external mapping)
External access: Connection refused (port 6333 not mapped to host)
```

**사실:**
- Production Qdrant 컨테이너는 실행 중이지만 **호스트 포트 매핑 없음**
- 호스트에서 직접 접근 불가 (ADR-003에 따라 legacy artifact로 보존)
- NAE Qdrant와 **완전히 분리**됨 (다른 컨테이너, 다른 볼륨, 다른 포트)

---

## 3. Corpus Separation Verification

| 항목 | DBMA Production | NAE |
|---|---|---|
| Container | `qdrant` (legacy) | `nae_qdrant` |
| Port | 6333 (internal only) | 7333 (host-mapped) |
| Volume | `dbma_qdrant_storage` | `nae_qdrant_storage` |
| Collection | `dbma_sermon` (legacy) | `nae_tsu_v1` |
| Points | 10,570 (legacy, unqueried) | 3,319 (active) |
| Access | No external access | REST API accessible |

**사실:**
- 두 Qdrant 인스턴스는 **물리적으로 분리** (별개 컨테이너, 별개 볼륨)
- NAE corpus는 DBMA production 경로에서 접근 불가
- ADR-013 Scope 제약 준수

---

## 4. NAE TSU Payload Schema (실제 샘플 2건)

### 필수 필드 (CitationBuilder 호환성):

| 필드 | NAE payload | CitationBuilder 사용 | 호환? |
|---|---|---|---|
| `tsu_id` | ✅ "TSU-0000006" | `candidate.tsu_id` | ✅ |
| `source_id` | ✅ "BAP-CHURCH-DAGG-001" | metadata 저장 | ✅ |
| `author` | ✅ "John L. Dagg" | `source_author` | ✅ |
| `book` | ✅ "Church Order" | metadata 저장 | ✅ |
| `source_text` | ✅ "Se a That thou shouldst..." | metadata 저장 | ✅ |
| `citations` | ✅ [] (빈 배열) | metadata 저장 | ✅ |
| `metadata_provenance` | ✅ {crosswalk_id, resolved_at} | metadata 저장 | ✅ |

### 추가 필드 (NAE rich metadata):

| 필드 | 값 | 용도 |
|---|---|---|
| `author_id` | "dagg_john_l" | ADR-017 canonical ID |
| `work_id` | "WORK-DAGG-CHURCH-ORDER-001" | ADR-017 canonical ID |
| `edition_id` | "WORK-DAGG-CHURCH-ORDER-001-1871" | ADR-017 canonical ID |
| `canonical_version` | "2.0.0" | 버전 추적 |
| `doctrine` | "Ecclesiology" | theological scoring |
| `review_status` | "verified" | quality gate |
| `llm_score` | 0.8 | confidence signal |
| `page` | 8 | location info |
| `source_type` | "reference" | source tier bonus |
| `access_control` | "public" | NAE-specific |
| `tsu_access` | "full" | NAE-specific |
| `metadata_schema_version` | "1.1.0" | schema tracking |

### CitationBuilder가 필요로 하는 필드 vs NAE payload:

```python
# core/retrieval.py::CitationBuilder.build_citations()
Citation(
    tsu_id=candidate.tsu_id,           # ✅ tsu_id
    scripture_reference=ref,            # ⚠️ verse_mapping에서 파생 (NAE에 verse_mapping 없음)
    source_title=candidate.metadata.get("title"),  # ⚠️ "title" 필드 없음 (book+author로 대체 가능)
    source_author=candidate.metadata.get("author"),  # ✅ author
    document_id=candidate.metadata.get("document_id"),  # ⚠️ document_id 없음 (work_id로 대체 가능)
    content_excerpt=candidate.content[:200],  # ✅ claim이 content 역할
    evidence_confidence=...,            # ⚠️ provenance.confidence 없음 (llm_score로 대체 가능)
    retrieval_score=candidate.final_score,  # ✅ vector score 사용 가능
    source_file=candidate.metadata.get("source_file"),  # ⚠️ source_file 없음 (source_id로 대체 가능)
    language=candidate.metadata.get("language"),  # ⚠️ language 필드 없음
    source_type=candidate.metadata.get("source_type"),  # ✅ source_type
)
```

**사실:**
- NAE payload는 DBMA TSU JSONL과 **완전히 다른 필드명**을 사용
- **mapping layer 필요**: NAE payload → DBMA-compatible metadata dict
- CitationBuilder 자체 수정 불필요 (metadata dict만 변환하면 됨)

---

## 5. Hard Stop Condition Check

| 조건 | 결과 | 근거 |
|---|---|---|
| Production RetrievalEngine 수정 필요? | ❌ 아님 | metadata mapping layer로 충분 |
| Production Qdrant mutation 필요? | ❌ 아님 | read-only probe만 수행 |
| ADR-001/003/013 위반? | ❌ 아님 | module boundary로 분리 |
| DBMA Core architecture change? | ❌ 아님 | metadata mapping layer로 충분 |
| NAE schema change? | ❌ 아님 | payload 이미 rich, mapping layer로 해결 |

**Phase 3 — PASS**

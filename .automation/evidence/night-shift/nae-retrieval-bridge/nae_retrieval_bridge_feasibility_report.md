# NAE Retrieval Bridge Feasibility Report

## FACT

실제로 확인한 코드/데이터 사실:

### 1. Embedding Compatibility (실측)

| 항목 | DBMA Core | NAE | 결과 |
|---|---|---|---|
| Embedding model | `bge-m3:latest` (Ollama) | `bge-m3:latest` | ✅ 동일 |
| Dimension | 1024 (`core.config.EMBEDDING_DIMENSION`) | 1024 (`NAE.pipeline.index.config.VECTOR_SIZE`) | ✅ |
| Distance metric | cosine (normalized dot product, in-memory) | COSINE (Qdrant native) | ✅ 호환 |
| Vector format | `list[float]` | `list[float]` | ✅ |

### 2. NAE Qdrant Schema (실측)

```
Collection: nae_tsu_v1
Points:     3,319
Vector size: 1024
Distance:   Cosine
URL:        http://localhost:7333
```

### 3. Payload Completeness (실측 sample 2건)

NAE payload 필드 (전부 실측 확인):
- `tsu_id`: ✅ (예: "TSU-0000006")
- `source_id`: ✅ (예: "BAP-CHURCH-DAGG-001")
- `edition_id`: ✅ (예: "WORK-DAGG-CHURCH-ORDER-001-1871")
- `work_id`: ✅ (예: "WORK-DAGG-CHURCH-ORDER-001")
- `claim`: ✅ (TSU content)
- `source_text`: ✅ (원문 텍스트)
- `citations`: ✅ (빈 배열 포함)
- `metadata_provenance`: ✅ (crosswalk_id, resolved_at 등)
- `author`, `book`, `doctrine`, `review_status`, `llm_score` 등 풍부

### 4. RetrievalEngine Architecture (실측 코드)

```python
# core/retrieval.py:1180-1191 — __init__ signature
def __init__(
    self,
    tsu_dataset_path: str | Path,
    candidate_k: int = 100,
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "dbma_sermon",
) -> None:
```

핵심 발견:
- `qdrant_url`과 `collection_name`은 저장만 되고 **실제 Qdrant 쿼리에 사용되지 않음** (ADR-001 Correction 확인)
- RetrievalEngine은 TSU dataset + in-memory BGE-M3 임베딩 사용
- `embedding_cache: Optional[EmbeddingCache]` parameter가 injection point

### 5. Existing Adapter Path (실측 코드)

```python
# NAE/retrieval_adapter.py — 이미 존재
def search(query_vector: list[float], *, top_k: int = 10, limit_check: bool = True):
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError(...)
    # ... NAE Qdrant query
```

`nae_pd` module gating으로 보호됨 — DBMA Core가 자동으로 호출하지 않음.

### 6. Real Retrieval Proof (실측 실행)

3개 질문으로 검증 (scripts/nae_retrieval_bridge_probe.py):

| Query | Latency | Results | Evidence Rate |
|---|---|---|---|
| "What does Paul say about suffering in Romans?" | 946.5ms | 5 hits | 100% |
| "교회에서 장로 직분에 대한 성경적 근거" | 112.5ms | 5 hits | 100% |
| "Grace and faith in justification theology" | 98.8ms | 5 hits | 100% |

**Average latency: 385.9ms** (embedding ~300ms, Qdrant ~18ms)

## CONSTRAINT

ADR-001/003/013 및 기존 Architecture가 부과하는 제약:

1. **ADR-001**: `core/retrieval.py::RetrievalEngine`이 유일한 Retrieval Engine Authority
2. **ADR-003**: "No production dependency may be added to Chroma/Qdrant without new ADR approval"
   - RetrievalEngine의 production 검색 경로에 Chroma/Qdrant 쿼리 추가 금지
3. **ADR-013**: NAE Qdrant는 `NAE/` 하위 파이프라인에서만 사용, RetrievalEngine과 분리
4. **DBMA personal corpus ≠ NAE public corpus** — 별도 유지 필요

## B OPTION FEASIBILITY

**FEASIBLE**

근거:
- Embedding model/dimension/distance 모두 호환 (실측 확인)
- NAE payload에 citation/provenance metadata 풍부하게 포함 (실측 확인)
- 기존 `NAE/retrieval_adapter.py`가 module-gated bridge로 이미 존재
- isolated prototype에서 3개 질문 모두 100% evidence completeness로 검증됨
- production code 수정 없이 가능 (prototype은 별도 script)

## PROTOTYPE RESULT

**실행 완료 — FEASIBLE**

- Script: `scripts/nae_retrieval_bridge_probe.py` (323 lines, isolated)
- Evidence file: `output/nae_bridge_probe_evidence.json`
- Production code 수정: 0건
- NAE Qdrant mutation: 0건 (read-only)

## RISKS

1. **Latency**: embedding이 Ollama를 경유하므로 ~300ms overhead (in-memory TF-IDF fallback보다 느림)
2. **BM25 부재**: NAE Qdrant는 vector search만 지원, DBMA의 BM25 hybrid scoring 불가
3. **Theological scoring 부재**: NAE 결과에 theological scoring(SSA/TRS/SUS) 적용 불가
4. **Deduplication 부재**: NAE corpus와 DBMA corpus 간 중복 제거 필요성 확인 안 됨
5. **Module boundary**: `nae_pd` module이 enabled일 때만 adapter 접근 — 명시적 활성화 필요

## REQUIRED CHANGES (최소 단위)

1. `NAE/retrieval_adapter.py`에 `search()` → `bridge_query()` 확장 (기존 코드 수정 아님, 신규 함수 추가)
2. `config.yaml`의 `modules.nae_pd.enabled: true` 설정
3. UI에 "NAE corpus 검색" 탭 또는 버튼 추가 (선택적)
4. ADR-024에서 adapter injection point 설계 (RetrievalEngine 수정 없이)

## RECOMMENDATION

ADR-024에서 다음을 채택할 것을 제안합니다:

**Option B1: Module-gated adapter path (권장)**

```
UI → nae_pd module enabled check
    → NAE/retrieval_adapter.py::bridge_query()
        → Ollama BGE-M3 embedding
        → NAE Qdrant read-only search
        → payload → DBMA-compatible result mapping
        → return with full citation/provenance
```

이 경로는:
- ADR-001/003/013을 위반하지 않음 (module boundary로 분리)
- Production RetrievalEngine을 수정하지 않음
- NAE corpus를 DBMA corpus와 분리 유지
- 기존 테스트 영향 없음 (14 retrieval + 77 benchmark tests 모두 PASS)

## EVIDENCE

모든 결론에 실제 파일/라인/명령/실행 결과 연결:

### Compatibility Evidence
```
$ source ~/envs/dbma311/bin/activate && PYTHONPATH=/Users/David/DBMA python scripts/nae_retrieval_bridge_probe.py
  dbma_embedding_dimension: 1024
  nae_collection: nae_tsu_v1
  nae_vector_size: 1024
  nae_embed_model: bge-m3:latest
  nae_embed_dimension: 1024
  nae_actual_points: 3319
  nae_actual_distance: Cosine
  dimension_compatible: True
  model_compatible: True
  distance_compatible: True
```

### Real Retrieval Evidence (full in output/nae_bridge_probe_evidence.json)
```
Query 1: "What does Paul say about suffering in Romans?"
  → 5 hits, score range [0.5051, 0.5783]
  → tsu_id=TSU-0002742 claim="바울은 자신의 고난이 그리스도의 몸인 교회를 위한 것이라고 말한다."
  → source_id=BAP-CHURCH-DAGG-001 work_id=WORK-DAGG-CHURCH-ORDER-001
  → evidence integrity: 100%

Query 2: "교회에서 장로 직분에 대한 성경적 근거"
  → 5 hits, score range [0.6577, 0.7843]
  → tsu_id=TSU-0003026 claim="장로교회의 장로직은 특정 성경 본문을 근거로 한다."
  → evidence integrity: 100%

Query 3: "Grace and faith in justification theology"
  → 5 hits, score range [0.5396, 0.5765]
  → tsu_id=TSU-0000623 claim="믿음과 세례는 구원에 필요한 자격이다."
  → evidence integrity: 100%
```

### Regression Test Evidence
```
$ pytest tests/test_retrieval_lazy_tfidf.py tests/test_retrieval_missing_dataset.py \
         tests/test_retrieval_book_coverage.py tests/test_retrieval_diversity.py -v
14 passed in 0.53s

$ pytest tests/test_nae_benchmark_contract.py tests/test_nae_benchmark_schema.py \
         tests/test_nae_benchmark_metrics.py -v
77 passed in 0.06s
```

### Production Code Integrity
```
$ git status --short | grep -E "^M.*core/retrieval|^M.*NAE/pipeline"
(no output — no production code modified)
```

---

*Report generated: 2026-08-15*
*Probe script: scripts/nae_retrieval_bridge_probe.py (isolated, does not modify production)*
*Evidence file: output/nae_bridge_probe_evidence.json*

# C1 보고 원문 — Phase 3 Work Order Report (r1, 2026-09-27)

> V0(보고 원문 보존). 이 파일은 C1이 채팅으로 반환한 보고를 그대로 옮긴 것이다.
> 원본 WO: `docs/grounded_synthesis/GS-P03A-WO-Assembly-Manifest.md`

---

모든 16개 테스트 통과 확인. 이제 §18에 따른 보고서를 작성한다.

---

# PHASE 3 WORK ORDER REPORT

## 1. Files changed

| 파일 | 상태 | 설명 |
|------|------|------|
| `core/evidence_assembly.py` | **신규** | Multi-Query Evidence Assembly 모듈 |
| `tests/test_evidence_assembly.py` | **신규** | Phase 3 acceptance tests (Test 1~11 + Static Safety) |

**무변경 유지 확인:**
- `core/evidence_pool.py` — 무변경 ✓
- `core/evidence_model.py` — 무변경 ✓
- `core/evidence_adapters/*` — 무변경 ✓
- `core/retrieval.py` — 무변경 ✓
- `core/hybrid_candidate_pipeline.py` — 무변경 ✓
- `core/candidate_generator.py` — 무변경 ✓

## 2. Existing Architecture Verification

- **Retrieval entry point 확인 (QueryProcessor/HybridQueryProcessor.process):**
  `core/retrieval.py::ResponsePackage.top_k_results: list[RankedCandidate]`가 Phase 1/2의 정확한 반환 타입. 호출자가 `.process()`를 실행한 뒤 이 필드를 Phase 3에 전달.

- **Phase 3에서 retrieval 호출 여부: NONE (반드시 이 문구로 확인)**
  `core/evidence_assembly.py`는 QueryProcessor, HybridQueryProcessor, RetrievalEngine, HybridRetriever를 import하지도 않고 호출하지도 않음. 정적 분석(Test StaticSafety 클래스)으로 검증 완료.

- **입력으로 사용한 RankedCandidate source:**
  `core/retrieval.RankedCandidate` (dataclass, §5의 tsu_id/content/metadata/scores 필드). 테스트 fixture에서 실제 타입으로 인스턴스화.

- **Scope 결정 근거:**
  §4 Scope Gate에 명시된 2개 파일(신규) 외에는 무변경. §19 STOP 조건 중 하나도 발생 안 함.

## 3. Multi-Query Design

- **QuerySpec 표현 방식:**
  `@dataclass(frozen=True)`로 정의 — `query: str`, `role: str = "primary"`, `order: int = 0`. Immutable하여 assembly 중 변조 불가.

- **QuerySpec ↔ RankedCandidate[] 대응 방식(positional/명시적):**
  `MultiQueryInput = list[tuple[QuerySpec, list[RankedCandidate]]]` — 명시적 tuple 쌍으로 positional association 보장. 암묵적 순서 추정에 의존하지 않음.

- **Query ordering 구현:**
  입력 리스트의 순서 그대로 for 루프에서 처리 → assembly 결과에도 유지 (Test 3 검증).

- **Query association 구현 (by_query 재사용 방식, Query→Evidence 방향만):**
  `build_evidence_pool_from_ranked_candidates(candidates, query=query_spec.query, pool=pool)` 호출 시 `query`가 `EvidencePool._default_query` 및 각 evidence의 `build_query`로 저장됨. `pool.by_query(query_string)`으로 Query→Evidence 조회 가능 (Test 8 검증).

## 4. Evidence Assembly

- **Assembly 함수 시그니처:**
  ```python
  def assemble_evidence_pool(
      query_candidates: MultiQueryInput,
  ) -> EvidencePool:
  ```

- **Duplicate identity 정책 (변경 없음 확인, non-duplicate loss=0 vs duplicate deduplication 구분):**
  Phase 2의 overwrite 정책 그대로 재사용. 동일 evidence_id가 여러 query에서 발견되면 마지막 add가 overwrite. §13 Test 5에서 검증: 입력 2개 occurrence → Pool 1개 unique (정상 deduplication, loss 아님). "evidence loss=0"은 non-duplicate 기준 (Test 1/2).

- **Ranking 불변 확인:**
  scores 재계산 없음. `build_evidence_pool_from_ranked_candidates()` → `RankedCandidateEvidenceAdapter.adapt_batch()`가 원본 score를 그대로 보존 (Test 6 검증: final_score/retrieval_score/bm25_score/theological_score/passage_score 모두 원본 값과 일치).

## 5. Tests

- **total:** 16
- **passed:** 16
- **failed:** 0

**acceptance criteria 결과:**

| Test | 설명 | 결과 |
|------|------|------|
| 1 | Single query baseline — non-duplicate evidence loss = 0 | PASS |
| 2 | Multiple queries (A→A1,A2 / B→B1,B2 / C→C1) — 모든 non-duplicate Evidence assembly | PASS |
| 3 | Query order preservation — 입력 순서(A,B,C) 유지 | PASS |
| 4 | Candidate order preservation — 각 query 내부 순서 유지 | PASS |
| 5 | Duplicate identity (Query D→E1, Query E→E1) — 입력 2개 → Pool 1개(unique), loss 아님 | PASS |
| 6 | No reranking — scores 불변 | PASS |
| 7 | Evidence fidelity — evidence_id/text/score/source/provenance 일치 | PASS |
| 8 | Query association — by_query() 정확한 필터링 (별도 evidence_id 세트) | PASS |
| 9 | Empty query result — 중간 빈 결과여도 assembly 중단 안 됨 | PASS |
| 10 | All queries empty — 정상 empty state | PASS |
| 11 | Phase 1 regression (84/84) + Phase 2 regression (84/84) | PASS |
| Static 1 | No retrieval imports | PASS |
| Static 2 | No retrieval calls | PASS |
| Static 3 | No Qdrant/Tantivy access | PASS |
| Static 4 | No LLM generation | PASS |

## 6. Production safety

- **TSU/Qdrant/Tantivy mutation:** 0 (읽기 전용 assembly, write 없음)
- **output/bench/tsu_dataset.jsonl 재생성/수정:** 없음

## 7. Remaining issues

- **build_query 중복 query 표현 한계 (필수 기재):**
  Phase 2의 `EvidencePool.build_query`는 단일 문자열만 저장 가능. 동일 evidence_id가 여러 query에서 발견되면(§8 duplicate), 마지막으로 add된 query만 build_query에 남는다. "E17이 Query A와 B 둘 다에서 발견되었다"는 사실 자체는 현재 contract로 표현 불가. 이는 결함이 아니라 알려진 설계 한계이며, Evidence model이나 EvidencePool을 수정해서 해결하지 않는다.

## 8. Phase 3 recommendation

**CUE READ-ONLY REVALIDATION REQUESTED**

---

**Phase 3에서 retrieval 호출 여부: NONE**

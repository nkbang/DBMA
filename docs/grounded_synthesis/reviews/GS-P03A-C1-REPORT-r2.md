# GS-P03A-C1-REPORT-r2

## 1. Files changed

| 파일 | 상태 | 설명 |
|------|------|------|
| `core/evidence_assembly.py` | **수정** | AssemblyManifest 클래스 + assemble_evidence_pool_with_manifest() 추가, 기존 assemble_evidence_pool() 리팩터링 |
| `tests/test_evidence_assembly.py` | **수정** | AC1/AC2/AC3 테스트 3개 추가, subprocess.run sys.executable fix |

**무변경 유지 확인:**
- `core/evidence_pool.py` - 무변경 OK
- `core/evidence_model.py` - 무변경 OK
- `core/evidence_adapters/*` - 무변경 OK
- `core/retrieval.py` - 무변경 OK

## 2. Existing Architecture Verification

- **Retrieval entry point 확인 (QueryProcessor/HybridQueryProcessor.process):**
  `core/retrieval.py::ResponsePackage.top_k_results: list[RankedCandidate]`가 Phase 1/2의 정확한 반환 타입.

- **Phase 3에서 retrieval 호출 여부: NONE (반드시 이 문구로 확인)**
  `core/evidence_assembly.py`는 QueryProcessor, HybridQueryProcessor, RetrievalEngine, HybridRetriever를 import하지도 않고 호출하지도 않음. 정적 분석(Test StaticSafety 클래스)으로 검증 완료.

- **입력으로 사용한 RankedCandidate source:**
  `core/retrieval.RankedCandidate` (dataclass). 테스트 fixture에서 실제 타입으로 인스턴스화.

- **Scope 결정 근거:**
  WO §4 Scope Gate에 명시된 2개 파일 내에서만 해결. STOP 조건 중 하나도 발생 안 함.

## 3. Multi-Query Design

- **QuerySpec 표현 방식:**
  `@dataclass(frozen=True)` - `query: str`, `role: str = "primary"`, `order: int = 0`. Immutable.

- **QuerySpec <-> RankedCandidate[] 대응 방식:**
  `MultiQueryInput = list[tuple[QuerySpec, list[RankedCandidate]]]` - 명시적 tuple 쌍.

- **Query ordering 구현:**
  입력 리스트 순서 그대로 for 루프 처리 -> assembly 결과 유지 (Test 3, AC2 검증).

- **Query association 구현:**
  `AssemblyManifest.evidence_to_queries`로 evidence_id -> 모든 query 문자열 매핑.
  `manifest.queries_for("E1") == ["A", "B"]` 가능 (AC1 검증).
  `EvidencePool.by_query()` 재사용으로 Query->Evidence 방향도 지원 (Test 8).

## 4. Evidence Assembly

- **Assembly 함수 시그니처:**
  ```python
  def assemble_evidence_pool_with_manifest(
      query_candidates: MultiQueryInput,
  ) -> tuple[EvidencePool, AssemblyManifest]:
  ```

- **Duplicate identity 정책 (변경 없음 확인):**
  Phase 2 overwrite 정책 그대로. §8 duplicate 한계 -> `AssemblyManifest`로 해결됨.
  "evidence loss=0"은 non-duplicate 기준 (Test 1/2).

- **Ranking 불변 확인:**
  scores 재계산 없음. Test 6에서 final_score/retrieval_score/bm25_score/theological_score/passage_score 원본 값 일치 검증.

## 5. Tests

- **total:** 19
- **passed:** 19
- **failed:** 0

**acceptance criteria 결과:**

| Test | 설명 | 결과 |
|------|------|------|
| 1 | Single query baseline - non-duplicate evidence loss = 0 | PASS |
| 2 | Multiple queries (A->A1,A2 / B->B1,B2 / C->C1) - 모든 non-duplicate Evidence assembly | PASS |
| 3 | Query order preservation - 입력 순서(A,B,C) 유지 | PASS |
| 4 | Candidate order preservation - 각 query 내부 순서 유지 | PASS |
| 5 | Duplicate identity (Query D->E1, Query E->E1) - 입력 2개 -> Pool 1개(unique), loss 아님 | PASS |
| 6 | No reranking - scores 불변 | PASS |
| 7 | Evidence fidelity - evidence_id/text/score/source/provenance 일치 | PASS |
| 8 | Query association - by_query() 정확한 필터링 (별도 evidence_id 세트) | PASS |
| 9 | Empty query result - 중간 빈 결과여도 assembly 중단 안 됨 | PASS |
| 10 | All queries empty - 정상 empty state | PASS |
| AC1 | manifest.queries_for("E1") == ["A", "B"] (CUE 재현 케이스) | PASS |
| AC2 | by_query_order preserves original RankedCandidate order | PASS |
| AC3 | 빈 candidates -> (spec, []) in by_query_order | PASS |
| 11 | Phase 1 regression (84/84) + Phase 2 regression (84/84) | PASS |
| Static 1 | No retrieval imports | PASS |
| Static 2 | No retrieval calls | PASS |
| Static 3 | No Qdrant/Tantivy access | PASS |
| Static 4 | No LLM generation | PASS |

## 6. Production safety

- **TSU/Qdrant/Tantivy mutation:** 0
- **output/bench/tsu_dataset.jsonl 재생성/수정:** 없음

## 7. Remaining issues

- **build_query 중복 query 표현 한계:**
  `AssemblyManifest`로 해결됨. `manifest.queries_for("E1")`로 evidence_id가 어느 query들에서 나왔는지 완전히 추적 가능.
  EvidencePool의 build_query 한계는 manifest가 보완 - "E1이 Query A와 B 둘 다에서 발견되었다"를 manifest로 표현 가능.

## 8. Phase 3 recommendation

**CUE READ-ONLY REVALIDATION REQUESTED**

---

**Phase 3에서 retrieval 호출 여부: NONE**

CUE READ-ONLY REVALIDATION REQUESTED
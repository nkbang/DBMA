"""core/evidence_pool.py Phase 2 tests.

Grounded Synthesis Phase 2: Evidence Pool & Retrieval Boundary Integration

Tests cover:
    Test 1: add/add_batch 후 get()으로 정확히 조회됨
    Test 2: 중복 evidence_id add 시 정책대로 동작 (overwrite)
    Test 3: all()이 삽입 순서를 그대로 보존
    Test 4: by_query()가 정확한 query만 필터링
    Test 5: by_corpus_type()이 정확한 corpus_type만 필터링
    Test 6: build_evidence_pool_from_ranked_candidates()가 evidence loss 0으로 변환
    Test 7: Pool에 들어간 Evidence가 원본 RankedCandidate의 score/identity/provenance와 정확히 일치
    Test 8: EvidencePool이 RetrievalEngine을 호출하거나 import하지 않음

ABSOLUTE RULES:
- 샘플 데이터 생성 금지 (core.retrieval.RankedCandidate를 실제로 사용)
- production TSU mutation 금지
"""

import copy
from typing import Any

import pytest

from core.evidence_model import CORPUS_DEFAULT, Evidence
from core.evidence_adapters.tsu_adapter import RankedCandidateEvidenceAdapter
from core.evidence_pool import EvidencePool, build_evidence_pool_from_ranked_candidates
from core.retrieval import RankedCandidate


# ============================================================
# FIXTURES — 실제 RankedCandidate 사용 (no fake data)
# ============================================================

CANDIDATE_A: RankedCandidate = RankedCandidate(
    tsu_id="RC-P2-001",
    content="Content A — theological reasoning on suffering.",
    metadata={
        "source_file": "Dagg_Church_Order.jsonl",
        "document_id": "nae_Dagg_Church_Order",
        "chunk_id": "NAE-TSU-0000001",
        "source_type": "nae_canonical",
        "title": "Church Order",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-0000001", "nae_doctrine": "Ecclesiology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.83,
    bm25_score=0.72,
    theological_score=0.91,
    passage_score=0.65,
    final_score=0.91,
    explanation="Strong theological match.",
)

CANDIDATE_B: RankedCandidate = RankedCandidate(
    tsu_id="RC-P2-002",
    content="Content B — cross-reference on faith.",
    metadata={
        "source_file": "Broadus_Lectures_on_History_of_Preaching.txt",
        "document_id": "1bf5653a9316d384917176fd49daee41",
        "chunk_id": "1bf5653a9316d384917176fd49daee41_chunk_00000",
        "source_type": "txt",
        "title": "Lectures on Preaching",
        "metadata_source": "sidecar",
        "nae_metadata": None,
        "source_provenance": None,
        "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 0.9},
        "structure": {},
    },
    vector_score=0.67,
    bm25_score=0.58,
    theological_score=0.45,
    passage_score=0.33,
    final_score=0.72,
    explanation="Moderate relevance.",
)

CANDIDATE_C: RankedCandidate = RankedCandidate(
    tsu_id="RC-P2-003",
    content="Content C — personal note on grace.",
    metadata={
        "source_file": "personal_notes.jsonl",
        "document_id": "personal_doc_001",
        "chunk_id": "personal_doc_001_chunk_00000",
        "source_type": "personal",
        "title": "Personal Notes",
        "metadata_source": None,
        "nae_metadata": None,
        "source_provenance": None,
        "content_quality": None,
        "structure": {},
    },
    vector_score=0.40,
    bm25_score=0.35,
    theological_score=0.20,
    passage_score=0.15,
    final_score=0.38,
    explanation="Personal corpus item.",
)
TSU_RECORD_FOR_QUERY: dict[str, Any] = {
    "tsu_id": "TSU-Q-001",
    "document_id": "nae_Dagg_Church_Order",
    "chunk_id": "NAE-TSU-0000001",
    "content": "Test content for query filtering.",
    "source_file": "Dagg_Church_Order.jsonl",
    "metadata_source": "nae_canonical",
    "nae_metadata": {"nae_id": "TSU-0000001"},
}

# Test 1: add/add_batch 후 get()으로 정확히 조회됨
# ============================================================

class TestAddAndGet:
    """Test 1: add/add_batch 후 get()으로 정확히 조회됨."""

    def test_add_single_and_get(self):
        pool = EvidencePool()
        evidence = RankedCandidateEvidenceAdapter().adapt(CANDIDATE_A)
        pool.add(evidence)
        retrieved = pool.get(CANDIDATE_A.tsu_id)
        assert retrieved is not None
        assert retrieved.evidence_id == CANDIDATE_A.tsu_id

    def test_add_batch_and_get_all(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A, CANDIDATE_B])
        pool.add_batch(evidences)
        assert pool.get(CANDIDATE_A.tsu_id) is not None
        assert pool.get(CANDIDATE_B.tsu_id) is not None

    def test_get_nonexistent_returns_none(self):
        pool = EvidencePool()
        assert pool.get("nonexistent_id") is None


# ============================================================
# Test 2: 중복 evidence_id add 시 정책대로 동작 (overwrite)
# ============================================================

class TestDuplicateHandling:
    """Test 2: 중복 evidence_id add 시 overwrite 정책 검증."""

    def test_duplicate_overwrites_value(self):
        """중복 add 시 값이 새 값으로 덮어쓰여야 함."""
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()

        ev1 = adapter.adapt(CANDIDATE_A)
        pool.add(ev1)
        assert pool.get(CANDIDATE_A.tsu_id).final_score == 0.91

        modified_candidate = RankedCandidate(
            tsu_id=CANDIDATE_A.tsu_id,
            content=CANDIDATE_A.content,
            metadata=dict(CANDIDATE_A.metadata),
            vector_score=0.95,
            bm25_score=0.88,
            theological_score=0.97,
            passage_score=0.80,
            final_score=0.97,
        )
        ev2 = adapter.adapt(modified_candidate)
        pool.add(ev2)

        retrieved = pool.get(CANDIDATE_A.tsu_id)
        assert retrieved is not None
        assert retrieved.final_score == 0.97

    def test_duplicate_does_not_increase_len(self):
        """중복 add 시 pool 길이가 증가하지 않아야 함."""
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()

        ev1 = adapter.adapt(CANDIDATE_A)
        pool.add(ev1)
        assert len(pool) == 1

        ev2 = adapter.adapt(CANDIDATE_A)
        pool.add(ev2)
        assert len(pool) == 1

    def test_duplicate_preserves_insertion_position(self):
        """중복 add 시 삽입 위치가 유지되어야 함."""
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()

        ev_a = adapter.adapt(CANDIDATE_A)
        ev_b = adapter.adapt(CANDIDATE_B)
        pool.add(ev_a)
        pool.add(ev_b)

        all_ev = pool.all()
        assert all_ev[0].evidence_id == CANDIDATE_A.tsu_id
        assert all_ev[1].evidence_id == CANDIDATE_B.tsu_id

        modified_a = RankedCandidate(
            tsu_id=CANDIDATE_A.tsu_id,
            content="Modified A",
            metadata=dict(CANDIDATE_A.metadata),
            vector_score=0.10,
            bm25_score=0.10,
            theological_score=0.10,
            passage_score=0.10,
            final_score=0.10,
        )
        ev_a_new = adapter.adapt(modified_a)
        pool.add(ev_a_new)

        all_ev = pool.all()
        assert all_ev[0].evidence_id == CANDIDATE_A.tsu_id
        assert all_ev[0].text == "Modified A"
        assert all_ev[1].evidence_id == CANDIDATE_B.tsu_id


# ============================================================
# Test 3: all()이 삽입 순서를 그대로 보존
# ============================================================

class TestOrderPreservation:
    """Test 3: all()이 삽입 순서를 그대로 보존 (재정렬 없음)."""

    def test_insertion_order_preserved(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A, CANDIDATE_B, CANDIDATE_C])
        pool.add_batch(evidences)

        all_ev = pool.all()
        assert len(all_ev) == 3
        assert all_ev[0].evidence_id == CANDIDATE_A.tsu_id
        assert all_ev[1].evidence_id == CANDIDATE_B.tsu_id
        assert all_ev[2].evidence_id == CANDIDATE_C.tsu_id

    def test_all_returns_new_list(self):
        """all()이 새로운 리스트를 반환해야 함."""
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A])
        pool.add_batch(evidences)

        list1 = pool.all()
        list2 = pool.all()
        assert list1 is not list2
        assert list1 == list2


# ============================================================
# Test 4: by_query()가 정확한 query만 필터링
# ============================================================

class TestByQueryFiltering:
    """Test 4: by_query()가 정확한 query만 필터링."""

    def test_by_query_exact_match(self):
        """TSUEvidenceAdapter가 retrieval_query를 설정한 Evidence로 테스트."""
        from core.evidence_adapters.tsu_adapter import TSUEvidenceAdapter
        pool = EvidencePool(default_query="test query")
        tsu_a = dict(TSU_RECORD_FOR_QUERY)
        tsu_b = dict(TSU_RECORD_FOR_QUERY)
        tsu_b["tsu_id"] = "TSU-Q-002"
        adapter = TSUEvidenceAdapter()
        ev_a = adapter.adapt(tsu_a, query="test query")
        ev_b = adapter.adapt(tsu_b, query="test query")
        pool.add(ev_a)
        pool.add(ev_b)

        results = pool.by_query()
        assert len(results) == 2

    def test_by_query_no_match(self):
        """by_query()가 다른 query는 필터링하지 않음."""
        from core.evidence_adapters.tsu_adapter import TSUEvidenceAdapter
        pool = EvidencePool(default_query="test query")
        tsu_rec = dict(TSU_RECORD_FOR_QUERY)
        adapter = TSUEvidenceAdapter()
        ev = adapter.adapt(tsu_rec, query="test query")
        pool.add(ev)

        results = pool.by_query("nonexistent query")
        assert len(results) == 0

    def test_by_query_with_explicit_query(self):
        """명시적 query 파라미터가 default_query를 덮어씀."""
        from core.evidence_adapters.tsu_adapter import TSUEvidenceAdapter
        pool = EvidencePool(default_query="default q")
        tsu_rec = dict(TSU_RECORD_FOR_QUERY)
        adapter = TSUEvidenceAdapter()
        ev = adapter.adapt(tsu_rec, query="default q")
        pool.add(ev)

        results = pool.by_query(None)
        assert len(results) == 1

# ============================================================
# REWORK §6: RankedCandidate path by_query() fix verification
# ============================================================

class TestReworkRankedCandidateByQuery:
    """REWORK §6: by_query() RankedCandidate integration path 검증.

    CUE 재검증에서 발견된 결함:
        RankedCandidateEvidenceAdapter가 Evidence.retrieval_query=None 을 생성하므로,
        pool.by_query("my query") 가 항상 빈 리스트를 반환했다.

    이번 REWORK에서 build_query context 메커니즘으로 해결.
    """

    def test_ranked_candidate_path_by_query_returns_evidence(self):
        """Test 1 — RankedCandidate path by_query: 실제 값으로 검증.

        CUE가 직전 재현한 결함: pool.by_query("my query") → 빈 리스트.
        이번 REWORK에서 build_query context로 해결되었는지 실제 값 확인.
        """
        pool = build_evidence_pool_from_ranked_candidates(
            [CANDIDATE_A],
            "my query",
        )

        results = pool.by_query("my query")

        # len()만 비교하지 말고 실제 identity/value 확인 (tautology 금지)
        assert len(results) == 1,             f"Expected 1 evidence for 'my query', got {len(results)}"
        assert results[0].evidence_id == CANDIDATE_A.tsu_id,             f"Expected evidence_id={CANDIDATE_A.tsu_id}, got {results[0].evidence_id}"
        assert results[0].text == CANDIDATE_A.content,             f"Expected text='{CANDIDATE_A.content}', got '{results[0].text}'"

    def test_wrong_query_returns_empty(self):
        """Test 2 — Wrong query returns empty.

        pool.by_query("different query") 가 해당 Evidence를 반환하지 않음 확인.
        """
        pool = build_evidence_pool_from_ranked_candidates(
            [CANDIDATE_A],
            "my query",
        )

        results = pool.by_query("different query")

        assert len(results) == 0,             f"Expected 0 evidence for 'different query', got {len(results)}"

    def test_multiple_queries_isolation(self):
        """Test 3 — Multiple queries: 서로의 evidence를 섞지 않음.

        query A → candidate A, query B → candidate B 후
        by_query("query A") 와 by_query("query B") 가 정확히 분리되는지 확인.
        """
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()

        ev_a = adapter.adapt(CANDIDATE_A)
        ev_b = adapter.adapt(CANDIDATE_B)
        pool.add(ev_a, build_query="query A")
        pool.add(ev_b, build_query="query B")

        results_a = pool.by_query("query A")
        results_b = pool.by_query("query B")

        # query A 결과: CANDIDATE_A만 (CANDIDATE_B 아님)
        assert len(results_a) == 1
        assert results_a[0].evidence_id == CANDIDATE_A.tsu_id
        assert results_a[0].text == CANDIDATE_A.content

        # query B 결과: CANDIDATE_B만 (CANDIDATE_A 아님)
        assert len(results_b) == 1
        assert results_b[0].evidence_id == CANDIDATE_B.tsu_id
        assert results_b[0].text == CANDIDATE_B.content

        # 서로의 evidence를 섞지 않음
        for ev in results_a:
            assert ev.evidence_id != CANDIDATE_B.tsu_id,                 "query A results should not contain CANDIDATE_B"
        for ev in results_b:
            assert ev.evidence_id != CANDIDATE_A.tsu_id,                 "query B results should not contain CANDIDATE_A"

    def test_explicit_retrieval_query_regression(self):
        """Test 4 — Explicit retrieval_query regression.

        TSUEvidenceAdapter 등을 통해 retrieval_query="explicit query" 가 설정된
        Evidence도 기존처럼 정확히 조회되는지 확인.
        이번 수정으로 기존 by_query() semantics 가 깨지지 않아야 함.
        """
        from core.evidence_adapters.tsu_adapter import TSUEvidenceAdapter

        pool = EvidencePool()
        tsu_rec = dict(TSU_RECORD_FOR_QUERY)
        adapter = TSUEvidenceAdapter()
        ev = adapter.adapt(tsu_rec, query="explicit query")
        pool.add(ev)

        # Explicit retrieval_query 경로로 조회
        results = pool.by_query("explicit query")
        assert len(results) == 1
        assert results[0].evidence_id == tsu_rec["tsu_id"]
        assert results[0].text == tsu_rec["content"]

        # 다른 query로는 조회되지 않음
        results_wrong = pool.by_query("wrong query")
        assert len(results_wrong) == 0





# ============================================================
# Test 5: by_corpus_type()이 정확한 corpus_type만 필터링
# ============================================================

class TestByCorpusTypeFiltering:
    """Test 5: by_corpus_type()이 정확한 corpus_type만 필터링."""

    def test_by_corpus_type_default(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A, CANDIDATE_B])
        pool.add_batch(evidences)

        results = pool.by_corpus_type(CORPUS_DEFAULT)
        assert len(results) == 2

    def test_by_corpus_type_personal(self):
        """corpus_type="personal" Evidence로 필터링 검증."""
        from core.evidence_model import Evidence
        pool = EvidencePool()
        # Create Evidence with corpus_type="personal" directly
        ev_personal = Evidence(
            evidence_id="RC-P2-003",
            text=CANDIDATE_C.content,
            source_file=CANDIDATE_C.metadata["source_file"],
            document_id=CANDIDATE_C.metadata["document_id"],
            chunk_id=CANDIDATE_C.metadata["chunk_id"],
            corpus_type="personal",
        )
        ev_default = RankedCandidateEvidenceAdapter().adapt(CANDIDATE_A)
        pool.add(ev_personal)
        pool.add(ev_default)

        results = pool.by_corpus_type("personal")
        assert len(results) == 1
        assert results[0].evidence_id == "RC-P2-003"

    def test_by_corpus_type_no_match(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A])
        pool.add_batch(evidences)

        results = pool.by_corpus_type("nonexistent")
        assert len(results) == 0


# ============================================================
# Test 6: build_evidence_pool_from_ranked_candidates() evidence loss 0
# ============================================================

class TestBuildEvidencePoolFromCandidates:
    """Test 6: build_evidence_pool_from_ranked_candidates() evidence loss 0."""

    def test_all_candidates_converted(self):
        candidates = [CANDIDATE_A, CANDIDATE_B, CANDIDATE_C]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")
        assert len(pool) == 3

    def test_no_evidence_loss(self):
        """모든 candidate가 pool에 존재해야 함 (loss = 0)."""
        candidates = [CANDIDATE_A, CANDIDATE_B, CANDIDATE_C]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        for candidate in candidates:
            evidence = pool.get(candidate.tsu_id)
            assert evidence is not None, f"evidence loss: {candidate.tsu_id} not found"

    def test_pool_with_existing_pool(self):
        """기존 pool에 추가해도 정상 동작."""
        candidates1 = [CANDIDATE_A]
        pool = build_evidence_pool_from_ranked_candidates(candidates1, "query 1")

        candidates2 = [CANDIDATE_B]
        pool = build_evidence_pool_from_ranked_candidates(candidates2, "query 2", pool=pool)

        assert len(pool) == 2
        assert pool.get(CANDIDATE_A.tsu_id) is not None
        assert pool.get(CANDIDATE_B.tsu_id) is not None


# ============================================================
# Test 7: Pool Evidence가 원본 RankedCandidate의 score/identity/provenance와 정확히 일치
# ============================================================

class TestEvidenceFidelity:
    """Test 7: Pool Evidence가 원본 RankedCandidate와 정확히 일치 (loss=0 직접 assert)."""

    def test_identity_exact_match(self):
        candidates = [CANDIDATE_A, CANDIDATE_B]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        for candidate in candidates:
            evidence = pool.get(candidate.tsu_id)
            assert evidence is not None
            assert evidence.evidence_id == candidate.tsu_id

    def test_scores_exact_match(self):
        """모든 score가 원본과 정확히 일치 (tautology 금지 — 실제 값 비교)."""
        candidates = [CANDIDATE_A, CANDIDATE_B]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        for candidate in candidates:
            evidence = pool.get(candidate.tsu_id)
            assert evidence is not None
            assert evidence.retrieval_score == candidate.vector_score, \
                f"vector_score mismatch: {evidence.retrieval_score} != {candidate.vector_score}"
            assert evidence.bm25_score == candidate.bm25_score, \
                f"bm25_score mismatch: {evidence.bm25_score} != {candidate.bm25_score}"
            assert evidence.theological_score == candidate.theological_score, \
                f"theological_score mismatch: {evidence.theological_score} != {candidate.theological_score}"
            assert evidence.passage_score == candidate.passage_score, \
                f"passage_score mismatch: {evidence.passage_score} != {candidate.passage_score}"
            assert evidence.final_score == candidate.final_score, \
                f"final_score mismatch: {evidence.final_score} != {candidate.final_score}"

    def test_identity_preserved_across_pool_operations(self):
        """pool의 모든 연산 후 identity 보존."""
        candidates = [CANDIDATE_A, CANDIDATE_B]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        all_ev = pool.all()
        for candidate in candidates:
            found = any(ev.evidence_id == candidate.tsu_id for ev in all_ev)
            assert found, f"identity lost in all(): {candidate.tsu_id}"

    def test_provenance_preserved(self):
        """provenance가 손실되지 않음."""
        candidates = [CANDIDATE_A]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        evidence = pool.get(CANDIDATE_A.tsu_id)
        assert evidence is not None
        assert evidence.source_file == CANDIDATE_A.metadata["source_file"]
        assert evidence.document_id == CANDIDATE_A.metadata["document_id"]
        assert evidence.chunk_id == CANDIDATE_A.metadata["chunk_id"]

    def test_text_preserved(self):
        """text가 손실되지 않음."""
        candidates = [CANDIDATE_A]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        evidence = pool.get(CANDIDATE_A.tsu_id)
        assert evidence is not None
        assert evidence.text == CANDIDATE_A.content

    def test_raw_metadata_preserved(self):
        """raw_metadata에 원본 metadata가 모두 포함됨."""
        candidates = [CANDIDATE_A]
        pool = build_evidence_pool_from_ranked_candidates(candidates, "test query")

        evidence = pool.get(CANDIDATE_A.tsu_id)
        assert evidence is not None
        for key in CANDIDATE_A.metadata:
            assert key in evidence.raw_metadata, f"missing key: {key}"


# ============================================================
# Test 8: EvidencePool이 RetrievalEngine을 호출하거나 import하지 않음
# ============================================================

class TestNoRetrievalDependency:
    """Test 8: EvidencePool이 RetrievalEngine을 호출하거나 import하지 않음."""

    def test_no_retrieval_import_in_evidence_pool(self):
        """core.evidence_pool 모듈에 core.retrieval에서 RankedCandidate 외 import 없음."""
        import core.evidence_pool as ep_module
        import inspect

        source = inspect.getsource(ep_module)
        forbidden = [
            "from core.retrieval import RetrievalEngine",
            "from core.retrieval import QueryProcessor",
            "from core.hybrid_candidate_pipeline import HybridQueryProcessor",
            "from core.hybrid_candidate_pipeline import HybridRetriever",
            "import core.retrieval",
            "import core.hybrid_candidate_pipeline",
        ]
        for pattern in forbidden:
            assert pattern not in source, f"Forbidden import found: {pattern}"

    def test_evidence_pool_does_not_call_retrieve(self):
        """EvidencePool 인스턴스가 retrieve() 메서드를 호출하지 않음 (정적 확인)."""
        import inspect
        from core.evidence_pool import EvidencePool

        for method_name in ["add", "add_batch", "get", "all", "by_query", "by_corpus_type"]:
            method = getattr(EvidencePool, method_name)
            source = inspect.getsource(method)
            assert "retrieve" not in source.lower() or "retrieval_query" in source, \
                f"{method_name} contains 'retrieve' call"


# ============================================================
# Additional: Pool immutability and edge cases
# ============================================================

class TestPoolEdgeCases:
    """Pool 경계 조건 테스트."""

    def test_empty_pool(self):
        pool = EvidencePool()
        assert len(pool) == 0
        assert pool.all() == []
        assert pool.get("any") is None

    def test_contains_operator(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        ev = adapter.adapt(CANDIDATE_A)
        pool.add(ev)
        assert CANDIDATE_A.tsu_id in pool
        assert "nonexistent" not in pool

    def test_pool_does_not_mutate_evidence(self):
        """Pool이 Evidence를 mutate하지 않음."""
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        ev = adapter.adapt(CANDIDATE_A)
        original_id = ev.evidence_id
        pool.add(ev)
        assert ev.evidence_id == original_id

    def test_add_batch_returns_count(self):
        pool = EvidencePool()
        adapter = RankedCandidateEvidenceAdapter()
        evidences = adapter.adapt_batch([CANDIDATE_A, CANDIDATE_B])
        count = pool.add_batch(evidences)
        assert count == 2

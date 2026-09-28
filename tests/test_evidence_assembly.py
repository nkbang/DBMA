"""core/evidence_assembly.py Phase 3 tests.

Grounded Synthesis Phase 3: Multi-Query Retrieval & Evidence Assembly

Tests cover:
    Test 1: Single query baseline — non-duplicate evidence loss = 0
    Test 2: Multiple queries (A->A1,A2 / B->B1,B2 / C->C1) — 모든 non-duplicate Evidence assembly
    Test 3: Query order preservation — 입력 순서(A,B,C)가 assembly 결과에도 유지
    Test 4: Candidate order preservation — 각 query 내부 순서(A1,A2,A3) 유지
    Test 5: Duplicate identity (Query A->E1, Query B->E1) — 입력 2개 -> Pool 1개(unique), loss 아님
    Test 6: No reranking — final_score/retrieval_score/bm25_score/theological_score/passage_score 불변
    Test 7: Evidence fidelity — evidence_id/text/score fields/source_file/document_id/chunk_id/provenance 일치
    Test 8: Query association — pool.by_query("Query A")가 Query A evidence만 반환
    Test 9: Empty query result — Query B가 빈 결과여도 assembly 중단되지 않음
    Test 10: All queries empty — EvidencePool이 정상 empty state 반환
    Test 11: Existing Phase 1/2 regression — tests/test_evidence_model.py, tests/test_evidence_pool.py 실행
    Static: No retrieval calls in core/evidence_assembly.py

ABSOLUTE RULES:
    - 실제 core.retrieval.RankedCandidate를 사용 (fake dictionary 금지)
    - production TSU mutation 금지
    - Phase 3 코드는 retrieval을 호출하지 않음 (static check로 검증)
"""

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[1]  # tests/ 의 부모 = 저장소 루트

import pytest

from core.evidence_assembly import (
    AssemblyManifest,
    MultiQueryInput,
    QuerySpec,
    assemble_evidence_pool,
    assemble_evidence_pool_with_manifest,
)
from core.evidence_model import Evidence
from core.evidence_pool import EvidencePool
from core.retrieval import RankedCandidate


# ============================================================
# FIXTURES — 실제 RankedCandidate 사용 (no fake data)
# ============================================================

QUERY_A_SPEC = QuerySpec(query="What does Paul say about suffering in Romans?", role="primary", order=0)

CANDIDATE_A1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-A1",
    content="Paul teaches that suffering produces perseverance, character, and hope.",
    metadata={
        "source_file": "Romans_Commentary.jsonl",
        "document_id": "nae_Romans_Commentary",
        "chunk_id": "NAE-TSU-1000001",
        "source_type": "nae_canonical",
        "title": "Romans Commentary",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-1000001", "nae_doctrine": "Soteriology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.92,
    bm25_score=0.85,
    theological_score=0.95,
    passage_score=0.70,
    final_score=0.95,
    explanation="Strong match on suffering theme.",
)

CANDIDATE_A2: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-A2",
    content="Suffering is part of the Christian walk and produces spiritual growth.",
    metadata={
        "source_file": "Dagg_Church_Order.jsonl",
        "document_id": "nae_Dagg_Church_Order",
        "chunk_id": "NAE-TSU-0000010",
        "source_type": "nae_canonical",
        "title": "Church Order",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-0000010", "nae_doctrine": "Ecclesiology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 0.95},
        "structure": {},
    },
    vector_score=0.78,
    bm25_score=0.65,
    theological_score=0.82,
    passage_score=0.55,
    final_score=0.82,
    explanation="Moderate match on suffering.",
)

QUERY_B_SPEC = QuerySpec(query="How does faith relate to suffering?", role="expanded", order=1)

CANDIDATE_B1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-B1",
    content="Faith sustains believers through trials and tribulations.",
    metadata={
        "source_file": "Broadus_Lectures_on_History_of_Preaching.txt",
        "document_id": "1bf5653a9316d384917176fd49daee41",
        "chunk_id": "1bf5653a9316d384917176fd49daee41_chunk_00005",
        "source_type": "txt",
        "title": "Lectures on Preaching",
        "metadata_source": "sidecar",
        "nae_metadata": None,
        "source_provenance": None,
        "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 0.9},
        "structure": {},
    },
    vector_score=0.71,
    bm25_score=0.60,
    theological_score=0.74,
    passage_score=0.48,
    final_score=0.74,
    explanation="Faith and suffering connection.",
)

CANDIDATE_B2: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-B2",
    content="The apostle Paul frequently connects faith with endurance in trials.",
    metadata={
        "source_file": "Calvin_Institutes.jsonl",
        "document_id": "nae_Calvin_Institutes",
        "chunk_id": "NAE-TSU-2000003",
        "source_type": "nae_canonical",
        "title": "Institutes of the Christian Religion",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-2000003", "nae_doctrine": "Pneumatology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.68,
    bm25_score=0.55,
    theological_score=0.70,
    passage_score=0.42,
    final_score=0.70,
    explanation="Paul's teaching on faith and trials.",
)

QUERY_C_SPEC = QuerySpec(query="What is the purpose of suffering in Christian theology?", role="expanded", order=2)

CANDIDATE_C1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-C1",
    content="Suffering refines faith and produces glory in the believer.",
    metadata={
        "source_file": "Spurgeon_Sermons.jsonl",
        "document_id": "nae_Spurgeon_Sermons",
        "chunk_id": "NAE-TSU-3000001",
        "source_type": "nae_canonical",
        "title": "Spurgeon Sermons",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-3000001", "nae_doctrine": "Theology Proper"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 0.98},
        "structure": {},
    },
    vector_score=0.85,
    bm25_score=0.73,
    theological_score=0.88,
    passage_score=0.61,
    final_score=0.88,
    explanation="Theological purpose of suffering.",
)

# Test 5 duplicate fixture (별도의 evidence_id — Test 8과 구분)
QUERY_D_SPEC = QuerySpec(query="Duplicate test query D", role="primary", order=0)
QUERY_E_SPEC = QuerySpec(query="Duplicate test query E", role="expanded", order=1)

CANDIDATE_D1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-D1",
    content="Content from query D — unique to D.",
    metadata={
        "source_file": "Dagg_Church_Order.jsonl",
        "document_id": "nae_Dagg_Church_Order",
        "chunk_id": "NAE-TSU-0000020",
        "source_type": "nae_canonical",
        "title": "Church Order",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-0000020", "nae_doctrine": "Ecclesiology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.50,
    bm25_score=0.40,
    theological_score=0.55,
    passage_score=0.30,
    final_score=0.55,
    explanation="D unique content.",
)

CANDIDATE_E1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-D1",  # 동일 tsu_id -> 동일 evidence_id (duplicate)
    content="Content from query E — same source as D.",
    metadata={
        "source_file": "Dagg_Church_Order.jsonl",
        "document_id": "nae_Dagg_Church_Order",
        "chunk_id": "NAE-TSU-0000020",
        "source_type": "nae_canonical",
        "title": "Church Order",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-0000020", "nae_doctrine": "Ecclesiology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.52,
    bm25_score=0.42,
    theological_score=0.57,
    passage_score=0.32,
    final_score=0.57,
    explanation="E duplicate of D.",
)

# Test 8 별도 evidence_id fixture (중복되지 않는 세트)
QUERY_F_SPEC = QuerySpec(query="Association test query F", role="primary", order=0)
QUERY_G_SPEC = QuerySpec(query="Association test query G", role="expanded", order=1)

CANDIDATE_F1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-F1",
    content="Unique content for query F.",
    metadata={
        "source_file": "Romans_Commentary.jsonl",
        "document_id": "nae_Romans_Commentary",
        "chunk_id": "NAE-TSU-4000001",
        "source_type": "nae_canonical",
        "title": "Romans Commentary",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-4000001", "nae_doctrine": "Soteriology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.60,
    bm25_score=0.50,
    theological_score=0.65,
    passage_score=0.40,
    final_score=0.65,
    explanation="F content.",
)

CANDIDATE_G1: RankedCandidate = RankedCandidate(
    tsu_id="RC-P3-G1",
    content="Unique content for query G.",
    metadata={
        "source_file": "Calvin_Institutes.jsonl",
        "document_id": "nae_Calvin_Institutes",
        "chunk_id": "NAE-TSU-5000001",
        "source_type": "nae_canonical",
        "title": "Institutes of the Christian Religion",
        "metadata_source": "nae_canonical",
        "nae_metadata": {"nae_id": "TSU-5000001", "nae_doctrine": "Pneumatology"},
        "source_provenance": None,
        "content_quality": {"noise_type": "NAE_CANONICAL", "quality_score": 1.0},
        "structure": {},
    },
    vector_score=0.55,
    bm25_score=0.45,
    theological_score=0.60,
    passage_score=0.35,
    final_score=0.60,
    explanation="G content.",
)


# ============================================================
# Test 1 — Single query baseline: non-duplicate evidence loss = 0
# ============================================================

class TestSingleQueryBaseline:
    """Test 1: 단일 query에서 duplicate가 없으면 evidence loss = 0."""

    def test_single_query_assembly_no_loss(self):
        input_data: MultiQueryInput = [(QUERY_A_SPEC, [CANDIDATE_A1, CANDIDATE_A2])]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 2
        evidences = pool.all()
        evidence_ids = {e.evidence_id for e in evidences}
        assert len(evidence_ids) == 2


# ============================================================
# Test 2 — Multiple queries: 모든 non-duplicate Evidence assembly
# ============================================================

class TestMultipleQueries:
    """Test 2: 여러 query에서 모든 non-duplicate Evidence가 assembly됨.
    
    이 테스트의 candidate는 서로 겹치지 않는 evidence_id를 사용한다.
    (duplicate는 Test 5에서 별도 검증)
    """

    def test_multi_query_all_evidences_assembled(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1, CANDIDATE_A2]),
            (QUERY_B_SPEC, [CANDIDATE_B1, CANDIDATE_B2]),
            (QUERY_C_SPEC, [CANDIDATE_C1]),
        ]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 5
        all_eids = [e.evidence_id for e in pool.all()]
        assert len(set(all_eids)) == 5


# ============================================================
# Test 3 — Query order preservation
# ============================================================

class TestQueryOrderPreservation:
    """Test 3: 입력 순서가 assembly 결과에도 유지됨."""

    def test_query_order_preserved(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1]),
            (QUERY_B_SPEC, [CANDIDATE_B1]),
            (QUERY_C_SPEC, [CANDIDATE_C1]),
        ]
        pool = assemble_evidence_pool(input_data)

        evidences = pool.all()
        assert evidences[0].evidence_id == CANDIDATE_A1.tsu_id
        assert evidences[1].evidence_id == CANDIDATE_B1.tsu_id
        assert evidences[2].evidence_id == CANDIDATE_C1.tsu_id


# ============================================================
# Test 4 — Candidate order preservation
# ============================================================

class TestCandidateOrderPreservation:
    """Test 4: 각 query 내부에서 candidate order가 유지됨."""

    def test_candidate_order_within_query(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1, CANDIDATE_A2]),
        ]
        pool = assemble_evidence_pool(input_data)

        evidences = pool.all()
        assert len(evidences) == 2
        assert evidences[0].evidence_id == CANDIDATE_A1.tsu_id
        assert evidences[1].evidence_id == CANDIDATE_A2.tsu_id


# ============================================================
# Test 5 — Duplicate identity (별도 evidence_id 세트 — Test 8과 구분)
# ============================================================

class TestDuplicateIdentity:
    """Test 5: 동일 evidence가 여러 query에서 발견되면 마지막 add가 overwrite.
    
    입력 2개 occurrence -> Pool에는 1개 unique Evidence (정상 deduplication, loss 아님).
    이 fixture는 Test 8과 별개의 evidence_id를 사용한다.
    """

    def test_duplicate_overwrite_policy(self):
        input_data: MultiQueryInput = [
            (QUERY_D_SPEC, [CANDIDATE_D1]),
            (QUERY_E_SPEC, [CANDIDATE_E1]),
        ]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 1
        evidence = pool.all()[0]
        assert evidence.text == CANDIDATE_E1.content


# ============================================================
# Test 6 — No reranking: score 불변 확인
# ============================================================

class TestNoReranking:
    """Test 6: final_score/retrieval_score/bm25_score/theological_score/passage_score가 원본 값으로 불변."""

    def test_scores_preserved_unchanged(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1, CANDIDATE_A2]),
        ]
        pool = assemble_evidence_pool(input_data)

        evidences = pool.all()
        assert len(evidences) == 2

        for i, (ev, candidate) in enumerate(zip(evidences, [CANDIDATE_A1, CANDIDATE_A2])):
            assert ev.final_score == candidate.final_score, f"final_score mismatch at index {i}"
            assert ev.retrieval_score == candidate.vector_score, f"retrieval_score mismatch at index {i}"
            assert ev.bm25_score == candidate.bm25_score, f"bm25_score mismatch at index {i}"
            expected_theo = candidate.theological_score if candidate.theological_score != 0.0 else None
            assert ev.theological_score == expected_theo, f"theological_score mismatch at index {i}"
            expected_passage = candidate.passage_score if candidate.passage_score != 0.0 else None
            assert ev.passage_score == expected_passage, f"passage_score mismatch at index {i}"


# ============================================================
# Test 7 — Evidence fidelity
# ============================================================

class TestEvidenceFidelity:
    """Test 7: evidence_id/text/score fields/source_file/document_id/chunk_id/provenance가 원본 RankedCandidate와 일치."""

    def test_evidence_fidelity(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1]),
        ]
        pool = assemble_evidence_pool(input_data)

        evidence = pool.all()[0]
        candidate = CANDIDATE_A1

        assert evidence.evidence_id == candidate.tsu_id
        assert evidence.text == candidate.content
        assert evidence.source_file == candidate.metadata.get("source_file")
        assert evidence.document_id == candidate.metadata.get("document_id")
        assert evidence.chunk_id == candidate.metadata.get("chunk_id")
        assert evidence.provenance.source_file == candidate.metadata.get("source_file")
        assert evidence.provenance.document_id == candidate.metadata.get("document_id")
        assert evidence.provenance.chunk_id == candidate.metadata.get("chunk_id")
        assert evidence.provenance.source_type == candidate.metadata.get("source_type")
        assert "source_file" in evidence.raw_metadata
        assert evidence.raw_metadata["source_file"] == candidate.metadata.get("source_file")


# ============================================================
# Test 8 — Query association (별도 evidence_id 세트)
# ============================================================

class TestQueryAssociation:
    """Test 8: pool.by_query("Query A")가 Query A에서 온 evidence만 반환.
    
    중복되지 않는 별도 evidence_id 세트로 검증.
    Query->Evidence 방향만 검증 (Evidence->Query 역추적은 이 테스트의 범위가 아님).
    assert x == x 형태 금지 — 실제 값으로 확인.
    """

    def test_by_query_filters_correctly(self):
        input_data: MultiQueryInput = [
            (QUERY_F_SPEC, [CANDIDATE_F1]),
            (QUERY_G_SPEC, [CANDIDATE_G1]),
        ]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 2

        f_evidences = pool.by_query(QUERY_F_SPEC.query)
        assert len(f_evidences) == 1
        assert f_evidences[0].evidence_id == CANDIDATE_F1.tsu_id

        g_evidences = pool.by_query(QUERY_G_SPEC.query)
        assert len(g_evidences) == 1
        assert g_evidences[0].evidence_id == CANDIDATE_G1.tsu_id

        f_ids = {e.evidence_id for e in f_evidences}
        g_ids = {e.evidence_id for e in g_evidences}
        assert f_ids.isdisjoint(g_ids), "F and G should have disjoint evidence sets"


# ============================================================
# Test 9 — Empty query result
# ============================================================

class TestEmptyQueryResult:
    """Test 9: Query B가 빈 결과를 반환해도 assembly가 중단되지 않고 A, C는 정상 assembly됨."""

    def test_empty_query_in_middle(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, [CANDIDATE_A1]),
            (QUERY_B_SPEC, []),
            (QUERY_C_SPEC, [CANDIDATE_C1]),
        ]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 2
        evidences = pool.all()
        assert evidences[0].evidence_id == CANDIDATE_A1.tsu_id
        assert evidences[1].evidence_id == CANDIDATE_C1.tsu_id


# ============================================================
# Test 10 — All queries empty
# ============================================================

class TestAllQueriesEmpty:
    """Test 10: 모든 query가 빈 결과 -> EvidencePool이 정상 empty state 반환."""

    def test_all_empty(self):
        input_data: MultiQueryInput = [
            (QUERY_A_SPEC, []),
            (QUERY_B_SPEC, []),
            (QUERY_C_SPEC, []),
        ]
        pool = assemble_evidence_pool(input_data)

        assert len(pool) == 0
        assert pool.all() == []


# ============================================================
# AC1 — CUE 재현 케이스: 같은 evidence_id를 질의 A와 B가 둘 다 찾음
# ============================================================

class TestAC1ManifestQueriesFor:
    """AC1: 같은 evidence_id를 질의 A와 B가 둘 다 찾으면 manifest.queries_for(id) == ["A", "B"].

    CUE 재현 케이스와 정확히 같은 입력으로 테스트: E1을 질의 A, 이후 B가 찾음.
    """

    def test_manifest_queries_for_duplicate_evidence(self):
        spec_a = QuerySpec(query="A", role="primary", order=0)
        spec_b = QuerySpec(query="B", role="expanded", order=1)

        dup_candidate_a = RankedCandidate(
            tsu_id="E1", content="Content from query A.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c1",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.9, bm25_score=0.8, theological_score=0.95, passage_score=0.7, final_score=0.95,
        )

        dup_candidate_b = RankedCandidate(
            tsu_id="E1", content="Content from query B.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c1",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.85, bm25_score=0.75, theological_score=0.9, passage_score=0.65, final_score=0.9,
        )

        input_data: MultiQueryInput = [(spec_a, [dup_candidate_a]), (spec_b, [dup_candidate_b])]
        pool, manifest = assemble_evidence_pool_with_manifest(input_data)

        assert len(pool) == 1
        queries = manifest.queries_for("E1")
        assert queries == ["A", "B"], f"Expected ['A', 'B'], got {queries}"


# ============================================================
# AC2 — by_query_order의 각 질의 안에서 evidence_id 순서가 원본 RankedCandidate 순위 순서
# ============================================================

class TestAC2ByQueryOrder:
    """AC2: by_query_order의 각 질의 안에서 evidence_id 순서가 그 질의의 원본 RankedCandidate 순위 순서와 동일."""

    def test_by_query_order_preserves_candidate_ranking(self):
        spec = QuerySpec(query="Ranking test", role="primary", order=0)

        c1 = RankedCandidate(
            tsu_id="E-R1", content="Top ranked.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c1",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.95, bm25_score=0.9, theological_score=0.98, passage_score=0.8, final_score=0.98,
        )
        c2 = RankedCandidate(
            tsu_id="E-R2", content="Second ranked.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c2",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.85, bm25_score=0.8, theological_score=0.88, passage_score=0.7, final_score=0.88,
        )
        c3 = RankedCandidate(
            tsu_id="E-R3", content="Third ranked.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c3",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.75, bm25_score=0.7, theological_score=0.78, passage_score=0.6, final_score=0.78,
        )

        input_data: MultiQueryInput = [(spec, [c1, c2, c3])]
        pool, manifest = assemble_evidence_pool_with_manifest(input_data)

        spec_eids = {s.query: eids for s, eids in manifest.by_query_order}
        assert spec_eids["Ranking test"] == ["E-R1", "E-R2", "E-R3"]


# ============================================================
# AC3 — 빈 candidates 리스트를 가진 QuerySpec은 by_query_order에 (spec, [])로 등장
# ============================================================

class TestAC3EmptyCandidatesInManifest:
    """AC3: 빈 candidates 리스트를 가진 QuerySpec은 by_query_order에 (spec, [])로 등장(누락되지 않음)."""

    def test_empty_candidates_appear_in_manifest(self):
        spec_a = QuerySpec(query="A", role="primary", order=0)
        spec_b_empty = QuerySpec(query="B-empty", role="expanded", order=1)
        spec_c = QuerySpec(query="C", role="expanded", order=2)

        c1 = RankedCandidate(
            tsu_id="E-C1", content="Content C.",
            metadata={"source_file": "t.jsonl", "document_id": "d1", "chunk_id": "c1",
                      "source_type": "nae_canonical", "title": "T", "metadata_source": "nae_canonical",
                      "nae_metadata": None, "source_provenance": None,
                      "content_quality": {"noise_type": "NORMAL_CONTENT", "quality_score": 1.0}, "structure": {}},
            vector_score=0.9, bm25_score=0.8, theological_score=0.95, passage_score=0.7, final_score=0.95,
        )

        input_data: MultiQueryInput = [(spec_a, []), (spec_b_empty, []), (spec_c, [c1])]
        pool, manifest = assemble_evidence_pool_with_manifest(input_data)

        manifest_queries = [s.query for s, _ in manifest.by_query_order]
        assert "A" in manifest_queries
        assert "B-empty" in manifest_queries
        assert "C" in manifest_queries
        assert len(manifest.by_query_order) == 3

        for s, eids in manifest.by_query_order:
            if s.query == "A":
                assert eids == [], f"Expected [], got {eids}"
            elif s.query == "B-empty":
                assert eids == [], f"Expected [], got {eids}"


# ============================================================
# AC7 — CUE V7 재현 케이스: tsu_id가 없는 candidate
# ============================================================

class TestAC7TSUMissingManifestKeyMatch:
    """AC7: tsu_id가 없는 candidate에서도 manifest의 evidence_id가 Pool의
    실제 evidence_id와 정확히 일치해야 한다 (CUE V7 재현 케이스)."""

    def test_manifest_key_matches_pool_evidence_id_when_tsu_id_missing(self):
        """tsu_id가 없는 candidate에서도 manifest의 evidence_id가 Pool의
        실제 evidence_id와 정확히 일치해야 한다 (CUE V7 재현 케이스)."""
        c = RankedCandidate(
            tsu_id="", content="some text",
            metadata={"document_id": "doc1", "chunk_id": "c1", "source_file": "f.pdf"},
            final_score=0.9,
        )
        spec = QuerySpec(query="Q1")
        pool, manifest = assemble_evidence_pool_with_manifest([(spec, [c])])

        pool_ids = [e.evidence_id for e in pool.all()]
        assert pool_ids == ["evid:2d127395921e8a34"]
        assert manifest.queries_for(pool_ids[0]) == ["Q1"]
        assert manifest.queries_for("") == []  # 빈 문자열 키가 더 이상 쓰이지 않음


# ============================================================
# Test 11 — Existing Phase 1/2 regression
# ============================================================

class TestPhase1Phase2Regression:
    """Test 11: 기존 Phase 1/2 테스트 반드시 함께 실행, 통과해야 함."""

    def test_evidence_model_tests_pass(self):
        """Phase 1: tests/test_evidence_model.py 실행."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_evidence_model.py", "-v", "--tb=short"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)},
        )
        assert result.returncode == 0, (
            f"Phase 1 tests failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_evidence_pool_tests_pass(self):
        """Phase 2: tests/test_evidence_pool.py 실행."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_evidence_pool.py", "-v", "--tb=short"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(_PROJECT_ROOT)},
        )
        assert result.returncode == 0, (
            f"Phase 2 tests failed:\n{result.stdout}\n{result.stderr}"
        )


# ============================================================
# Static Safety Tests
# ============================================================

class TestStaticSafety:
    """Static checks: core/evidence_assembly.py가 retrieval을 호출하지 않음을 정적으로 확인."""

    def test_no_retrieval_imports(self):
        """core/evidence_assembly.py가 retrieval 관련 클래스를 import하지 않음."""
        source_path = str(_PROJECT_ROOT / "core" / "evidence_assembly.py")
        with open(source_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        forbidden_imports = {
            "QueryProcessor",
            "HybridQueryProcessor",
            "RetrievalEngine",
            "HybridRetriever",
            "QdrantClient",
            "tantivy",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    for forbidden in forbidden_imports:
                        assert forbidden not in name, (
                            f"Forbidden import found: {name} contains {forbidden}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_imports:
                        assert forbidden not in node.module, (
                            f"Forbidden import from found: {node.module} contains {forbidden}"
                        )

    def test_no_retrieval_calls(self):
        """core/evidence_assembly.py가 retrieval 함수를 호출하지 않음."""
        source_path = str(_PROJECT_ROOT / "core" / "evidence_assembly.py")
        with open(source_path, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        forbidden_calls = {"process", "retrieve", "search"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    assert func_name not in forbidden_calls, (
                        f"Forbidden call found: {func_name}"
                    )

    def test_no_qdrant_tantivy_access(self):
        """core/evidence_assembly.py가 Qdrant/Tantivy에 접근하지 않음."""
        source_path = str(_PROJECT_ROOT / "core" / "evidence_assembly.py")
        with open(source_path, "r") as f:
            source = f.read()

        forbidden_patterns = ["qdrant", "tantivy", "QdrantClient"]
        for pattern in forbidden_patterns:
            assert pattern.lower() not in source.lower(), (
                f"Forbidden pattern found: {pattern}"
            )

    def test_no_llm_generation(self):
        """core/evidence_assembly.py가 LLM generation을 수행하지 않음."""
        source_path = str(_PROJECT_ROOT / "core" / "evidence_assembly.py")
        with open(source_path, "r") as f:
            source = f.read()

        forbidden_patterns = ["llm", "chat", "generate", "completion", "openai", "anthropic"]
        for pattern in forbidden_patterns:
            assert pattern.lower() not in source.lower(), (
                f"Forbidden pattern found: {pattern}"
            )

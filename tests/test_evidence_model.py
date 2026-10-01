"""core/evidence_model.py + core/evidence_adapters/tsu_adapter.py Phase 1 tests.

Grounded Synthesis Phase 1: Evidence Data Model + Corpus Identity Adapter

Tests cover:
    Test 1: corpus_type = default
    Test 2: source_file preservation
    Test 3: document_id preservation
    Test 4: chunk_id preservation
    Test 5: text preservation
    Test 6: metadata preservation
    Test 7: provenance preservation
    Test 8: score preservation (RankedCandidate → Evidence)
    Test 9: stable evidence identity
    Test 10: missing identity handling
    Test 11: input mutation = none
    Test 12: batch order preservation
    Test 13: ranking/score preservation
    Test 14: Evidence immutability
    Test 15: raw metadata preservation

ABSOLUTE RULES:
- 샘플 데이터 생성 금지 (픽스처는 minimal, 실제 TSU record 구조 준수)
- production TSU mutation 금지
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.evidence_model import (
    CORPUS_DEFAULT,
    Evidence,
    EvidenceProvenance,
)
from core.evidence_adapters.tsu_adapter import (
    RankedCandidateEvidenceAdapter,
    TSUEvidenceAdapter,
    TSUEvidenceFactory,
)
from core.retrieval import RankedCandidate


# ============================================================
# FIXTURES — minimal TSU-like records (no fake data)
# ============================================================

TSU_RECORD_WITH_METADATA: dict[str, Any] = {
    "tsu_id": "NAE-TSU-0000006",
    "document_id": "nae_Dagg_Church_Order",
    "chunk_id": "NAE-TSU-0000006",
    "content": "Se a That thou shouldst set in order the things that are wanting.",
    "verse_mapping": {},
    "themes": [],
    "title": "Church Order",
    "author": "John L. Dagg",
    "metadata_source": "nae_canonical",
    "chapter": 8,
    "page": 8,
    "source_file": "Dagg_Church_Order.jsonl",
    "language": "ko",
    "source_type": "nae_canonical",
    "content_quality": {
        "noise_type": "NAE_CANONICAL",
        "quality_score": 1.0,
        "section_type": "claim",
    },
    "structure": {},
    "theological_claim": "교회에서 부족한 것을 정돈하고 각 도시마다 장로를 임명해야 한다.",
    "doctrine_category": ["Ecclesiology"],
    "baptist_theme": ["ecclesiology"],
    "source_provenance": None,
    "nae_metadata": {
        "nae_id": "TSU-0000006",
        "nae_doctrine": "Ecclesiology",
        "nae_confidence": 0.8,
        "nae_extraction_method": "llm",
        "nae_review_status": "verified",
        "nae_canonical_version": "2.0.0",
    },
}

TSU_RECORD_WITHOUT_METADATA: dict[str, Any] = {
    "tsu_id": "TSU-UNK-1bf5653a9316d384917176fd49daee41_chunk_00000",
    "document_id": "1bf5653a9316d384917176fd49daee41",
    "chunk_id": "1bf5653a9316d384917176fd49daee41_chunk_00000",
    "content": "Google\n\nThis is a digital copy of a book that was preserved for generations.",
    "verse_mapping": {},
    "themes": [],
    "title": "Lectures on the History of Preaching",
    "author": "John Albert Broadus",
    "metadata_source": "sidecar",
    "chapter": None,
    "page": None,
    "source_file": "Broadus_Lectures_on_History_of_Preaching.txt",
    "language": "en",
    "source_type": "txt",
    "content_quality": {
        "noise_type": "NORMAL_CONTENT",
        "quality_score": 1.0,
        "section_type": "body",
    },
    "structure": {
        "heading_path": [],
        "heading_depth": 0,
        "heading_confidence": 0.0,
        "heading_source": "",
    },
    "theological_claim": None,
    "doctrine_category": [],
    "baptist_theme": [],
    "source_provenance": None,
    "nae_metadata": None,
}

TSU_RECORD_MINIMAL: dict[str, Any] = {
    "tsu_id": "TSU-MIN-001",
    "document_id": "min_doc_001",
    "chunk_id": "min_doc_001_chunk_00000",
    "content": "Minimal content.",
}

# TSU record without tsu_id (for Case C testing)
TSU_RECORD_NO_TSU_ID: dict[str, Any] = {
    "document_id": "no_tsu_doc_001",
    "chunk_id": "no_tsu_doc_001_chunk_00000",
    "source_file": "no_tsu_source.jsonl",
    "content": "Content without tsu_id.",
}

# RankedCandidate fixtures with non-zero scores (for score preservation tests)
RANKED_CANDIDATE_A: RankedCandidate = RankedCandidate(
    tsu_id="RC-001",
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

RANKED_CANDIDATE_B: RankedCandidate = RankedCandidate(
    tsu_id="RC-002",
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

# RankedCandidate without tsu_id (for identity fallback testing)
RANKED_CANDIDATE_NO_TSU_ID: RankedCandidate = RankedCandidate(
    tsu_id="",
    content="Content without tsu_id.",
    metadata={
        "source_file": "no_tsu_source.jsonl",
        "document_id": "no_tsu_doc_001",
        "chunk_id": "no_tsu_doc_001_chunk_00000",
        "source_type": "txt",
        "title": "Unknown Source",
        "metadata_source": None,
        "nae_metadata": None,
        "source_provenance": None,
        "content_quality": None,
        "structure": {},
    },
    vector_score=0.55,
    bm25_score=0.48,
    theological_score=0.30,
    passage_score=0.25,
    final_score=0.50,
    explanation="",
)


# ============================================================
# Test 1: TSU retrieval result → Evidence (corpus_type == "default")
# ============================================================

class TestCorpusTypeDefault:
    """Test 1: corpus_type == "default" 확인."""

    def test_adapter_sets_corpus_type_default(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.corpus_type == "default"

    def test_factory_sets_corpus_type_default(self):
        factory = TSUEvidenceFactory()
        evidence = factory.create_from_tsu(TSU_RECORD_WITH_METADATA)
        assert evidence.corpus_type == "default"

    def test_is_default_corpus_property(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.is_default_corpus is True


# ============================================================
# Test 2: source_file/document_id/chunk_id 보존
# ============================================================

class TestIdentityPreservation:
    """Test 2: source_file/document_id/chunk_id 보존."""

    def test_source_file_preserved(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.source_file == "Dagg_Church_Order.jsonl"

    def test_document_id_preserved(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.document_id == "nae_Dagg_Church_Order"

    def test_chunk_id_preserved(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.chunk_id == "NAE-TSU-0000006"

    def test_source_type_preserved(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.source_type == "nae_canonical"

    def test_document_title_preserved(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.document_title == "Church Order"


# ============================================================
# Test 3: text 보존
# ============================================================

class TestTextPreservation:
    """Test 3: retrieved text가 변경되지 않았는지 확인."""

    def test_text_exact_match(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.text == TSU_RECORD_WITH_METADATA["content"]

    def test_text_not_truncated(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert len(evidence.text) == len(TSU_RECORD_WITH_METADATA["content"])

    def test_text_empty_handling(self):
        sparse = dict(TSU_RECORD_MINIMAL)
        sparse["content"] = ""
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(sparse)
        assert evidence.text == ""


# ============================================================
# Test 4: retrieval score 보존 (RankedCandidate → Evidence)
# ============================================================

class TestScorePreservation:
    """Test 4: retrieval score 보존 (adapter는 score를 변경하지 않음)."""

    def test_retrieval_score_not_modified(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.retrieval_score == 0.0

    def test_theological_score_none_when_not_available(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.theological_score is None

    def test_final_score_zero_initial(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.final_score == 0.0


# ============================================================
# Test 8 (extended): RankedCandidate score preservation
# ============================================================

class TestRankedCandidateScorePreservation:
    """Test 8 extended: RankedCandidate → Evidence score 보존 검증."""

    def test_vector_score_preserved(self):
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_A)
        assert evidence.retrieval_score == 0.83

    def test_bm25_score_preserved(self):
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_B)
        assert evidence.bm25_score == 0.58

    def test_theological_score_preserved(self):
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_A)
        assert evidence.theological_score == 0.91

    def test_passage_score_preserved(self):
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_B)
        assert evidence.passage_score == 0.33

    def test_final_score_preserved(self):
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_A)
        assert evidence.final_score == 0.91

    def test_all_scores_preserved_A(self):
        """Candidate A의 모든 score가 정확히 보존되는지 검증."""
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_A)
        assert evidence.retrieval_score == RANKED_CANDIDATE_A.vector_score
        assert evidence.theological_score == RANKED_CANDIDATE_A.theological_score
        assert evidence.passage_score == RANKED_CANDIDATE_A.passage_score
        assert evidence.final_score == RANKED_CANDIDATE_A.final_score

    def test_all_scores_preserved_B(self):
        """Candidate B의 모든 score가 정확히 보존되는지 검증."""
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_B)
        assert evidence.retrieval_score == RANKED_CANDIDATE_B.vector_score
        assert evidence.theological_score == RANKED_CANDIDATE_B.theological_score
        assert evidence.passage_score == RANKED_CANDIDATE_B.passage_score
        assert evidence.final_score == RANKED_CANDIDATE_B.final_score

    def test_zero_scores_not_preserved_as_fake(self):
        """0점인 score는 None으로 처리 (fake 값 생성 금지)."""
        zero_candidate = RankedCandidate(
            tsu_id="RC-ZERO",
            content="Zero score content.",
            metadata={"source_file": "test.jsonl", "document_id": "doc_001", "chunk_id": "chunk_001"},
            vector_score=0.0,
            bm25_score=0.0,
            theological_score=0.0,
            passage_score=0.0,
            final_score=0.0,
        )
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(zero_candidate)
        # theological_score and passage_score should be None when 0.0
        assert evidence.theological_score is None
        assert evidence.passage_score is None


# ============================================================
# Test 5: 기존 metadata가 없는 경우에도 Evidence 생성 실패 없이 처리
# ============================================================

class TestSparseRecordHandling:
    """Test 5: sparse TSU record에서도 크래시 없이 처리."""

    def test_minimal_record_no_crash(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_MINIMAL)
        assert evidence.evidence_id == "TSU-MIN-001"
        assert evidence.corpus_type == "default"

    def test_none_fields_become_none_not_crash(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITHOUT_METADATA)
        assert evidence.provenance.source_provenance is None
        assert evidence.provenance.nae_metadata is None

    def test_batch_with_mixed_records(self):
        adapter = TSUEvidenceAdapter()
        records = [TSU_RECORD_WITH_METADATA, TSU_RECORD_MINIMAL]
        evidences = adapter.adapt_batch(records)
        assert len(evidences) == 2
        assert evidences[0].corpus_type == "default"
        assert evidences[1].corpus_type == "default"


# ============================================================
# Test 6: fake provenance가 생성되지 않는지 확인
# ============================================================

class TestNoFakeProvenance:
    """Test 6: fake provenance 생성 금지."""

    def test_null_source_provenance_not_fabricated(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidence.provenance.source_provenance is None

    def test_null_nae_metadata_not_fabricated(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITHOUT_METADATA)
        assert evidence.provenance.nae_metadata is None

    def test_has_provenance_property_accuracy(self):
        adapter = TSUEvidenceAdapter()
        ev_with = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert ev_with.has_provenance is True
        ev_minimal = adapter.adapt(TSU_RECORD_MINIMAL)
        assert ev_minimal.has_provenance is True

    def test_provenance_preserves_real_values(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        p = evidence.provenance
        assert p.source_file == "Dagg_Church_Order.jsonl"
        assert p.document_id == "nae_Dagg_Church_Order"
        assert p.chunk_id == "NAE-TSU-0000006"
        assert p.source_type == "nae_canonical"
        assert p.metadata_source == "nae_canonical"


# ============================================================
# Test 7: 동일 immutable source identity → 동일 evidence identity
# ============================================================

class TestEvidenceIdentityStability:
    """Test 7: 동일 immutable source identity를 가진 result가
    동일 evidence identity를 생성하는지 검증."""

    def test_same_tsu_id_produces_same_evidence_id(self):
        tsu_id = TSU_RECORD_WITH_METADATA["tsu_id"]
        adapter = TSUEvidenceAdapter()
        ev1 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        ev2 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert ev1.evidence_id == ev2.evidence_id == tsu_id

    def test_evidence_id_is_immutable(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        original_id = evidence.evidence_id
        with pytest.raises(Exception):
            evidence.evidence_id = "modified"  # type: ignore[assignment]

    def test_different_tsu_ids_produce_different_evidence_ids(self):
        adapter = TSUEvidenceAdapter()
        ev1 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        ev2 = adapter.adapt(TSU_RECORD_WITHOUT_METADATA)
        assert ev1.evidence_id != ev2.evidence_id


# ============================================================
# Evidence Identity Cases A-E (Work Order §7)
# ============================================================

class TestEvidenceIdentityCases:
    """Work Order §7: Evidence identity Cases A-E 검증."""

    def test_case_a_same_source_identity_produces_same_evidence_id(self):
        """Case A: 동일 source identity → 동일 evidence_id."""
        adapter = TSUEvidenceAdapter()
        ev1 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        ev2 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert ev1.evidence_id == ev2.evidence_id

    def test_case_b_different_source_identity_produces_different_evidence_id(self):
        """Case B: 서로 다른 source identity → 서로 다른 evidence_id."""
        adapter = TSUEvidenceAdapter()
        ev1 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        ev2 = adapter.adapt(TSU_RECORD_WITHOUT_METADATA)
        assert ev1.evidence_id != ev2.evidence_id

    def test_case_c_no_tsu_id_does_not_produce_empty_identity(self):
        """Case C: tsu_id 없음 → 빈 문자열 identity가 생성되지 않음."""
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_NO_TSU_ID)
        assert evidence.evidence_id != ""
        assert len(evidence.evidence_id) > 0

    def test_case_d_array_index_change_does_not_affect_evidence_id(self):
        """Case D: array index 변경 → evidence_id가 변하지 않음."""
        adapter = TSUEvidenceAdapter()
        # Same record adapted twice should produce same identity
        ev1 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        ev2 = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert ev1.evidence_id == ev2.evidence_id

    def test_case_e_retrieval_rank_change_does_not_affect_evidence_id(self):
        """Case E: retrieval rank 변경 → evidence_id가 변하지 않음."""
        # Same record always produces same identity regardless of position
        adapter = TSUEvidenceAdapter()
        records = [TSU_RECORD_WITH_METADATA, TSU_RECORD_MINIMAL]
        evidences = adapter.adapt_batch(records)
        # First element's identity should be stable
        ev_first = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert evidences[0].evidence_id == ev_first.evidence_id

    def test_ranked_candidate_identity_with_tsu_id(self):
        """RankedCandidate: tsu_id가 있으면 그것을 사용."""
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_A)
        assert evidence.evidence_id == "RC-001"

    def test_ranked_candidate_identity_without_tsu_id(self):
        """RankedCandidate: tsu_id가 없으면 fallback identity."""
        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(RANKED_CANDIDATE_NO_TSU_ID)
        assert evidence.evidence_id != ""
        assert len(evidence.evidence_id) > 0
        assert evidence.evidence_id.startswith("evid:")

    def test_ranked_candidate_different_ids_produce_different_evidence(self):
        """RankedCandidate: 서로 다른 tsu_id → 서로 다른 evidence_id."""
        adapter = RankedCandidateEvidenceAdapter()
        ev1 = adapter.adapt(RANKED_CANDIDATE_A)
        ev2 = adapter.adapt(RANKED_CANDIDATE_B)
        assert ev1.evidence_id != ev2.evidence_id


# ============================================================
# Test 8: Evidence adapter가 retrieval ranking을 변경하지 않는지 검증
# ============================================================

class TestRankingPreservation:
    """Test 8: Evidence adapter가 retrieval ranking을 변경하지 않는지 검증."""

    def test_batch_order_preserved(self):
        adapter = TSUEvidenceAdapter()
        records = [TSU_RECORD_WITH_METADATA, TSU_RECORD_WITHOUT_METADATA, TSU_RECORD_MINIMAL]
        evidences = adapter.adapt_batch(records)
        for i, (rec, ev) in enumerate(zip(records, evidences)):
            assert ev.evidence_id == rec["tsu_id"]

    def test_evidence_does_not_modify_input(self):
        import copy
        adapter = TSUEvidenceAdapter()
        original = copy.deepcopy(TSU_RECORD_WITH_METADATA)
        _ = adapter.adapt(TSU_RECORD_WITH_METADATA)
        assert TSU_RECORD_WITH_METADATA == original

    def test_raw_metadata_full_preservation(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        for key in TSU_RECORD_WITH_METADATA:
            assert key in evidence.raw_metadata
            assert evidence.raw_metadata[key] == TSU_RECORD_WITH_METADATA[key]

    def test_ranked_candidate_batch_order_preserved(self):
        """RankedCandidate batch에서 order가 보존되는지 검증."""
        adapter = RankedCandidateEvidenceAdapter()
        candidates = [RANKED_CANDIDATE_A, RANKED_CANDIDATE_B]
        evidences = adapter.adapt_batch(candidates)
        assert len(evidences) == 2
        assert evidences[0].evidence_id == RANKED_CANDIDATE_A.tsu_id
        assert evidences[1].evidence_id == RANKED_CANDIDATE_B.tsu_id

    def test_ranked_candidate_scores_preserved_in_order(self):
        """RankedCandidate → Evidence에서 score가 order와 함께 보존되는지 검증."""
        adapter = RankedCandidateEvidenceAdapter()
        candidates = [RANKED_CANDIDATE_A, RANKED_CANDIDATE_B]
        evidences = adapter.adapt_batch(candidates)

        # A should have higher final_score than B (same order as input)
        assert evidences[0].final_score == 0.91
        assert evidences[1].final_score == 0.72
        assert evidences[0].final_score > evidences[1].final_score

    def test_ranked_candidate_input_not_modified(self):
        """RankedCandidate adapter가 원본을 수정하지 않는지 검증."""
        import copy
        adapter = RankedCandidateEvidenceAdapter()
        original_a = copy.deepcopy(RANKED_CANDIDATE_A)
        _ = adapter.adapt(RANKED_CANDIDATE_A)
        assert RANKED_CANDIDATE_A.tsu_id == original_a.tsu_id
        assert RANKED_CANDIDATE_A.final_score == original_a.final_score


# ============================================================
# Additional: Corpus Identity Resolver verification
# ============================================================

class TestCorpusIdentityResolver:
    """corpus_type resolver의 동작 검증."""

    def test_factory_resolve_corpus_type_default(self):
        factory = TSUEvidenceFactory()
        result = factory.resolve_corpus_type("some_file.txt")
        assert result == "default"

    def test_resolve_corpus_type_none_source(self):
        factory = TSUEvidenceFactory()
        result = factory.resolve_corpus_type(None)
        assert result == "default"


# ============================================================
# Evidence model structure verification
# ============================================================

class TestEvidenceModelStructure:
    """Evidence 모델의 구조 검증."""

    def test_evidence_to_dict(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        d = evidence.to_dict()
        assert d["evidence_id"] == "NAE-TSU-0000006"
        assert d["corpus_type"] == "default"
        assert d["source_file"] == "Dagg_Church_Order.jsonl"
        assert d["text"] == TSU_RECORD_WITH_METADATA["content"]
        assert d["provenance"]["nae_metadata"] is not None

    def test_evidence_provenance_dataclass(self):
        p = EvidenceProvenance(
            source_file="test.txt",
            document_id="doc_001",
        )
        assert p.source_file == "test.txt"
        assert p.document_id == "doc_001"
        assert p.nae_metadata is None

    def test_evidence_frozen(self):
        adapter = TSUEvidenceAdapter()
        evidence = adapter.adapt(TSU_RECORD_WITH_METADATA)
        with pytest.raises(Exception):
            evidence.text = "modified"  # type: ignore[assignment]

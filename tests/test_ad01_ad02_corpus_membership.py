"""tests/test_ad01_ad02_corpus_membership.py - AD-01/AD-02 단위 검증.

AD-01: registry corpus_membership -> Evidence.corpus_type 전달
AD-02: retrieval relevance + corpus role preservation (ranking 무변경)

격리 환경(worktree isolated fixture)에서만 실행 - production data 사용 금지.
"""

import json
import os
from unittest import mock

import pytest

from core.evidence_adapters.tsu_adapter import (
    RankedCandidateEvidenceAdapter,
    TSUEvidenceFactory,
)
from core.evidence_model import CORPUS_DEFAULT, CORPUS_PERSONAL
from core.retrieval import RankedCandidate


class TestAD01ResolveCorpusType:
    """TSUEvidenceFactory.resolve_corpus_type() - registry 기반 결정."""

    def test_no_document_id_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type()
        assert result == CORPUS_DEFAULT

    def test_empty_document_id_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="")
        assert result == CORPUS_DEFAULT

    def test_nonexistent_document_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type(
            document_id="nonexistent_doc_id_00000"
        )
        assert result == CORPUS_DEFAULT

    def test_missing_corpus_membership_field_returns_default(self, tmp_path):
        reg = {"documents": {"some_doc_id": {"source_file": "test.txt"}}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_invalid_corpus_membership_returns_default(self, tmp_path):
        reg = {"documents": {"some_doc_id": {"corpus_membership": "invalid_value"}}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_registry_file_not_found_returns_default(self):
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", "/nonexistent/path.json"):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_corrupted_registry_returns_default(self, tmp_path):
        reg_file = tmp_path / "documents.json"
        reg_file.write_text("{invalid json", encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT


class TestAD01TSUEvidenceFactory:
    """TSUEvidenceFactory - document_id 기반 corpus_type."""

    def test_init_with_personal_document(self):
        factory = TSUEvidenceFactory(document_id="6f323b08ce388551d2fa772c756a828e")
        assert factory._corpus_type == CORPUS_PERSONAL

    def test_init_with_default_document(self):
        factory = TSUEvidenceFactory(document_id="nonexistent_doc_id_00000")
        assert factory._corpus_type == CORPUS_DEFAULT

    def test_create_from_tsu_preserves_corpus_type(self):
        factory = TSUEvidenceFactory(document_id="6f323b08ce388551d2fa772c756a828e")
        tsu_record = {
            "tsu_id": "TSU-TEST-001",
            "source_file": "test.txt",
            "document_id": "6f323b08ce388551d2fa772c756a828e",
            "content": "test content",
        }
        evidence = factory.create_from_tsu(tsu_record)
        assert evidence.corpus_type == CORPUS_PERSONAL


class TestAD02RankedCandidateEvidenceAdapter:
    """RankedCandidateEvidenceAdapter - per-candidate corpus_type."""

    def _make_candidate(self, final_score: float, document_id: str) -> RankedCandidate:
        return RankedCandidate(
            tsu_id=f"TSU-AD02-{document_id[:8]}",
            content="test evidence text",
            vector_score=0.85,
            bm25_score=0.72,
            final_score=final_score,
            metadata={
                "source_file": f"fixture_{document_id}.txt",
                "document_id": document_id,
                "chunk_id": "chunk-1",
                "source_type": "txt",
                "title": "Test Document",
            },
        )

    def test_adapt_personal_fixture_a(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        candidate = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL
        assert evidence.retrieval_score == 0.85
        assert evidence.bm25_score == 0.72
        assert evidence.final_score == 0.78
        assert evidence.provenance.source_file == "fixture_6f323b08ce388551d2fa772c756a828e.txt"
        assert evidence.provenance.document_id == "6f323b08ce388551d2fa772c756a828e"

    def test_adapt_nonexistent_document_default(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="nonexistent_doc_id_00000")
        candidate = self._make_candidate(0.78, "nonexistent_doc_id_00000")
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_DEFAULT

    def test_adapt_batch_preserves_order(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        c1 = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
        c2 = self._make_candidate(0.82, "nonexistent_doc_id_00000")
        evidences = adapter.adapt_batch([c1, c2])
        assert len(evidences) == 2
        assert evidences[0].corpus_type == CORPUS_PERSONAL
        assert evidences[1].corpus_type == CORPUS_DEFAULT
        assert evidences[0].final_score == c1.final_score
        assert evidences[1].final_score == c2.final_score

    def test_adapt_always_uses_per_candidate_lookup(self):
        """adapt()는 항상 per-candidate registry lookup을 사용함 (AD-02 설계)."""
        adapter = RankedCandidateEvidenceAdapter(
            corpus_type=CORPUS_DEFAULT,
            document_id="6f323b08ce388551d2fa772c756a828e",
        )
        candidate = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL


class TestAD02RankingUnchanged:
    """AD-02: corpus_type 태깅이 ranking/scoring에 영향을 주지 않음."""

    def _make_candidate(self, final_score: float, document_id: str) -> RankedCandidate:
        return RankedCandidate(
            tsu_id=f"TSU-RANK-{document_id[:8]}",
            content="test",
            vector_score=0.5,
            bm25_score=0.6,
            final_score=final_score,
            metadata={
                "source_file": f"doc_{document_id}.txt",
                "document_id": document_id,
                "chunk_id": "chunk-1",
                "source_type": "txt",
            },
        )

    def test_personal_candidate_does_not_boost_score(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        original_score = 0.78
        candidate = self._make_candidate(original_score, "6f323b08ce388551d2fa772c756a828e")
        evidence = adapter.adapt(candidate)
        assert evidence.final_score == original_score
        assert evidence.retrieval_score == candidate.vector_score
        assert evidence.bm25_score == candidate.bm25_score

    def test_mixed_corpus_candidates_preserve_original_order(self):
        personal_candidate = self._make_candidate(0.85, "6f323b08ce388551d2fa772c756a828e")
        default_candidate = self._make_candidate(0.92, "nonexistent_doc_id_00000")
        personal_adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        default_adapter = RankedCandidateEvidenceAdapter(document_id="nonexistent_doc_id_00000")
        personal_evidence = personal_adapter.adapt(personal_candidate)
        default_evidence = default_adapter.adapt(default_candidate)
        assert personal_evidence.final_score == 0.85
        assert default_evidence.final_score == 0.92
        assert default_evidence.final_score > personal_evidence.final_score


class TestIsolatedFixtureVerification:
    """worktree isolated registry의 fixture A/B가 실제로 personal로 인식되는지."""

    @pytest.fixture(autouse=True)
    def _verify_isolated_registry(self):
        from core.config import DEFAULT_REGISTRY_PATH
        reg_path = os.path.abspath(DEFAULT_REGISTRY_PATH)
        assert os.path.isfile(reg_path), f"Registry file not found: {reg_path}"
        with open(reg_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        docs = registry.get("documents", {})
        fixture_a = docs.get("6f323b08ce388551d2fa772c756a828e")
        assert fixture_a is not None, "Fixture A (John 15) not in isolated registry"
        assert fixture_a.get("corpus_membership") == "personal", \
            f"Fixture A corpus_membership = {fixture_a.get('corpus_membership')!r}, expected 'personal'"
        fixture_b = docs.get("5ce2824e947da15da8893fbb45c07239")
        assert fixture_b is not None, "Fixture B (1 Cor 12) not in isolated registry"
        assert fixture_b.get("corpus_membership") == "personal", \
            f"Fixture B corpus_membership = {fixture_b.get('corpus_membership')!r}, expected 'personal'"

    def test_fixture_a_resolve_personal(self):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="6f323b08ce388551d2fa772c756a828e")
        assert result == CORPUS_PERSONAL

    def test_fixture_b_resolve_personal(self):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="5ce2824e947da15da8893fbb45c07239")
        assert result == CORPUS_PERSONAL

    def test_fixture_a_evidence_personal(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        candidate = RankedCandidate(
            tsu_id="TSU-JHN-6f323b08",
            content="test vine text",
            vector_score=0.65, bm25_score=0.70, final_score=0.67,
            metadata={
                "source_file": "rpv_fixture_A_john15_sermon_notes.txt",
                "document_id": "6f323b08ce388551d2fa772c756a828e",
                "chunk_id": "chunk-1", "source_type": "txt",
            },
        )
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL

    def test_fixture_b_evidence_personal(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="5ce2824e947da15da8893fbb45c07239")
        candidate = RankedCandidate(
            tsu_id="TSU-UNK-5ce2824e",
            content="test gifts text",
            vector_score=0.55, bm25_score=0.60, final_score=0.57,
            metadata={
                "source_file": "rpv_fixture_B_spirit_gifts_notes.txt",
                "document_id": "5ce2824e947da15da8893fbb45c07239",
                "chunk_id": "chunk-1", "source_type": "txt",
            },
        )
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL

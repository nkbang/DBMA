"""tests/test_ad01_ad02_corpus_regression.py — F-2 AD-01/AD-02 regression tests.

AD-01: registry corpus_membership -> Evidence.corpus_type 전달
AD-02: retrieval relevance + corpus role preservation (ranking 무변경)

격리 환경(tmp_path + monkeypatch)에서만 실행 - production data 사용 금지.
"""

import json
import tempfile

import pytest

from core.evidence_model import CORPUS_DEFAULT, CORPUS_PERSONAL
from core.evidence_adapters.tsu_adapter import (
    RankedCandidateEvidenceAdapter,
    TSUEvidenceFactory,
)
from core.retrieval import RankedCandidate


def _make_registry(documents: dict) -> str:
    """Create a minimal documents.json in a temp directory."""
    tmp = tempfile.mkdtemp()
    path = f"{tmp}/documents.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"documents": documents}, f)
    return path


class TestCaseAPersonalCorpus:
    """registry corpus_membership='personal' -> Evidence.corpus_type == 'personal'."""

    def test_adapt_path_personal(self, monkeypatch):
        reg_path = _make_registry(
            {"personal_doc": {"corpus_membership": "personal"}}
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        candidate = RankedCandidate(
            tsu_id="RC-A-001",
            content="test personal evidence",
            metadata={
                "source_file": "personal_notes.jsonl",
                "document_id": "personal_doc",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.85,
            bm25_score=0.72,
            final_score=0.78,
        )

        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(candidate)

        assert evidence.corpus_type == CORPUS_PERSONAL


class TestCaseBDefaultCorpus:
    """registry corpus_membership='default' -> Evidence.corpus_type == 'default'."""

    def test_adapt_path_default(self, monkeypatch):
        reg_path = _make_registry(
            {"default_doc": {"corpus_membership": "default"}}
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        candidate = RankedCandidate(
            tsu_id="RC-B-001",
            content="test default evidence",
            metadata={
                "source_file": "default_notes.jsonl",
                "document_id": "default_doc",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.85,
            bm25_score=0.72,
            final_score=0.78,
        )

        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(candidate)

        assert evidence.corpus_type == CORPUS_DEFAULT


class TestCaseCFailSafe:
    """document_id 없음 또는 registry에 없는 document -> safely default."""

    def test_adapt_no_document_id(self, monkeypatch):
        reg_path = _make_registry(
            {"some_doc": {"corpus_membership": "personal"}}
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        candidate = RankedCandidate(
            tsu_id="RC-C-001",
            content="test no doc_id evidence",
            metadata={
                "source_file": "no_docid.jsonl",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.85,
            bm25_score=0.72,
            final_score=0.78,
        )

        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(candidate)

        assert evidence.corpus_type == CORPUS_DEFAULT

    def test_adapt_unknown_document_id(self, monkeypatch):
        reg_path = _make_registry(
            {"known_doc": {"corpus_membership": "personal"}}
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        candidate = RankedCandidate(
            tsu_id="RC-C-002",
            content="test unknown doc evidence",
            metadata={
                "source_file": "unknown_doc.jsonl",
                "document_id": "nonexistent_doc_999",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.85,
            bm25_score=0.72,
            final_score=0.78,
        )

        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(candidate)

        assert evidence.corpus_type == CORPUS_DEFAULT


class TestCaseDMixedCorpus:
    """동일 batch에서 personal + default candidate가 각자 자신의 corpus_type을 얻는다."""

    def test_mixed_candidates_independent_corpus(self, monkeypatch):
        reg_path = _make_registry(
            {
                "personal_doc": {"corpus_membership": "personal"},
                "default_doc": {"corpus_membership": "default"},
            }
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        personal_candidate = RankedCandidate(
            tsu_id="RC-D-PERSONAL",
            content="personal evidence text",
            metadata={
                "source_file": "personal_notes.jsonl",
                "document_id": "personal_doc",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.85,
            bm25_score=0.72,
            final_score=0.78,
        )

        default_candidate = RankedCandidate(
            tsu_id="RC-D-DEFAULT",
            content="default evidence text",
            metadata={
                "source_file": "default_notes.jsonl",
                "document_id": "default_doc",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=0.92,
            bm25_score=0.80,
            final_score=0.86,
        )

        adapter = RankedCandidateEvidenceAdapter()
        personal_evidence = adapter.adapt(personal_candidate)
        default_evidence = adapter.adapt(default_candidate)

        assert personal_evidence.corpus_type == CORPUS_PERSONAL
        assert default_evidence.corpus_type == CORPUS_DEFAULT


class TestCaseEScorePreservation:
    """corpus_membership resolution 전후 candidate score가 변하지 않는다."""

    def test_scores_unchanged_after_corpus_resolution(self, monkeypatch):
        reg_path = _make_registry(
            {"score_doc": {"corpus_membership": "personal"}}
        )
        monkeypatch.setattr(
            "core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", reg_path
        )

        original_vector = 0.65
        original_bm25 = 0.70
        original_final = 0.67

        candidate = RankedCandidate(
            tsu_id="RC-E-001",
            content="score preservation test",
            metadata={
                "source_file": "score_doc.jsonl",
                "document_id": "score_doc",
                "chunk_id": "chunk_001",
                "source_type": "txt",
            },
            vector_score=original_vector,
            bm25_score=original_bm25,
            final_score=original_final,
        )

        adapter = RankedCandidateEvidenceAdapter()
        evidence = adapter.adapt(candidate)

        assert evidence.corpus_type == CORPUS_PERSONAL
        assert evidence.retrieval_score == original_vector
        assert evidence.bm25_score == original_bm25
        assert evidence.final_score == original_final

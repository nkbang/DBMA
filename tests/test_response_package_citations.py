"""Regression test — ResponsePackage must preserve citations (SPRINT17-Phase5).

ResponseFormatter.format() previously accepted a `citations` argument but
never passed it into the ResponsePackage it constructed, so
QueryProcessor.process()'s citations were silently discarded. This test
guards against that regression.
"""

import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import (
    Citation,
    CitationBuilder,
    ResponseFormatter,
    RankedCandidate,
    ParsedQuery,
    PerformanceMetrics,
)


def _make_candidate(tsu_id: str, book_id: str, chapter: int, verse: int) -> RankedCandidate:
    return RankedCandidate(
        tsu_id=tsu_id,
        content="In the beginning God created the heavens and the earth.",
        metadata={"verse_mapping": {"book_id": book_id, "chapter": chapter, "verse_start": verse}},
        final_score=0.87,
    )


class TestResponsePackageCitations:
    def test_format_preserves_citations(self):
        """ResponseFormatter.format() must carry citations into ResponsePackage."""
        candidates = [_make_candidate("TSU-GEN-000001", "GEN", 1, 1)]
        parsed_query = ParsedQuery(original_query="test query", intent="unknown")
        citation_builder = CitationBuilder()
        citations = citation_builder.build_citations(candidates)

        formatter = ResponseFormatter()
        response = formatter.format(
            parsed_query, candidates, scripture_contexts=[],
            llm_context_block="context", citations=citations,
            metrics=PerformanceMetrics(),
        )

        assert response.citations == citations
        assert len(response.citations) == 1
        assert isinstance(response.citations[0], Citation)
        assert "GEN 1:1" in str(response.citations[0])

    def test_to_dict_includes_citations(self):
        """ResponsePackage.to_dict() must expose citations for serialization."""
        candidates = [_make_candidate("TSU-GEN-000001", "GEN", 1, 1)]
        parsed_query = ParsedQuery(original_query="test query", intent="unknown")
        citations = CitationBuilder().build_citations(candidates)

        response = ResponseFormatter().format(
            parsed_query, candidates, scripture_contexts=[],
            llm_context_block="context", citations=citations,
            metrics=PerformanceMetrics(),
        )

        d = response.to_dict()
        assert "citations" in d
        assert d["citations"] == [c.__dict__ for c in citations]
        json.dumps(d["citations"])  # must be JSON serializable

    def test_empty_candidates_yields_empty_citations(self):
        """No candidates -> no citations, but the field must still exist."""
        parsed_query = ParsedQuery(original_query="test query", intent="unknown")
        response = ResponseFormatter().format(
            parsed_query, [], scripture_contexts=[],
            llm_context_block="", citations=[],
            metrics=PerformanceMetrics(),
        )

        assert response.citations == []

    def test_citation_fields_and_confidence_passthrough(self):
        """Citation must carry title/author/document_id/evidence_confidence from
        TSU metadata, and evidence_confidence must be None when provenance is absent
        (SPRINT19-B provenance is optional on older TSU records)."""
        with_provenance = RankedCandidate(
            tsu_id="TSU-JHN-000001",
            content="For God so loved the world.",
            metadata={
                "verse_mapping": {"book_id": "JHN", "chapter": 3, "verse_start": 16},
                "title": "Gospel Commentary",
                "author": "J. Doe",
                "document_id": "doc-abc123",
                "provenance": {"confidence": 0.83},
            },
            final_score=0.9234,
        )
        without_provenance = _make_candidate("TSU-GEN-000001", "GEN", 1, 1)

        citations = CitationBuilder().build_citations([with_provenance, without_provenance])

        assert citations[0].source_title == "Gospel Commentary"
        assert citations[0].source_author == "J. Doe"
        assert citations[0].document_id == "doc-abc123"
        assert citations[0].evidence_confidence == 0.83
        assert citations[0].retrieval_score == with_provenance.final_score

        assert citations[1].evidence_confidence is None
        assert citations[1].retrieval_score == without_provenance.final_score

    def test_citation_source_metadata_passthrough(self):
        """Citation must carry source_file/language/source_type from TSU
        metadata (SPRINT20-E registry propagation), and stay None when the
        TSU record does not have them (no inference/fallback generation)."""
        with_source_metadata = RankedCandidate(
            tsu_id="TSU-JHN-000001",
            content="For God so loved the world.",
            metadata={
                "verse_mapping": {"book_id": "JHN", "chapter": 3, "verse_start": 16},
                "source_file": "5. 요한복음1.pdf",
                "language": "ko",
                "source_type": "pdf",
            },
            final_score=0.9234,
        )
        without_source_metadata = _make_candidate("TSU-GEN-000001", "GEN", 1, 1)

        citations = CitationBuilder().build_citations(
            [with_source_metadata, without_source_metadata]
        )

        assert citations[0].source_file == "5. 요한복음1.pdf"
        assert citations[0].language == "ko"
        assert citations[0].source_type == "pdf"

        assert citations[1].source_file is None
        assert citations[1].language is None
        assert citations[1].source_type is None

        d = ResponseFormatter().format(
            ParsedQuery(original_query="q", intent="unknown"),
            [with_source_metadata], scripture_contexts=[],
            llm_context_block="", citations=citations,
            metrics=PerformanceMetrics(),
        ).to_dict()
        assert d["citations"][0]["source_file"] == "5. 요한복음1.pdf"
        assert d["citations"][0]["language"] == "ko"
        assert d["citations"][0]["source_type"] == "pdf"
        json.dumps(d["citations"])  # must remain JSON serializable


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

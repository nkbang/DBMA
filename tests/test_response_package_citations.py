"""Regression test — ResponsePackage must preserve citations (SPRINT17-Phase5).

ResponseFormatter.format() previously accepted a `citations` argument but
never passed it into the ResponsePackage it constructed, so
QueryProcessor.process()'s citations were silently discarded. This test
guards against that regression.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import (
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
        assert "GEN 1:1" in response.citations[0]

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
        assert d["citations"] == citations

    def test_empty_candidates_yields_empty_citations(self):
        """No candidates -> no citations, but the field must still exist."""
        parsed_query = ParsedQuery(original_query="test query", intent="unknown")
        response = ResponseFormatter().format(
            parsed_query, [], scripture_contexts=[],
            llm_context_block="", citations=[],
            metrics=PerformanceMetrics(),
        )

        assert response.citations == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

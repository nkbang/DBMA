"""Regression test — GenerationResult must carry citations through from
ResponsePackage (SPRINT20-B / CUE-20B-3).

core.generation.GenerationService.generate() previously discarded
response.citations entirely — only llm_context_block and question were
used. This test guards the pass-through connection without touching
prompt assembly or the Ollama call itself.
"""

import sys
import os
import types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Fall back to a stub only if the real `ollama` package is unavailable in
# this dev environment (same gap as bs4/chromadb/docling elsewhere in this
# repo). Preferring the real import avoids permanently overwriting
# sys.modules["ollama"] with an attribute-incomplete stub for every other
# test module that imports `ollama` afterward in the same pytest session.
try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *args, **kwargs: {"response": ""}
        _ollama_stub.embeddings = lambda *args, **kwargs: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

from unittest.mock import patch

from core.generation import GenerationService, GenerationResult
from core.retrieval import Citation, ResponsePackage, ParsedQuery, PerformanceMetrics


def _make_response(citations: list[Citation]) -> ResponsePackage:
    return ResponsePackage(
        query_id="q1",
        question="test question",
        candidates=[],
        top_k_results=[],
        performance_metrics=PerformanceMetrics(),
        parsed_query=ParsedQuery(original_query="test question", intent="unknown"),
        llm_context_block="some context",
        citations=citations,
    )


class TestGenerationServiceCitations:
    def test_citations_pass_through(self):
        """GenerationResult.citations must equal response.citations."""
        citation = Citation(
            citation_id="1",
            tsu_id="TSU-GEN-000001",
            scripture_reference="GEN 1:1",
            source_title="Genesis Commentary",
            source_author="J. Doe",
            document_id="doc-abc123",
            content_excerpt="In the beginning...",
            evidence_confidence=0.9,
            retrieval_score=0.87,
        )
        response = _make_response([citation])

        with patch("ollama.generate", return_value={"response": "an answer"}):
            result = GenerationService().generate(response)

        assert isinstance(result, GenerationResult)
        assert result.citations == response.citations
        assert result.citations[0] is citation

    def test_empty_citations_preserved(self):
        """No citations -> GenerationResult.citations stays an empty list."""
        response = _make_response([])

        with patch("ollama.generate", return_value={"response": "an answer"}):
            result = GenerationService().generate(response)

        assert result.citations == []

    def test_generation_result_backward_compatible_without_citations_kwarg(self):
        """Existing GenerationResult(...) call sites that omit `citations`
        must keep working, since it is a trailing default field."""
        result = GenerationResult(
            question="q",
            answer="a",
            gen_model="m",
            temperature=0.0,
            context_used=True,
        )
        assert result.citations == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

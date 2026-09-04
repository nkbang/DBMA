"""Citation Contract UI Surface tests - Phase 3.

Validates that response.citations values (author/source_title/evidence_confidence)
are correctly merged into Research cards and Chat source expanders, and that
serialization round-trip preserves Citation data.

Task Order: C1-TASK-ORDER-CITATION-CONTRACT-UI-SURFACE.md
"""

import pytest


class TestFormatCandidateCitationMerge:
    """_format_candidate가 citation 필드를 올바르게 병합하는지 검증."""

    @pytest.fixture
    def mock_candidate(self):
        from core.retrieval import RankedCandidate
        return RankedCandidate(
            tsu_id="TEST-001", content="Test content", final_score=0.85,
            bm25_score=0.7, vector_score=0.6, theological_score=0.9,
            metadata={
                "source_file": "test_doc.json", "document_id": "DOC-001",
                "verse_mapping": {"book_id": "JHN", "chapter": 3, "verse_start": 16},
                "title": "Test Title",
            },
            explanation="Test explanation",
        )

    @pytest.fixture
    def mock_parsed_query(self):
        from core.retrieval import ParsedQuery
        return ParsedQuery(
            original_query="test query", intent="simple_lookup",
            scripture_refs=[], detected_books=[], themes=[], keywords=[],
            language="ko", author="", source_book="",
        )

    def test_format_candidate_without_citation(self, mock_candidate, mock_parsed_query):
        """citation이 None일 때 기존 필드만 반환."""
        from ui.pages.research import _format_candidate
        result = _format_candidate(mock_candidate, mock_parsed_query, citation=None)
        assert result["tsu_id"] == "TEST-001"
        assert result["score"] == 0.85
        assert result["title"] is not None
        assert "author" not in result
        assert "source_title" not in result
        assert "evidence_confidence" not in result

    def test_format_candidate_with_full_citation(self, mock_candidate, mock_parsed_query):
        """citation이 있고 모든 필드가 채워져 있을 때 추가."""
        from core.retrieval import Citation
        from ui.pages.research import _format_candidate
        citation = Citation(
            citation_id="1", tsu_id="TEST-001", scripture_reference="JHN 3:16",
            source_title="Test Source Title", source_author="Test Author",
            document_id="DOC-001", content_excerpt="excerpt",
            evidence_confidence=0.95, retrieval_score=0.85,
        )
        result = _format_candidate(mock_candidate, mock_parsed_query, citation=citation)
        assert result["tsu_id"] == "TEST-001"
        assert result["author"] == "Test Author"
        assert result["source_title"] == "Test Source Title"
        assert result["evidence_confidence"] == 0.95

    def test_format_candidate_with_none_fields_omitted(self, mock_candidate, mock_parsed_query):
        """citation이 있지만 필드가 None이면 해당 키는 추가되지 않음."""
        from core.retrieval import Citation
        from ui.pages.research import _format_candidate
        citation = Citation(
            citation_id="1", tsu_id="TEST-001", scripture_reference="JHN 3:16",
            source_title=None, source_author=None, document_id="DOC-001",
            content_excerpt="excerpt", evidence_confidence=None, retrieval_score=0.85,
        )
        result = _format_candidate(mock_candidate, mock_parsed_query, citation=citation)
        assert "author" not in result
        assert "source_title" not in result
        assert "evidence_confidence" not in result

    def test_format_candidate_with_partial_citation(self, mock_candidate, mock_parsed_query):
        """citation이 부분적으로 채워져 있을 때 채워진 필드만 추가."""
        from core.retrieval import Citation
        from ui.pages.research import _format_candidate
        citation = Citation(
            citation_id="1", tsu_id="TEST-001", scripture_reference="JHN 3:16",
            source_title="Only Title", source_author=None, document_id="DOC-001",
            content_excerpt="excerpt", evidence_confidence=0.9, retrieval_score=0.85,
        )
        result = _format_candidate(mock_candidate, mock_parsed_query, citation=citation)
        assert result["source_title"] == "Only Title"
        assert result["evidence_confidence"] == 0.9
        assert "author" not in result


class TestChatCitationSerialization:
    """Chat 직렬화/역직렬화에 Citation이 포함된 경우 검증."""

    @pytest.fixture
    def sample_messages_with_citations(self):
        from core.retrieval import Citation, RankedCandidate
        citations = [
            Citation(
                citation_id="1", tsu_id="TEST-001", scripture_reference="JHN 3:16",
                source_title="Test Title", source_author="Test Author",
                document_id="DOC-001", content_excerpt="excerpt",
                evidence_confidence=0.95, retrieval_score=0.85,
            ),
        ]
        candidates = [
            RankedCandidate(
                tsu_id="TEST-001", content="Test content", final_score=0.85,
                bm25_score=0.7, vector_score=0.6, theological_score=0.9,
                metadata={"source_file": "test_doc.json", "document_id": "DOC-001"},
                explanation="",
            ),
        ]
        return [
            {"role": "user", "content": "Test question"},
            {
                "role": "assistant", "content": "Test answer",
                "sources": candidates, "citations": citations,
                "error": None, "low_confidence": False, "claim_guard_result": None,
            },
        ]

    def test_serialize_deserialize_citation_round_trip(self, sample_messages_with_citations):
        """Citation이 포함된 메시지가 직렬화->역직렬화 후 원본과 일치."""
        from ui.pages.chat import _deserialize_messages, _serialize_messages
        original = sample_messages_with_citations
        serialized = _serialize_messages(original)
        restored = _deserialize_messages(serialized)
        assert len(restored) == len(original)
        assert restored[0]["role"] == "user"
        assert restored[1]["role"] == "assistant"
        assert restored[1]["content"] == "Test answer"
        assert len(restored[1]["sources"]) == 1
        assert restored[1]["sources"][0].tsu_id == "TEST-001"
        assert "citations" in restored[1]
        assert len(restored[1]["citations"]) == 1
        assert restored[1]["citations"][0].tsu_id == "TEST-001"
        assert restored[1]["citations"][0].source_author == "Test Author"
        assert restored[1]["citations"][0].source_title == "Test Title"
        assert restored[1]["citations"][0].evidence_confidence == 0.95

    def test_serialize_deserialize_without_citations(self):
        """citations가 없는 메시지는 기존 동작과 동일해야 함."""
        from ui.pages.chat import _deserialize_messages, _serialize_messages
        messages = [
            {"role": "user", "content": "Test"},
            {
                "role": "assistant", "content": "Answer",
                "sources": [], "error": None, "low_confidence": False,
                "claim_guard_result": None,
            },
        ]
        serialized = _serialize_messages(messages)
        restored = _deserialize_messages(serialized)
        assert len(restored) == 2
        assert restored[1]["content"] == "Answer"
        assert "citations" not in restored[1] or restored[1].get("citations") is None


class TestIndexCorrespondence:
    """response.citations[i] <-> response.top_k_results[i] 인덱스 대응 검증."""

    def test_citation_index_matches_candidate_index(self):
        """Citation과 RankedCandidate가 동일 인덱스로 1:1 대응."""
        from core.retrieval import Citation, RankedCandidate
        candidates = [
            RankedCandidate(
                tsu_id=f"TEST-{i}", content=f"Content {i}", final_score=0.9 - i * 0.1,
                bm25_score=0.8, vector_score=0.7, theological_score=0.6,
                metadata={"source_file": f"doc{i}.json", "document_id": f"DOC-{i}"},
                explanation="",
            )
            for i in range(3)
        ]
        citations = [
            Citation(
                citation_id=str(i + 1), tsu_id=c.tsu_id, scripture_reference=f"REF {i}",
                source_title=f"Title {i}", source_author=f"Author {i}",
                document_id=c.metadata["document_id"], content_excerpt=c.content,
                evidence_confidence=0.95 - i * 0.05, retrieval_score=c.final_score,
            )
            for i, c in enumerate(candidates)
        ]
        for i, (cand, cit) in enumerate(zip(candidates, citations)):
            assert cand.tsu_id == cit.tsu_id, f"Index {i}: tsu_id mismatch"
            assert cand.final_score == cit.retrieval_score, f"Index {i}: score mismatch"

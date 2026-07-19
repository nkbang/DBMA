"""Regression test — core/heading_extractor.py (SPRINT29-C).

Metadata-aware heading foundation: deterministic ATX-only detection,
boundary-preserving (chunks never mutated), hierarchical path with
inheritance across chunks, and an explicit no-op on heading-less text
(no PDF heuristic).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.heading_extractor import (
    extract_headings,
    annotate_chunks,
    HeadingStack,
    ChunkHeading,
)


class TestExtractHeadings:
    def test_atx_levels_and_titles(self):
        text = "# One\n\nbody\n\n### Three deep\n\nbody"
        assert extract_headings(text) == [(1, "One"), (3, "Three deep")]

    def test_closed_atx_trailing_hashes_stripped(self):
        assert extract_headings("## Section ##") == [(2, "Section")]

    def test_hashtag_without_space_is_not_heading(self):
        assert extract_headings("#hashtag and #1 place") == []

    def test_headingless_text_is_empty(self):
        assert extract_headings("plain pdf-derived text with no markers.") == []

    def test_empty_and_none_safe(self):
        assert extract_headings("") == []
        assert extract_headings(None) == []


class TestHeadingStackNesting:
    def test_child_nests_under_parent(self):
        s = HeadingStack()
        assert s.apply_chunk("# Chapter 1").heading_path == ["Chapter 1"]
        assert s.apply_chunk("## Section 1.1").heading_path == ["Chapter 1", "Section 1.1"]

    def test_sibling_replaces_and_drops_deeper(self):
        s = HeadingStack()
        s.apply_chunk("# Chapter 1")
        s.apply_chunk("## Section 1.1")
        s.apply_chunk("### Sub 1.1.1")
        # a new H2 sibling must drop the H3 beneath the previous H2
        assert s.apply_chunk("## Section 1.2").heading_path == ["Chapter 1", "Section 1.2"]

    def test_higher_level_resets_lower(self):
        s = HeadingStack()
        s.apply_chunk("# A")
        s.apply_chunk("## A.1")
        assert s.apply_chunk("# B").heading_path == ["B"]


class TestAnnotateChunks:
    def test_inheritance_across_chunks(self):
        chunks = [
            "# Chapter 1\n\nintro",
            "continuation with no heading",
            "## Section 1.1\n\ncontent",
        ]
        result = annotate_chunks(chunks)
        assert [r.heading_path for r in result] == [
            ["Chapter 1"],
            ["Chapter 1"],           # inherited
            ["Chapter 1", "Section 1.1"],
        ]
        assert [r.heading_depth for r in result] == [1, 1, 2]

    def test_boundary_preserving_does_not_mutate_chunks(self):
        chunks = ["# H\n\nbody", "more body"]
        before = list(chunks)
        annotate_chunks(chunks)
        assert chunks == before

    def test_headingless_document_all_empty(self):
        chunks = ["pdf chunk one.", "pdf chunk two.", "pdf chunk three."]
        result = annotate_chunks(chunks)
        assert all(r.heading_path == [] and r.heading_depth == 0 for r in result)

    def test_returns_one_result_per_chunk(self):
        chunks = ["a", "b", "c", "d"]
        assert len(annotate_chunks(chunks)) == 4

"""Regression test — Scripture Evidence Resolver v1 (SPRINT19-B).

Guards the "first match wins" -> "best-scoring candidate wins" policy
change at build_tsu_records()'s call site (Preflight §2/§3 finding:
_resolve_scripture_ref() took refs[0] unconditionally, discarding every
other candidate even when it was a truncated/noisy match). Also guards
the verse_start=0 sentinel fix (Preflight §4: EnhancedReferenceParser's
chapter-only patterns encode "no verse specified" as verse_start=0,
which SPRINT19-A's refs[0] policy had been storing as if it were a real
verse 0 — e.g. the observed "JHN 3:0" citation).

Per HQ SPRINT19-B scope: only scripts/build_tsu_dataset.py is modified.
core/retrieval.py, RetrievalEngine, QueryParser, ScriptureReference,
and the Benchmark Runner are untouched.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import ScriptureReference
from scripts.build_tsu_dataset import _score_candidate, _resolve_evidence, build_tsu_records


class TestScoreCandidate:
    def test_canonical_range_valid_scores_higher(self):
        in_range = ScriptureReference(book_id="JHN", chapter=3, verse_start=16, verse_end=None)
        out_of_range = ScriptureReference(book_id="JHN", chapter=748, verse_start=16, verse_end=None)
        score_in, reasons_in = _score_candidate(in_range, [in_range], None)
        score_out, reasons_out = _score_candidate(out_of_range, [out_of_range], None)
        assert score_in > score_out
        assert "canonical_range_valid" in reasons_in
        assert "canonical_range_valid" not in reasons_out

    def test_verse_start_zero_sentinel_not_scored_as_explicit(self):
        """verse_start=0 is EnhancedReferenceParser's "no verse specified"
        sentinel (chapter-only match), not a real verse — must not earn
        the verse_explicit bonus."""
        chapter_only = ScriptureReference(book_id="JHN", chapter=3, verse_start=0, verse_end=None)
        score, reasons = _score_candidate(chapter_only, [chapter_only], None)
        assert "verse_explicit" not in reasons

    def test_verse_start_positive_scores_verse_explicit(self):
        ref = ScriptureReference(book_id="JHN", chapter=3, verse_start=16, verse_end=None)
        score, reasons = _score_candidate(ref, [ref], None)
        assert "verse_explicit" in reasons

    def test_verse_range_present_bonus(self):
        ref = ScriptureReference(book_id="1CO", chapter=1, verse_start=1, verse_end=9)
        score, reasons = _score_candidate(ref, [ref], None)
        assert "verse_range_present" in reasons

    def test_duplicate_support_bonus(self):
        ref1 = ScriptureReference(book_id="ROM", chapter=8, verse_start=1, verse_end=None)
        ref2 = ScriptureReference(book_id="ROM", chapter=8, verse_start=28, verse_end=None)
        other = ScriptureReference(book_id="MRK", chapter=1, verse_start=1, verse_end=None)
        score, reasons = _score_candidate(ref1, [ref1, ref2, other], None)
        assert "duplicate_support" in reasons

    def test_no_duplicate_support_when_unique(self):
        ref = ScriptureReference(book_id="ROM", chapter=8, verse_start=1, verse_end=None)
        other = ScriptureReference(book_id="MRK", chapter=1, verse_start=1, verse_end=None)
        score, reasons = _score_candidate(ref, [ref, other], None)
        assert "duplicate_support" not in reasons

    def test_book_id_consistent_bonus(self):
        ref = ScriptureReference(book_id="JHN", chapter=3, verse_start=16, verse_end=None)
        score_match, reasons_match = _score_candidate(ref, [ref], "JHN")
        score_mismatch, reasons_mismatch = _score_candidate(ref, [ref], "ROM")
        assert "book_id_consistent" in reasons_match
        assert "book_id_consistent" not in reasons_mismatch
        assert score_match > score_mismatch

    def test_score_capped_at_one(self):
        ref = ScriptureReference(book_id="JHN", chapter=3, verse_start=16, verse_end=18)
        dup = ScriptureReference(book_id="JHN", chapter=3, verse_start=1, verse_end=None)
        score, _ = _score_candidate(ref, [ref, dup], "JHN")
        assert score <= 1.0


class TestResolveEvidence:
    def test_no_content_returns_none_none(self):
        assert _resolve_evidence("", "JHN") == (None, None)

    def test_no_candidates_returns_none_none(self):
        ref, provenance = _resolve_evidence("아무 성구 참조도 없는 본문입니다.", "JHN")
        assert ref is None
        assert provenance is None

    def test_higher_scoring_candidate_wins_over_first_match(self):
        """A truncated/noisy first-in-list match must lose to a
        canonically valid, book-consistent, verse-explicit candidate
        found later in the same content — this is the actual policy
        change SPRINT19-B makes over SPRINT19-A's refs[0]."""
        # "2 Kings 748" (out-of-canonical-range noise) appears before a
        # valid "2 Kings 5:14" reference in the same content.
        content = "2 Kings 748 index reference. Later in the text: 2 Kings 5:14 describes Naaman's healing."
        ref, provenance = _resolve_evidence(content, "2KI")
        assert ref.chapter == 5
        assert ref.verse_start == 14
        assert provenance["candidate_count"] == 2
        assert "canonical_range_valid" in provenance["selected_reason"]

    def test_provenance_shape(self):
        ref, provenance = _resolve_evidence("고전1:1-9", "1CO")
        assert provenance["resolver"] == "scripture_evidence_resolver_v1"
        assert 0.0 <= provenance["confidence"] <= 1.0
        assert provenance["candidate_count"] == 1
        assert isinstance(provenance["selected_reason"], list)


def _build_with_content(content: str, book: str = "2CO") -> list:
    registry = {
        "documents": {
            "doc1": {
                "source_file": "12. 고린도후서.pdf",
                "chunk_count": 1,
                "book": book,
            }
        }
    }

    import core.tsu_builder as mod
    from pathlib import Path

    original_read_chunk_texts = mod._read_chunk_texts
    original_read_md_fallback = mod._read_md_fallback
    mod._read_chunk_texts = lambda output_dir, source_file: [content]
    mod._read_md_fallback = lambda output_dir, source_file: None
    try:
        return build_tsu_records(registry, Path("."))
    finally:
        mod._read_chunk_texts = original_read_chunk_texts
        mod._read_md_fallback = original_read_md_fallback


class TestBuildTsuRecordsProvenance:
    def test_record_with_evidence_has_provenance_key(self):
        records = _build_with_content("고후1:8-14 본문 내용입니다.")
        assert "provenance" in records[0]
        assert records[0]["provenance"]["resolver"] == "scripture_evidence_resolver_v1"
        assert records[0]["verse_mapping"] == {
            "book_id": "2CO", "chapter": 1, "verse_start": 8, "verse_end": 14,
        }

    def test_record_without_evidence_has_no_provenance_key(self):
        records = _build_with_content("아무 성구 참조도 없는 본문입니다.")
        assert "provenance" not in records[0]
        assert records[0]["verse_mapping"] == {"book_id": "2CO"}

    def test_chapter_only_sentinel_never_stored_as_verse(self):
        """A chapter-only reference (e.g. "2 Corinthians 1") must produce
        verse_mapping without a verse_start key — the parser's
        verse_start=0 sentinel must never leak into stored data."""
        records = _build_with_content("2 Corinthians 1 개관입니다.")
        vm = records[0]["verse_mapping"]
        assert vm.get("book_id") == "2CO"
        if "chapter" in vm:
            assert "verse_start" not in vm or vm["verse_start"] > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

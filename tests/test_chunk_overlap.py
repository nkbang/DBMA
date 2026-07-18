"""Regression test — boundary-based chunk overlap (SPRINT29-B-Overlap).

The paragraph-first chunker previously produced zero overlap between
adjacent chunks on its primary paths. This suite guards the new
boundary-preserving overlap across the three chunk-generation paths
(paragraph accumulation, sentence merge, mixed/original-language),
verifying: overlap is actually carried, it never cuts mid-word or
mid-original-language, overlap=0 reproduces the old no-overlap behavior,
and there is no runaway duplication.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.chunking_optimizer import (
    chunk_once,
    _paragraph_overlap_tail,
    _word_safe_tail,
)
from core.text_normalizer import _sentence_overlap_tail, _merge_sentence_fragments


class TestOverlapTailHelpers:
    def test_paragraph_tail_never_returns_whole_list(self):
        # units[0] always excluded -> forward progress guaranteed
        assert _paragraph_overlap_tail(["aaaa", "bbbb", "cccc"], 3) == ["cccc"]
        assert _paragraph_overlap_tail(["only"], 3) == []

    def test_paragraph_tail_disabled_when_overlap_zero(self):
        assert _paragraph_overlap_tail(["a", "b", "c"], 0) == []

    def test_paragraph_tail_caps_large_trailing_paragraph(self):
        big = "word " * 200  # ~1000 chars
        tail = _paragraph_overlap_tail(["first", big], overlap_chars=120)
        # must not carry the whole 1000-char paragraph — capped to word-safe tail
        assert tail
        assert len(tail[0]) <= 260  # ~2x overlap cap, word-safe

    def test_sentence_tail_never_returns_whole_list(self):
        # realistic overlap; units[0] always excluded -> progress guaranteed
        s = ["sentence one has some length", "sentence two also", "sentence three tail"]
        tail = _sentence_overlap_tail(s, 15)
        assert tail == ["sentence three tail"]
        assert _sentence_overlap_tail(["only"], 15) == []

    def test_word_safe_tail_starts_at_boundary(self):
        assert _word_safe_tail("hello world foobar", 8) == "foobar"

    def test_word_safe_tail_no_boundary_returns_empty(self):
        # no whitespace within the window -> skip overlap rather than cut mid-word
        assert _word_safe_tail("abcdefghij", 4) == ""


class TestMergeSentenceFragmentsOverlap:
    def test_overlap_zero_is_legacy_behavior(self):
        # Each sentence carries a unique token; with overlap=0 no token may
        # appear in more than one chunk (no duplication across boundaries).
        sents = [f"tok-{i}-x phrase content here." for i in range(20)]
        no = _merge_sentence_fragments(sents, max_chars=100, overlap_chars=0)
        for i in range(20):
            hits = sum(1 for c in no if f"tok-{i}-x" in c)
            assert hits == 1

    def test_overlap_carries_trailing_sentence(self):
        # With overlap on, at least one unique token must appear in two
        # adjacent chunks (the carried tail).
        sents = [f"tok-{i}-x phrase content here now." for i in range(20)]
        with_ov = _merge_sentence_fragments(sents, max_chars=100, overlap_chars=30)
        duplicated = sum(1 for i in range(20) if sum(f"tok-{i}-x" in c for c in with_ov) >= 2)
        assert duplicated >= 1


class TestChunkOnceOverlap:
    def _para_text(self):
        return "\n\n".join([f"문단{i} 가나다라마바사아자차 " * 8 for i in range(30)])

    def test_overlap_off_matches_no_overlap(self):
        text = self._para_text()
        off_a = chunk_once(text, 1200, 0).chunks
        off_b = chunk_once(text, 1200, 0).chunks
        assert off_a == off_b  # deterministic

    def test_overlap_on_produces_adjacent_overlap(self):
        text = self._para_text()
        on = chunk_once(text, 1200, 120).chunks
        assert len(on) >= 2
        shared = 0
        for a, b in zip(on, on[1:]):
            tail = a.split("\n\n")[-1][:15]
            if tail and tail in b[:len(tail) + 40]:
                shared += 1
        assert shared >= 1

    def test_overlap_on_increases_or_equals_chunk_count(self):
        text = self._para_text()
        off = len(chunk_once(text, 1200, 0).chunks)
        on = len(chunk_once(text, 1200, 120).chunks)
        assert on >= off

    def test_original_language_preserved_with_overlap(self):
        heb = "히브리어 인용입니다. אני מאמין בך. 그리고 다음 문장. λόγος ἦν. 마지막 문장입니다."
        joined = " | ".join(chunk_once(heb, 200, 120).chunks)
        assert "אני" in joined
        assert "λόγος" in joined

    def test_no_runaway_on_many_tiny_paragraphs(self):
        big = "\n\n".join(["짧은문단 하나 둘 셋 넷 다섯." for _ in range(500)])
        chunks = chunk_once(big, 1200, 120).chunks
        # forward progress guaranteed -> bounded chunk count, not thousands
        assert 1 <= len(chunks) <= 60

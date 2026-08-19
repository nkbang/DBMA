# tests/test_text_normalizer.py
"""
text_normalizer.py 단위 테스트
대상: normalize_pipeline_text, split_sentences
"""
import pytest
from core.text_normalizer import (
    normalize_pipeline_text,
    split_sentences,
    split_sentences_mixed,
    _merge_sentence_fragments,
)


# ─── normalize_pipeline_text ─────────────────────────────────────────────────

class TestNormalizePipelineText:

    def test_empty_string_returns_empty(self):
        assert normalize_pipeline_text("") == ""

    def test_none_like_empty_string_handled(self):
        # 함수 내부에서 text or "" 처리
        assert normalize_pipeline_text("") == ""

    def test_crlf_normalized(self):
        out = normalize_pipeline_text("line1\r\nline2\rline3")
        assert "\r" not in out
        assert out == "line1 line2 line3"

    def test_multiple_spaces_collapsed(self):
        out = normalize_pipeline_text("Hello   world\t  again")
        assert out == "Hello world again"

    def test_excessive_newlines_reduced_to_two(self):
        out = normalize_pipeline_text("a\n\n\n\n\nb")
        assert out == "a\n\nb"

    def test_leading_trailing_whitespace_stripped(self):
        out = normalize_pipeline_text("  hello  ")
        assert out == "hello"


# ─── split_sentences ─────────────────────────────────────────────────────────

class TestSplitSentences:

    def test_empty_text_returns_empty_list(self):
        assert split_sentences("") == []

    def test_returns_list_of_strings(self):
        out = split_sentences("Hello world. Next sentence.\nThird.")
        assert isinstance(out, list)
        assert all(isinstance(s, str) for s in out)

    def test_splits_by_period(self):
        out = split_sentences("First sentence. Second sentence. Third.")
        assert len(out) >= 2

    def test_splits_by_newline(self):
        out = split_sentences("Line one.\nLine two.\nLine three.")
        assert len(out) >= 2

    def test_no_empty_items(self):
        out = split_sentences("Hello.   \n\n   World.")
        assert all(s.strip() for s in out)


# ─── _merge_sentence_fragments — chunk overflow regression (Preflight 하위결함 B) ──
# core/text_normalizer.py::split_sentences_mixed() only splits on physical
# newlines. A single-line paragraph (the normal case after
# collapse_soft_linebreaks()) therefore always comes back as one "sentence",
# which _merge_sentence_fragments used to append verbatim once it exceeded
# max_chars — silently breaking the chunk_size cap. See
# docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md.

class TestMergeSentenceFragmentsOversizedUnit:

    def test_single_oversized_sentence_is_hard_sliced_under_max_chars(self):
        sentence = "가나다라마바사아자차카타파하 " * 200  # single unit, no newline
        assert len(sentence) > 1200
        chunks = _merge_sentence_fragments([sentence], max_chars=1200)
        assert all(len(c) <= 1200 for c in chunks)

    def test_oversized_sentence_slice_is_word_safe(self):
        sentence = " ".join(f"word{i}" for i in range(500))
        chunks = _merge_sentence_fragments([sentence], max_chars=200)
        assert all(len(c) <= 200 for c in chunks)
        # No word split across a chunk boundary: rejoining recovers every token.
        assert " ".join(chunks).split() == sentence.split()

    def test_pure_korean_long_paragraph_no_newline_stays_under_cap(self):
        # Reproduces the Preflight's 하위결함 B case: a pure-Korean paragraph
        # with normal sentence punctuation but no "\n" (the post-
        # collapse_soft_linebreaks() norm), fed through the same two-step
        # path production uses (split_sentences_mixed -> merge).
        para = ("이것은 테스트를 위한 문장입니다. " * 150).strip()
        sents = split_sentences_mixed(para)
        assert len(sents) == 1  # confirms the known split_sentences_mixed limitation
        chunks = _merge_sentence_fragments(sents, max_chars=1200, overlap_chars=200)
        assert all(len(c) <= 1200 for c in chunks)

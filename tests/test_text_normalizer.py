# tests/test_text_normalizer.py
"""
text_normalizer.py 단위 테스트
대상: normalize_pipeline_text, split_sentences
"""
import pytest
from core.text_normalizer import normalize_pipeline_text, split_sentences


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

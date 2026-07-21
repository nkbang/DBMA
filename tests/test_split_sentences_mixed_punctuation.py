"""Regression test — core/text_normalizer.py::split_sentences_mixed()
(ADR-008 제안 4 수정, 2026-07-21).

실증된 결함: collapse_soft_linebreaks()가 문단 내부 개행을 이미
공백으로 합쳐 놓기 때문에, split_sentences_mixed()가 개행 기준으로만
나누던 원래 구현은 프로덕션 청커가 넘기는 개행 없는 긴 문단을 "문장
1개"로 그대로 반환했다(원어/혼합 언어 보호 로직 무력화). 이 테스트는
마침표류 문장부호 기준으로도 나뉘는지 확인한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.text_normalizer import split_sentences_mixed, split_paragraphs


def test_single_line_korean_paragraph_splits_on_sentence_end():
    text = "이것은 첫 번째 문장입니다. 이것은 두 번째 문장입니다. 이것은 세 번째 문장입니다."
    sentences = split_sentences_mixed(text)
    assert len(sentences) == 3


def test_matches_real_pipeline_input_shape():
    """chunking_optimizer.py:305가 실제로 넘기는 입력 형태 — split_paragraphs()가
    만든, 내부 개행이 없는 단일 문단."""
    long_text = "이것은 완전한 문장입니다. " * 50
    paras = split_paragraphs(long_text)
    assert len(paras) == 1
    p = paras[0]
    assert "\n" not in p

    sentences = split_sentences_mixed(p)
    assert len(sentences) == 50


def test_english_paragraph_splits_on_sentence_end():
    text = "This is the first sentence. This is the second sentence. This is the third."
    sentences = split_sentences_mixed(text)
    assert len(sentences) == 3


def test_no_sentence_ending_punctuation_stays_unsplit():
    text = "가나다라마바사아자차카타파하 " * 20
    sentences = split_sentences_mixed(text)
    assert len(sentences) == 1


def test_multiline_input_still_works_as_before():
    text = "이것은 첫 문장입니다.\n이것은 둘째 줄입니다.\n"
    sentences = split_sentences_mixed(text)
    assert len(sentences) >= 1


def test_empty_and_whitespace_input():
    assert split_sentences_mixed("") == []
    assert split_sentences_mixed("   ") == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

"""Regression tests for P1 (docs/TODO.md) — BM25 Korean morphological
tokenizer. Covers core/tli/korean_tokenizer.py's factory/adapter and its
wiring into core/retrieval.py::_tokenize()/bm25_score().
"""

from core.tli.korean_tokenizer import create_korean_tokenizer
from core.retrieval import _tokenize, bm25_score


def test_factory_returns_working_tokenizer():
    tokenizer = create_korean_tokenizer()
    tokens = tokenizer.tokenize("성령의 자유")
    assert tokens  # non-empty for real Korean input


def test_particle_suffixed_words_match_same_stem():
    """The whole point of the fix: '성령의'/'성령께서' must tokenize to
    the same content token '성령', not stay as two distinct opaque
    whitespace-split units."""
    a = _tokenize("성령의 은혜")
    b = _tokenize("성령께서 임하셨다")
    assert "성령" in a
    assert "성령" in b


def test_particles_and_endings_are_dropped():
    tokens = _tokenize("성령께서 우리를 자유롭게 하셨습니다.")
    # 조사(께서/를)와 어미(-습니다)는 별도 토큰으로 남지 않아야 한다.
    assert "께서" not in tokens
    assert "를" not in tokens
    assert "하셨습니다" not in tokens


def test_bm25_score_nonzero_for_particle_suffixed_match():
    doc = "성령의 자유로우심에 대해 바울은 로마서 8장에서 말한다. 성령께서 우리를 자유케 하셨다."
    query_tokens = _tokenize("성령")
    assert query_tokens == ["성령"]
    score = bm25_score(query_tokens, doc)
    assert score > 0.0


def test_bm25_score_zero_for_empty_inputs():
    assert bm25_score([], "아무 텍스트") == 0.0
    assert bm25_score(["성령"], "") == 0.0


def test_tokenizer_handles_empty_and_mixed_content():
    assert _tokenize("") == []
    tokens = _tokenize("Romans 8:1 로마서 8장 1절")
    assert tokens  # mixed Korean/English/numbers doesn't crash

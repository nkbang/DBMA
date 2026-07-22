"""Regression test — core/semantic_boundary_detector.py::
EmbeddingSimilarityBoundaryFeature (ADR-008 제안 3, 2026-07-21).

인접 후보 임베딩 코사인 유사도가 임계값 미만이면 경계 신호(1.0)를
낸다 — 실제 Ollama 호출 없이 embed_fn을 주입해 순수 로직만 검증한다
(다른 dormant feature 테스트와 동일한 격리 패턴).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.semantic_boundary_detector import (
    BoundaryContext,
    EmbeddingSimilarityBoundaryFeature,
)


def _ctx(candidate_text: str, previous_candidate_text: str = "") -> BoundaryContext:
    return BoundaryContext(
        candidate_text=candidate_text,
        position=1,
        previous_candidate_text=previous_candidate_text,
    )


def _fixed_embed(vectors: dict):
    def _embed(text: str):
        return vectors[text]
    return _embed


def test_similarity_drop_fires_boundary_signal():
    embed_fn = _fixed_embed({"이전 문단": [1.0, 0.0], "새 주제 문단": [0.0, 1.0]})
    feature = EmbeddingSimilarityBoundaryFeature(embed_fn=embed_fn, drop_threshold=0.5)
    ctx = _ctx("새 주제 문단", previous_candidate_text="이전 문단")
    assert feature.score(ctx) == 1.0


def test_high_similarity_does_not_fire():
    embed_fn = _fixed_embed({"이전 문단": [1.0, 0.0], "비슷한 문단": [0.99, 0.01]})
    feature = EmbeddingSimilarityBoundaryFeature(embed_fn=embed_fn, drop_threshold=0.5)
    ctx = _ctx("비슷한 문단", previous_candidate_text="이전 문단")
    assert feature.score(ctx) == 0.0


def test_no_previous_candidate_returns_zero_without_calling_embed():
    calls = []

    def _embed(text):
        calls.append(text)
        return [1.0, 0.0]

    feature = EmbeddingSimilarityBoundaryFeature(embed_fn=_embed)
    ctx = _ctx("첫 후보", previous_candidate_text="")
    assert feature.score(ctx) == 0.0
    assert calls == []


def test_empty_candidate_text_returns_zero():
    feature = EmbeddingSimilarityBoundaryFeature(embed_fn=lambda t: [1.0, 0.0])
    ctx = _ctx("   ", previous_candidate_text="이전 문단")
    assert feature.score(ctx) == 0.0


def test_embed_failure_falls_back_to_zero_not_raise():
    def _broken_embed(text):
        raise RuntimeError("ollama connection refused")

    feature = EmbeddingSimilarityBoundaryFeature(embed_fn=_broken_embed)
    ctx = _ctx("문단", previous_candidate_text="이전 문단")
    assert feature.score(ctx) == 0.0


def test_default_embed_fn_uses_production_get_embedder_not_legacy_embed():
    """[ADR-008 제안 3 수정, 2026-07-21] core.embedder.embed()는 legacy
    MiniLM(768차원)만 로드해 EMBEDDING_DIMENSION(1024)과 항상 불일치
    (DimensionMismatchError) — 실제 프로덕션이 쓰는 get_embedder()(Ollama
    bge-m3 우선)를 기본값으로 써야 한다."""
    from core.semantic_boundary_detector import _embedder

    feature = EmbeddingSimilarityBoundaryFeature()
    assert feature._embed_fn == _embedder.embed


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

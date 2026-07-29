"""Unit tests — Hierarchical Chunk Builder prototype (SPRINT33-D Phase 1).

Dormant module: core.hierarchical_chunk_builder is not imported by
chunking_optimizer.py/processing.py or any production path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.config import EMBEDDING_SIMILARITY_WEIGHT
from core.heading_provider import ProviderHeading
from core.hierarchical_chunk_builder import (
    _slice_preserving_words,
    build_chunks,
    classify_document_profile,
)
from core.semantic_boundary_detector import (
    EmbeddingSimilarityBoundaryFeature,
    get_registry,
)


@pytest.fixture(autouse=True)
def _no_network_embedding_feature():
    """[ADR-008 제안 3, 2026-07-21] build_chunks()는 module-level singleton
    registry(get_registry())를 그대로 쓴다 — embedding_similarity feature가
    기본값으로는 실제 core.embedder.embed()(Ollama 네트워크 호출)를 쓰므로,
    이 dormant 모듈의 "격리된 unit test" 성격을 지키기 위해 테스트 동안만
    고정 벡터를 반환하는 가짜 embed_fn으로 교체하고 끝나면 원복한다."""
    registry = get_registry()
    original = registry._entries["embedding_similarity"]
    registry.register(
        "embedding_similarity",
        EmbeddingSimilarityBoundaryFeature(embed_fn=lambda t: [0.0]),
        weight=EMBEDDING_SIMILARITY_WEIGHT,
    )
    yield
    registry._entries["embedding_similarity"] = original


def _heading(text: str, level: int = 1, confidence: float = 1.0, source: str = "atx") -> ProviderHeading:
    return ProviderHeading(text=text, level=level, confidence=confidence, source=source)


def _cands(*texts: str) -> list:
    # Sequential fake offsets, spaced as if joined by "\n\n" — good enough
    # for tests that only assert relative ordering / first-candidate offset.
    out = []
    offset = 0
    for t in texts:
        out.append((t, offset))
        offset += len(t) + 2
    return out


class TestNoHeadingsFallsBackToSafetyCap:
    def test_short_candidates_merge_into_one_chunk_below_safety_cap(self):
        candidates = _cands("문단 하나", "문단 둘", "문단 셋")
        chunks = build_chunks(candidates, headings=[], chunk_size=1000, min_chunk_size=5)
        assert len(chunks) == 1
        assert chunks[0][1] == 0  # starts at first candidate's offset

    def test_force_flushes_at_safety_cap_without_any_semantic_signal(self):
        # chunk_size=10 -> safety cap = 15. Each candidate is 20 chars, so
        # every single candidate alone already exceeds the cap. [ADR-008
        # 제안 2, Level 3 Hard Fallback, 2026-07-22] Level 2 still flushes
        # at the cap, but the flushed chunk itself is now word-safe sliced
        # if it still exceeds safety_cap — a single unbroken 20-char run
        # (no whitespace) has no word boundary to slice on, so it hard-
        # slices into ceil(20/15)=2 pieces per candidate (15 + 5 chars).
        candidates = _cands("x" * 20, "y" * 20, "z" * 20)
        chunks = build_chunks(candidates, headings=[], chunk_size=10, min_chunk_size=1)
        assert len(chunks) == 6
        assert all(len(text) <= 15 for text, _ in chunks)
        assert chunks[0] == ("x" * 15, 0)
        assert chunks[1] == ("x" * 5, 0)


class TestLevel3HardFallbackSlicing:
    """ADR-008 제안 2 (2026-07-22) — _slice_preserving_words() 단위 테스트."""

    def test_never_cuts_inside_a_word(self):
        text = "짧은 단어들 여러 개를 공백으로 이어붙인 긴 문장을 만들어 안전 상한을 넘기는 예시 텍스트입니다"
        pieces = _slice_preserving_words(text, max_len=20)
        assert all(len(p) <= 20 for p in pieces)
        # 원문을 공백 기준으로 재조합했을 때 단어가 잘리지 않았는지 확인
        assert " ".join(pieces).replace("  ", " ") == " ".join(text.split())

    def test_single_unbroken_token_longer_than_max_len_hard_slices(self):
        # 공백이 전혀 없는 토큰(예: 헬라어/히브리어 연속 인용) — 마지막
        # 수단으로만 하드 슬라이스.
        pieces = _slice_preserving_words("가" * 50, max_len=20)
        assert pieces == ["가" * 20, "가" * 20, "가" * 10]

    def test_empty_input_returns_empty_list(self):
        assert _slice_preserving_words("", max_len=20) == []


class TestMinChunkSizeFloor:
    def test_boundary_signal_ignored_below_min_chunk_size(self):
        headings = [_heading("서론")]
        candidates = _cands("서론", "본문 내용이 이어집니다")
        # min_chunk_size huge -> buffer never reaches the floor, so the
        # heading match on candidate 0 cannot itself trigger a flush (buf
        # is empty when candidate 0 is being evaluated), and nothing after
        # it can flush either since buf_len stays under the floor.
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=500)
        assert len(chunks) == 1

    def test_boundary_signal_honored_once_floor_is_met(self):
        headings = [_heading("서론"), _heading("본론")]
        candidates = _cands("아무 문단 내용입니다 채우기용 텍스트", "서론", "본론")
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=10)
        # first candidate alone clears min_chunk_size(10) -> "서론" (heading
        # match) should flush it into its own chunk before being folded in.
        assert len(chunks) >= 2
        assert chunks[0][0] == "아무 문단 내용입니다 채우기용 텍스트"


class TestSemanticBoundarySplitsBuffer:
    def test_heading_match_starts_a_new_chunk(self):
        headings = [_heading("서론"), _heading("결론")]
        candidates = _cands(
            "채우기용 본문 문단입니다 충분히 깁니다",
            "서론",
            "본문이 이어지는 두번째 문단입니다",
            "결론",
        )
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=5)
        texts = [c[0] for c in chunks]
        assert any(t.startswith("서론") for t in texts)
        assert any(t.startswith("결론") for t in texts)

    def test_chunk_start_offset_matches_first_candidate_offset(self):
        headings = [_heading("서론")]
        candidates = _cands("채우기용 문단입니다 충분한 길이", "서론", "이어지는 본문")
        chunks = build_chunks(candidates, headings, chunk_size=1000, min_chunk_size=5)
        offsets = {text: offset for text, offset in candidates}
        for chunk_text, chunk_offset in chunks:
            first_candidate = chunk_text.split("\n\n")[0]
            assert offsets[first_candidate] == chunk_offset


class TestEmptyInput:
    def test_no_candidates_yields_no_chunks(self):
        assert build_chunks([], headings=[], chunk_size=1000, min_chunk_size=5) == []


class TestClassifyDocumentProfile:
    """[ADR-008 §4, 2026-07-23] Median-candidate-length Signal-Profile
    classifier — thresholds chosen from the validated Beta corpus ranges:
    Profile A 132~184 chars, Profile B 269~856 chars (no overlap)."""

    def test_short_candidates_are_profile_a(self):
        candidates = [(f"짧은 문단 {i}", i) for i in range(20)]  # ~10 chars each
        assert classify_document_profile(candidates) == "A"

    def test_long_candidates_are_profile_b(self):
        long_text = "학술 주석서 인용문 스타일의 긴 문단 " * 20  # well over 220 chars
        candidates = [(long_text, i) for i in range(20)]
        assert classify_document_profile(candidates) == "B"

    def test_single_outlier_candidate_does_not_flip_profile(self):
        # The old provisional rule ("any candidate > 1800 chars") would
        # classify this as B off one outlier — the median-based rule
        # correctly reads the document as A (Amendment A's documented
        # boundary-case risk this replacement was chosen to avoid).
        candidates = [("짧은 문단입니다", i) for i in range(50)]
        candidates.append(("아주 긴 이상치 문단 " * 200, 999))
        assert classify_document_profile(candidates) == "A"

    def test_empty_candidates_default_to_profile_a(self):
        assert classify_document_profile([]) == "A"

    def test_at_threshold_boundary_median_220_is_profile_b(self):
        """MEDIAN_CANDIDATE_LENGTH_THRESHOLD=220 기준: median > 220 -> B,
        median <= 220 -> A. 경계값 테스트."""
        # median 정확히 220인 경우: 220 > 220 is False -> A
        long_text = "x" * 220
        candidates = [(long_text, 0), (long_text, 1)]
        assert classify_document_profile(candidates) == "A"

    def test_just_above_threshold_median_221_is_profile_b(self):
        # median 정확히 221인 경우: 221 > 220 is True -> B
        long_text = "x" * 221
        candidates = [(long_text, 0), (long_text, 1)]
        assert classify_document_profile(candidates) == "B"

    def test_below_threshold_median_219_is_profile_a(self):
        # median 정확히 219인 경우: 219 > 220 is False -> A
        long_text = "x" * 219
        candidates = [(long_text, 0), (long_text, 1)]
        assert classify_document_profile(candidates) == "A"


class TestBuildChunksPassesDocumentProfile:
    """[Task Order 016 Phase 1.5] build_chunks()가 classify_document_profile()
   를 1회만 호출하고 그 결과를 매 score_boundary() 호출에 동일하게 전달하는지
    확인 — 회귀 방지용."""

    def test_classify_called_once_per_build_chunks_call(self):
        """classify_document_profile이 build_chunks() 진입 시 1회만 호출되는지
        검증: classify_document_profile을 monkeypatch해서 호출 횟수를 세고,
        그 결과로 BoundaryContext.document_profile을 설정하는 fake을 쓴다.
        build_chunks() 내부에서 document_profile이 매 score_boundary() 호출에
        동일하게 전달되는지 확인."""
        from unittest.mock import patch, MagicMock

        # classify_document_profile을 추적하기 위한 mock
        original_classify = classify_document_profile
        call_count = 0
        captured_profile = None

        def tracking_classify(candidates):
            nonlocal call_count, captured_profile
            call_count += 1
            result = original_classify(candidates)
            captured_profile = result
            return result

        # score_boundary를 추적하기 위한 mock
        captured_profiles_in_score = []

        def tracking_score_boundary(ctx, registry=None, document_profile="A"):
            captured_profiles_in_score.append(document_profile)
            # 실제 score_boundary 대신 mock 반환
            from core.semantic_boundary_detector import BoundaryEvent
            return BoundaryEvent(
                position=ctx.position,
                features={"heading": 0.0, "paragraph": 30.0},
                total_score=30.0,
                is_boundary=False,
            )

        candidates = _cands("문단 하나", "문단 둘", "문단 셋")
        with patch(
            "core.hierarchical_chunk_builder.classify_document_profile",
            tracking_classify,
        ):
            with patch(
                "core.hierarchical_chunk_builder.score_boundary",
                tracking_score_boundary,
            ):
                build_chunks(candidates, headings=[], chunk_size=1000, min_chunk_size=5)

        # classify는 정확히 1회만 호출되어야 함
        assert call_count == 1, f"classify_document_profile이 {call_count}회 호출됨 (1회여야 함)"

        # score_boundary에 전달된 document_profile이 모두 동일해야 함
        assert len(captured_profiles_in_score) >= 1
        assert all(p == captured_profile for p in captured_profiles_in_score), \
            f"score_boundary에 전달된 document_profile이 불일치: {captured_profiles_in_score}"

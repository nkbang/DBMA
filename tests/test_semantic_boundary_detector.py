"""Unit tests — Boundary Score model skeleton (SPRINT33-B).

Dormant module: core.semantic_boundary_detector is not wired into
chunking_optimizer.py or any production path. These tests validate the
signal/event model and registry skeleton in isolation, plus the
HeadingBoundaryFeature's reuse of heading_provider's matching primitives.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import DEFAULT_MIN_CHUNK_SIZE
from core.heading_provider import ProviderHeading
from core.semantic_boundary_detector import (
    BoundaryContext,
    BoundaryEvent,
    FeatureRegistry,
    HeadingBoundaryFeature,
    ParagraphBoundaryFeature,
    SentenceBoundaryConfidenceFeature,
    TinyFragmentPenaltyFeature,
    DEFAULT_THRESHOLD,
    get_registry,
    score_boundary,
)


def _heading(text: str, level: int = 1, confidence: float = 1.0, source: str = "atx") -> ProviderHeading:
    return ProviderHeading(text=text, level=level, confidence=confidence, source=source)


def _long(lead: str) -> str:
    # Pads `lead` well past DEFAULT_MIN_CHUNK_SIZE so TinyFragmentPenaltyFeature
    # never fires incidentally in tests that aren't testing it.
    return lead + " 본문 내용이 이어집니다" * 10


class TestHeadingBoundaryFeature:
    def test_scores_one_when_candidate_contains_next_heading(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론"), _heading("본론")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 1.0

    def test_scores_zero_when_no_heading_matches(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="아무 관련 없는 본문 문장입니다.",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 0.0

    def test_scores_zero_when_no_headings_present(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(candidate_text="서론", position=0, headings=[], heading_cursor=0)
        assert feature.score(ctx) == 0.0

    def test_scores_zero_when_cursor_exhausted(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=1,
        )
        assert feature.score(ctx) == 0.0

    def test_word_boundary_guard_rejects_partial_match(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="INTRODUCTION to the text",
            position=0,
            headings=[_heading("INTRO")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 0.0

    def test_finds_heading_merged_into_longer_line(self):
        # Same shape as SPRINT32-F's real-corpus finding: a short heading
        # merged into adjacent body text by collapse_soft_linebreaks.
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="톰라이트 10 모든사람을위한로마서 I",
            position=0,
            headings=[_heading("톰라이트")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 1.0

    def test_lookahead_finds_heading_beyond_cursor(self):
        feature = HeadingBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="본론",
            position=0,
            headings=[_heading("서론"), _heading("본론")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 1.0


class TestParagraphBoundaryFeature:
    def test_scores_one_for_non_empty_candidate(self):
        feature = ParagraphBoundaryFeature()
        ctx = BoundaryContext(candidate_text="아무 문단 내용입니다.", position=0)
        assert feature.score(ctx) == 1.0

    def test_scores_zero_for_empty_candidate(self):
        feature = ParagraphBoundaryFeature()
        ctx = BoundaryContext(candidate_text="", position=0)
        assert feature.score(ctx) == 0.0

    def test_scores_zero_for_whitespace_only_candidate(self):
        feature = ParagraphBoundaryFeature()
        ctx = BoundaryContext(candidate_text="   \n  ", position=0)
        assert feature.score(ctx) == 0.0

    def test_is_independent_of_headings(self):
        # Paragraph feature scores the candidate's own shape only — heading
        # presence/absence must not affect it (no double-counting with
        # HeadingBoundaryFeature).
        feature = ParagraphBoundaryFeature()
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        assert feature.score(ctx) == 1.0


class TestTinyFragmentPenaltyFeature:
    def test_scores_one_when_shorter_than_default_min_chunk_size(self):
        feature = TinyFragmentPenaltyFeature()
        ctx = BoundaryContext(candidate_text="서론", position=0)
        assert feature.score(ctx) == 1.0

    def test_scores_zero_when_at_or_above_default_min_chunk_size(self):
        feature = TinyFragmentPenaltyFeature()
        ctx = BoundaryContext(candidate_text="x" * DEFAULT_MIN_CHUNK_SIZE, position=0)
        assert feature.score(ctx) == 0.0

    def test_scores_one_just_below_default_min_chunk_size(self):
        feature = TinyFragmentPenaltyFeature()
        ctx = BoundaryContext(candidate_text="x" * (DEFAULT_MIN_CHUNK_SIZE - 1), position=0)
        assert feature.score(ctx) == 1.0

    def test_context_min_chunk_size_overrides_default(self):
        feature = TinyFragmentPenaltyFeature()
        ctx = BoundaryContext(candidate_text="x" * 50, position=0, min_chunk_size=30)
        assert feature.score(ctx) == 0.0  # 50 >= override(30), not tiny

    def test_strips_whitespace_before_measuring(self):
        feature = TinyFragmentPenaltyFeature()
        ctx = BoundaryContext(candidate_text="   서론   ", position=0)
        assert feature.score(ctx) == 1.0


class TestSentenceBoundaryConfidenceFeature:
    def test_scores_one_when_last_line_ends_with_period(self):
        feature = SentenceBoundaryConfidenceFeature()
        ctx = BoundaryContext(candidate_text="이것은 완전한 문장입니다.", position=0)
        assert feature.score(ctx) == 1.0

    def test_scores_one_when_last_line_ends_with_korean_final_ending(self):
        feature = SentenceBoundaryConfidenceFeature()
        ctx = BoundaryContext(candidate_text="문장이 종결어미로 끝난다", position=0)
        assert feature.score(ctx) == 1.0

    def test_scores_zero_when_cut_mid_sentence(self):
        feature = SentenceBoundaryConfidenceFeature()
        ctx = BoundaryContext(candidate_text="문장이 중간에서 끊", position=0)
        assert feature.score(ctx) == 0.0

    def test_scores_zero_for_empty_candidate(self):
        feature = SentenceBoundaryConfidenceFeature()
        ctx = BoundaryContext(candidate_text="   \n  ", position=0)
        assert feature.score(ctx) == 0.0

    def test_uses_last_non_empty_line_only(self):
        # Multi-line candidate: only the LAST line's ending determines the
        # score, mirroring how collapse_soft_linebreaks applies
        # _ends_like_sentence per-line rather than to the whole block.
        feature = SentenceBoundaryConfidenceFeature()
        ctx = BoundaryContext(
            candidate_text="첫 줄은 끊긴다\n\n마지막 줄은 완결됩니다.\n\n",
            position=0,
        )
        assert feature.score(ctx) == 1.0


class TestFeatureRegistry:
    def test_register_and_score_all_applies_weight(self):
        reg = FeatureRegistry()
        reg.register("heading", HeadingBoundaryFeature(), weight=100.0)
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        scores = reg.score_all(ctx)
        assert scores == {"heading": 100.0}

    def test_re_register_overwrites_previous_entry(self):
        reg = FeatureRegistry()
        reg.register("heading", HeadingBoundaryFeature(), weight=100.0)
        reg.register("heading", HeadingBoundaryFeature(), weight=25.0)
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        assert reg.score_all(ctx) == {"heading": 25.0}

    def test_empty_registry_scores_nothing(self):
        reg = FeatureRegistry()
        ctx = BoundaryContext(candidate_text="anything", position=0)
        assert reg.score_all(ctx) == {}

    def test_default_registry_has_heading_feature(self):
        reg = get_registry()
        ctx = BoundaryContext(
            candidate_text=_long("서론"),
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        assert reg.score_all(ctx)["heading"] == 100.0

    def test_default_registry_has_paragraph_feature(self):
        reg = get_registry()
        ctx = BoundaryContext(candidate_text=_long("아무 문단."), position=0)
        assert reg.score_all(ctx)["paragraph"] == 30.0

    def test_default_registry_has_tiny_fragment_feature(self):
        reg = get_registry()
        ctx = BoundaryContext(candidate_text="서론", position=0)
        assert reg.score_all(ctx)["tiny_fragment"] == -60.0

    def test_default_registry_has_sentence_boundary_feature(self):
        reg = get_registry()
        ctx = BoundaryContext(candidate_text=_long("아무 문단"), position=0)
        assert reg.score_all(ctx)["sentence_boundary"] == 10.0

    def test_default_registry_does_not_register_blank_line_feature(self):
        # SPRINT33-C Phase 2 Preflight: "Blank line" was explicitly excluded
        # (HQ-approved) because split_paragraphs() already splits on blank
        # lines, making it a duplicate of "paragraph". Only these four
        # feature names should exist in the default registry.
        reg = get_registry()
        ctx = BoundaryContext(candidate_text=_long("아무 문단."), position=0)
        assert set(reg.score_all(ctx).keys()) == {
            "heading", "paragraph", "tiny_fragment", "sentence_boundary",
        }


class TestScoreBoundary:
    def test_score_at_or_above_threshold_is_boundary(self):
        ctx = BoundaryContext(
            candidate_text=_long("서론"),
            position=3,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert isinstance(event, BoundaryEvent)
        assert event.position == 3
        # heading(100) + paragraph(30) + tiny_fragment(0, long enough not to
        # trigger it) + sentence_boundary(10, _long()'s padding ends like a
        # sentence) — all four default-registry features contribute.
        assert event.total_score == 140.0
        assert event.total_score >= DEFAULT_THRESHOLD
        assert event.is_boundary is True

    def test_score_below_threshold_is_not_boundary(self):
        # No heading match: paragraph(30) + sentence_boundary(10) = 40,
        # still doesn't reach DEFAULT_THRESHOLD(50) — non-heading candidates
        # stay non-boundary under the current default weights.
        ctx = BoundaryContext(
            candidate_text=_long("아무 관련 없는 본문."),
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert event.total_score == 40.0
        assert event.is_boundary is False

    def test_tiny_heading_match_is_not_suppressed_by_penalty_alone(self):
        # Documents the real arithmetic (core/semantic_boundary_detector.py
        # TinyFragmentPenaltyFeature docstring): a short candidate that ALSO
        # matches a heading nets 100+30-60=70 (sentence_boundary contributes
        # 0 here — "서론" doesn't end like a sentence), still >= threshold.
        # The penalty alone does not filter every tiny OCR-noise match seen
        # in SPRINT33-C Phase 3 — only a heading-less tiny paragraph
        # (0+30-60=-30) is pulled further from threshold.
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert event.total_score == 70.0
        assert event.is_boundary is True

    def test_custom_registry_is_honored_over_default(self):
        reg = FeatureRegistry()
        reg.register("heading", HeadingBoundaryFeature(), weight=10.0)
        ctx = BoundaryContext(
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx, registry=reg)
        assert event.total_score == 10.0
        assert event.is_boundary is False  # below DEFAULT_THRESHOLD

    def test_features_breakdown_is_exposed_on_event(self):
        ctx = BoundaryContext(
            candidate_text=_long("서론"),
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert event.features == {
            "heading": 100.0, "paragraph": 30.0, "tiny_fragment": 0.0, "sentence_boundary": 10.0,
        }

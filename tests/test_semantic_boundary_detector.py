"""Unit tests — Boundary Score model skeleton (SPRINT33-B).

Dormant module: core.semantic_boundary_detector is not wired into
chunking_optimizer.py or any production path. These tests validate the
signal/event model and registry skeleton in isolation, plus the
HeadingBoundaryFeature's reuse of heading_provider's matching primitives.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.heading_provider import ProviderHeading
from core.semantic_boundary_detector import (
    BoundaryContext,
    BoundaryEvent,
    FeatureRegistry,
    HeadingBoundaryFeature,
    DEFAULT_THRESHOLD,
    get_registry,
    score_boundary,
)


def _heading(text: str, level: int = 1, confidence: float = 1.0, source: str = "atx") -> ProviderHeading:
    return ProviderHeading(text=text, level=level, confidence=confidence, source=source)


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
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        assert reg.score_all(ctx)["heading"] == 100.0


class TestScoreBoundary:
    def test_score_at_or_above_threshold_is_boundary(self):
        ctx = BoundaryContext(
            candidate_text="서론",
            position=3,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert isinstance(event, BoundaryEvent)
        assert event.position == 3
        assert event.total_score == 100.0
        assert event.total_score >= DEFAULT_THRESHOLD
        assert event.is_boundary is True

    def test_score_below_threshold_is_not_boundary(self):
        ctx = BoundaryContext(
            candidate_text="아무 관련 없는 본문.",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert event.total_score == 0.0
        assert event.is_boundary is False

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
            candidate_text="서론",
            position=0,
            headings=[_heading("서론")],
            heading_cursor=0,
        )
        event = score_boundary(ctx)
        assert event.features == {"heading": 100.0}

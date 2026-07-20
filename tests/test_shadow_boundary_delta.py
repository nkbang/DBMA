"""Unit tests — shadow boundary delta measurement driver (SPRINT33-C
Phase 6-B). Diagnostic-only, not production code (scripts/, core/ never
imports this).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from shadow_boundary_delta import candidates_with_offsets, nearest_distance


class TestCandidatesWithOffsets:
    def test_recovers_exact_offsets_for_simple_paragraphs(self):
        text = "문단1입니다.\n\n문단2입니다\n\n문단3입니다."
        pairs = candidates_with_offsets(text)
        assert [t for t, _ in pairs] == ["문단1입니다.", "문단2입니다", "문단3입니다."]
        for t, o in pairs:
            assert text[o : o + len(t)] == t

    def test_skips_empty_segments(self):
        text = "문단1\n\n\n\n\n\n문단2"
        pairs = candidates_with_offsets(text)
        assert [t for t, _ in pairs] == ["문단1", "문단2"]

    def test_adjusts_offset_past_leading_whitespace(self):
        text = "문단1\n\n   문단2"
        pairs = candidates_with_offsets(text)
        assert pairs[1] == ("문단2", text.index("문단2"))

    def test_empty_text_yields_no_candidates(self):
        assert candidates_with_offsets("") == []


class TestNearestDistance:
    def test_returns_zero_for_exact_match(self):
        assert nearest_distance(50, [10, 50, 90]) == 0

    def test_returns_distance_to_closer_neighbor(self):
        assert nearest_distance(45, [10, 50, 90]) == 5

    def test_handles_point_before_all_targets(self):
        assert nearest_distance(0, [10, 50, 90]) == 10

    def test_handles_point_after_all_targets(self):
        assert nearest_distance(100, [10, 50, 90]) == 10

    def test_empty_targets_returns_large_sentinel(self):
        assert nearest_distance(50, []) > 10**8

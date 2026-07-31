"""Tests for core/rrf.py (DBMA-SEARCH-INFRA-001 HQ 제안 ⑦, Reciprocal Rank Fusion)."""

import pytest

from core.rrf import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_single_ranking_preserves_relative_order(self):
        scores = reciprocal_rank_fusion([["a", "b", "c"]])
        assert scores["a"] > scores["b"] > scores["c"]

    def test_top_rank_score_matches_formula(self):
        scores = reciprocal_rank_fusion([["a", "b"]], k=60)
        assert scores["a"] == pytest.approx(1 / 61)
        assert scores["b"] == pytest.approx(1 / 62)

    def test_agreement_across_lists_boosts_score(self):
        # "a" is #1 in both lists — should clearly outrank "b", which only
        # appears in one list at #1.
        list1 = ["a", "b"]
        list2 = ["a", "c"]
        scores = reciprocal_rank_fusion([list1, list2])
        assert scores["a"] > scores["b"]
        assert scores["a"] > scores["c"]
        assert scores["a"] == pytest.approx(2 / 61)

    def test_id_missing_from_a_list_contributes_zero_not_penalty(self):
        list1 = ["a", "b", "c"]
        list2 = ["b"]  # "a" and "c" absent here
        scores = reciprocal_rank_fusion([list1, list2])
        # "b" appears in both (rank 2 in list1, rank 1 in list2) — should
        # beat "a" (rank 1 in list1 only) once list2's agreement is counted.
        assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
        assert scores["a"] == pytest.approx(1 / 61)

    def test_empty_lists_produce_empty_scores(self):
        assert reciprocal_rank_fusion([]) == {}
        assert reciprocal_rank_fusion([[], []]) == {}

    def test_k_parameter_changes_score_scale(self):
        scores_k60 = reciprocal_rank_fusion([["a"]], k=60)
        scores_k1 = reciprocal_rank_fusion([["a"]], k=1)
        assert scores_k1["a"] > scores_k60["a"]

    def test_three_way_fusion_matches_manual_sum(self):
        lists = [["a", "b"], ["b", "a"], ["a", "c"]]
        scores = reciprocal_rank_fusion(lists, k=60)
        expected_a = 1 / 61 + 1 / 62 + 1 / 61
        expected_b = 1 / 62 + 1 / 61
        expected_c = 1 / 62
        assert scores["a"] == pytest.approx(expected_a)
        assert scores["b"] == pytest.approx(expected_b)
        assert scores["c"] == pytest.approx(expected_c)

"""NAE Benchmark Metrics 테스트.

고정 데이터 테스트:
    retrieved: [A, B, C]
    expected:  [B]
    recall@3 = 1.0 (B가 포함됨)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from NAE.benchmark.metrics import (
    recall_at_k,
    precision_at_k,
    mean_reciprocal_rank,
    hit_rate,
    compute_all_metrics,
)


# ------------------------------------------------------------------
# Recall@K Tests
# ------------------------------------------------------------------

class TestRecallAtK:
    """Recall@K 테스트."""

    def test_recall_with_hit(self):
        """관련 결과가 Top-K 안에 있으면 recall > 0."""
        result = recall_at_k(["A", "B", "C"], ["B"])
        assert result == 1.0

    def test_recall_with_no_hit(self):
        """관련 결과가 없으면 recall = 0."""
        result = recall_at_k(["A", "D", "E"], ["B"])
        assert result == 0.0

    def test_recall_partial_hit(self):
        """부분적 일치: 2/3 관련 결과."""
        result = recall_at_k(["A", "B", "C"], ["A", "B", "D"])
        assert result == pytest.approx(2.0 / 3.0)

    def test_recall_empty_relevant(self):
        """관련 결과가 없으면 recall = 1.0."""
        result = recall_at_k(["A", "B", "C"], [])
        assert result == 1.0

    def test_recall_with_k_parameter(self):
        """k 파라미터가 올바르게 적용되어야 함."""
        # retrieved: [A, B, C], relevant: [C]
        # k=1: A만 확인 → hit 없음 → recall = 0
        result = recall_at_k(["A", "B", "C"], ["C"], k=1)
        assert result == 0.0

        # k=3: [A, B, C] 모두 확인 → C 포함 → recall = 1.0
        result = recall_at_k(["A", "B", "C"], ["C"], k=3)
        assert result == 1.0

    def test_recall_multiple_relevant(self):
        """여러 관련 결과 중 일부만 포함."""
        # relevant: [A, B], retrieved: [B, C, D]
        # B만 포함 → recall = 0.5
        result = recall_at_k(["B", "C", "D"], ["A", "B"])
        assert result == pytest.approx(0.5)

    def test_recall_empty_retrieved(self):
        """검색 결과가 없으면 recall = 0."""
        result = recall_at_k([], ["A"])
        assert result == 0.0

    def test_recall_never_exceeds_one_with_duplicate_retrieved(self):
        """중복된 검색 결과가 relevant를 여러 번 카운트하지 않아야 함 (recall <= 1.0)."""
        result = recall_at_k(["A", "A", "A"], ["A"], k=3)
        assert result == 1.0

    def test_recall_duplicate_retrieved_partial_relevant(self):
        """relevant 2개 중 1개만 중복으로 여러 번 검색된 경우."""
        # relevant: [A, B], retrieved: [A, A, A] → A만 히트 → recall = 0.5
        result = recall_at_k(["A", "A", "A"], ["A", "B"])
        assert result == pytest.approx(0.5)


# ------------------------------------------------------------------
# Precision@K Tests
# ------------------------------------------------------------------

class TestPrecisionAtK:
    """Precision@K 테스트."""

    def test_precision_perfect(self):
        """모든 결과가 관련 있으면 precision = 1.0."""
        result = precision_at_k(["A", "B"], ["A", "B"])
        assert result == 1.0

    def test_precision_partial(self):
        """부분적 일치: 1/3."""
        result = precision_at_k(["A", "D", "E"], ["A", "B"])
        assert result == pytest.approx(1.0 / 3.0)

    def test_precision_with_k(self):
        """k 파라미터가 올바르게 적용되어야 함."""
        # retrieved: [A, B, C], relevant: [C]
        # k=1: A만 확인 → hit 없음 → precision = 0
        result = precision_at_k(["A", "B", "C"], ["C"], k=1)
        assert result == 0.0

        # k=3: [A, B, C] 중 C 포함 → precision = 1/3
        result = precision_at_k(["A", "B", "C"], ["C"], k=3)
        assert result == pytest.approx(1.0 / 3.0)

    def test_precision_empty_retrieved(self):
        """검색 결과가 없으면 precision = 0."""
        result = precision_at_k([], ["A"])
        assert result == 0.0

    def test_precision_duplicate_retrieved_not_double_counted(self):
        """동일 ID가 중복 검색되어도 고유 관련 항목 수만 분자로 카운트."""
        # retrieved: [A, A], relevant: [A] → 고유 hit 1개 / 반환 2개 = 0.5
        result = precision_at_k(["A", "A"], ["A"], k=2)
        assert result == pytest.approx(0.5)


# ------------------------------------------------------------------
# MRR (Mean Reciprocal Rank) Tests
# ------------------------------------------------------------------

class TestMRR:
    """MRR 테스트."""

    def test_mrr_first_hit(self):
        """첫 번째 결과가 관련 있으면 MRR = 1.0."""
        result = mean_reciprocal_rank(["A", "B", "C"], ["A"])
        assert result == 1.0

    def test_mrr_second_hit(self):
        """두 번째 결과가 관련 있으면 MRR = 0.5."""
        result = mean_reciprocal_rank(["A", "B", "C"], ["B"])
        assert result == pytest.approx(0.5)

    def test_mrr_third_hit(self):
        """세 번째 결과가 관련 있으면 MRR = 1/3."""
        result = mean_reciprocal_rank(["A", "B", "C"], ["C"])
        assert result == pytest.approx(1.0 / 3.0)

    def test_mrr_no_hit(self):
        """관련 결과가 없으면 MRR = 0."""
        result = mean_reciprocal_rank(["A", "B", "C"], ["D"])
        assert result == 0.0

    def test_mrr_multiple_relevant_first_hit(self):
        """여러 관련 결과 중 첫 번째가 관련 있으면 MRR = 1.0."""
        result = mean_reciprocal_rank(["A", "B", "C"], ["A", "D"])
        assert result == 1.0

    def test_mrr_empty_retrieved(self):
        """검색 결과가 없으면 MRR = 0."""
        result = mean_reciprocal_rank([], ["A"])
        assert result == 0.0


# ------------------------------------------------------------------
# Hit Rate Tests
# ------------------------------------------------------------------

class TestHitRate:
    """Hit Rate 테스트."""

    def test_hit_rate_with_hit(self):
        """관련 결과가 있으면 hit_rate = 1.0."""
        result = hit_rate(["A", "B", "C"], ["B"])
        assert result == 1.0

    def test_hit_rate_without_hit(self):
        """관련 결과가 없으면 hit_rate = 0.0."""
        result = hit_rate(["A", "D", "E"], ["B"])
        assert result == 0.0


# ------------------------------------------------------------------
# compute_all_metrics Tests
# ------------------------------------------------------------------

class TestComputeAllMetrics:
    """compute_all_metrics 테스트."""

    def test_compute_all_metrics_returns_dict(self):
        """딕셔너리를 반환해야 함."""
        result = compute_all_metrics(["A", "B", "C"], ["B"], 5)
        assert isinstance(result, dict)

    def test_compute_all_metrics_has_required_keys(self):
        """필수 키가 모두 포함되어야 함."""
        result = compute_all_metrics(["A", "B", "C"], ["B"], 5)
        assert "recall@5" in result
        assert "precision@5" in result
        assert "mrr" in result
        assert "hit_rate@5" in result

    def test_compute_all_metrics_fixed_data(self):
        """고정 데이터로 계산: retrieved=[A,B,C], expected=[B]."""
        result = compute_all_metrics(["A", "B", "C"], ["B"], 5)

        # recall@5: B가 포함됨 → 1.0
        assert result["recall@5"] == pytest.approx(1.0)

        # precision@5: 1/3 hits → 0.333...
        assert result["precision@5"] == pytest.approx(1.0 / 3.0)

        # mrr: B는 2번째 → 0.5
        assert result["mrr"] == pytest.approx(0.5)

        # hit_rate@5: 최소 1개 hit → 1.0
        assert result["hit_rate@5"] == pytest.approx(1.0)

    def test_compute_all_metrics_with_k(self):
        """k 파라미터가 올바르게 적용되어야 함."""
        result = compute_all_metrics(["A", "B", "C"], ["C"], 1)
        # recall@1: A만 확인 → C 없음 → 0.0
        assert result["recall@1"] == pytest.approx(0.0)

    def test_compute_all_metrics_empty_retrieved(self):
        """검색 결과가 비어있으면 모든 지표 = 0."""
        result = compute_all_metrics([], ["A"], 5)
        assert result["recall@5"] == pytest.approx(0.0)
        assert result["precision@5"] == pytest.approx(0.0)
        assert result["mrr"] == pytest.approx(0.0)

    def test_compute_all_metrics_empty_relevant(self):
        """관련 결과가 비어있으면 recall = 1.0."""
        result = compute_all_metrics(["A", "B"], [], 5)
        assert result["recall@5"] == pytest.approx(1.0)


# ------------------------------------------------------------------
# Integration: Fixed Data Test (Task Requirement)
# ------------------------------------------------------------------

class TestIntegration:
    """통합 테스트 — 작업 요구사항의 고정 데이터."""

    def test_fixed_data_recall_equals_1(self):
        """고정 데이터: retrieved=[A,B,C], expected=[B] → recall=1."""
        retrieved = ["A", "B", "C"]
        relevant = ["B"]
        result = recall_at_k(retrieved, relevant)
        assert result == 1.0

    def test_fixed_data_mrr_equals_0_5(self):
        """고정 데이터: retrieved=[A,B,C], expected=[B] → MRR=0.5."""
        retrieved = ["A", "B", "C"]
        relevant = ["B"]
        result = mean_reciprocal_rank(retrieved, relevant)
        assert result == pytest.approx(0.5)

    def test_fixed_data_precision_equals_1_3(self):
        """고정 데이터: retrieved=[A,B,C], expected=[B] → precision=1/3."""
        retrieved = ["A", "B", "C"]
        relevant = ["B"]
        result = precision_at_k(retrieved, relevant)
        assert result == pytest.approx(1.0 / 3.0)
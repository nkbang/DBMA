"""NAE Benchmark Evaluator 테스트.

Phase 5 기술 검토(CUE)에서 발견된 report() 집계 버그의 회귀 테스트를 포함한다:
첫 번째 결과가 skipped(metrics={})인 경우 이후 결과의 실제 지표가
avg_metrics에서 통째로 누락되던 문제.
"""

from NAE.benchmark.evaluator import Evaluator
from NAE.benchmark.schema import BenchmarkExpected, BenchmarkItem, BenchmarkQuestion


def _item(benchmark_id: str, scriptures=None) -> BenchmarkItem:
    return BenchmarkItem(
        benchmark_id=benchmark_id,
        question=BenchmarkQuestion(text=f"question {benchmark_id}"),
        expected=BenchmarkExpected(expected_scriptures=scriptures or []),
    )


class TestEvaluatorEvaluate:
    def test_evaluate_passed_when_recall_above_threshold(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", ["A"]), retrieved_ids=["A", "B", "C"])
        assert result.status == "passed"
        assert result.metrics["recall@3"] == 1.0

    def test_evaluate_failed_when_recall_below_threshold(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", ["A", "B"]), retrieved_ids=["C", "D"])
        assert result.status == "failed"

    def test_evaluate_skipped_when_relevant_ids_empty(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", []), retrieved_ids=["A"])
        assert result.status == "skipped"
        assert result.metrics == {}

    def test_evaluate_explicit_relevant_ids_overrides_item_expected(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", ["A"]), retrieved_ids=["X"], relevant_ids=["X"])
        assert result.status == "passed"

    def test_evaluate_empty_retrieved_does_not_crash(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", ["A"]), retrieved_ids=[])
        assert result.status == "failed"
        assert result.metrics["recall@0"] == 0.0


class TestEvaluatorReport:
    def test_report_empty_when_no_results(self):
        ev = Evaluator(top_k=5)
        report = ev.report()
        assert report["total_questions"] == 0
        assert report["metrics"] == {}

    def test_report_averages_metrics_across_results(self):
        ev = Evaluator(top_k=5)
        ev.evaluate(_item("B1", ["A"]), retrieved_ids=["A"])  # recall@1 = 1.0
        ev.evaluate(_item("B2", ["A"]), retrieved_ids=["X"])  # recall@1 = 0.0
        report = ev.report()
        assert report["metrics"]["recall@1"] == 0.5

    def test_report_not_biased_by_leading_skipped_result(self):
        """회귀 테스트: 첫 결과가 skipped여도 이후 결과의 지표가 avg_metrics에 반영되어야 함."""
        ev = Evaluator(top_k=5)
        ev.evaluate(_item("B1", []), retrieved_ids=["X"])  # skipped, metrics={}
        ev.evaluate(_item("B2", ["A"]), retrieved_ids=["A", "B", "C"])  # real metrics

        report = ev.report()

        assert report["metrics"] != {}
        assert report["metrics"]["recall@3"] == 1.0
        assert report["skipped"] == 1
        assert report["passed"] == 1

    def test_report_status_distribution_counts_all_statuses(self):
        ev = Evaluator(top_k=5)
        ev.evaluate(_item("B1", ["A"]), retrieved_ids=["A"])       # passed
        ev.evaluate(_item("B2", ["A"]), retrieved_ids=["X"])       # failed
        ev.evaluate(_item("B3", []), retrieved_ids=["X"])          # skipped

        report = ev.report()
        assert report["status_distribution"] == {"passed": 1, "failed": 1, "skipped": 1}

    def test_report_includes_per_question_detail(self):
        ev = Evaluator(top_k=5)
        ev.evaluate(_item("B1", ["A"]), retrieved_ids=["A"])
        report = ev.report()
        assert len(report["per_question"]) == 1
        assert report["per_question"][0]["benchmark_id"] == "B1"

    def test_reset_clears_all_state(self):
        ev = Evaluator(top_k=5)
        ev.evaluate(_item("B1", ["A"]), retrieved_ids=["A"])
        ev.reset()
        report = ev.report()
        assert report["total_questions"] == 0

"""NAE Benchmark Evaluator 테스트.

Phase 5 기술 검토(CUE)에서 발견된 report() 집계 버그의 회귀 테스트를 포함한다:
첫 번째 결과가 skipped(metrics={})인 경우 이후 결과의 실제 지표가
avg_metrics에서 통째로 누락되던 문제.

[CUE-RECONCILIATION-010, 2026-08-01] Phase 5.1 Remediation-004 이후 이
파일 전체가 실행 실패 상태였음(12개 중 이 파일에서 8개) — 근본 원인은
아래 두 가지, 실제 evaluator.py 버그가 아니라 이 테스트 파일이 구
계약을 쓰고 있었음:
  1. _item() 헬퍼가 deprecated된 BenchmarkExpected.expected_scriptures로
     gold를 만들었으나, evaluate()는 BenchmarkItem.gold_tsu_ids만 읽음
     (canonical, Remediation-004) — 모든 테스트가 항상 zero_gold였음.
  2. evaluate()에 더 이상 존재하지 않는 relevant_ids override 파라미터를
     기대하는 테스트 1건 제거(canonical 단일 gold 소스 원칙과 상충하는
     기능이라 의도적으로 제거된 것으로 판단, 복원하지 않음).
  3. "skipped" status는 evaluate()가 더 이상 반환하지 않는 죽은 값 —
     빈 gold_tsu_ids는 "zero_gold"로 분류됨. 관련 단언을 갱신.
"""

from NAE.benchmark.evaluator import Evaluator
from NAE.benchmark.schema import BenchmarkItem, BenchmarkQuestion


def _item(benchmark_id: str, gold_tsu_ids=None) -> BenchmarkItem:
    """[CUE-RECONCILIATION-010] Was building gold via the deprecated
    BenchmarkExpected.expected_scriptures field, which Evaluator.evaluate()
    never reads (per NAE/benchmark/evaluator.py's own docstring: canonical
    ground truth is BenchmarkItem.gold_tsu_ids only, per Phase 5.1
    Remediation-004). Every test using this helper always got an empty
    gold_tsu_ids and therefore always hit the zero_gold path, regardless of
    the "gold" list passed in — fixed to set gold_tsu_ids directly.
    """
    return BenchmarkItem(
        benchmark_id=benchmark_id,
        question=BenchmarkQuestion(text=f"question {benchmark_id}"),
        gold_tsu_ids=gold_tsu_ids or [],
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

    def test_evaluate_zero_gold_when_relevant_ids_empty(self):
        """[CUE-RECONCILIATION-010] Renamed from
        test_evaluate_skipped_when_relevant_ids_empty — evaluate() never
        returns status="skipped" (dead status value, still zero-initialized
        in report()'s status_dist but never set); an empty gold_tsu_ids
        list produces status="zero_gold" (Phase 5.1 Remediation-004)."""
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", []), retrieved_ids=["A"])
        assert result.status == "zero_gold"
        # zero_gold still computes real (all-zero) metrics via
        # compute_all_metrics(retrieved_ids, [], top_k) — it is not an
        # empty dict like the old "skipped" path was.
        assert result.metrics == {
            "recall@5": 0.0, "precision@5": 0.0, "mrr": 0.0, "hit_rate@5": 0.0,
        }

    def test_evaluate_empty_retrieved_does_not_crash(self):
        ev = Evaluator(top_k=5)
        result = ev.evaluate(_item("B1", ["A"]), retrieved_ids=[])
        assert result.status == "failed"
        # [CUE-RECONCILIATION-010] Metric keys always use top_k (5), even
        # when the effective retrieved count is 0 — was asserting the
        # never-produced "recall@0" key.
        assert result.metrics["recall@5"] == 0.0


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
        ev.evaluate(_item("B3", []), retrieved_ids=["X"])          # zero_gold

        report = ev.report()
        # [CUE-RECONCILIATION-010] "skipped" is never actually produced by
        # evaluate() (dead status value); empty gold_tsu_ids produces
        # "zero_gold" instead.
        assert report["status_distribution"] == {
            "passed": 1, "failed": 1, "skipped": 0, "zero_gold": 1,
        }

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

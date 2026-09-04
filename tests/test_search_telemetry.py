"""Tests for core/search_telemetry.py (DBMA-SEARCH-INFRA-001 HQ 제안 ⑨)."""

import pytest

from core.search_telemetry import SearchTelemetry


@pytest.fixture()
def telemetry(tmp_path):
    return SearchTelemetry(tmp_path / "telemetry.sqlite3")


class TestRecordQuery:
    def test_returns_incrementing_row_id(self, telemetry):
        id1 = telemetry.record_query("은혜", "hybrid", result_count=5, candidate_count=30, latency_ms=10.0)
        id2 = telemetry.record_query("사랑", "hybrid", result_count=3, candidate_count=30, latency_ms=8.0)
        assert id2 > id1


class TestSuccessAndZeroHitRate:
    def test_success_rate_with_mixed_results(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=5, candidate_count=10, latency_ms=1.0)
        telemetry.record_query("q2", "hybrid", result_count=0, candidate_count=0, latency_ms=1.0)
        telemetry.record_query("q3", "hybrid", result_count=2, candidate_count=10, latency_ms=1.0)
        assert telemetry.success_rate() == pytest.approx(2 / 3)
        assert telemetry.zero_hit_rate() == pytest.approx(1 / 3)

    def test_no_queries_returns_zero_not_error(self, telemetry):
        assert telemetry.success_rate() == 0.0
        assert telemetry.zero_hit_rate() == 0.0


class TestAverages:
    def test_avg_candidate_count(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0)
        telemetry.record_query("q2", "hybrid", result_count=1, candidate_count=30, latency_ms=1.0)
        assert telemetry.avg_candidate_count() == pytest.approx(20.0)

    def test_avg_merge_time_ms(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0, merge_time_ms=2.0)
        telemetry.record_query("q2", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0, merge_time_ms=4.0)
        assert telemetry.avg_merge_time_ms() == pytest.approx(3.0)

    def test_avg_latency_ms(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=10.0)
        telemetry.record_query("q2", "hybrid", result_count=1, candidate_count=10, latency_ms=20.0)
        assert telemetry.avg_latency_ms() == pytest.approx(15.0)

    def test_embedding_and_ann_time_default_to_zero(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0)
        assert telemetry.avg_embedding_time_ms() == 0.0
        assert telemetry.avg_ann_time_ms() == 0.0


class TestCacheHitRate:
    def test_cache_hit_rate(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0, cache_hit=True)
        telemetry.record_query("q2", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0, cache_hit=False)
        assert telemetry.cache_hit_rate() == pytest.approx(0.5)

    def test_no_cache_system_yet_defaults_to_false(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=1, candidate_count=10, latency_ms=1.0)
        assert telemetry.cache_hit_rate() == 0.0


class TestClickThroughRate:
    def test_top1_click_rate(self, telemetry):
        qid1 = telemetry.record_query("q1", "hybrid", result_count=5, candidate_count=10, latency_ms=1.0)
        qid2 = telemetry.record_query("q2", "hybrid", result_count=5, candidate_count=10, latency_ms=1.0)
        telemetry.record_click(qid1, tsu_id="TSU-1", rank=1)
        telemetry.record_click(qid2, tsu_id="TSU-2", rank=3)
        assert telemetry.click_through_rate(top_n=1) == pytest.approx(0.5)
        assert telemetry.click_through_rate(top_n=5) == pytest.approx(1.0)

    def test_no_clicks_returns_zero(self, telemetry):
        telemetry.record_query("q1", "hybrid", result_count=5, candidate_count=10, latency_ms=1.0)
        assert telemetry.click_through_rate(top_n=1) == 0.0

    def test_multiple_clicks_on_same_query_counts_once(self, telemetry):
        qid = telemetry.record_query("q1", "hybrid", result_count=5, candidate_count=10, latency_ms=1.0)
        telemetry.record_click(qid, tsu_id="TSU-1", rank=1)
        telemetry.record_click(qid, tsu_id="TSU-2", rank=2)
        assert telemetry.click_through_rate(top_n=1) == pytest.approx(1.0)


class TestSummary:
    def test_summary_contains_all_hq_metrics(self, telemetry):
        qid = telemetry.record_query(
            "은혜", "hybrid", result_count=5, candidate_count=30, latency_ms=10.0, merge_time_ms=1.0,
        )
        telemetry.record_click(qid, tsu_id="TSU-1", rank=1)

        summary = telemetry.summary()
        assert set(summary.keys()) == {
            "success_rate", "zero_hit_rate", "top1_click_rate", "top5_click_rate",
            "avg_candidate_count", "avg_merge_time_ms", "avg_latency_ms",
            "cache_hit_rate", "avg_embedding_time_ms", "avg_ann_time_ms",
        }
        assert summary["success_rate"] == 1.0
        assert summary["top1_click_rate"] == 1.0

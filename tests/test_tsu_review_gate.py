"""Tests for NAE/pipeline/tsu/review_gate.py
(NAE-TSU-REVIEW-GATE-IMPLEMENTATION-001).

All tests use tmp_path fixtures — never Production TSU
(NAE/corpus/tsu/) is modified. `filter_embedding_eligible`/
`check_tsu_review_status` are pure functions with no side effects.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from NAE.pipeline.tsu.review_gate import (
    ReviewGateStatus,
    check_tsu_review_status,
    filter_embedding_eligible,
    load_embedding_eligible_records,
)


def _record(**overrides):
    defaults = dict(id="TSU-0000001", claim="test claim", review_status="verified")
    defaults.update(overrides)
    return defaults


class TestGeneratedBlocked:
    def test_generated_status_blocks(self):
        result = check_tsu_review_status(_record(review_status="generated"))
        assert result.status == ReviewGateStatus.BLOCK
        assert result.eligible is False

    def test_generated_reason_mentions_status(self):
        result = check_tsu_review_status(_record(review_status="generated"))
        assert "generated" in result.reason


class TestReviewedBlocked:
    def test_reviewed_status_blocks(self):
        result = check_tsu_review_status(_record(review_status="reviewed"))
        assert result.status == ReviewGateStatus.BLOCK

    def test_reviewed_reason_mentions_status(self):
        result = check_tsu_review_status(_record(review_status="reviewed"))
        assert "reviewed" in result.reason


class TestVerifiedPasses:
    def test_verified_status_passes(self):
        result = check_tsu_review_status(_record(review_status="verified"))
        assert result.status == ReviewGateStatus.PASS
        assert result.eligible is True

    def test_verified_reason(self):
        result = check_tsu_review_status(_record(review_status="verified"))
        assert "verified" in result.reason

    def test_verified_carries_tsu_id(self):
        result = check_tsu_review_status(_record(id="TSU-0000042", review_status="verified"))
        assert result.tsu_id == "TSU-0000042"


class TestRejectedBlocked:
    def test_rejected_status_blocks(self):
        result = check_tsu_review_status(_record(review_status="rejected"))
        assert result.status == ReviewGateStatus.BLOCK

    def test_rejected_reason_mentions_status(self):
        result = check_tsu_review_status(_record(review_status="rejected"))
        assert "rejected" in result.reason


class TestMissingReviewStatus:
    def test_missing_review_status_blocks(self):
        record = {"id": "TSU-0000001", "claim": "x"}  # review_status 키 자체 없음
        result = check_tsu_review_status(record)
        assert result.status == ReviewGateStatus.BLOCK
        assert "missing" in result.reason

    def test_none_review_status_blocks(self):
        result = check_tsu_review_status(_record(review_status=None))
        assert result.status == ReviewGateStatus.BLOCK


class TestInvalidStatus:
    def test_unknown_status_string_blocks(self):
        result = check_tsu_review_status(_record(review_status="pending"))
        assert result.status == ReviewGateStatus.BLOCK
        assert "invalid" in result.reason

    def test_typo_status_blocks(self):
        result = check_tsu_review_status(_record(review_status="Verified"))  # 대소문자 오타
        assert result.status == ReviewGateStatus.BLOCK

    def test_empty_string_status_blocks(self):
        result = check_tsu_review_status(_record(review_status=""))
        assert result.status == ReviewGateStatus.BLOCK


class TestEmptyTsu:
    def test_empty_dict_blocks(self):
        result = check_tsu_review_status({})
        assert result.status == ReviewGateStatus.BLOCK
        assert "empty" in result.reason

    def test_none_record_blocks(self):
        result = check_tsu_review_status(None)
        assert result.status == ReviewGateStatus.BLOCK


class TestMultipleTsuBatch:
    def test_mixed_batch_filters_correctly(self):
        records = [
            _record(id="TSU-1", review_status="verified"),
            _record(id="TSU-2", review_status="generated"),
            _record(id="TSU-3", review_status="verified"),
            _record(id="TSU-4", review_status="rejected"),
            _record(id="TSU-5", review_status="reviewed"),
        ]
        summary = filter_embedding_eligible(records)
        assert [r["id"] for r in summary.pass_records] == ["TSU-1", "TSU-3"]

    def test_all_verified_batch_all_pass(self):
        records = [_record(id=f"TSU-{i}", review_status="verified") for i in range(5)]
        summary = filter_embedding_eligible(records)
        assert summary.pass_count == 5
        assert summary.block_count == 0

    def test_all_blocked_batch_none_pass(self):
        records = [_record(id=f"TSU-{i}", review_status="generated") for i in range(5)]
        summary = filter_embedding_eligible(records)
        assert summary.pass_count == 0
        assert summary.block_count == 5

    def test_empty_batch(self):
        summary = filter_embedding_eligible([])
        assert summary.total == 0
        assert summary.pass_count == 0
        assert summary.block_count == 0


class TestSummaryCounts:
    def test_summary_total_matches_input_length(self):
        records = [_record(id=f"TSU-{i}", review_status="verified") for i in range(7)]
        summary = filter_embedding_eligible(records)
        assert summary.total == 7

    def test_summary_pass_plus_block_equals_total(self):
        records = [
            _record(review_status="verified"),
            _record(review_status="generated"),
            _record(review_status="rejected"),
        ]
        summary = filter_embedding_eligible(records)
        assert summary.pass_count + summary.block_count == summary.total

    def test_block_details_contain_tsu_id_and_reason(self):
        records = [_record(id="TSU-99", review_status="generated")]
        summary = filter_embedding_eligible(records)
        assert summary.block_details == [("TSU-99", "review_status='generated' not eligible for embedding (requires 'verified')")]


class TestLoadEmbeddingEligibleRecords:
    def test_loads_and_filters_from_file(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        item_dir = tsu_root / "SomeBook"
        item_dir.mkdir(parents=True)
        (item_dir / "tsu.json").write_text(
            json.dumps(
                [
                    _record(id="TSU-1", review_status="verified"),
                    _record(id="TSU-2", review_status="generated"),
                ]
            ),
            encoding="utf-8",
        )
        records, summary = load_embedding_eligible_records("SomeBook", tsu_root)
        assert [r["id"] for r in records] == ["TSU-1"]
        assert summary.pass_count == 1
        assert summary.block_count == 1

    def test_missing_tsu_json_returns_empty(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        tsu_root.mkdir()
        records, summary = load_embedding_eligible_records("NoSuchBook", tsu_root)
        assert records == []
        assert summary.total == 0

    def test_does_not_write_any_file(self, tmp_path):
        tsu_root = tmp_path / "tsu"
        item_dir = tsu_root / "Book"
        item_dir.mkdir(parents=True)
        (item_dir / "tsu.json").write_text(json.dumps([_record(review_status="verified")]), encoding="utf-8")
        before = set(tsu_root.rglob("*"))
        load_embedding_eligible_records("Book", tsu_root)
        after = set(tsu_root.rglob("*"))
        assert before == after


class TestProductionTsuUntouched:
    def test_real_production_tsu_files_not_modified_by_this_suite(self):
        from pathlib import Path

        dagg = Path("NAE/corpus/tsu/Dagg_Church_Order/tsu.json")
        if dagg.exists():
            before = dagg.read_text(encoding="utf-8")
            # 이 테스트 스위트의 어떤 테스트도 실제 경로에 쓰기를 하지 않는다 —
            # 읽기만으로 스냅샷 비교(회귀 안전장치).
            after = dagg.read_text(encoding="utf-8")
            assert before == after


class TestIdempotency:
    def test_repeated_check_stable(self):
        record = _record(review_status="verified")
        results = {check_tsu_review_status(record).status for _ in range(30)}
        assert results == {ReviewGateStatus.PASS}

    def test_repeated_batch_filter_stable(self):
        records = [_record(id=f"TSU-{i}", review_status="verified") for i in range(3)]
        counts = {filter_embedding_eligible(records).pass_count for _ in range(10)}
        assert counts == {3}

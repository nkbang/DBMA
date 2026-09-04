"""Tests for NAE/pipeline/tsu/review_promotion.py
(NAE-TSU-REVIEW-WORKFLOW-IMPLEMENTATION-001).

All tests operate on in-memory dicts / tmp_path — Production TSU
(NAE/corpus/tsu/) is never written by this suite.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from NAE.pipeline.tsu.review_promotion import PromotionStatus, promote_batch, promote_tsu_to_verified


def _tsu_record(**overrides):
    defaults = dict(
        id="TSU-0000001",
        claim="a theological claim",
        doctrine="Ecclesiology",
        scriptures=[],
        citations=[],
        confidence=0.8,
        extraction_method="llm",
        review_status="generated",
        model="my-theology-bot-v2:latest",
    )
    defaults.update(overrides)
    return defaults


class TestReviewerMissing:
    def test_no_reviewer_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer=None, review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK
        assert "reviewer" in result.reason
        assert result.record is None

    def test_empty_string_reviewer_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="   ", review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK


class TestReviewDateMissing:
    def test_no_review_date_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date=None, review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK
        assert "review_date" in result.reason

    def test_empty_string_review_date_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK


class TestReviewDecisionNotApproved:
    def test_missing_decision_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision=None
        )
        assert result.status == PromotionStatus.BLOCK
        assert "invalid review_decision" in result.reason

    def test_garbage_decision_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision="maybe"
        )
        assert result.status == PromotionStatus.BLOCK


class TestAllConditionsMetPasses:
    def test_valid_promotion_passes(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.PASS
        assert result.promoted is True
        assert result.record["review_status"] == "verified"

    def test_valid_promotion_preserves_claim_fields(self):
        original = _tsu_record(claim="original claim text", doctrine="Soteriology")
        result = promote_tsu_to_verified(
            original, reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert result.record["claim"] == "original claim text"
        assert result.record["doctrine"] == "Soteriology"
        assert result.record["id"] == original["id"]

    def test_valid_promotion_does_not_mutate_original(self):
        original = _tsu_record()
        promote_tsu_to_verified(original, reviewer="Human", review_date="2026-08-07", review_decision="approved")
        assert original["review_status"] == "generated"  # 원본 불변

    def test_valid_promotion_includes_review_metadata(self):
        result = promote_tsu_to_verified(
            _tsu_record(),
            reviewer="Human",
            review_date="2026-08-07",
            review_decision="approved",
            review_notes="title page and claim wording cross-checked",
        )
        meta = result.record["review_metadata"]
        assert meta["reviewer"] == "Human"
        assert meta["review_date"] == "2026-08-07"
        assert meta["review_decision"] == "approved"
        assert meta["review_notes"] == "title page and claim wording cross-checked"


class TestRejectedTsu:
    def test_review_decision_rejected_blocks_verification(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision="rejected"
        )
        assert result.status == PromotionStatus.BLOCK
        assert result.record["review_status"] == "rejected"

    def test_rejected_record_still_carries_audit_metadata(self):
        result = promote_tsu_to_verified(
            _tsu_record(),
            reviewer="Human",
            review_date="2026-08-07",
            review_decision="rejected",
            review_notes="claim not grounded in source text",
        )
        assert result.record["review_metadata"]["reviewer"] == "Human"
        assert result.record["review_metadata"]["review_decision"] == "rejected"


class TestAlreadyVerifiedRePromotion:
    def test_already_verified_reprotion_is_idempotent_pass(self):
        already_verified = _tsu_record(review_status="verified")
        result = promote_tsu_to_verified(
            already_verified, reviewer="Human2", review_date="2026-08-08", review_decision="approved"
        )
        assert result.status == PromotionStatus.PASS
        assert "already verified" in result.reason

    def test_reprotion_does_not_overwrite_original_review_metadata(self):
        already_verified = _tsu_record(
            review_status="verified",
            review_metadata={"reviewer": "FirstReviewer", "review_date": "2026-08-01", "review_decision": "approved", "review_notes": None},
        )
        result = promote_tsu_to_verified(
            already_verified, reviewer="SecondReviewer", review_date="2026-08-08", review_decision="approved"
        )
        assert result.record["review_metadata"]["reviewer"] == "FirstReviewer"  # 덮어쓰지 않음


class TestAuditMetadataPreserved:
    def test_who_when_why_all_present(self):
        result = promote_tsu_to_verified(
            _tsu_record(),
            reviewer="Human",
            review_date="2026-08-07T12:00:00+09:00",
            review_decision="approved",
            review_notes="grounded in original OCR title page",
        )
        meta = result.record["review_metadata"]
        assert meta["reviewer"]  # who
        assert meta["review_date"]  # when
        assert meta["review_notes"]  # why

    def test_review_notes_optional(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert result.record["review_metadata"]["review_notes"] is None


class TestBatchPromotion:
    def test_batch_promotes_multiple_records(self):
        records = [_tsu_record(id=f"TSU-{i}") for i in range(3)]
        results = promote_batch(records, reviewer="Human", review_date="2026-08-07", review_decision="approved")
        assert all(r.status == PromotionStatus.PASS for r in results)
        assert len(results) == 3

    def test_batch_independent_failure_does_not_block_others(self):
        records = [_tsu_record(id="TSU-1"), {}, _tsu_record(id="TSU-3")]
        results = promote_batch(records, reviewer="Human", review_date="2026-08-07", review_decision="approved")
        assert results[0].status == PromotionStatus.PASS
        assert results[1].status == PromotionStatus.BLOCK
        assert results[2].status == PromotionStatus.PASS


class TestInvalidMetadata:
    def test_non_string_reviewer_blocks(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer=12345, review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK

    def test_empty_tsu_record_blocks(self):
        result = promote_tsu_to_verified(
            {}, reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK
        assert "empty" in result.reason

    def test_none_tsu_record_blocks(self):
        result = promote_tsu_to_verified(
            None, reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert result.status == PromotionStatus.BLOCK


class TestNoForcedOrDefaultVerify:
    def test_no_keyword_defaults_to_verified(self):
        """reviewer/review_date/review_decision을 아예 생략(None 기본값)하면
        절대 verified가 되지 않는다 — "default verify" 금지 확인."""
        result = promote_tsu_to_verified(_tsu_record(), reviewer=None, review_date=None, review_decision=None)
        assert result.status == PromotionStatus.BLOCK
        assert result.record is None

    def test_original_review_status_never_silently_becomes_verified(self):
        record = _tsu_record(review_status="reviewed")
        result = promote_tsu_to_verified(record, reviewer="", review_date="", review_decision="")
        assert result.status == PromotionStatus.BLOCK
        assert record["review_status"] == "reviewed"  # 원본도 그대로


class TestRegression:
    def test_promote_tsu_to_verified_importable_and_callable(self):
        assert callable(promote_tsu_to_verified)

    def test_result_dataclass_has_expected_fields(self):
        result = promote_tsu_to_verified(
            _tsu_record(), reviewer="Human", review_date="2026-08-07", review_decision="approved"
        )
        assert hasattr(result, "status")
        assert hasattr(result, "reason")
        assert hasattr(result, "tsu_id")
        assert hasattr(result, "record")

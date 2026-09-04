"""Tests for pipeline_stages.py — the rule that a stage with no evidence
of having run must report QUEUED, never RUNNING/COMPLETE."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1] / ".automation" / "night-shift" / "dashboard" / "backend"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _BACKEND_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pipeline_stages = _load("pipeline_stages")


def _records(*statuses):
    return [{"review_status": s} for s in statuses]


class TestRegistrationSourceId:
    def test_maps_fuller_volume(self):
        assert pipeline_stages.registration_source_id("Fuller_Complete_Works_Vol01") == "BAP-MISS-FULLER-VOL01"
        assert pipeline_stages.registration_source_id("Fuller_Complete_Works_Vol08") == "BAP-MISS-FULLER-VOL08"

    def test_none_for_unrecognized_identifier(self):
        assert pipeline_stages.registration_source_id("Dagg_Church_Order") is None
        assert pipeline_stages.registration_source_id("") is None


class TestRegistrationStageStatus:
    def test_complete_when_quality_passed(self):
        state = {"BAP-MISS-FULLER-VOL01": {"state": "QUALITY_PASSED"}}
        assert pipeline_stages.registration_stage_status("Fuller_Complete_Works_Vol01", state) == "COMPLETE"

    def test_running_when_in_progress_state(self):
        state = {"BAP-MISS-FULLER-VOL01": {"state": "VALIDATED"}}
        assert pipeline_stages.registration_stage_status("Fuller_Complete_Works_Vol01", state) == "RUNNING"

    def test_error_on_failure_state(self):
        state = {"BAP-MISS-FULLER-VOL01": {"state": "QUALITY_GATE_FAILED"}}
        assert pipeline_stages.registration_stage_status("Fuller_Complete_Works_Vol01", state) == "ERROR"

    def test_queued_when_absent(self):
        assert pipeline_stages.registration_stage_status("Fuller_Complete_Works_Vol02", {}) == "QUEUED"
        assert pipeline_stages.registration_stage_status("Unmapped_Identifier", {"x": {"state": "QUALITY_PASSED"}}) == "QUEUED"


class TestTallyReviewStatus:
    def test_counts_each_bucket(self):
        tally = pipeline_stages.tally_review_status(
            _records("generated", "generated", "reviewed", "verified", "verified", "rejected")
        )
        assert tally.total == 6
        assert tally.generated == 2
        assert tally.reviewed == 1
        assert tally.verified == 2
        assert tally.rejected == 1

    def test_empty(self):
        tally = pipeline_stages.tally_review_status([])
        assert tally.total == 0


class TestQualityGateAndReviewStageStatus:
    def test_no_records_yet_is_queued(self):
        tally = pipeline_stages.ReviewTally(total=0)
        assert pipeline_stages.quality_gate_stage_status(tally, False) == "QUEUED"
        assert pipeline_stages.review_stage_status(tally, False) == "QUEUED"

    def test_all_generated_zero_verified_blocks_gate_but_review_is_queued(self):
        """This is the real Fuller Vol.01 situation right now: extraction
        has produced thousands of claims, none reviewed yet."""
        tally = pipeline_stages.tally_review_status(_records("generated", "generated", "generated"))
        assert pipeline_stages.quality_gate_stage_status(tally, False) == "BLOCKED"
        assert pipeline_stages.review_stage_status(tally, False) == "QUEUED"

    def test_partial_review_is_running(self):
        tally = pipeline_stages.tally_review_status(_records("generated", "reviewed", "verified"))
        assert pipeline_stages.review_stage_status(tally, True) == "RUNNING"
        assert pipeline_stages.quality_gate_stage_status(tally, True) == "RUNNING"

    def test_fully_reviewed_and_extraction_complete_is_complete(self):
        tally = pipeline_stages.tally_review_status(_records("verified", "verified", "rejected"))
        assert pipeline_stages.review_stage_status(tally, True) == "COMPLETE"

    def test_fully_verified_but_extraction_still_running_is_not_yet_complete(self):
        tally = pipeline_stages.tally_review_status(_records("verified", "verified"))
        assert pipeline_stages.quality_gate_stage_status(tally, False) == "RUNNING"


class TestIndexStatusFromReport:
    def test_none_when_no_report(self):
        assert pipeline_stages.index_status_from_report(None) is None
        assert pipeline_stages.index_status_from_report({}) is None

    def test_none_when_indexed_zero(self):
        """Backup/remediation runs leave a report with indexed=0 — that
        must not read as COMPLETE."""
        assert pipeline_stages.index_status_from_report({"indexed": 0, "gate_pass": 0}) is None

    def test_complete_when_indexed_positive(self):
        assert pipeline_stages.index_status_from_report({"indexed": 5}) == "COMPLETE"


class TestEmbeddingAndQdrantStageStatus:
    def test_zero_verified_is_always_queued_regardless_of_index_report(self):
        tally = pipeline_stages.tally_review_status(_records("generated", "generated"))
        assert pipeline_stages.embedding_stage_status(tally, "COMPLETE") == "QUEUED"
        assert pipeline_stages.qdrant_stage_status(tally, "COMPLETE") == "QUEUED"

    def test_verified_records_but_no_index_evidence_is_queued(self):
        tally = pipeline_stages.tally_review_status(_records("verified"))
        assert pipeline_stages.embedding_stage_status(tally, None) == "QUEUED"

    def test_verified_records_with_index_evidence_is_complete(self):
        tally = pipeline_stages.tally_review_status(_records("verified"))
        assert pipeline_stages.embedding_stage_status(tally, "COMPLETE") == "COMPLETE"
        assert pipeline_stages.qdrant_stage_status(tally, "COMPLETE") == "COMPLETE"


class TestComputePipelineStagesIntegration:
    def test_matches_real_fuller_vol01_shape(self):
        """Registration complete, extraction running, nothing downstream
        has touched this volume's records yet — the actual situation as
        of this dashboard build."""
        registration_state = {"BAP-MISS-FULLER-VOL01": {"state": "QUALITY_PASSED"}}
        tsu_records = _records(*(["generated"] * 2400))

        stages = pipeline_stages.compute_pipeline_stages(
            identifier="Fuller_Complete_Works_Vol01",
            registration_state=registration_state,
            tsu_records=tsu_records,
            extraction_status="RUNNING",
            index_report=None,
        )
        by_stage = {s["stage"]: s["status"] for s in stages}

        assert by_stage["Registration"] == "COMPLETE"
        assert by_stage["TSU Extraction"] == "RUNNING"
        assert by_stage["Quality Gate"] == "BLOCKED"
        assert by_stage["Review"] == "QUEUED"
        assert by_stage["Embedding"] == "QUEUED"
        assert by_stage["Qdrant"] == "QUEUED"

    def test_queued_volume_is_queued_end_to_end(self):
        stages = pipeline_stages.compute_pipeline_stages(
            identifier="Fuller_Complete_Works_Vol02",
            registration_state={"BAP-MISS-FULLER-VOL02": {"state": "QUALITY_PASSED"}},
            tsu_records=None,
            extraction_status="QUEUED",
            index_report=None,
        )
        by_stage = {s["stage"]: s["status"] for s in stages}
        assert by_stage["Registration"] == "COMPLETE"
        assert by_stage["TSU Extraction"] == "QUEUED"
        assert by_stage["Quality Gate"] == "QUEUED"
        assert by_stage["Review"] == "QUEUED"

    def test_failed_extraction_maps_to_error(self):
        stages = pipeline_stages.compute_pipeline_stages(
            identifier="Fuller_Complete_Works_Vol03",
            registration_state={},
            tsu_records=None,
            extraction_status="FAILED",
            index_report=None,
        )
        by_stage = {s["stage"]: s["status"] for s in stages}
        assert by_stage["TSU Extraction"] == "ERROR"

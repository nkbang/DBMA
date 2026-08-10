"""Tests for scripts/crosswalk/tsu_gate.py (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001 §7)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.tsu_gate import TsuGateStatus, check_tsu_gate


def _record(**overrides):
    defaults = dict(
        crosswalk_id="cw_001",
        source_identifier="BAP-CHURCH-DAGG-001",
        source_type=SourceType.REGISTRY_SOURCE_ID,
        target_identifier="PBC1742",
        target_type=TargetType.CORPUS_CANONICAL_ID,
        mapping_status=MappingStatus.MANUAL_CONFIRMED,
        confidence=Confidence.HIGH,
        evidence="archive.org metadata title/author cross-checked",
        created_at="2026-08-05T00:00:00+09:00",
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


class TestGateEligible:
    def test_eligible_when_tsu_ready_and_manual_confirmed(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_record())
        assert result.eligible is True

    def test_pass_status_explicit(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_record())
        assert result.status == TsuGateStatus.PASS
        assert result.status.value == "TSU_GATE_PASS"


class TestGateBlocked:
    def test_blocked_when_tsu_not_eligible(self):
        result = check_tsu_gate(tsu_eligible=False, crosswalk_record=_record())
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK
        assert "TSU_ELIGIBLE" in result.reason

    def test_blocked_when_no_crosswalk_record(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=None)
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK
        assert "Crosswalk mapping" in result.reason

    def test_blocked_when_status_is_verified_not_manual_confirmed(self):
        record = _record(mapping_status=MappingStatus.VERIFIED)
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=record)
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK
        assert "manual-confirmed" in result.reason

    def test_blocked_when_status_is_evidence_backed(self):
        record = _record(mapping_status=MappingStatus.EVIDENCE_BACKED)
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=record)
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK

    def test_blocked_when_confidence_not_high(self):
        record = _record(confidence=Confidence.MEDIUM)
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=record)
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK
        assert "Gate 조건" in result.reason

    def test_blocked_when_evidence_missing(self):
        record = _record(evidence="")
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=record)
        assert result.eligible is False
        assert result.status == TsuGateStatus.BLOCK

    def test_block_status_value_string(self):
        result = check_tsu_gate(tsu_eligible=False, crosswalk_record=None)
        assert result.status.value == "TSU_GATE_BLOCK"


class TestGateError:
    def test_storage_error_returns_error_status(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_record(), storage_error="YAML parse 실패")
        assert result.status == TsuGateStatus.ERROR
        assert result.eligible is False
        assert "YAML parse 실패" in result.reason

    def test_storage_error_takes_priority_over_valid_record(self):
        """저장소 오류가 있으면, 넘겨받은 crosswalk_record가 아무리
        완벽해도(is_gate_eligible=True) ERROR가 우선한다 — 저장소를
        신뢰할 수 없으면 그 안의 어떤 값도 신뢰할 근거가 없기 때문."""
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_record(), storage_error="index corrupted")
        assert result.status == TsuGateStatus.ERROR

    def test_storage_error_status_value_string(self):
        result = check_tsu_gate(tsu_eligible=True, crosswalk_record=None, storage_error="repository unavailable")
        assert result.status.value == "TSU_GATE_ERROR"

    def test_error_distinct_from_block(self):
        error_result = check_tsu_gate(tsu_eligible=True, crosswalk_record=None, storage_error="broken")
        block_result = check_tsu_gate(tsu_eligible=True, crosswalk_record=None)
        assert error_result.status != block_result.status
        assert error_result.eligible == block_result.eligible == False  # noqa: E712 — 둘 다 False지만 status는 달라야 함


class TestBackwardCompatibility:
    def test_eligible_property_still_works_without_status_check(self):
        """기존 호출자가 result.eligible만 보고 판단해도 여전히 정확하게
        동작한다(TsuGateStatus 도입 이전 호출 코드와의 하위 호환)."""
        pass_result = check_tsu_gate(tsu_eligible=True, crosswalk_record=_record())
        block_result = check_tsu_gate(tsu_eligible=False, crosswalk_record=None)
        error_result = check_tsu_gate(tsu_eligible=True, crosswalk_record=None, storage_error="x")
        assert pass_result.eligible is True
        assert block_result.eligible is False
        assert error_result.eligible is False


class TestIdempotency:
    def test_repeated_calls_stable(self):
        record = _record()
        results = {check_tsu_gate(tsu_eligible=True, crosswalk_record=record).eligible for _ in range(50)}
        assert results == {True}

    def test_repeated_error_calls_stable(self):
        results = {
            check_tsu_gate(tsu_eligible=True, crosswalk_record=None, storage_error="x").status for _ in range(50)
        }
        assert results == {TsuGateStatus.ERROR}

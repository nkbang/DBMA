"""Tests for scripts/crosswalk/schema.py (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.crosswalk.schema import (
    Confidence,
    CrosswalkRecord,
    MappingStatus,
    SchemaError,
    SourceType,
    TargetType,
    confidence_score,
)


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
        verified_at="2026-08-05T01:00:00+09:00",
    )
    defaults.update(overrides)
    return CrosswalkRecord(**defaults)


class TestConstruction:
    def test_valid_record_constructs(self):
        record = _record()
        assert record.crosswalk_id == "cw_001"
        assert record.mapping_status == MappingStatus.MANUAL_CONFIRMED

    def test_missing_crosswalk_id_raises(self):
        with pytest.raises(SchemaError):
            _record(crosswalk_id="")

    def test_missing_source_identifier_raises(self):
        with pytest.raises(SchemaError):
            _record(source_identifier="   ")

    def test_missing_target_identifier_raises(self):
        with pytest.raises(SchemaError):
            _record(target_identifier="")

    def test_missing_created_at_raises(self):
        with pytest.raises(SchemaError):
            _record(created_at="")

    def test_invalid_source_type_raises(self):
        with pytest.raises(ValueError):
            _record(source_type="not_a_real_source_type")

    def test_invalid_target_type_raises(self):
        with pytest.raises(ValueError):
            _record(target_type="not_a_real_target_type")

    def test_invalid_mapping_status_raises(self):
        with pytest.raises(ValueError):
            _record(mapping_status="auto-guessed")

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError):
            _record(confidence="extremely-sure")

    def test_confidence_none_allowed(self):
        record = _record(mapping_status=MappingStatus.UNMAPPED, confidence=None, evidence=None)
        assert record.confidence is None


class TestSerialization:
    def test_to_dict_roundtrip(self):
        record = _record()
        data = record.to_dict()
        restored = CrosswalkRecord.from_dict(data)
        assert restored.to_dict() == data

    def test_from_dict_missing_field_raises(self):
        with pytest.raises(SchemaError):
            CrosswalkRecord.from_dict({"crosswalk_id": "cw_001"})

    def test_to_dict_serializes_enums_as_strings(self):
        record = _record()
        data = record.to_dict()
        assert data["mapping_status"] == "manual-confirmed"
        assert data["confidence"] == "high"


class TestConfidenceScore:
    def test_high_is_1_0(self):
        assert confidence_score(Confidence.HIGH) == 1.0

    def test_medium_below_1_0(self):
        assert confidence_score(Confidence.MEDIUM) < 1.0

    def test_low_below_medium(self):
        assert confidence_score(Confidence.LOW) < confidence_score(Confidence.MEDIUM)

    def test_none_is_zero(self):
        assert confidence_score(None) == 0.0


class TestGateEligibility:
    def test_manual_confirmed_high_confidence_with_evidence_is_eligible(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=Confidence.HIGH)
        assert record.is_gate_eligible() is True

    def test_verified_high_confidence_with_evidence_is_eligible(self):
        record = _record(mapping_status=MappingStatus.VERIFIED, confidence=Confidence.HIGH)
        assert record.is_gate_eligible() is True

    def test_evidence_backed_is_not_eligible(self):
        record = _record(mapping_status=MappingStatus.EVIDENCE_BACKED, confidence=Confidence.HIGH)
        assert record.is_gate_eligible() is False

    def test_unmapped_is_not_eligible(self):
        record = _record(mapping_status=MappingStatus.UNMAPPED, confidence=None, evidence=None)
        assert record.is_gate_eligible() is False

    def test_medium_confidence_is_not_eligible(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=Confidence.MEDIUM)
        assert record.is_gate_eligible() is False

    def test_missing_evidence_is_not_eligible(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=Confidence.HIGH, evidence="")
        assert record.is_gate_eligible() is False

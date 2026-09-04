"""Tests for scripts/crosswalk/validator.py (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType
from scripts.crosswalk.validator import validate


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


class TestEmptyInput:
    def test_no_records_warns(self):
        result = validate([])
        assert result.warning_count == 1
        assert result.fail_count == 0


class TestCheck1DuplicateCrosswalkId:
    def test_unique_ids_pass(self):
        records = [_record(crosswalk_id="cw_001"), _record(crosswalk_id="cw_002", target_identifier="PBC1765")]
        result = validate(records)
        assert result.fail_count == 0

    def test_duplicate_id_fails(self):
        records = [_record(crosswalk_id="cw_001"), _record(crosswalk_id="cw_001", target_identifier="PBC1765")]
        result = validate(records)
        assert result.fail_count >= 2  # 두 레코드 모두 중복으로 표시됨
        assert any("crosswalk_id 중복" in line for line in result.lines)


class TestCheck2DuplicateSourceTargetPair:
    def test_unique_pairs_pass(self):
        records = [
            _record(crosswalk_id="cw_001", source_identifier="BAP-CHURCH-DAGG-001", target_identifier="PBC1742"),
            _record(crosswalk_id="cw_002", source_identifier="BAP-CHURCH-HISCOX", target_identifier="PBC1765"),
        ]
        result = validate(records)
        assert result.fail_count == 0

    def test_duplicate_pair_fails(self):
        records = [
            _record(crosswalk_id="cw_001", source_identifier="BAP-CHURCH-DAGG-001", target_identifier="PBC1742"),
            _record(crosswalk_id="cw_002", source_identifier="BAP-CHURCH-DAGG-001", target_identifier="PBC1742"),
        ]
        result = validate(records)
        assert any("source-target 쌍 중복" in line for line in result.lines)


class TestCheck3MissingEvidence:
    def test_manual_confirmed_without_evidence_fails(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, evidence="")
        result = validate([record])
        assert any("evidence 누락" in line for line in result.lines)
        assert result.fail_count >= 1

    def test_evidence_backed_without_evidence_fails(self):
        record = _record(mapping_status=MappingStatus.EVIDENCE_BACKED, evidence=None)
        result = validate([record])
        assert any("evidence 누락" in line for line in result.lines)

    def test_verified_with_evidence_passes(self):
        record = _record(mapping_status=MappingStatus.VERIFIED, evidence="manual archive.org check")
        result = validate([record])
        assert not any("evidence 누락" in line for line in result.lines if record.crosswalk_id in line)

    def test_unmapped_without_evidence_does_not_fail_evidence_check(self):
        record = _record(mapping_status=MappingStatus.UNMAPPED, confidence=None, evidence=None)
        result = validate([record])
        assert any("evidence 불필요" in line for line in result.lines)


class TestCheck4InvalidMappingStatus:
    def test_unmapped_with_confidence_set_fails(self):
        record = _record(mapping_status=MappingStatus.UNMAPPED, confidence=Confidence.HIGH, evidence=None)
        result = validate([record])
        assert any("unmapped인데 confidence가 설정됨" in line for line in result.lines)

    def test_non_unmapped_without_confidence_fails(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=None)
        result = validate([record])
        assert any("confidence 누락" in line for line in result.lines)

    def test_valid_status_confidence_pair_passes(self):
        record = _record(mapping_status=MappingStatus.MANUAL_CONFIRMED, confidence=Confidence.HIGH)
        result = validate([record])
        assert result.fail_count == 0


class TestCheck5BrokenIdentifierReference:
    def test_valid_source_identifier_passes(self):
        record = _record(source_identifier="BAP-CHURCH-DAGG-001")
        result = validate([record], valid_source_identifiers={"BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX"})
        assert result.fail_count == 0

    def test_unknown_source_identifier_fails(self):
        record = _record(source_identifier="UNKNOWN-SOURCE-999")
        result = validate([record], valid_source_identifiers={"BAP-CHURCH-DAGG-001"})
        assert any("Broken Reference" in line for line in result.lines)

    def test_no_valid_set_provided_warns_and_skips(self):
        record = _record()
        result = validate([record], valid_source_identifiers=None)
        assert any("생략" in line for line in result.lines)


class TestIdempotency:
    def test_validate_twice_yields_same_counts(self):
        records = [_record(crosswalk_id="cw_001"), _record(crosswalk_id="cw_002", target_identifier="PBC1765")]
        result1 = validate(records)
        result2 = validate(records)
        assert (result1.pass_count, result1.warning_count, result1.fail_count) == (
            result2.pass_count,
            result2.warning_count,
            result2.fail_count,
        )

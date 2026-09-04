"""Tests for scripts/crosswalk/repository.py (NAE-CROSSWALK-TEST-EVIDENCE-FIX-001 T2).

Covers: save(add), query(get/get_by_source/list_all), duplicate
detection, and immutable identifier(frozen CrosswalkRecord).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from scripts.crosswalk.repository import DuplicateCrosswalkIdError, InMemoryCrosswalkRepository
from scripts.crosswalk.schema import Confidence, CrosswalkRecord, MappingStatus, SourceType, TargetType


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


class TestSave:
    def test_add_then_get_roundtrip(self):
        repo = InMemoryCrosswalkRepository()
        record = _record()
        repo.add(record)
        assert repo.get("cw_001") is record

    def test_add_multiple_distinct_records(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        assert len(repo.list_all()) == 2


class TestQuery:
    def test_get_missing_returns_none(self):
        repo = InMemoryCrosswalkRepository()
        assert repo.get("nonexistent") is None

    def test_get_by_source_returns_matching_records_only(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001", source_identifier="BAP-CHURCH-DAGG-001"))
        repo.add(_record(crosswalk_id="cw_002", source_identifier="BAP-CHURCH-HISCOX", target_identifier="PBC1765"))
        results = repo.get_by_source("BAP-CHURCH-DAGG-001")
        assert len(results) == 1
        assert results[0].crosswalk_id == "cw_001"

    def test_get_by_source_no_match_returns_empty_list(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record())
        assert repo.get_by_source("NEVER-SEEN") == []

    def test_list_all_empty_repository(self):
        repo = InMemoryCrosswalkRepository()
        assert repo.list_all() == []

    def test_list_all_returns_every_record(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))
        ids = {r.crosswalk_id for r in repo.list_all()}
        assert ids == {"cw_001", "cw_002"}


class TestDuplicateDetection:
    def test_duplicate_crosswalk_id_raises(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001"))
        with pytest.raises(DuplicateCrosswalkIdError):
            repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))

    def test_duplicate_add_does_not_overwrite_original(self):
        repo = InMemoryCrosswalkRepository()
        original = _record(crosswalk_id="cw_001", target_identifier="PBC1742")
        repo.add(original)
        try:
            repo.add(_record(crosswalk_id="cw_001", target_identifier="PBC1765"))
        except DuplicateCrosswalkIdError:
            pass
        assert repo.get("cw_001").target_identifier == "PBC1742"

    def test_different_ids_do_not_raise(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record(crosswalk_id="cw_001"))
        repo.add(_record(crosswalk_id="cw_002", target_identifier="PBC1765"))  # no raise


class TestImmutableIdentifier:
    def test_mutating_crosswalk_id_raises(self):
        record = _record()
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError (subclass of AttributeError)
            record.crosswalk_id = "changed"

    def test_mutating_source_identifier_raises(self):
        record = _record()
        with pytest.raises(Exception):
            record.source_identifier = "CHANGED-SOURCE"

    def test_mutating_mapping_status_raises(self):
        record = _record()
        with pytest.raises(Exception):
            record.mapping_status = MappingStatus.UNMAPPED

    def test_stored_record_identity_unchanged_after_retrieval(self):
        repo = InMemoryCrosswalkRepository()
        record = _record()
        repo.add(record)
        retrieved = repo.get("cw_001")
        assert retrieved.source_identifier == "BAP-CHURCH-DAGG-001"
        assert retrieved.crosswalk_id == "cw_001"


class TestIdempotency:
    def test_get_called_twice_returns_same_object(self):
        repo = InMemoryCrosswalkRepository()
        repo.add(_record())
        assert repo.get("cw_001") is repo.get("cw_001")

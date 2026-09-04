"""Tests for scripts/crosswalk/resolver.py (NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.crosswalk.repository import InMemoryCrosswalkRepository
from scripts.crosswalk.resolver import CrosswalkResolver
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


def _resolver_with(*records) -> CrosswalkResolver:
    repo = InMemoryCrosswalkRepository()
    for r in records:
        repo.add(r)
    return CrosswalkResolver(repo)


class TestResolveSuccess:
    def test_resolve_returns_target_for_gate_eligible_record(self):
        resolver = _resolver_with(_record())
        assert resolver.resolve("BAP-CHURCH-DAGG-001") == "PBC1742"

    def test_resolve_verified_status_also_succeeds(self):
        resolver = _resolver_with(_record(mapping_status=MappingStatus.VERIFIED))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") == "PBC1742"

    def test_resolve_record_returns_full_record(self):
        record = _record()
        resolver = _resolver_with(record)
        resolved = resolver.resolve_record("BAP-CHURCH-DAGG-001")
        assert resolved is not None
        assert resolved.crosswalk_id == "cw_001"


class TestResolveFailure:
    def test_resolve_unknown_source_returns_none(self):
        resolver = _resolver_with(_record())
        assert resolver.resolve("NEVER-SEEN-SOURCE") is None

    def test_resolve_evidence_backed_status_returns_none(self):
        resolver = _resolver_with(_record(mapping_status=MappingStatus.EVIDENCE_BACKED))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None

    def test_resolve_low_confidence_returns_none(self):
        resolver = _resolver_with(_record(confidence=Confidence.LOW))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None

    def test_resolve_medium_confidence_returns_none(self):
        resolver = _resolver_with(_record(confidence=Confidence.MEDIUM))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None

    def test_resolve_missing_evidence_returns_none(self):
        resolver = _resolver_with(_record(evidence=""))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None

    def test_resolve_ambiguous_multiple_eligible_returns_none(self):
        resolver = _resolver_with(
            _record(crosswalk_id="cw_001", target_identifier="PBC1742"),
            _record(crosswalk_id="cw_002", target_identifier="PBC1765"),
        )
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None

    def test_resolve_empty_repository_returns_none(self):
        resolver = _resolver_with()
        assert resolver.resolve("BAP-CHURCH-DAGG-001") is None


class TestNoFuzzyMatching:
    def test_similar_but_different_identifier_does_not_match(self):
        """대소문자/공백/유사 문자열이 달라도 정확히 일치하지 않으면
        매칭하지 않는다 — fuzzy matching 금지 요구사항의 코드 검증."""
        resolver = _resolver_with(_record(source_identifier="BAP-CHURCH-DAGG-001"))
        assert resolver.resolve("bap-church-dagg-001") is None
        assert resolver.resolve("BAP-CHURCH-DAGG-002") is None
        assert resolver.resolve("BAP CHURCH DAGG 001") is None

    def test_exact_match_required(self):
        resolver = _resolver_with(_record(source_identifier="BAP-CHURCH-DAGG-001"))
        assert resolver.resolve("BAP-CHURCH-DAGG-001") == "PBC1742"


class TestIdempotency:
    def test_resolve_called_twice_returns_same_result(self):
        resolver = _resolver_with(_record())
        first = resolver.resolve("BAP-CHURCH-DAGG-001")
        second = resolver.resolve("BAP-CHURCH-DAGG-001")
        assert first == second == "PBC1742"

    def test_resolve_100_times_stable(self):
        resolver = _resolver_with(_record())
        results = {resolver.resolve("BAP-CHURCH-DAGG-001") for _ in range(100)}
        assert results == {"PBC1742"}

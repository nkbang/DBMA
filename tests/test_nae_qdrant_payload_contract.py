"""Tests for NAE/pipeline/index/qdrant_store.py::build_point()
Metadata Schema 1.1.0 payload contract
(NAE-VECTOR-PAYLOAD-CONTRACT-IMPLEMENTATION-001).

`build_point()` is a pure function (no network I/O — it never calls
Qdrant or the embedding client), so these tests never touch a real
Qdrant instance and never write to Production TSU files.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from NAE.pipeline.index import qdrant_store


def _migrated_record(**overrides):
    defaults = dict(
        id="TSU-0000006",
        tsu_schema_version="1",
        book="Church Order",
        author="John L. Dagg",
        identifier="Dagg_Church_Order",
        source_identifier="Dagg_Church_Order",
        collector_version="",
        canonical_version="2.0.0",
        page=8,
        paragraph=8,
        sentence=0,
        source_text="source text",
        claim="a claim",
        doctrine="Ecclesiology",
        scriptures=[],
        citations=[],
        confidence=0.8,
        extraction_method="llm",
        review_status="verified",
        model="my-theology-bot-v2:latest",
        source_id="BAP-CHURCH-DAGG-001",
        author_id="dagg_john_l",
        work_id="WORK-DAGG-CHURCH-ORDER-001",
        edition_id="WORK-DAGG-CHURCH-ORDER-001-1871",
        volume_id=None,
        publication_year=1871,
        source_type="reference",
        copyright_status="public_domain",
        usage_permission="research",
        access_control="public",
        tsu_access="full",
        metadata_schema_version="1.1.0",
        category=None,
        category_status="AUTHORITATIVE_SOURCE_MISSING",
        citation_policy=None,
        citation_policy_status="AUTHORITATIVE_SOURCE_MISSING",
        metadata_provenance={"crosswalk_id": "f914f6c442983e59", "resolved_at": "2026-08-08T00:00:00+00:00", "resolver_version": "1.0.0"},
    )
    defaults.update(overrides)
    return defaults


_VECTOR = [0.1] * 1024


class TestExistingPayloadPreservation:
    def test_tsu_id_preserved(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["tsu_id"] == "TSU-0000006"

    def test_claim_preserved(self):
        point = qdrant_store.build_point(_migrated_record(claim="original claim text"), _VECTOR)
        assert point.payload["claim"] == "original claim text"

    def test_doctrine_preserved(self):
        point = qdrant_store.build_point(_migrated_record(doctrine="Soteriology"), _VECTOR)
        assert point.payload["doctrine"] == "Soteriology"

    def test_scriptures_and_citations_preserved(self):
        point = qdrant_store.build_point(_migrated_record(scriptures=["Acts 2:41"], citations=["John Gill"]), _VECTOR)
        assert point.payload["scriptures"] == ["Acts 2:41"]
        assert point.payload["citations"] == ["John Gill"]

    def test_no_existing_field_removed(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        legacy_fields = {
            "tsu_id", "book", "author", "identifier", "source_identifier", "doctrine",
            "page", "paragraph", "sentence", "claim", "source_text", "scriptures",
            "citations", "review_status", "llm_score", "parser_score", "evidence_score",
            "citation_score", "overall_score", "duplicate_of", "tsu_schema_version",
            "collector_version", "canonical_version",
        }
        assert legacy_fields <= set(point.payload.keys())


class TestMetadataMapping:
    def test_source_id_mapped(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["source_id"] == "BAP-CHURCH-DAGG-001"

    def test_author_id_work_id_edition_id_mapped(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["author_id"] == "dagg_john_l"
        assert point.payload["work_id"] == "WORK-DAGG-CHURCH-ORDER-001"
        assert point.payload["edition_id"] == "WORK-DAGG-CHURCH-ORDER-001-1871"

    def test_source_work_edition_full_chain_mapping(self):
        point = qdrant_store.build_point(
            _migrated_record(source_id="X-1", author_id="A-1", work_id="W-1", edition_id="E-1"), _VECTOR
        )
        assert (point.payload["source_id"], point.payload["author_id"],
                point.payload["work_id"], point.payload["edition_id"]) == ("X-1", "A-1", "W-1", "E-1")

    def test_copyright_usage_access_mapped(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["copyright_status"] == "public_domain"
        assert point.payload["usage_permission"] == "research"
        assert point.payload["access_control"] == "public"

    def test_tsu_access_mapped(self):
        point = qdrant_store.build_point(_migrated_record(tsu_access="citation_only"), _VECTOR)
        assert point.payload["tsu_access"] == "citation_only"

    def test_publication_year_and_source_type_mapped(self):
        point = qdrant_store.build_point(_migrated_record(publication_year=1890, source_type="public_archive"), _VECTOR)
        assert point.payload["publication_year"] == 1890
        assert point.payload["source_type"] == "public_archive"

    def test_volume_id_null_for_monograph_preserved(self):
        point = qdrant_store.build_point(_migrated_record(volume_id=None), _VECTOR)
        assert point.payload["volume_id"] is None


class TestSchemaVersionAndProvenance:
    def test_metadata_schema_version_mapped(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["metadata_schema_version"] == "1.1.0"

    def test_metadata_provenance_preserved_as_object(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["metadata_provenance"]["crosswalk_id"] == "f914f6c442983e59"

    def test_metadata_provenance_missing_defaults_to_none(self):
        record = _migrated_record()
        del record["metadata_provenance"]
        point = qdrant_store.build_point(record, _VECTOR)
        assert point.payload["metadata_provenance"] is None


class TestReviewStatus:
    def test_review_status_verified_mapped(self):
        point = qdrant_store.build_point(_migrated_record(review_status="verified"), _VECTOR)
        assert point.payload["review_status"] == "verified"

    def test_review_status_defaults_when_missing(self):
        record = _migrated_record()
        del record["review_status"]
        point = qdrant_store.build_point(record, _VECTOR)
        assert point.payload["review_status"] == "unverified"


class TestCategoryCitationPolicyMissingSource:
    def test_category_null_preserved(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["category"] is None

    def test_category_status_authoritative_source_missing_preserved(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["category_status"] == "AUTHORITATIVE_SOURCE_MISSING"

    def test_citation_policy_null_preserved(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["citation_policy"] is None

    def test_citation_policy_status_authoritative_source_missing_preserved(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["citation_policy_status"] == "AUTHORITATIVE_SOURCE_MISSING"

    def test_no_guessed_category_value_ever_appears(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["category"] != ""
        assert point.payload["citation_policy"] != ""


class TestMissingMetadata:
    def test_pre_migration_record_missing_metadata_fields_defaults_to_none(self):
        """Migration을 거치지 않은(§Metadata Schema 1.1.0 필드가 아예 없는)
        레코드도 KeyError 없이 처리되어야 한다 — 신규 필드는 전부 None."""
        pre_migration_record = {
            "id": "TSU-0000001", "book": "B", "claim": "c", "doctrine": "d",
            "scriptures": [], "citations": [], "review_status": "verified",
            "tsu_schema_version": "1",
        }
        point = qdrant_store.build_point(pre_migration_record, _VECTOR)
        assert point.payload["source_id"] is None
        assert point.payload["metadata_schema_version"] is None
        assert point.payload["metadata_provenance"] is None

    def test_missing_author_id_only(self):
        record = _migrated_record()
        del record["author_id"]
        point = qdrant_store.build_point(record, _VECTOR)
        assert point.payload["author_id"] is None
        assert point.payload["work_id"] == "WORK-DAGG-CHURCH-ORDER-001"  # 다른 필드는 영향 없음


class TestMalformedMetadata:
    def test_malformed_metadata_provenance_type_passed_through_as_is(self):
        """build_point()는 검증기가 아니라 pass-through — 잘못된 타입이 와도
        예외를 던지지 않고 그대로 옮긴다(검증은 Migration Script의 책임)."""
        record = _migrated_record(metadata_provenance="not-a-dict")
        point = qdrant_store.build_point(record, _VECTOR)
        assert point.payload["metadata_provenance"] == "not-a-dict"

    def test_empty_record_dict_raises_key_error_on_required_id(self):
        import pytest
        with pytest.raises(KeyError):
            qdrant_store.build_point({}, _VECTOR)


class TestTsuIdPreservation:
    def test_tsu_id_format_unchanged_by_migration_fields(self):
        point = qdrant_store.build_point(_migrated_record(id="TSU-0001234"), _VECTOR)
        assert point.payload["tsu_id"] == "TSU-0001234"
        assert point.id == 1234

    def test_point_id_derivation_unaffected_by_new_fields(self):
        point = qdrant_store.build_point(_migrated_record(id="TSU-0000042"), _VECTOR)
        assert point.id == 42


class TestDatasetIsolation:
    def test_identifier_and_source_identifier_distinct_from_registry_source_id(self):
        """TSU identifier(Corpus 식별자, 'Dagg_Church_Order')와 Metadata Layer의
        source_id(Registry 식별자, 'BAP-CHURCH-DAGG-001')는 값이 다른 별개
        네임스페이스 — payload에서도 두 값이 혼동 없이 각자 필드에 담긴다."""
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert point.payload["identifier"] == "Dagg_Church_Order"
        assert point.payload["source_id"] == "BAP-CHURCH-DAGG-001"
        assert point.payload["identifier"] != point.payload["source_id"]


class TestReviewGateBypassPrevention:
    def test_build_point_never_calls_review_gate(self):
        """build_point()는 review_gate 모듈을 import하지 않는다 — payload
        구성 단계는 Review Gate 판정을 다시 수행하거나 우회하지 않고,
        이미 필터링된 레코드만 받는다는 계약(indexer.py가 보증)을 그대로
        신뢰한다."""
        import inspect
        source = inspect.getsource(qdrant_store)
        assert "review_gate" not in source
        assert "filter_embedding_eligible" not in source

    def test_build_point_does_not_filter_by_review_status_itself(self):
        """build_point() 자체는 review_status 값과 무관하게 payload를 만든다
        (필터링은 indexer.py::load_records_with_gate_summary()의 책임) —
        이 레이어에서 이중 필터링을 하지 않는다는 설계를 그대로 확인."""
        point = qdrant_store.build_point(_migrated_record(review_status="generated"), _VECTOR)
        assert point.payload["review_status"] == "generated"  # 필터링 안 함(호출자 책임)


class TestSourceTsuImmutability:
    def test_build_point_does_not_mutate_input_record(self):
        record = _migrated_record()
        original = dict(record)
        qdrant_store.build_point(record, _VECTOR)
        assert record == original

    def test_build_point_returns_new_payload_dict_each_call(self):
        record = _migrated_record()
        point1 = qdrant_store.build_point(record, _VECTOR)
        point2 = qdrant_store.build_point(record, _VECTOR)
        assert point1.payload is not point2.payload


class TestIdempotencyAndDuplicateHandling:
    def test_calling_build_point_twice_produces_identical_payload(self):
        record = _migrated_record()
        point1 = qdrant_store.build_point(record, _VECTOR)
        point2 = qdrant_store.build_point(record, _VECTOR)
        assert point1.payload == point2.payload
        assert point1.id == point2.id

    def test_duplicate_of_field_still_preserved_alongside_new_fields(self):
        point = qdrant_store.build_point(_migrated_record(duplicate_of="TSU-0000001"), _VECTOR)
        assert point.payload["duplicate_of"] == "TSU-0000001"
        assert point.payload["metadata_schema_version"] == "1.1.0"


class TestSerialization:
    def test_payload_is_json_serializable(self):
        import json
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        json.dumps(point.payload)  # should not raise

    def test_payload_round_trips_through_json(self):
        import json
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        restored = json.loads(json.dumps(point.payload))
        assert restored["source_id"] == "BAP-CHURCH-DAGG-001"
        assert restored["metadata_provenance"]["crosswalk_id"] == "f914f6c442983e59"


class TestSchemaValidation:
    def test_all_16_metadata_fields_present_in_payload(self):
        expected_new_fields = {
            "source_id", "author_id", "work_id", "edition_id", "volume_id",
            "publication_year", "source_type", "copyright_status", "usage_permission",
            "access_control", "tsu_access", "metadata_schema_version",
            "category", "category_status", "citation_policy", "citation_policy_status",
        }
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert expected_new_fields <= set(point.payload.keys())

    def test_metadata_provenance_field_present(self):
        point = qdrant_store.build_point(_migrated_record(), _VECTOR)
        assert "metadata_provenance" in point.payload


class TestBackwardCompatibility:
    def test_hiscox_style_record_also_works(self):
        record = _migrated_record(
            id="TSU-0003400", identifier="Hiscox_Standard_Manual", source_identifier="Hiscox_Standard_Manual",
            source_id="BAP-CHURCH-HISCOX", author_id="hiscox_edward_t",
            work_id="WORK-HISCOX-STANDARD-MANUAL-001", edition_id="WORK-HISCOX-STANDARD-MANUAL-001-1890",
            publication_year=1890,
            metadata_provenance={"crosswalk_id": "260d31b2331a3f8b", "resolved_at": "2026-08-08T00:00:00+00:00", "resolver_version": "1.0.0"},
        )
        point = qdrant_store.build_point(record, _VECTOR)
        assert point.payload["source_id"] == "BAP-CHURCH-HISCOX"
        assert point.id == 3400

    def test_signature_unchanged_two_positional_args(self):
        import inspect
        sig = inspect.signature(qdrant_store.build_point)
        assert list(sig.parameters) == ["record", "vector"]


class TestRegression:
    def test_upsert_points_and_ensure_collection_unchanged(self):
        import inspect
        assert "upsert" in inspect.getsource(qdrant_store.upsert_points)
        assert "create_collection" in inspect.getsource(qdrant_store.ensure_collection)

    def test_tsu_id_to_point_id_unchanged(self):
        assert qdrant_store.tsu_id_to_point_id("TSU-0000007") == 7

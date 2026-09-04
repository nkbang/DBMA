import pytest

from NAE.pipeline.index import qdrant_store


def test_tsu_id_to_point_id_parses_correctly():
    assert qdrant_store.tsu_id_to_point_id("TSU-0000001") == 1
    assert qdrant_store.tsu_id_to_point_id("TSU-0001234") == 1234


def test_tsu_id_to_point_id_rejects_bad_format():
    with pytest.raises(ValueError):
        qdrant_store.tsu_id_to_point_id("not-a-tsu-id")


def test_build_point_includes_expected_payload_fields():
    record = {
        "id": "TSU-0000005",
        "book": "Body of Divinity",
        "author": "John Gill",
        "identifier": "gill_item",
        "doctrine": "Baptism",
        "page": 12,
        "paragraph": 3,
        "sentence": 1,
        "claim": "Believer's baptism follows profession of faith.",
        "source_text": "Original sentence.",
        "scriptures": ["Acts 2:41"],
        "citations": ["John Gill"],
        "review_status": "unverified",
        "overall_score": 0.75,
        "duplicate_of": None,
        "tsu_schema_version": "1",
        "collector_version": "1.1.0",
        "canonical_version": "2.0.0",
    }
    point = qdrant_store.build_point(record, [0.1] * 1024)
    assert point.id == 5
    assert point.payload["tsu_id"] == "TSU-0000005"
    assert point.payload["book"] == "Body of Divinity"
    assert point.payload["doctrine"] == "Baptism"
    assert point.payload["overall_score"] == 0.75
    assert point.payload["source_identifier"] == "gill_item"
    assert point.payload["tsu_schema_version"] == "1"
    assert point.payload["collector_version"] == "1.1.0"
    assert point.payload["canonical_version"] == "2.0.0"
    assert len(point.vector) == 1024

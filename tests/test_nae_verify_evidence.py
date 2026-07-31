from NAE.pipeline.verify import evidence


def test_check_reference_valid_form():
    result = evidence.check_reference("John 3:16")
    assert result["format_valid"] is True
    assert result["textual_verification"] == "not_available"


def test_check_reference_invalid_form():
    result = evidence.check_reference("not a reference")
    assert result["format_valid"] is False


def test_check_reference_implausible_chapter_verse():
    result = evidence.check_reference("John 999:9999")
    assert result["format_valid"] is False


def test_check_record_evidence_multiple_refs():
    record = {"scriptures": ["John 3:16", "garbage"]}
    results = evidence.check_record_evidence(record)
    assert len(results) == 2
    assert results[0]["format_valid"] is True
    assert results[1]["format_valid"] is False


def test_check_record_evidence_empty():
    assert evidence.check_record_evidence({"scriptures": []}) == []

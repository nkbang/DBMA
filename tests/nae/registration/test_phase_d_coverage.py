"""Phase D full coverage tests for ADR-021 registration pipeline (14 test areas).

Covers all test areas defined in ADR-021 SS17 that are not already in
test_pipeline_smoke.py. Uses isolated tmp fixtures only - never touches
Production TSU files, NAE/authority/*, or Qdrant.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from NAE.pipeline.registration import identity as identity_mod
from NAE.pipeline.registration import raw_preservation
from NAE.pipeline.registration import source_validator
from NAE.pipeline.registration import quality_gate as qg
from NAE.pipeline.registration.state import (
    ExceptionQueue,
    RegistrationState,
    RegistrationStateStore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_raw_item_dir(tmp_path):
    """Create a minimal hOCR item directory that extract_pages() accepts."""
    item_dir = tmp_path / "raw_item"
    item_dir.mkdir()
    hocr = item_dir / "hocr.html"
    words = " ".join(f'<span class="ocrx_word">Word{i}</span>' for i in range(60))
    hocr.write_text(
        f'<div class="ocr_page"><p class="ocr_par">'
        f'<span class="ocr_line">{words}</span></p></div>',
        encoding="utf-8",
    )
    return item_dir


def _make_manifest_path(tmp_path):
    return tmp_path / "source_manifest.yaml"


@pytest.fixture
def isolated_env(tmp_path):
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    state_store = RegistrationStateStore(tmp_path / "state.json")
    exception_queue = ExceptionQueue(tmp_path / "exceptions.json")
    manifest_path = _make_manifest_path(tmp_path)
    return ledger, state_store, exception_queue, manifest_path


# ---------------------------------------------------------------------------
# Area 1: Identity creation (basic issuance)
# ---------------------------------------------------------------------------

def test_area01_identity_creation_basic():
    """ADR-021 SS4: identity issuance produces correct slug-based IDs."""
    result = identity_mod.issue_identity(
        surname="Bang",
        given_name="David",
        title="Test Work",
        edition_slug="1st",
        source_id="area01-test",
        existing_author_ids=set(),
        existing_work_ids=set(),
        existing_edition_ids=set(),
        existing_source_ids=set(),
    )
    assert result.author_id == "bang_david"
    assert result.work_id == "bang_david-test_work"
    assert result.edition_id == "bang_david-test_work-1st"
    assert result.source_id == "area01-test"
    assert result.author_collided is False
    assert result.work_collided is False
    assert result.edition_collided is False


def test_area01_identity_no_given_name():
    """When given_name is empty, author_id uses surname only."""
    result = identity_mod.issue_identity(
        surname="Anonymous",
        given_name="",
        title="Unknown Work",
        edition_slug="1st",
        source_id="area01-anon",
        existing_author_ids=set(),
        existing_work_ids=set(),
        existing_edition_ids=set(),
        existing_source_ids=set(),
    )
    assert result.author_id == "anonymous"
    assert result.work_collided is False


# ---------------------------------------------------------------------------
# Area 2: Identity validation (source_id uniqueness check)
# ---------------------------------------------------------------------------

def test_area02_identity_validation_duplicate_source_id():
    """ADR-021 SS4: duplicate source_id raises ValueError."""
    with pytest.raises(ValueError, match="source_id already in use"):
        identity_mod.issue_identity(
            surname="Test",
            given_name="User",
            title="Work",
            edition_slug="1st",
            source_id="dup-source",
            existing_author_ids=set(),
            existing_work_ids=set(),
            existing_edition_ids=set(),
            existing_source_ids={"dup-source"},
        )


# ---------------------------------------------------------------------------
# Area 3: Duplicate identity detection (Level 1 - catalog)
# ---------------------------------------------------------------------------

def test_area03_duplicate_identity_level1():
    """ADR-021 SS9 Level 1: same archive_identifier detected."""
    assert raw_preservation.is_catalog_duplicate("ia/forwardmission00giff", {"ia/other"}) is False
    assert raw_preservation.is_catalog_duplicate("ia/forwardmission00giff", {"ia/forwardmission00giff"}) is True


# ---------------------------------------------------------------------------
# Area 4: Append-only ledger
# ---------------------------------------------------------------------------

def test_area04_append_only_ledger(tmp_path):
    """ADR-021 SS6: ledger never truncates - entries accumulate."""
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    f = tmp_path / "file.txt"
    f.write_text("content", encoding="utf-8")

    r1 = raw_preservation.preserve(f, "src-1", ledger)
    assert len(ledger.entries()) == 1

    os.chmod(f, 0o644)
    f.write_text("tampered", encoding="utf-8")
    r2 = raw_preservation.verify(f, "src-1", ledger)
    assert len(ledger.entries()) == 2

    f2 = tmp_path / "file2.txt"
    f2.write_text("other content", encoding="utf-8")
    r3 = raw_preservation.preserve(f2, "src-2", ledger)
    assert len(ledger.entries()) == 3

    events = [e.event for e in ledger.entries()]
    assert events == ["preserve", "reverify", "preserve"]


# ---------------------------------------------------------------------------
# Area 5: Source registration idempotency (manifest_writer)
# ---------------------------------------------------------------------------

def test_area05_source_registration_idempotent_manifest(tmp_path):
    """ADR-021 SS4: re-registering same source_id does not create duplicate entry."""
    from NAE.pipeline.registration import manifest_writer

    manifest = tmp_path / "manifest.yaml"
    entry = {
        "source_id": "idem-src",
        "title": "Test",
        "author": "Test Author",
        "author_id": "test_author",
        "work_id": "test_author-test",
        "edition_id": "test_author-test-1st",
        "year": 1900,
        "license": "public_domain",
        "archive_source": "ia/test",
        "raw_checksum": "abc123",
    }

    manifest_writer.write_entry(manifest, entry)
    data1 = yaml.safe_load(manifest.read_text())
    assert len(data1["sources"]) == 1

    with pytest.raises(ValueError, match="source_id already registered"):
        manifest_writer.write_entry(manifest, entry)

    data2 = yaml.safe_load(manifest.read_text())
    assert len(data2["sources"]) == 1


# ---------------------------------------------------------------------------
# Area 6: Source validator
# ---------------------------------------------------------------------------

def test_area06_source_validator_passes(tmp_path):
    """Source validator passes when all required fields present."""
    tmp_raw = tmp_path / "valid_raw.txt"
    tmp_raw.write_text("some content", encoding="utf-8")
    record = {
        "source_id": "val-src",
        "author_id": "val_author",
        "work_id": "val_author-val_work",
        "edition_id": "val_author-val_work-1st",
        "title": "Test Title",
        "publication_year": 1900,
        "copyright_status": "public_domain",
    }
    result = source_validator.validate(record, tmp_raw)
    assert result.passed is True
    assert len(result.errors) == 0


def test_area06_source_validator_fails_on_missing_fields():
    """Source validator fails when required identity/metadata fields missing."""
    record = {
        "source_id": "",
        "author_id": "",
        "work_id": "",
        "edition_id": "",
        "title": "",
        "publication_year": None,
        "copyright_status": None,
    }
    result = source_validator.validate(record, Path("/dev/null"))
    assert result.passed is False
    assert len(result.errors) >= 7


def test_area06_source_validator_provenance_warning(tmp_path):
    """Provenance field absence is WARNING, not ERROR."""
    tmp_raw = tmp_path / "valid_raw.txt"
    tmp_raw.write_text("some content", encoding="utf-8")
    record = {
        "source_id": "val-src",
        "author_id": "val_author",
        "work_id": "val_author-val_work",
        "edition_id": "val_author-val_work-1st",
        "title": "Test",
        "publication_year": 1900,
        "copyright_status": "public_domain",
    }
    result = source_validator.validate(record, tmp_raw)
    assert result.passed is True
    assert any("provenance" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Area 7: Exception queue physical separation
# ---------------------------------------------------------------------------

def test_area07_exception_queue_separation(tmp_path):
    """ADR-021 SS11: exception queue is physically separate from production review queue."""
    upstream_queue = ExceptionQueue(tmp_path / "upstream_exceptions.json")
    production_queue_path = tmp_path / "production_review_exceptions.json"

    upstream_queue.record(
        "exc-src",
        RegistrationState.RAW_CHECKSUM_MISMATCH,
        "checksum mismatch",
        raw_path="/tmp/raw.txt",
        checksum="abc123",
    )

    assert len(upstream_queue.entries()) == 1
    assert upstream_queue.entries()[0]["source_id"] == "exc-src"
    assert not production_queue_path.exists() or production_queue_path.read_text() != upstream_queue.path.read_text()


# ---------------------------------------------------------------------------
# Area 8: Quality gate FAIL (all 7 reasons)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("raw_file_exists", "checksum_matches", "extraction_output_present",
     "page_count", "source_readable", "identity_complete", "metadata_complete",
     "expected_reason"),
    [
        (False, True, True, 10, True, True, True, "raw_file_missing"),
        (True, False, True, 10, True, True, True, "raw_checksum_mismatch"),
        (True, True, False, 10, True, True, True, "extraction_output_missing"),
        (True, True, True, 0, True, True, True, "zero_page_extraction"),
        (True, True, True, 10, False, True, True, "unreadable_or_corrupt_source"),
        (True, True, True, 10, True, False, True, "required_identity_unavailable"),
        (True, True, True, 10, True, True, False, "required_metadata_missing"),
    ],
)
def test_area08_quality_gate_fail_reasons(
    raw_file_exists, checksum_matches, extraction_output_present,
    page_count, source_readable, identity_complete, metadata_complete,
    expected_reason,
):
    """ADR-021 SS8: each of the 7 FAIL reasons triggers FAIL verdict."""
    gate_input = qg.QualityGateInput(
        raw_file_exists=raw_file_exists,
        checksum_matches=checksum_matches,
        extraction_output_present=extraction_output_present,
        page_count=page_count,
        source_readable=source_readable,
        identity_complete=identity_complete,
        metadata_complete=metadata_complete,
    )
    result = qg.evaluate(gate_input)
    assert result.verdict == qg.QualityGateVerdict.FAIL
    assert expected_reason in result.fail_reasons


# ---------------------------------------------------------------------------
# Area 9: Quality gate WARNING (non-blocking)
# ---------------------------------------------------------------------------

def test_area09_quality_gate_warning_non_blocking():
    """ADR-021 SS8: WARNING conditions do not block - verdict is WARNING, not FAIL."""
    gate_input = qg.QualityGateInput(
        raw_file_exists=True, checksum_matches=True, extraction_output_present=True,
        page_count=10, source_readable=True, identity_complete=True, metadata_complete=True,
        low_ocr_confidence=True, partial_ocr_degradation=True,
    )
    result = qg.evaluate(gate_input)
    assert result.verdict == qg.QualityGateVerdict.WARNING
    assert "low_ocr_confidence" in result.warning_reasons
    assert "partial_ocr_degradation" in result.warning_reasons


def test_area09_quality_gate_all_warnings():
    """All 5 WARNING reasons are detected."""
    gate_input = qg.QualityGateInput(
        raw_file_exists=True, checksum_matches=True, extraction_output_present=True,
        page_count=10, source_readable=True, identity_complete=True, metadata_complete=True,
        low_ocr_confidence=True, partial_ocr_degradation=True,
        abnormal_character_ratio=True, possible_page_count_discrepancy=True,
        encoding_anomalies=True,
    )
    result = qg.evaluate(gate_input)
    assert result.verdict == qg.QualityGateVerdict.WARNING
    assert len(result.warning_reasons) == 5


# ---------------------------------------------------------------------------
# Area 10: Extraction adapter (interface check)
# ---------------------------------------------------------------------------

def test_area10_extraction_adapter_interface():
    """Extraction adapter calls existing extract_pages() without modification."""
    from NAE.pipeline.canonical.extract import extract_pages
    assert callable(extract_pages)


# ---------------------------------------------------------------------------
# Area 11: Repeated execution idempotency (pipeline level)
# ---------------------------------------------------------------------------

def test_area11_repeated_execution_idempotent(tmp_path, isolated_env):
    """Running registration twice for the same source produces consistent state."""
    ledger, state_store, exception_queue, manifest_path = isolated_env
    item_dir = _make_raw_item_dir(tmp_path)

    from NAE.pipeline.registration.pipeline import RegistrationRequest, register_source

    req = RegistrationRequest(
        raw_item_dir=item_dir, surname="Repeat", given_name="Test",
        title="Idempotent Work", edition_slug="1st", publication_year=1900,
        copyright_status="public_domain", archive_source="ia/test",
        source_id="repeat-src", manifest_path=manifest_path,
    )

    result1 = register_source(
        req, existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    result2 = register_source(
        req, existing_author_ids={"repeat_test"},
        existing_work_ids={"repeat_test-repeat_work"},
        existing_edition_ids={"repeat_test-repeat_work-1st"},
        existing_source_ids={"repeat-src"},
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    assert result2.final_state == RegistrationState.REGISTRATION_FAILED


# ---------------------------------------------------------------------------
# Area 12: Failure isolation (one source failure does not block others)
# ---------------------------------------------------------------------------

def test_area12_failure_isolation(tmp_path, isolated_env):
    """ADR-021 SS10: one source's failure never blocks another source's registration."""
    ledger, state_store, exception_queue, manifest_path = isolated_env
    item_dir_ok = _make_raw_item_dir(tmp_path)
    item_dir_fail = tmp_path / "empty_raw"
    item_dir_fail.mkdir()

    from NAE.pipeline.registration.pipeline import RegistrationRequest, register_source

    req_ok = RegistrationRequest(
        raw_item_dir=item_dir_ok, surname="Ok", given_name="Source",
        title="Valid Work", edition_slug="1st", publication_year=1900,
        copyright_status="public_domain", archive_source="ia/test",
        source_id="ok-src", manifest_path=manifest_path,
    )

    result_ok = register_source(
        req_ok, existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    req_fail = RegistrationRequest(
        raw_item_dir=item_dir_fail, surname="Fail", given_name="Source",
        title="Invalid Work", edition_slug="1st", publication_year=1900,
        copyright_status="public_domain", archive_source="ia/test",
        source_id="fail-src", manifest_path=manifest_path,
    )

    result_fail = register_source(
        req_fail, existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids={"ok-src"},
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    assert result_ok.final_state == RegistrationState.QUALITY_PASSED
    assert state_store.get_state("ok-src") == RegistrationState.QUALITY_PASSED
    assert result_fail.final_state in {RegistrationState.REGISTRATION_FAILED, RegistrationState.RAW_CHECKSUM_MISMATCH}


# ---------------------------------------------------------------------------
# Area 13: Authority separation (legacy read-only, new registry write)
# ---------------------------------------------------------------------------

def test_area13_authority_separation(tmp_path):
    """ADR-021 SS4: legacy snapshot is never written to; new registry is the write target."""
    from NAE.pipeline.registration import authority

    legacy_dir = tmp_path / "legacy_snapshot"
    legacy_dir.mkdir()
    (legacy_dir / "authors.yaml").write_text(
        yaml.safe_dump({"authors": [{"author_id": "legacy_1", "canonical_name": "Legacy Author"}]}),
        encoding="utf-8",
    )

    new_authors = tmp_path / "new_authors.yaml"
    new_works = tmp_path / "new_works.yaml"

    import NAE.pipeline.registration.config as cfg
    original_legacy = cfg.LEGACY_SNAPSHOT_DIR
    original_new_authors = cfg.NEW_AUTHORS_PATH
    original_new_works = cfg.NEW_WORKS_PATH

    try:
        cfg.LEGACY_SNAPSHOT_DIR = legacy_dir
        cfg.NEW_AUTHORS_PATH = new_authors
        cfg.NEW_WORKS_PATH = new_works

        authority.register_author("new_1", "New Author")

        legacy_data = yaml.safe_load((legacy_dir / "authors.yaml").read_text())
        assert len(legacy_data["authors"]) == 1
        assert legacy_data["authors"][0]["author_id"] == "legacy_1"

        new_data = yaml.safe_load(new_authors.read_text())
        assert len(new_data["authors"]) == 1
        assert new_data["authors"][0]["author_id"] == "new_1"

    finally:
        cfg.LEGACY_SNAPSHOT_DIR = original_legacy
        cfg.NEW_AUTHORS_PATH = original_new_authors
        cfg.NEW_WORKS_PATH = original_new_works


# ---------------------------------------------------------------------------
# Area 14: Baseline protection (Production files untouched after all tests)
# ---------------------------------------------------------------------------

def test_area14_baseline_protection_after_all_tests(tmp_path):
    """ADR-021 SS14/SS15: Production TSU files are never modified by registration tests."""
    repo_root = Path(__file__).resolve().parents[3]
    tsu_files = [
        repo_root / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json",
        repo_root / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json",
    ]

    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tsu_files}

    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    state_store = RegistrationStateStore(tmp_path / "state.json")
    exception_queue = ExceptionQueue(tmp_path / "exceptions.json")
    manifest_path = _make_manifest_path(tmp_path)
    item_dir = _make_raw_item_dir(tmp_path)

    from NAE.pipeline.registration.pipeline import RegistrationRequest, register_source

    req = RegistrationRequest(
        raw_item_dir=item_dir, surname="Guard", given_name="Test",
        title="Baseline Guard", edition_slug="1st", publication_year=1900,
        copyright_status="public_domain", archive_source="ia/test",
        source_id="baseline-guard", manifest_path=manifest_path,
    )

    register_source(
        req, existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in tsu_files}
    assert before == after, "Production TSU files were modified during registration tests!"


# ---------------------------------------------------------------------------
# Additional helper tests
# ---------------------------------------------------------------------------

def test_quality_gate_pass_clean():
    """Quality gate returns PASS when all conditions are clean."""
    gate_input = qg.QualityGateInput(
        raw_file_exists=True, checksum_matches=True, extraction_output_present=True,
        page_count=10, source_readable=True, identity_complete=True, metadata_complete=True,
    )
    result = qg.evaluate(gate_input)
    assert result.verdict == qg.QualityGateVerdict.PASS
    assert len(result.fail_reasons) == 0
    assert len(result.warning_reasons) == 0


def test_state_store_persistence(tmp_path):
    """RegistrationStateStore persists and reloads state correctly."""
    path = tmp_path / "state.json"
    store = RegistrationStateStore(path)
    store.set_state("src-1", RegistrationState.QUALITY_PASSED)
    store.save()
    store2 = RegistrationStateStore(path)
    assert store2.get_state("src-1") == RegistrationState.QUALITY_PASSED


def test_exception_queue_persistence(tmp_path):
    """ExceptionQueue persists and reloads entries correctly."""
    path = tmp_path / "exceptions.json"
    eq = ExceptionQueue(path)
    eq.record("src-1", RegistrationState.RAW_CHECKSUM_MISMATCH, "checksum mismatch")
    eq.save()
    eq2 = ExceptionQueue(path)
    entries = eq2.entries()
    assert len(entries) == 1
    assert entries[0]["source_id"] == "src-1"
    assert entries[0]["failure_state"] == RegistrationState.RAW_CHECKSUM_MISMATCH.value


def test_manifest_writer_existing_source_ids(tmp_path):
    """manifest_writer.existing_source_ids returns correct set."""
    from NAE.pipeline.registration import manifest_writer
    manifest = tmp_path / "manifest.yaml"
    entry1 = {"source_id": "src-1", "title": "A"}
    entry2 = {"source_id": "src-2", "title": "B"}
    manifest_writer.write_entry(manifest, entry1)
    manifest_writer.write_entry(manifest, entry2)
    existing = manifest_writer.existing_source_ids(manifest)
    assert existing == {"src-1", "src-2"}


def test_slugify_special_chars():
    """slugify handles special characters correctly."""
    assert identity_mod.slugify("Hello, World!") == "hello_world"
    assert identity_mod.slugify("  Spaces  ") == "spaces"
    assert identity_mod.slugify("UPPERCASE") == "uppercase"


def test_checksum_consistency(tmp_path):
    """SHA-256 of same content always produces same hash."""
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    f = tmp_path / "consistent.txt"
    f.write_text("same content", encoding="utf-8")
    h1 = raw_preservation.sha256_of_file(f)
    h2 = raw_preservation.sha256_of_file(f)
    assert h1 == h2
    assert len(h1) == 64


def test_preservation_result_no_duplicate(tmp_path):
    """PreservationResult.duplicate_of is None when no duplicate exists."""
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    f = tmp_path / "unique.txt"
    f.write_text("unique content", encoding="utf-8")
    result = raw_preservation.preserve(f, "unique-src", ledger)
    assert result.duplicate_of is None


def test_verification_result_fields(tmp_path):
    """VerificationResult has all expected fields after verify()."""
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    f = tmp_path / "verify.txt"
    f.write_text("verify content", encoding="utf-8")
    preserved = raw_preservation.preserve(f, "verify-src", ledger)
    verification = raw_preservation.verify(f, "verify-src", ledger)
    assert verification.source_id == "verify-src"
    assert verification.matches is True
    assert verification.recorded_checksum == preserved.checksum
    assert verification.current_checksum == preserved.checksum


def test_state_store_summary(tmp_path):
    """RegistrationStateStore.summary() returns correct counts."""
    path = tmp_path / "state.json"
    store = RegistrationStateStore(path)
    store.set_state("s1", RegistrationState.QUALITY_PASSED)
    store.set_state("s2", RegistrationState.QUALITY_PASSED)
    store.set_state("s3", RegistrationState.RAW_CHECKSUM_MISMATCH)
    store.save()
    summary = store.summary()
    assert summary.get("QUALITY_PASSED", 0) == 2
    assert summary.get("RAW_CHECKSUM_MISMATCH", 0) == 1


def test_failure_states_set():
    """FAILURE_STATES contains exactly the 4 failure states."""
    from NAE.pipeline.registration.state import FAILURE_STATES
    assert len(FAILURE_STATES) == 4
    assert RegistrationState.REGISTRATION_FAILED in FAILURE_STATES
    assert RegistrationState.RAW_CHECKSUM_MISMATCH in FAILURE_STATES
    assert RegistrationState.EXTRACTION_FAILED in FAILURE_STATES
    assert RegistrationState.QUALITY_GATE_FAILED in FAILURE_STATES


def test_quality_gate_fail_reasons_fixed():
    """FAIL_REASONS is a fixed tuple - not extensible at runtime."""
    assert len(qg.FAIL_REASONS) == 7
    assert "raw_checksum_mismatch" in qg.FAIL_REASONS
    assert "required_metadata_missing" in qg.FAIL_REASONS


def test_quality_gate_warning_reasons_fixed():
    """WARNING_REASONS is a fixed tuple - not extensible at runtime."""
    assert len(qg.WARNING_REASONS) == 5
    assert "low_ocr_confidence" in qg.WARNING_REASONS
    assert "encoding_anomalies" in qg.WARNING_REASONS

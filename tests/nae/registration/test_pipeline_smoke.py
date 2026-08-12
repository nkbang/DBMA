"""Phase B smoke test — proves the registration pipeline wiring works
end-to-end against isolated tmp fixtures. Never touches Production TSU
files, NAE/authority/*, or Qdrant. Full Phase D coverage (14 test areas
per ADR-021 SS17) is tracked separately."""
from __future__ import annotations

import json

import pytest

from NAE.pipeline.registration import raw_preservation
from NAE.pipeline.registration.pipeline import RegistrationRequest, register_source
from NAE.pipeline.registration.state import ExceptionQueue, RegistrationState, RegistrationStateStore


def _make_raw_item_dir(tmp_path):
    item_dir = tmp_path / "raw_item"
    item_dir.mkdir()
    hocr = item_dir / "hocr.html"  # extract_from_hocr() expects this exact filename
    words = " ".join(f'<span class="ocrx_word">Word{i}</span>' for i in range(60))  # pad past MIN_OCR_BYTES=200
    hocr.write_text(
        f'<div class="ocr_page"><p class="ocr_par">'
        f'<span class="ocr_line">{words}</span></p></div>',
        encoding="utf-8",
    )
    return item_dir


@pytest.fixture
def isolated_env(tmp_path):
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    state_store = RegistrationStateStore(tmp_path / "state.json")
    exception_queue = ExceptionQueue(tmp_path / "exceptions.json")
    manifest_path = tmp_path / "source_manifest.yaml"
    return ledger, state_store, exception_queue, manifest_path


def test_happy_path_reaches_quality_passed(tmp_path, isolated_env):
    ledger, state_store, exception_queue, manifest_path = isolated_env
    item_dir = _make_raw_item_dir(tmp_path)

    req = RegistrationRequest(
        raw_item_dir=item_dir,
        surname="Smoke",
        given_name="Test",
        title="A Smoke Test Document",
        edition_slug="1900",
        publication_year=1900,
        copyright_status="public_domain",
        archive_source="archive.org/smoketest",
        source_id="smoke-test-001",
        manifest_path=manifest_path,
    )

    result = register_source(
        req,
        existing_author_ids=set(),
        existing_work_ids=set(),
        existing_edition_ids=set(),
        existing_source_ids=set(),
        ledger=ledger,
        state_store=state_store,
        exception_queue=exception_queue,
    )

    assert result.final_state == RegistrationState.QUALITY_PASSED
    assert result.identity.author_id == "smoke_test"
    assert result.page_count > 0
    assert manifest_path.exists()
    assert exception_queue.entries() == []


def test_identity_collision_gets_suffix(tmp_path, isolated_env):
    ledger, state_store, exception_queue, manifest_path = isolated_env
    item_dir = _make_raw_item_dir(tmp_path)

    req = RegistrationRequest(
        raw_item_dir=item_dir, surname="Smoke", given_name="Test", title="Doc",
        edition_slug="1900", publication_year=1900, copyright_status="public_domain",
        archive_source="x", source_id="smoke-test-002", manifest_path=manifest_path,
    )
    result = register_source(
        req,
        existing_author_ids={"smoke_test"}, existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )
    assert result.identity.author_id == "smoke_test-2"
    assert result.identity.author_collided is True


def test_missing_raw_file_routes_to_exception_queue(tmp_path, isolated_env):
    ledger, state_store, exception_queue, manifest_path = isolated_env
    empty_dir = tmp_path / "empty_raw"
    empty_dir.mkdir()

    req = RegistrationRequest(
        raw_item_dir=empty_dir, surname="No", given_name="Raw", title="Doc",
        edition_slug="1900", publication_year=1900, copyright_status="public_domain",
        archive_source="x", source_id="smoke-test-003", manifest_path=manifest_path,
    )
    result = register_source(
        req,
        existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )
    assert result.final_state == RegistrationState.RAW_CHECKSUM_MISMATCH
    assert len(exception_queue.entries()) == 1


def test_checksum_reverify_detects_tamper(tmp_path, isolated_env):
    ledger, *_ = isolated_env
    f = tmp_path / "raw.txt"
    f.write_text("original content", encoding="utf-8")
    import os
    preserved = raw_preservation.preserve(f, "tamper-test", ledger)
    os.chmod(f, 0o644)
    f.write_text("tampered content", encoding="utf-8")
    verification = raw_preservation.verify(f, "tamper-test", ledger)
    assert verification.matches is False
    assert verification.recorded_checksum == preserved.checksum


def test_duplicate_detection_level2_same_content_different_id(tmp_path, isolated_env):
    ledger, *_ = isolated_env
    f1 = tmp_path / "a.txt"
    f1.write_text("identical content", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("identical content", encoding="utf-8")

    raw_preservation.preserve(f1, "source-a", ledger)
    result_b = raw_preservation.preserve(f2, "source-b", ledger)
    assert result_b.duplicate_of == "source-a"


def test_production_untouched(monkeypatch, tmp_path):
    """Guards against accidental import-time or call-time writes to the
    real NAE/authority/ or NAE/corpus/tsu/ trees."""
    import hashlib
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    tsu_files = [
        repo_root / "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json",
        repo_root / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json",
    ]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tsu_files}

    # Run the happy-path test body once more via isolated fixtures only.
    ledger = raw_preservation.ChecksumLedger(tmp_path / "ledger.jsonl")
    state_store = RegistrationStateStore(tmp_path / "state.json")
    exception_queue = ExceptionQueue(tmp_path / "exceptions.json")
    item_dir = _make_raw_item_dir(tmp_path)
    req = RegistrationRequest(
        raw_item_dir=item_dir, surname="Guard", given_name="Test", title="Doc",
        edition_slug="1900", publication_year=1900, copyright_status="public_domain",
        archive_source="x", source_id="smoke-test-guard", manifest_path=tmp_path / "m.yaml",
    )
    register_source(
        req, existing_author_ids=set(), existing_work_ids=set(),
        existing_edition_ids=set(), existing_source_ids=set(),
        ledger=ledger, state_store=state_store, exception_queue=exception_queue,
    )

    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tsu_files}
    assert before == after

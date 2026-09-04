"""Orchestration for the upstream registration pipeline (ADR-021 SS2).

Calls existing, unmodified code at exactly two points:
  - NAE.pipeline.canonical.extract.extract_pages() for Extraction
  - (not called here) NAE.pipeline.tsu.builder — TSU generation is
    explicitly NOT invoked by this module. Per ADR-021 SS14 (Dry-run
    Isolation Rule) and SS15 (Phase A scope), this pipeline stops right
    after the Quality Gate; handing off to the TSU Builder / ADR-020
    incremental pipeline is a separate, later, explicitly-approved step.

Nothing here touches NAE/pipeline/ingest/*, NAE/pipeline/embed/*,
NAE/pipeline/index/*, or Qdrant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from NAE.pipeline.canonical.extract import extract_pages

from . import identity as identity_mod
from . import manifest_writer
from . import quality_gate as qg
from . import raw_preservation
from . import source_validator
from .state import ExceptionQueue, RegistrationState, RegistrationStateStore


@dataclass
class RegistrationRequest:
    raw_item_dir: Path          # directory extract_pages() expects (e.g. NAE/corpus/raw/archive_org/<category>/<work>/)
    surname: str
    given_name: str
    title: str
    edition_slug: str
    publication_year: int | None
    copyright_status: str | None
    archive_source: str | None
    source_id: str
    manifest_path: Path


@dataclass
class RegistrationResult:
    source_id: str
    final_state: RegistrationState
    identity: identity_mod.NewIdentity | None = None
    preservation: raw_preservation.PreservationResult | None = None
    validation: source_validator.SourceValidationResult | None = None
    gate_result: qg.QualityGateResult | None = None
    page_count: int = 0
    notes: list[str] = field(default_factory=list)


def register_source(
    request: RegistrationRequest,
    *,
    existing_author_ids: set[str],
    existing_work_ids: set[str],
    existing_edition_ids: set[str],
    existing_source_ids: set[str],
    ledger: raw_preservation.ChecksumLedger,
    state_store: RegistrationStateStore,
    exception_queue: ExceptionQueue,
) -> RegistrationResult:
    source_id = request.source_id
    result = RegistrationResult(source_id=source_id, final_state=RegistrationState.DISCOVERED)
    state_store.set_state(source_id, RegistrationState.DISCOVERED)

    # --- Identity Resolution ---
    try:
        new_identity = identity_mod.issue_identity(
            surname=request.surname,
            given_name=request.given_name,
            title=request.title,
            edition_slug=request.edition_slug,
            source_id=source_id,
            existing_author_ids=existing_author_ids,
            existing_work_ids=existing_work_ids,
            existing_edition_ids=existing_edition_ids,
            existing_source_ids=existing_source_ids,
        )
    except ValueError as e:
        state_store.set_state(source_id, RegistrationState.REGISTRATION_FAILED)
        exception_queue.record(source_id, RegistrationState.REGISTRATION_FAILED, str(e))
        result.final_state = RegistrationState.REGISTRATION_FAILED
        result.notes.append(str(e))
        return result

    result.identity = new_identity
    for collided, label in ((new_identity.author_collided, "author_id"), (new_identity.work_collided, "work_id"), (new_identity.edition_collided, "edition_id")):
        if collided:
            result.notes.append(f"{label} collision resolved with numeric suffix: {getattr(new_identity, label)}")
    state_store.set_state(source_id, RegistrationState.REGISTERED)

    # --- Raw Preservation ---
    raw_files = [p for p in request.raw_item_dir.iterdir() if p.is_file()] if request.raw_item_dir.exists() else []
    if not raw_files:
        state_store.set_state(source_id, RegistrationState.RAW_CHECKSUM_MISMATCH)
        exception_queue.record(source_id, RegistrationState.RAW_CHECKSUM_MISMATCH, "no raw files found in raw_item_dir", raw_path=str(request.raw_item_dir))
        result.final_state = RegistrationState.RAW_CHECKSUM_MISMATCH
        return result

    primary_raw = raw_files[0]
    preservation = raw_preservation.preserve(primary_raw, source_id, ledger)
    result.preservation = preservation
    if preservation.duplicate_of:
        result.notes.append(f"SS9 Level 2 content duplicate of existing source_id: {preservation.duplicate_of}")
    state_store.set_state(source_id, RegistrationState.RAW_PRESERVED)

    # --- Source Validation ---
    record = {
        "source_id": source_id,
        "author_id": new_identity.author_id,
        "work_id": new_identity.work_id,
        "edition_id": new_identity.edition_id,
        "title": request.title,
        "publication_year": request.publication_year,
        "copyright_status": request.copyright_status,
        "archive_source": request.archive_source,
    }
    validation = source_validator.validate(record, primary_raw)
    result.validation = validation
    if not validation.passed:
        state_store.set_state(source_id, RegistrationState.QUALITY_GATE_FAILED)
        exception_queue.record(source_id, RegistrationState.QUALITY_GATE_FAILED, "; ".join(validation.errors), raw_path=str(primary_raw), checksum=preservation.checksum)
        result.final_state = RegistrationState.QUALITY_GATE_FAILED
        return result
    state_store.set_state(source_id, RegistrationState.VALIDATED)

    # --- Extraction Adapter (existing extract.py, unmodified) ---
    extraction = extract_pages(request.raw_item_dir)
    page_count = len([p for p in extraction.pages if p.strip()])
    result.page_count = page_count
    extraction_ok = extraction.source != "none" and page_count > 0
    if not extraction_ok:
        state_store.set_state(source_id, RegistrationState.EXTRACTION_FAILED)
        exception_queue.record(source_id, RegistrationState.EXTRACTION_FAILED, f"extraction produced 0 pages (source={extraction.source})", raw_path=str(primary_raw), checksum=preservation.checksum)
        result.final_state = RegistrationState.EXTRACTION_FAILED
        return result
    state_store.set_state(source_id, RegistrationState.EXTRACTED)

    # --- Quality Gate ---
    reverify = raw_preservation.verify(primary_raw, source_id, ledger)
    gate_input = qg.QualityGateInput(
        raw_file_exists=primary_raw.exists(),
        checksum_matches=reverify.matches,
        extraction_output_present=extraction_ok,
        page_count=page_count,
        source_readable=extraction_ok,
        identity_complete=all([new_identity.author_id, new_identity.work_id, new_identity.edition_id, new_identity.source_id]),
        metadata_complete=bool(request.publication_year and request.copyright_status),
    )
    gate_result = qg.evaluate(gate_input)
    result.gate_result = gate_result

    if gate_result.verdict == qg.QualityGateVerdict.FAIL:
        state_store.set_state(source_id, RegistrationState.QUALITY_GATE_FAILED)
        exception_queue.record(source_id, RegistrationState.QUALITY_GATE_FAILED, "; ".join(gate_result.fail_reasons), raw_path=str(primary_raw), checksum=preservation.checksum)
        result.final_state = RegistrationState.QUALITY_GATE_FAILED
        return result

    # PASS or WARNING both proceed (WARNING is non-blocking per ADR-021 SS8)
    manifest_writer.write_entry(request.manifest_path, {
        "source_id": source_id,
        "title": request.title,
        "author": f"{request.given_name} {request.surname}".strip(),
        "author_id": new_identity.author_id,
        "work_id": new_identity.work_id,
        "edition_id": new_identity.edition_id,
        "year": request.publication_year,
        "license": request.copyright_status,
        "archive_source": request.archive_source,
        "raw_checksum": preservation.checksum,
    })
    state_store.set_state(source_id, RegistrationState.QUALITY_PASSED)
    result.final_state = RegistrationState.QUALITY_PASSED
    if gate_result.verdict == qg.QualityGateVerdict.WARNING:
        result.notes.append(f"WARNING (non-blocking): {', '.join(gate_result.warning_reasons)}")

    return result

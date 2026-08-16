"""NAE Live Dashboard — pipeline stage status (Registration -> ... -> Qdrant).

Pure functions only — every status here is derived from evidence already
on disk (registration_state.json, tsu.json review_status tallies, the
existing TSU-extraction queue logic, index_report.json presence). Nothing
here is inferred or guessed: a stage with no evidence of having run is
QUEUED, never RUNNING or COMPLETE — this module exists specifically to
enforce that rule in one place instead of scattering judgment calls
through the UI layer.

Mirrors (does not import — the dashboard intentionally stays outside the
NAE package, see collector.py's module docstring) two upstream contracts:
 - NAE/pipeline/registration/state.py::RegistrationState
 - NAE/pipeline/tsu/review_gate.py's review_status vocabulary
   (generated/reviewed/verified/rejected) and EMBEDDING_ELIGIBLE_STATUSES
   = {"verified"} — also scripts/nae_incremental_ingest.py:33, the actual
   embedding step's input filter (`review_status == "verified"`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Mirrors NAE/pipeline/registration/state.py::RegistrationState.
_REGISTRATION_COMPLETE_STATE = "QUALITY_PASSED"
_REGISTRATION_FAILURE_STATES = frozenset({
    "REGISTRATION_FAILED", "RAW_CHECKSUM_MISMATCH",
    "EXTRACTION_FAILED", "QUALITY_GATE_FAILED",
})

STAGE_NAMES = ["Registration", "TSU Extraction", "Quality Gate", "Review", "Embedding", "Qdrant"]

_FULLER_VOLUME_PATTERN = re.compile(r"Fuller_Complete_Works_Vol(\d+)$")


def registration_source_id(identifier: str) -> str | None:
    """Fuller_Complete_Works_Vol01 -> BAP-MISS-FULLER-VOL01, mirroring the
    source_id keys actually observed in registration_state.json. Only
    covers Fuller volumes (the only identifiers this dashboard tracks) —
    returns None for anything else, and the caller then reports QUEUED
    rather than guessing at a key that was never verified to exist."""
    m = _FULLER_VOLUME_PATTERN.match(identifier or "")
    return f"BAP-MISS-FULLER-VOL{m.group(1)}" if m else None


def registration_stage_status(identifier: str, registration_state: dict) -> str:
    source_id = registration_source_id(identifier)
    if source_id is None:
        return "QUEUED"
    entry = (registration_state or {}).get(source_id)
    if not entry:
        return "QUEUED"
    state = entry.get("state")
    if state in _REGISTRATION_FAILURE_STATES:
        return "ERROR"
    if state == _REGISTRATION_COMPLETE_STATE:
        return "COMPLETE"
    return "RUNNING"


@dataclass
class ReviewTally:
    total: int = 0
    generated: int = 0
    reviewed: int = 0
    verified: int = 0
    rejected: int = 0


def tally_review_status(tsu_records: list[dict]) -> ReviewTally:
    tally = ReviewTally(total=len(tsu_records))
    for r in tsu_records:
        status = r.get("review_status")
        if status == "generated":
            tally.generated += 1
        elif status == "reviewed":
            tally.reviewed += 1
        elif status == "verified":
            tally.verified += 1
        elif status == "rejected":
            tally.rejected += 1
    return tally


def quality_gate_stage_status(tally: ReviewTally, extraction_complete: bool) -> str:
    """Reflects review_gate.py's live pass/fail judgment (only "verified"
    records are embedding-eligible) against whatever has been extracted
    so far — this is a standing gate condition, not a one-time step."""
    if tally.total == 0:
        return "QUEUED"
    if tally.verified == 0:
        return "BLOCKED"
    if tally.verified < tally.total or not extraction_complete:
        return "RUNNING"
    return "COMPLETE"


def review_stage_status(tally: ReviewTally, extraction_complete: bool) -> str:
    if tally.total == 0:
        return "QUEUED"
    past_generated = tally.reviewed + tally.verified + tally.rejected
    if past_generated == 0:
        return "QUEUED"
    if past_generated < tally.total or not extraction_complete:
        return "RUNNING"
    return "COMPLETE"


def embedding_stage_status(tally: ReviewTally, index_status: str | None) -> str:
    """scripts/nae_incremental_ingest.py:33 filters its own input on
    review_status == "verified"; with verified == 0 there is structurally
    nothing embedding could have processed yet, independent of whether
    anyone ran the script."""
    if tally.verified == 0:
        return "QUEUED"
    return index_status or "QUEUED"


def qdrant_stage_status(tally: ReviewTally, index_status: str | None) -> str:
    if tally.verified == 0:
        return "QUEUED"
    return index_status or "QUEUED"


def index_status_from_report(index_report: dict | None) -> str | None:
    """NAE/pipeline/index/indexer.py:146-147 writes index_report.json to
    the same per-identifier tsu/<identifier>/ directory as tsu_report.json,
    with an `indexed` count. Presence alone isn't enough — several backup/
    remediation runs leave a report with indexed=0 — so COMPLETE requires
    indexed > 0."""
    if not index_report:
        return None
    if (index_report.get("indexed") or 0) > 0:
        return "COMPLETE"
    return None


def compute_pipeline_stages(
    *,
    identifier: str,
    registration_state: dict,
    tsu_records: list[dict] | None,
    extraction_status: str,
    index_report: dict | None,
) -> list[dict]:
    """`extraction_status` comes from the existing TSU-extraction queue
    logic (RUNNING/COMPLETE/QUEUED/FAILED); FAILED is remapped to ERROR
    here to match this panel's status vocabulary."""
    tally = tally_review_status(tsu_records or [])
    extraction_complete = extraction_status == "COMPLETE"
    index_status = index_status_from_report(index_report)
    extraction_display = "ERROR" if extraction_status == "FAILED" else extraction_status

    return [
        {"stage": "Registration", "status": registration_stage_status(identifier, registration_state)},
        {"stage": "TSU Extraction", "status": extraction_display},
        {"stage": "Quality Gate", "status": quality_gate_stage_status(tally, extraction_complete)},
        {"stage": "Review", "status": review_stage_status(tally, extraction_complete)},
        {"stage": "Embedding", "status": embedding_stage_status(tally, index_status)},
        {"stage": "Qdrant", "status": qdrant_stage_status(tally, index_status)},
    ]

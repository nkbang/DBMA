"""Conservative / Warning-first Quality Gate (ADR-021 SS8).

FAIL is reserved for the 7 fixed integrity failures below — this list is
not meant to grow casually; extending it is an ADR-021 amendment, not a
code change. WARNING conditions are detected but never block; their
numeric thresholds are intentionally left unset until the first dry-run
produces real measurements (ADR-021 SS8 — no invented threshold).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QualityGateVerdict(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


# Fixed per ADR-021 SS8 — do not add items here without an ADR amendment.
FAIL_REASONS = (
    "raw_file_missing",
    "raw_checksum_mismatch",
    "extraction_output_missing",
    "zero_page_extraction",
    "unreadable_or_corrupt_source",
    "required_identity_unavailable",
    "required_metadata_missing",
)

WARNING_REASONS = (
    "low_ocr_confidence",
    "partial_ocr_degradation",
    "abnormal_character_ratio",
    "possible_page_count_discrepancy",
    "encoding_anomalies",
)


@dataclass
class QualityGateInput:
    raw_file_exists: bool
    checksum_matches: bool
    extraction_output_present: bool
    page_count: int
    source_readable: bool
    identity_complete: bool
    metadata_complete: bool
    # WARNING-tier signals — thresholds intentionally unset (SS8); caller
    # passes pre-computed booleans/flags once a real signal exists.
    low_ocr_confidence: bool = False
    partial_ocr_degradation: bool = False
    abnormal_character_ratio: bool = False
    possible_page_count_discrepancy: bool = False
    encoding_anomalies: bool = False


@dataclass
class QualityGateResult:
    verdict: QualityGateVerdict
    fail_reasons: list[str] = field(default_factory=list)
    warning_reasons: list[str] = field(default_factory=list)


def evaluate(gate_input: QualityGateInput) -> QualityGateResult:
    fail_reasons: list[str] = []
    if not gate_input.raw_file_exists:
        fail_reasons.append("raw_file_missing")
    if not gate_input.checksum_matches:
        fail_reasons.append("raw_checksum_mismatch")
    if not gate_input.extraction_output_present:
        fail_reasons.append("extraction_output_missing")
    if gate_input.page_count == 0:
        fail_reasons.append("zero_page_extraction")
    if not gate_input.source_readable:
        fail_reasons.append("unreadable_or_corrupt_source")
    if not gate_input.identity_complete:
        fail_reasons.append("required_identity_unavailable")
    if not gate_input.metadata_complete:
        fail_reasons.append("required_metadata_missing")

    if fail_reasons:
        return QualityGateResult(verdict=QualityGateVerdict.FAIL, fail_reasons=fail_reasons)

    warning_reasons = []
    if gate_input.low_ocr_confidence:
        warning_reasons.append("low_ocr_confidence")
    if gate_input.partial_ocr_degradation:
        warning_reasons.append("partial_ocr_degradation")
    if gate_input.abnormal_character_ratio:
        warning_reasons.append("abnormal_character_ratio")
    if gate_input.possible_page_count_discrepancy:
        warning_reasons.append("possible_page_count_discrepancy")
    if gate_input.encoding_anomalies:
        warning_reasons.append("encoding_anomalies")

    if warning_reasons:
        return QualityGateResult(verdict=QualityGateVerdict.WARNING, warning_reasons=warning_reasons)

    return QualityGateResult(verdict=QualityGateVerdict.PASS)

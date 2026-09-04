"""Upstream Source Validator (ADR-021 SS5) — a module distinct from the
existing `scripts/source_validator.py` (which checks manifest field
presence/uniqueness for already-registered entries) and from the TSU
Validator (structural TSU schema checks, unmodified, downstream of
Extraction).

This module checks the boundary this ADR actually owns: Raw / Metadata /
Provenance / Integrity, at Registration time, before Extraction runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_IDENTITY_FIELDS = ("source_id", "author_id", "work_id", "edition_id")
REQUIRED_METADATA_FIELDS = ("title", "publication_year", "copyright_status")
PROVENANCE_FIELDS = ("archive_source",)  # optional per ADR-021 SS5 / NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 7


@dataclass
class SourceValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_raw_integrity(raw_path: Path) -> SourceValidationResult:
    result = SourceValidationResult()
    if not raw_path.exists():
        result.errors.append(f"raw file missing: {raw_path}")
        return result
    if raw_path.stat().st_size == 0:
        result.errors.append(f"raw file is 0 bytes: {raw_path}")
    return result


def validate_identity(record: dict[str, Any]) -> SourceValidationResult:
    result = SourceValidationResult()
    for f in REQUIRED_IDENTITY_FIELDS:
        if not record.get(f):
            result.errors.append(f"required identity field missing: {f}")
    return result


def validate_metadata(record: dict[str, Any]) -> SourceValidationResult:
    result = SourceValidationResult()
    for f in REQUIRED_METADATA_FIELDS:
        if not record.get(f):
            result.errors.append(f"required metadata field missing: {f}")
    return result


def validate_provenance(record: dict[str, Any]) -> SourceValidationResult:
    """Provenance fields are optional — absence is a WARNING, not an error
    (ADR-021 SS5 / archive_source policy, confirmed 2026-08-02: RAW
    directories from Archive.org often lack sidecar metadata)."""
    result = SourceValidationResult()
    for f in PROVENANCE_FIELDS:
        if not record.get(f):
            result.warnings.append(f"provenance field missing (optional): {f}")
    return result


def validate(record: dict[str, Any], raw_path: Path) -> SourceValidationResult:
    """Combines Raw / Metadata / Provenance / Integrity checks. Errors from
    any sub-check make the whole result fail; warnings never block."""
    combined = SourceValidationResult()
    for sub in (validate_raw_integrity(raw_path), validate_identity(record), validate_metadata(record), validate_provenance(record)):
        combined.errors.extend(sub.errors)
        combined.warnings.extend(sub.warnings)
    return combined

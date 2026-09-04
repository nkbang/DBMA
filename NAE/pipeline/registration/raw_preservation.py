"""Raw immutability enforcement (ADR-021 SS6) + 2-tier duplicate detection (SS9).

Design principle: OS permissions do not prove immutability (owner/root can
always chmod back) — this module does NOT claim otherwise. The actual,
auditable guarantee is checksum recomputation against an append-only ledger
at every access. chmod is applied only as a secondary accident deterrent.

Threat model (explicit, per ADR-021 SS6): this defends against accidental
overwrite/corruption. It does NOT defend against a coordinated tamper of
both the raw file and the ledger at once — that is out of scope.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class LedgerEntry:
    source_id: str
    raw_path: str
    checksum: str
    event: str  # "preserve" | "reverify"
    recorded_at: str


class ChecksumLedger:
    """Append-only JSONL ledger. Never rewrites or truncates existing lines —
    only appends. Duplicate detection (SS9 Level 2) and reverification (SS6)
    both read the full history via `entries()`."""

    def __init__(self, path: Path = config.DEFAULT_CHECKSUM_LEDGER_PATH):
        self.path = path

    def entries(self) -> list[LedgerEntry]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            out.append(LedgerEntry(**d))
        return out

    def append(self, entry: LedgerEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")

    def first_checksum_for(self, source_id: str) -> str | None:
        """The checksum recorded at initial `preserve()` time — the
        authoritative value all later reverifications are compared against."""
        for e in self.entries():
            if e.source_id == source_id and e.event == "preserve":
                return e.checksum
        return None

    def find_duplicate_source_id(self, checksum: str, *, exclude_source_id: str | None = None) -> str | None:
        """SS9 Level 2 — same raw content under a different source_id/filename,
        regardless of when or how it was registered."""
        for e in self.entries():
            if e.event == "preserve" and e.checksum == checksum and e.source_id != exclude_source_id:
                return e.source_id
        return None


@dataclass(frozen=True)
class PreservationResult:
    source_id: str
    raw_path: str
    checksum: str
    duplicate_of: str | None  # set if SS9 Level 2 duplicate found; preservation still recorded


def preserve(raw_path: Path, source_id: str, ledger: ChecksumLedger) -> PreservationResult:
    """Registers a raw file's checksum, applies the accident-deterrent
    read-only permission, and checks for content duplicates against the
    full ledger history. Does NOT delete or reject duplicates — that
    decision belongs to a human (ADR-021 SS9)."""
    checksum = sha256_of_file(raw_path)
    duplicate_of = ledger.find_duplicate_source_id(checksum, exclude_source_id=source_id)

    ledger.append(LedgerEntry(
        source_id=source_id,
        raw_path=str(raw_path),
        checksum=checksum,
        event="preserve",
        recorded_at=datetime.now(timezone.utc).isoformat(),
    ))
    os.chmod(raw_path, config.RAW_READONLY_MODE)

    return PreservationResult(source_id=source_id, raw_path=str(raw_path), checksum=checksum, duplicate_of=duplicate_of)


@dataclass(frozen=True)
class VerificationResult:
    source_id: str
    matches: bool
    recorded_checksum: str | None
    current_checksum: str


def verify(raw_path: Path, source_id: str, ledger: ChecksumLedger) -> VerificationResult:
    """Recomputes the checksum and compares against the value recorded at
    `preserve()` time. This — not the file permission — is the actual
    integrity check (ADR-021 SS6)."""
    recorded = ledger.first_checksum_for(source_id)
    current = sha256_of_file(raw_path)
    matches = recorded is not None and recorded == current

    ledger.append(LedgerEntry(
        source_id=source_id,
        raw_path=str(raw_path),
        checksum=current,
        event="reverify",
        recorded_at=datetime.now(timezone.utc).isoformat(),
    ))

    return VerificationResult(source_id=source_id, matches=matches, recorded_checksum=recorded, current_checksum=current)


def is_catalog_duplicate(archive_identifier: str, existing_identifiers: set[str]) -> bool:
    """SS9 Level 1 — same catalog/source identity already registered."""
    return archive_identifier in existing_identifiers

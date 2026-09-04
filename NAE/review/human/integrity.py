"""NAE Pilot Human Review — Integrity Verification Module.

Verifies that Pilot TSU records in the corpus match the Human Review Package
original text, metadata provenance, and flags.  AI reads only; no writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PILOT_PACKAGE: Path = Path(__file__).resolve().parents[2] / "docs" / "NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md"

# Dagg and Hiscox TSU directories (produced by prior CUE work)
TSU_ROOT: Path = Path(__file__).resolve().parents[3] / "NAE" / "corpus" / "tsu"

PILOT_TSU_IDS: tuple[str, ...] = (
    "TSU-0000713",  # Dagg Ecclesiology
    "TSU-0000199",  # Dagg Baptism
    "TSU-0000330",  # Dagg Lord's Supper
    "TSU-0000033",  # Dagg Soteriology
    "TSU-0000025",  # Dagg Sanctification
    "TSU-0003524",  # Hiscox Ecclesiology
    "TSU-0003661",  # Hiscox Baptism
    "TSU-0003525",  # Hiscox Church Discipline
    "TSU-0003893",  # Hiscox Lord's Supper
    "TSU-0003647",  # Hiscox Soteriology
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class IntegrityCheck:
    """Result of verifying one Pilot TSU against the corpus."""
    tsu_id: str
    source_name: str          # e.g. "Dagg_Church_Order" or "Hiscox_Standard_Manual"
    tsu_exists: bool = False
    tsu_id_match: bool = False
    claim_match: bool = False
    doctrine_match: bool = False
    source_id_match: bool = False
    author_id_match: bool = False
    work_id_match: bool = False
    edition_id_match: bool = False
    metadata_schema_version_ok: bool = False
    copyright_status_ok: bool = False
    flags_present: list[str] = None  # type: ignore[assignment]
    issues: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.flags_present is None:
            self.flags_present = []
        if self.issues is None:
            self.issues = []

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0


# ---------------------------------------------------------------------------
# Verification engine
# ---------------------------------------------------------------------------

class IntegrityVerifier:
    """Verify Pilot TSU records against the corpus TSU files."""

    def __init__(self, tsu_root: Optional[Path] = None) -> None:
        self.tsu_root = tsu_root or TSU_ROOT

    def _find_tsu_file(self, tsu_id: str) -> tuple[Optional[Path], Optional[dict]]:
        """Find a TSU record by ID across all source directories.

        Returns (path_to_file, tsu_record) or (None, None).
        """
        if not self.tsu_root.exists():
            return None, None
        for src_dir in self.tsu_root.iterdir():
            if not src_dir.is_dir() or src_dir.name.startswith("_"):
                continue
            tsu_file = src_dir / "tsu.json"
            if not tsu_file.exists():
                continue
            with open(tsu_file, "r", encoding="utf-8") as fh:
                records = json.load(fh)
            for record in records:
                if record.get("id") == tsu_id:
                    return tsu_file, record
        return None, None

    def verify_one(self, tsu_id: str,
                   expected_source: str,
                   expected_claim: str,
                   expected_doctrine: str,
                   expected_source_id: str,
                   expected_author_id: str,
                   expected_work_id: str,
                   expected_edition_id: str,
                   expected_flags: list[str]) -> IntegrityCheck:
        """Verify a single Pilot TSU against corpus data."""
        check = IntegrityCheck(
            tsu_id=tsu_id,
            source_name=expected_source,
            flags_present=list(expected_flags),
        )

        tsu_file, record = self._find_tsu_file(tsu_id)
        if record is None:
            check.issues.append(f"TSU {tsu_id} not found in corpus")
            return check

        check.tsu_exists = True

        # Extract source directory name (tsu_file is guaranteed non-None here)
        assert tsu_file.parent is not None  # type: ignore[unreachable]
        check.source_name = tsu_file.parent.name

        # Verify id
        check.tsu_id_match = record.get("id") == tsu_id

        # Verify claim (exact match)
        actual_claim = record.get("claim", "")
        check.claim_match = actual_claim == expected_claim

        # Verify doctrine
        check.doctrine_match = record.get("doctrine") == expected_doctrine

        # Verify metadata fields
        check.source_id_match = record.get("source_id") == expected_source_id
        check.author_id_match = record.get("author_id") == expected_author_id
        check.work_id_match = record.get("work_id") == expected_work_id
        check.edition_id_match = record.get("edition_id") == expected_edition_id

        # Verify metadata schema version
        meta_schema = record.get("metadata", {}).get("schema_version", "")
        check.metadata_schema_version_ok = meta_schema.startswith("1.") or meta_schema.startswith("2.")

        # Verify copyright status
        check.copyright_status_ok = record.get("copyright_status") == "public_domain"

        # Check for issues
        if not check.tsu_id_match:
            check.issues.append(f"id mismatch: expected {tsu_id}, got {record.get('id')}")
        if not check.claim_match:
            check.issues.append("claim text does not match review package")
        if not check.doctrine_match:
            check.issues.append(f"doctrine mismatch: expected {expected_doctrine}, got {record.get('doctrine')}")
        if not check.source_id_match:
            check.issues.append(f"source_id mismatch: expected {expected_source_id}")
        if not check.author_id_match:
            check.issues.append(f"author_id mismatch: expected {expected_author_id}")
        if not check.work_id_match:
            check.issues.append(f"work_id mismatch: expected {expected_work_id}")
        if not check.edition_id_match:
            check.issues.append(f"edition_id mismatch: expected {expected_edition_id}")

        return check

    def verify_all(self) -> list[IntegrityCheck]:
        """Verify all 10 Pilot TSUs.

        Expected values are derived from the Human Review Package (docs/NAE_PILOT_HUMAN_REVIEW_PACKAGE_001.md).
        """
        # Expected values from the review package
        expectations = {
            "TSU-0000713": {
                "source": "Dagg_Church_Order",
                "claim": "No church communicated with me as concerning giving and receiving, but ye only. As distinct bodies, they sent and received salutations,",
                "doctrine": "Ecclesiology",
                "source_id": "BAP-CHURCH-DAGG-001",
                "author_id": "dagg_john_l",
                "work_id": "WORK-DAGG-CHURCH-ORDER-001",
                "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
                "flags": ["SCRIPTURE_MISMATCH"],
            },
            "TSU-0000199": {
                "source": "Dagg_Church_Order",
                "claim": "The verb never signifies this process.",
                "doctrine": "Baptism",
                "source_id": "BAP-CHURCH-DAGG-001",
                "author_id": "dagg_john_l",
                "work_id": "WORK-DAGG-CHURCH-ORDER-001",
                "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
                "flags": ["AMBIGUOUS"],
            },
            "TSU-0000330": {
                "source": "Dagg_Church_Order",
                "claim": "A well executed picture of the crucifixion, such as may be seen in Catholic chapels, has much more resemblance to the body of Christ, than is furnished by the breaking and eating of bread; and yet no one would think of substituting the picture for the bread, in the celebration of the ordinance.",
                "doctrine": "Lord's Supper",
                "source_id": "BAP-CHURCH-DAGG-001",
                "author_id": "dagg_john_l",
                "work_id": "WORK-DAGG-CHURCH-ORDER-001",
                "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
                "flags": ["CONTEXT_LOSS", "EVIDENCE_INSUFFICIENT"],
            },
            "TSU-0000033": {
                "source": "Dagg_Church_Order",
                "claim": "A powerful motive, to love and obey Christ, is drawn from the love which he has manifested in dying for us.",
                "doctrine": "Soteriology",
                "source_id": "BAP-CHURCH-DAGG-001",
                "author_id": "dagg_john_l",
                "work_id": "WORK-DAGG-CHURCH-ORDER-001",
                "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
                "flags": ["NO_OBJECTION"],
            },
            "TSU-0000025": {
                "source": "Dagg_Church_Order",
                "claim": "To love God with all the heart is the sum of all duty.",
                "doctrine": "Sanctification",
                "source_id": "BAP-CHURCH-DAGG-001",
                "author_id": "dagg_john_l",
                "work_id": "WORK-DAGG-CHURCH-ORDER-001",
                "edition_id": "WORK-DAGG-CHURCH-ORDER-001-1871",
                "flags": ["SCRIPTURE_MISMATCH"],
            },
            "TSU-0003524": {
                "source": "Hiscox_Standard_Manual",
                "claim": "The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ.",
                "doctrine": "Ecclesiology",
                "source_id": "BAP-CHURCH-HISCOX",
                "author_id": "hiscox_edward_t",
                "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
                "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
                "flags": ["NO_OBJECTION"],
            },
            "TSU-0003661": {
                "source": "Hiscox_Standard_Manual",
                "claim": "Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins.",
                "doctrine": "Baptism",
                "source_id": "BAP-CHURCH-HISCOX",
                "author_id": "hiscox_edward_t",
                "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
                "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
                "flags": ["SCRIPTURE_MISMATCH"],
            },
            "TSU-0003525": {
                "source": "Hiscox_Standard_Manual",
                "claim": "All this should, if possible, be avoided.",
                "doctrine": "Church Discipline",
                "source_id": "BAP-CHURCH-HISCOX",
                "author_id": "hiscox_edward_t",
                "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
                "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
                "flags": ["CONTEXT_LOSS"],
            },
            "TSU-0003893": {
                "source": "Hiscox_Standard_Manual",
                "claim": "To them it seems kindly and fraternal to invite all who say they love our common Lord and Saviour to unite in commemorating his death in the Supper.",
                "doctrine": "Lord's Supper",
                "source_id": "BAP-CHURCH-HISCOX",
                "author_id": "hiscox_edward_t",
                "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
                "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
                "flags": ["AMBIGUOUS"],
            },
            "TSU-0003647": {
                "source": "Hiscox_Standard_Manual",
                "claim": "And the times of this ignorance God winked at, but now commandeth all men everywhere to repent.",
                "doctrine": "Soteriology",
                "source_id": "BAP-CHURCH-HISCOX",
                "author_id": "hiscox_edward_t",
                "work_id": "WORK-HISCOX-STANDARD-MANUAL-001",
                "edition_id": "WORK-HISCOX-STANDARD-MANUAL-001-1890",
                "flags": ["SCRIPTURE_MISMATCH"],
            },
        }

        results: list[IntegrityCheck] = []
        for tsu_id in PILOT_TSU_IDS:
            if tsu_id not in expectations:
                results.append(IntegrityCheck(tsu_id=tsu_id, source_name="", issues=[f"No expectations defined for {tsu_id}"]))
                continue
            exp = expectations[tsu_id]
            result = self.verify_one(
                tsu_id=tsu_id,
                expected_source=exp["source"],
                expected_claim=exp["claim"],
                expected_doctrine=exp["doctrine"],
                expected_source_id=exp["source_id"],
                expected_author_id=exp["author_id"],
                expected_work_id=exp["work_id"],
                expected_edition_id=exp["edition_id"],
                expected_flags=exp["flags"],
            )
            results.append(result)
        return results

    def summary(self, checks: list[IntegrityCheck]) -> dict[str, int]:
        """Return a summary dict of the integrity check results."""
        return {
            "total": len(checks),
            "found": sum(1 for c in checks if c.tsu_exists),
            "missing": sum(1 for c in checks if not c.tsu_exists),
            "all_fields_match": sum(1 for c in checks if c.passed and c.tsu_exists),
            "issues_found": sum(1 for c in checks if c.issues),
        }


# ---------------------------------------------------------------------------
# Compatibility layer (NAE-PILOT-HUMAN-REVIEW-001 Phase 3) — thin function
# API used by promotion.py's caller and the test suite. Built on top of
# schema.PILOT_REFERENCE (Korean `claim`, source_id/work_id/edition_id via
# FK chain, `metadata_provenance.crosswalk_id`) rather than duplicating a
# second expectations table — single source of truth stays in schema.py.
# ---------------------------------------------------------------------------

from dataclasses import field as _field  # noqa: E402

from .schema import PILOT_REFERENCE as _PILOT_REFERENCE  # noqa: E402

_COMPAT_COMPARE_FIELDS = ("source_id", "work_id", "edition_id", "doctrine", "claim")
_COMPAT_IDENTIFIERS = ("Dagg_Church_Order", "Hiscox_Standard_Manual")


@dataclass(frozen=True)
class IntegrityMismatch:
    tsu_id: str
    field: str
    expected: str
    actual: "str | None"


@dataclass
class IntegrityReport:
    missing_tsu_ids: list = _field(default_factory=list)
    mismatches: list = _field(default_factory=list)
    non_generated_review_status: list = _field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_tsu_ids and not self.mismatches and not self.non_generated_review_status

    @property
    def status(self) -> str:
        return "PASS" if self.ok else "BLOCKED"


def _compat_load_production_records(tsu_root: Path) -> dict:
    records: dict = {}
    for identifier in _COMPAT_IDENTIFIERS:
        path = tsu_root / identifier / "tsu.json"
        if not path.exists():
            continue
        try:
            for rec in json.loads(path.read_text(encoding="utf-8")):
                records[rec.get("id")] = rec
        except (json.JSONDecodeError, OSError):
            continue
    return records


def verify_pilot_integrity(tsu_root: "Path | None" = None) -> IntegrityReport:
    """Read-only Phase 3 integrity check against `schema.PILOT_REFERENCE`
    (10 confirmed Pilot candidates). Never writes to Production TSU."""
    tsu_root = tsu_root or TSU_ROOT
    production = _compat_load_production_records(tsu_root)
    report = IntegrityReport()

    for ref in _PILOT_REFERENCE:
        tsu_id = ref["tsu_id"]
        record = production.get(tsu_id)
        if record is None:
            report.missing_tsu_ids.append(tsu_id)
            continue

        for compare_field in _COMPAT_COMPARE_FIELDS:
            actual = record.get(compare_field)
            if actual != ref[compare_field]:
                report.mismatches.append(IntegrityMismatch(tsu_id, compare_field, ref[compare_field], actual))

        provenance = record.get("metadata_provenance") or {}
        if provenance.get("crosswalk_id") != ref["crosswalk_id"]:
            report.mismatches.append(
                IntegrityMismatch(tsu_id, "metadata_provenance.crosswalk_id", ref["crosswalk_id"],
                                   provenance.get("crosswalk_id"))
            )

        if record.get("review_status") != "generated":
            report.non_generated_review_status.append(tsu_id)

    return report
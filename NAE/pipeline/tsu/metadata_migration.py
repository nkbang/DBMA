"""NAE/pipeline/tsu/metadata_migration.py — Additive Metadata Layer Migration
(NAE-METADATA-SCHEMA-2.0.0-MIGRATION-IMPLEMENTATION-001).

Authority: docs/NAE_METADATA_SCHEMA_2_MIGRATION_PACKAGE_001.md (C1 Final
Review APPROVED WITH CONDITIONS — C1-COND-001/002 해제됨,
`metadata_schema_version="1.1.0"` 확정, docs/NAE_METADATA_GOVERNANCE_v1.md
§2.3 참고).

Provenance chain(읽기 전용, 절대 Crosswalk/Registry/Editions/Works 파일에
쓰지 않음): TSU.identifier -> Crosswalk -> Registry -> Edition -> Work.

기존 TSU 필드(IMMUTABLE_FIELDS)는 절대 변경/삭제하지 않는다 — 신규
필드만 additive로 추가한다. `category`/`citation_policy`는 authoritative
source가 없으므로 절대 추측하지 않고 `AUTHORITATIVE_SOURCE_MISSING`으로
명시한다.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from scripts.crosswalk.schema import CrosswalkRecord, Confidence, MappingStatus
from scripts.crosswalk.storage.yaml_repository import YamlCrosswalkRepository

METADATA_SCHEMA_VERSION = "1.1.0"
RESOLVER_VERSION = "1.0.0"

# builder.py::build_tsu_for_identifier()가 생성하는 기존 필드 — 이번
# Migration에서 절대 변경/삭제되지 않아야 하는 필드 목록(Migration
# Package §4와 동일).
IMMUTABLE_FIELDS: tuple[str, ...] = (
    "id", "tsu_schema_version", "book", "author", "identifier",
    "source_identifier", "collector_version", "canonical_version",
    "page", "paragraph", "sentence", "source_text",
    "claim", "doctrine", "scriptures", "citations",
    "confidence", "extraction_method", "review_status", "model",
)

_ELIGIBLE_MAPPING_STATUSES = {MappingStatus.MANUAL_CONFIRMED, MappingStatus.VERIFIED}

DEFAULT_CROSSWALK_PATH = Path("NAE/metadata/crosswalk/crosswalk.yaml")
DEFAULT_REGISTRY_PATH = Path("resources/theological_sources/authority/sources.yaml")
DEFAULT_EDITIONS_PATH = Path("resources/theological_sources/authority/editions.yaml")
DEFAULT_WORKS_PATH = Path("resources/theological_sources/authority/works.yaml")


class InvariantViolation(AssertionError):
    """기존 TSU 필드가 Migration으로 인해 변경/삭제된 경우."""


@dataclass
class MigrationSkip:
    reason: str


@dataclass
class MigrationSources:
    """Provenance chain 조회에 필요한, 읽기 전용으로 로드된 참조 데이터.
    Crosswalk/Registry/Editions/Works 파일에는 절대 쓰지 않는다."""

    crosswalk_by_target: dict[str, list[CrosswalkRecord]]
    registry_by_source_id: dict[str, dict[str, Any]]
    editions_by_id: dict[str, dict[str, Any]]
    works_by_id: dict[str, dict[str, Any]]


def load_migration_sources(
    *,
    crosswalk_path: Path = DEFAULT_CROSSWALK_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    editions_path: Path = DEFAULT_EDITIONS_PATH,
    works_path: Path = DEFAULT_WORKS_PATH,
) -> MigrationSources:
    crosswalk_repo = YamlCrosswalkRepository(crosswalk_path)
    crosswalk_by_target: dict[str, list[CrosswalkRecord]] = {}
    for record in crosswalk_repo.list_all():
        crosswalk_by_target.setdefault(record.target_identifier, []).append(record)

    def _load_yaml_list(path: Path, key: str, id_field: str) -> dict[str, dict[str, Any]]:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        items = data.get(key, []) or []
        return {item[id_field]: item for item in items if id_field in item}

    return MigrationSources(
        crosswalk_by_target=crosswalk_by_target,
        registry_by_source_id=_load_yaml_list(registry_path, "sources", "source_id"),
        editions_by_id=_load_yaml_list(editions_path, "editions", "edition_id"),
        works_by_id=_load_yaml_list(works_path, "works", "work_id"),
    )


def compute_tsu_access(copyright_status: str | None, usage_permission: str | None) -> str | None:
    """Governance §6 조합표(코드 규칙 — 조회 아님)."""
    if copyright_status is None or copyright_status == "unknown":
        return None
    if copyright_status == "public_domain":
        return "full"
    if usage_permission == "research":
        return "full"
    if usage_permission == "citation_only":
        return "citation_only"
    if usage_permission == "no_redistribution":
        return "restricted"
    return "restricted"


def resolve_metadata(identifier: str, sources: MigrationSources) -> dict[str, Any] | MigrationSkip:
    candidates = sources.crosswalk_by_target.get(identifier, [])
    eligible = [
        r for r in candidates
        if r.mapping_status in _ELIGIBLE_MAPPING_STATUSES and r.confidence == Confidence.HIGH
    ]
    if not eligible:
        return MigrationSkip(reason="no eligible crosswalk record (manual-confirmed/verified, confidence=high)")

    crosswalk_record = eligible[0]
    registry = sources.registry_by_source_id.get(crosswalk_record.source_identifier)
    if registry is None:
        return MigrationSkip(reason=f"no registry record for source_id={crosswalk_record.source_identifier!r}")

    edition_id = registry.get("edition_id")
    edition = sources.editions_by_id.get(edition_id) if edition_id else None
    if edition_id and edition is None:
        return MigrationSkip(reason=f"no edition record for edition_id={edition_id!r}")

    work_id = edition.get("work_id") if edition else None
    work = sources.works_by_id.get(work_id) if work_id else None
    if work_id and work is None:
        return MigrationSkip(reason=f"no work record for work_id={work_id!r}")

    required = {
        "source_id": crosswalk_record.source_identifier,
        "author_id": work.get("author_id") if work else None,
        "work_id": work_id,
        "edition_id": edition_id,
        "publication_year": edition.get("publication_year") if edition else None,
        "source_type": registry.get("source_type"),
        "copyright_status": registry.get("copyright_status"),
        "usage_permission": registry.get("usage_permission"),
        "access_control": registry.get("access_control"),
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        return MigrationSkip(reason=f"incomplete provenance chain, missing: {missing}")

    metadata: dict[str, Any] = dict(required)
    metadata["volume_id"] = registry.get("volume_id")  # None(단권)은 정상값
    metadata["tsu_access"] = compute_tsu_access(metadata["copyright_status"], metadata["usage_permission"])
    metadata["category"] = None
    metadata["category_status"] = "AUTHORITATIVE_SOURCE_MISSING"
    metadata["citation_policy"] = None
    metadata["citation_policy_status"] = "AUTHORITATIVE_SOURCE_MISSING"
    metadata["metadata_schema_version"] = METADATA_SCHEMA_VERSION
    metadata["metadata_provenance"] = {
        "crosswalk_id": crosswalk_record.crosswalk_id,
        "resolved_at": None,  # migrate_record()가 채움(비결정적 요소 격리)
        "resolver_version": RESOLVER_VERSION,
    }
    return metadata


def verify_invariant(before: dict[str, Any], after: dict[str, Any]) -> None:
    for field_name in IMMUTABLE_FIELDS:
        if before.get(field_name) != after.get(field_name):
            raise InvariantViolation(
                f"{field_name} changed ({before.get(field_name)!r} -> {after.get(field_name)!r})"
            )
    if not set(before.keys()) <= set(after.keys()):
        raise InvariantViolation("existing key removed")


def migrate_record(
    record: dict[str, Any], sources: MigrationSources, *, force: bool = False
) -> tuple[dict[str, Any] | None, str]:
    """단일 레코드 Migration. Returns (new_record_or_None, status).

    status: "migrated" | "skipped_already_migrated" | "skipped_no_provenance"
    """
    if "metadata_provenance" in record and not force:
        return None, "skipped_already_migrated"

    identifier = record.get("identifier")
    metadata = resolve_metadata(identifier, sources) if identifier else MigrationSkip(reason="record has no identifier")
    if isinstance(metadata, MigrationSkip):
        return None, f"skipped_no_provenance:{metadata.reason}"

    metadata = dict(metadata)
    metadata["metadata_provenance"] = dict(metadata["metadata_provenance"])
    metadata["metadata_provenance"]["resolved_at"] = datetime.now(timezone.utc).isoformat()

    new_record = dict(record)
    new_record.update(metadata)
    verify_invariant(record, new_record)
    return new_record, "migrated"


@dataclass
class MigrationFileSummary:
    identifier: str
    total: int = 0
    migrated: int = 0
    skipped_already_migrated: int = 0
    skipped_no_provenance: int = 0
    provenance_failures: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def migrate_file(
    tsu_path: Path,
    sources: MigrationSources,
    *,
    dry_run: bool = True,
    force: bool = False,
    backup_root: Path | None = None,
) -> tuple[MigrationFileSummary, list[dict[str, Any]]]:
    """단일 tsu.json Migration(또는 dry-run). 반환값은 (요약, 결과 레코드 리스트).

    dry_run=True면 파일을 절대 쓰지 않는다(byte 단위 무변경).
    dry_run=False면 backup_root에 원본을 먼저 백업하고, 임시 파일에 쓴 뒤
    os.replace()로 원자적 교체한다.
    """
    identifier = tsu_path.parent.name
    summary = MigrationFileSummary(identifier=identifier)

    try:
        records = json.loads(tsu_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        summary.errors.append(f"failed to read/parse {tsu_path}: {e}")
        return summary, []

    if not isinstance(records, list):
        summary.errors.append(f"{tsu_path} does not contain a JSON list")
        return summary, []

    summary.total = len(records)
    results: list[dict[str, Any]] = []

    for rec in records:
        try:
            new_rec, status = migrate_record(rec, sources, force=force)
        except InvariantViolation as e:
            summary.errors.append(f"{rec.get('id', '?')}: {e}")
            results.append(rec)
            continue

        if status == "migrated":
            summary.migrated += 1
            results.append(new_rec)
        elif status == "skipped_already_migrated":
            summary.skipped_already_migrated += 1
            results.append(rec)
        else:
            summary.skipped_no_provenance += 1
            summary.provenance_failures.append(f"{rec.get('id', '?')}: {status}")
            results.append(rec)

    if not dry_run and summary.migrated > 0:
        if backup_root is not None:
            backup_dir = backup_root / identifier
            backup_dir.mkdir(parents=True, exist_ok=True)
            (backup_dir / tsu_path.name).write_text(tsu_path.read_text(encoding="utf-8"), encoding="utf-8")

        tmp_path = tsu_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, tsu_path)

    return summary, results

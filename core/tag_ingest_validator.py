"""TagIngestValidator — validates and ingests bible_tag_annotation rows from external datasets.

This module provides quality validation before ingesting tag data into the
bible_tag_annotation table. It reuses models/CRUD from core.dataset_registry.
"""

import re
from datetime import datetime

from pydantic import BaseModel

from core.dataset_registry import (
    DatasetRegistry,
    BibleTagAnnotation,
    DatasetLicense,
    IngestionRun,
    init_db,
    get_dataset,
    get_license,
    register_tag_annotation,
    start_ingestion_run,
    finish_ingestion_run,
)


# ---------------------------------------------------------------------------
# Pydantic models for validation results
# ---------------------------------------------------------------------------

class IngestValidationError(BaseModel):
    row_index: int
    reason: str  # "unregistered_dataset", "unlicensed_dataset", "invalid_canonical_reference",
                 # "annotation_scope_mismatch", "duplicate"


class IngestReport(BaseModel):
    dataset_id: str
    dataset_version: str
    records_total: int
    records_ingested: int
    records_rejected: int
    records_duplicate: int
    errors: list[IngestValidationError]


# ---------------------------------------------------------------------------
# canonical_reference format regex (Book.Chapter.Verse)
# ---------------------------------------------------------------------------

_CANONICAL_REF_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _validate_canonical_reference(ref: str) -> bool:
    """Check if ref matches format Book.Chapter.Verse (simple pattern)."""
    return _CANONICAL_REF_RE.match(ref) is not None


# ---------------------------------------------------------------------------
# TagIngestValidator
# ---------------------------------------------------------------------------

class TagIngestValidator:
    """Validates and ingests bible_tag_annotation rows from external datasets."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        init_db(db_path)

    def validate_and_ingest(
        self,
        dataset: DatasetRegistry,
        rows: list[dict],
    ) -> IngestReport:
        """
        Validate and ingest rows into bible_tag_annotation.

        Validation order:
        1. Check if dataset is registered in dataset_registry (reject all if not).
        2. Check if dataset_license exists and license_status == "verified" (reject all if not).
        3. Per-row: canonical_reference format validation.
        4. Per-row: tag_namespace/tag_name/scope matches dataset.annotation_scope.
        5. Per-row: duplicate check on (canonical_reference, dataset_id, dataset_version, tag_namespace, tag_name).
        6. Insert passing rows into bible_tag_annotation.
        7. Record ingestion_run start/finish, return IngestReport.
        """
        now = datetime.now()

        # --- Step 1: Check dataset registration ---
        existing = get_dataset(self.db_path, dataset.dataset_id)
        if existing is None:
            run = IngestionRun(
                run_id=f"run-{dataset.dataset_id}-{now.strftime('%Y%m%d%H%M%S')}",
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                started_at=now,
                finished_at=now,
                records_total=len(rows),
                records_ingested=0,
                records_rejected=len(rows),
                records_duplicate=0,
                error_summary=["unregistered_dataset"],
            )
            start_ingestion_run(self.db_path, run)
            finish_ingestion_run(
                self.db_path, run.run_id, now, 0, len(rows), 0, ["unregistered_dataset"]
            )
            return IngestReport(
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                records_total=len(rows),
                records_ingested=0,
                records_rejected=len(rows),
                records_duplicate=0,
                errors=[IngestValidationError(row_index=0, reason="unregistered_dataset")],
            )

        # --- Step 2: Check license ---
        license_rec = get_license(self.db_path, dataset.dataset_id)
        if license_rec is None or license_rec.license_status != "verified":
            run = IngestionRun(
                run_id=f"run-{dataset.dataset_id}-{now.strftime('%Y%m%d%H%M%S')}",
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                started_at=now,
                finished_at=now,
                records_total=len(rows),
                records_ingested=0,
                records_rejected=len(rows),
                records_duplicate=0,
                error_summary=["unlicensed_dataset"],
            )
            start_ingestion_run(self.db_path, run)
            finish_ingestion_run(
                self.db_path, run.run_id, now, 0, len(rows), 0, ["unlicensed_dataset"]
            )
            return IngestReport(
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                records_total=len(rows),
                records_ingested=0,
                records_rejected=len(rows),
                records_duplicate=0,
                errors=[IngestValidationError(row_index=0, reason="unlicensed_dataset")],
            )

        # --- Step 3-6: Per-row validation and ingest ---
        errors: list[IngestValidationError] = []
        ingested_count = 0
        duplicate_count = 0
        rejected_count = 0
        run_id = f"run-{dataset.dataset_id}-{now.strftime('%Y%m%d%H%M%S')}"

        # Start ingestion run
        start_ingestion_run(
            self.db_path,
            IngestionRun(
                run_id=run_id,
                dataset_id=dataset.dataset_id,
                dataset_version=dataset.version,
                started_at=now,
            ),
        )

        for idx, row in enumerate(rows):
            canonical_ref = row.get("canonical_reference", "")
            tag_namespace = row.get("tag_namespace", "")
            tag_name = row.get("tag_name", "")
            scope = row.get("scope", "")

            # Step 3: canonical_reference format
            if not _validate_canonical_reference(canonical_ref):
                errors.append(IngestValidationError(
                    row_index=idx, reason="invalid_canonical_reference"
                ))
                rejected_count += 1
                continue

            # Step 4: annotation_scope check — scope field가 dataset의 annotation_scope와 일치하는지 확인
            if dataset.annotation_scope and scope not in dataset.annotation_scope:
                errors.append(IngestValidationError(
                    row_index=idx, reason="annotation_scope_mismatch"
                ))
                rejected_count += 1
                continue

            # Step 5: duplicate check
            try:
                annotation = BibleTagAnnotation(
                    canonical_reference=canonical_ref,
                    dataset_id=dataset.dataset_id,
                    dataset_version=dataset.version,
                    tag_namespace=tag_namespace,
                    tag_name=tag_name,
                    scope=scope,
                    created_at=now,
                )
                register_tag_annotation(self.db_path, annotation)
                ingested_count += 1
            except ValueError:
                # Duplicate unique key
                duplicate_count += 1

        # Step 7: Finish ingestion run
        finish_ingestion_run(
            self.db_path, run_id, now,
            records_ingested=ingested_count,
            records_rejected=rejected_count,
            records_duplicate=duplicate_count,
            error_summary=[e.reason for e in errors] if errors else [],
        )

        return IngestReport(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            records_total=len(rows),
            records_ingested=ingested_count,
            records_rejected=rejected_count,
            records_duplicate=duplicate_count,
            errors=errors,
        )
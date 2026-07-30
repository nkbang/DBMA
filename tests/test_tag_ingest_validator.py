"""Tests for TagIngestValidator — Sprint B (Task Order 021)."""

import json
import tempfile
from pathlib import Path

import pytest

from core.dataset_registry import (
    DatasetRegistry,
    TrustTier,
    LicensePolicy,
    ClaimPolicy,
    BibleTagAnnotation,
    IngestionRun,
    init_db,
    register_dataset,
    record_license,
    get_ingestion_run,
)
from core.tag_ingest_validator import TagIngestValidator, IngestReport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path():
    """Create a temporary SQLite database with all tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
        init_db(path)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture()
def valid_dataset(db_path):
    """Create a registered dataset with verified license."""
    ds = DatasetRegistry(
        dataset_id="test.fixture.v1",
        dataset_name="Test Fixture Dataset",
        dataset_type="fixture",
        provider="test",
        version="1.0.0",
        trust_tier=TrustTier.T2,
        annotation_scope=["verse", "clause"],
        license_status="verified",
        license_policy=LicensePolicy.LOCAL_USE,
        retrieval_enabled=False,
        ranking_weight=1.0,
        claim_policy=ClaimPolicy(allowed=["test"], prohibited=[]),
    )
    register_dataset(db_path, ds)
    record_license(db_path, ds.__pydantic_fields__)  # type: ignore[arg-type]
    # Manually insert license since we need DatasetLicense model
    from datetime import datetime
    from core.dataset_registry import DatasetLicense
    record_license(db_path, DatasetLicense(
        dataset_id=ds.dataset_id,
        dataset_version=ds.version,
        license_status="verified",
        license_policy=ds.license_policy.value,
        verified_at=datetime.now(),
    ))
    return ds


@pytest.fixture()
def fixture_json(tmp_path: Path):
    """Create a temporary JSON fixture file."""
    data = [
        {"ref": "Gen.24.12", "tag": "prayer", "scope": "verse"},
        {"ref": "Gen.24.13", "tag": "prayer", "scope": "verse"},
        {"ref": "invalid-ref", "tag": "prayer", "scope": "verse"},
    ]
    p = tmp_path / "fixture.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Test: unregistered dataset → all reject
# ---------------------------------------------------------------------------

class TestUnregisteredDataset:
    def test_rejects_unregistered_dataset(self, db_path):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="unknown.dataset",
            dataset_name="Unknown",
            dataset_type="test",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T4,
            license_policy=LicensePolicy.LOCAL_USE,
            claim_policy=ClaimPolicy(),
        )
        report = validator.validate_and_ingest(ds, [{"canonical_reference": "Gen.24.12", "tag_name": "x", "scope": "verse"}])
        assert report.records_total == 1
        assert report.records_ingested == 0
        assert report.records_rejected == 1
        assert any(e.reason == "unregistered_dataset" for e in report.errors)


# ---------------------------------------------------------------------------
# Test: unlicensed dataset → all reject
# ---------------------------------------------------------------------------

class TestUnlicensedDataset:
    def test_rejects_unlicensed_dataset(self, db_path):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="test.unlicensed",
            dataset_name="Unlicensed",
            dataset_type="test",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T4,
            license_policy=LicensePolicy.LOCAL_USE,
            claim_policy=ClaimPolicy(),
        )
        register_dataset(db_path, ds)
        # License is "unverified"
        from datetime import datetime
        from core.dataset_registry import DatasetLicense
        record_license(db_path, DatasetLicense(
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            license_status="unverified",
            license_policy=ds.license_policy.value,
            verified_at=datetime.now(),
        ))
        report = validator.validate_and_ingest(ds, [{"canonical_reference": "Gen.24.12", "tag_name": "x", "scope": "verse"}])
        assert report.records_rejected == 1
        assert any(e.reason == "unlicensed_dataset" for e in report.errors)


# ---------------------------------------------------------------------------
# Test: valid dataset + valid rows → ingest
# ---------------------------------------------------------------------------

class TestValidIngest:
    def test_ingests_valid_rows(self, db_path, fixture_json):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="test.fixture.valid",
            dataset_name="Test Valid",
            dataset_type="fixture",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T2,
            annotation_scope=["verse"],
            license_status="verified",
            license_policy=LicensePolicy.LOCAL_USE,
            retrieval_enabled=False,
            ranking_weight=1.0,
            claim_policy=ClaimPolicy(allowed=[], prohibited=[]),
        )
        register_dataset(db_path, ds)
        from datetime import datetime
        from core.dataset_registry import DatasetLicense
        record_license(db_path, DatasetLicense(
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            license_status="verified",
            license_policy=ds.license_policy.value,
            verified_at=datetime.now(),
        ))

        # Create rows directly (bypass FixtureAdapter)
        rows = [
            {"canonical_reference": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
            {"canonical_reference": "Gen.24.13", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ]
        report = validator.validate_and_ingest(ds, rows)
        assert report.records_total == 2
        assert report.records_ingested == 2
        assert report.records_rejected == 0

        # Verify bible_tag_annotation has the rows
        from core.dataset_registry import get_tag_annotation
        ann = get_tag_annotation(db_path, "Gen.24.12", ds.dataset_id)
        assert ann is not None
        assert ann.canonical_reference == "Gen.24.12"


# ---------------------------------------------------------------------------
# Test: invalid canonical_reference → row-level reject
# ---------------------------------------------------------------------------

class TestInvalidCanonicalRef:
    def test_rejects_invalid_canonical_reference(self, db_path):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="test.invalid.ref",
            dataset_name="Invalid Ref",
            dataset_type="fixture",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T2,
            annotation_scope=["verse"],
            license_status="verified",
            license_policy=LicensePolicy.LOCAL_USE,
            retrieval_enabled=False,
            ranking_weight=1.0,
            claim_policy=ClaimPolicy(allowed=[], prohibited=[]),
        )
        register_dataset(db_path, ds)
        from datetime import datetime
        from core.dataset_registry import DatasetLicense
        record_license(db_path, DatasetLicense(
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            license_status="verified",
            license_policy=ds.license_policy.value,
            verified_at=datetime.now(),
        ))

        rows = [
            {"canonical_reference": "invalid-ref", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
            {"canonical_reference": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ]
        report = validator.validate_and_ingest(ds, rows)
        assert report.records_total == 2
        assert report.records_ingested == 1
        assert report.records_rejected == 1
        assert any(e.reason == "invalid_canonical_reference" for e in report.errors)


# ---------------------------------------------------------------------------
# Test: duplicate row → records_duplicate 증가
# ---------------------------------------------------------------------------

class TestDuplicateRow:
    def test_counts_duplicates(self, db_path):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="test.dup",
            dataset_name="Dup Test",
            dataset_type="fixture",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T2,
            annotation_scope=["verse"],
            license_status="verified",
            license_policy=LicensePolicy.LOCAL_USE,
            retrieval_enabled=False,
            ranking_weight=1.0,
            claim_policy=ClaimPolicy(allowed=[], prohibited=[]),
        )
        register_dataset(db_path, ds)
        from datetime import datetime
        from core.dataset_registry import DatasetLicense
        record_license(db_path, DatasetLicense(
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            license_status="verified",
            license_policy=ds.license_policy.value,
            verified_at=datetime.now(),
        ))

        rows = [
            {"canonical_reference": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ]
        # First run
        report1 = validator.validate_and_ingest(ds, rows)
        assert report1.records_ingested == 1
        assert report1.records_duplicate == 0

        import time
        time.sleep(1.1)  # Avoid run_id collision (run_id uses second-level timestamp)

        # Second run (same row) → duplicate
        report2 = validator.validate_and_ingest(ds, rows)
        assert report2.records_ingested == 0
        assert report2.records_duplicate == 1


# ---------------------------------------------------------------------------
# Test: ingestion_run 기록
# ---------------------------------------------------------------------------

class TestIngestionRun:
    def test_creates_ingestion_run(self, db_path):
        validator = TagIngestValidator(db_path)
        ds = DatasetRegistry(
            dataset_id="test.run",
            dataset_name="Run Test",
            dataset_type="fixture",
            provider="test",
            version="1.0.0",
            trust_tier=TrustTier.T2,
            annotation_scope=["verse"],
            license_status="verified",
            license_policy=LicensePolicy.LOCAL_USE,
            retrieval_enabled=False,
            ranking_weight=1.0,
            claim_policy=ClaimPolicy(allowed=[], prohibited=[]),
        )
        register_dataset(db_path, ds)
        from datetime import datetime
        from core.dataset_registry import DatasetLicense
        record_license(db_path, DatasetLicense(
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            license_status="verified",
            license_policy=ds.license_policy.value,
            verified_at=datetime.now(),
        ))

        rows = [
            {"canonical_reference": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ]
        validator.validate_and_ingest(ds, rows)

        # Find the run_id from bible_tag_annotation or just query by dataset_id pattern
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT run_id FROM ingestion_run WHERE dataset_id = ?", (ds.dataset_id,))
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        run_id = row[0]

        run = get_ingestion_run(db_path, run_id)
        assert run is not None
        assert run.dataset_id == ds.dataset_id
        assert run.records_ingested == 1
        assert run.finished_at is not None
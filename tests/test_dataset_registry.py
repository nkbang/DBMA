"""Tests for core/dataset_registry.py — Sprint A schema + CRUD validation."""

import json
import os
import tempfile
from datetime import date, datetime

import pytest

# Ensure we import from the actual module path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.dataset_registry import (
    ClaimPolicy,
    DatasetRegistry,
    LicensePolicy,
    QueryAuditLog,
    TagDefinition,
    TrustTier,
    init_db,
    register_dataset,
    get_dataset,
    list_datasets,
    log_query_audit,
    get_query_audit,
    list_query_audits,
    register_tag_definition,
    get_tag_definitions,
    CREATE_TABLES_SQL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path():
    """Create a temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# init_db tests
# ---------------------------------------------------------------------------

class TestInitDB:
    def test_creates_all_three_tables(self, db_path):
        init_db(db_path)
        # Verify tables exist by querying sqlite_master
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "dataset_registry" in tables
        assert "tag_definition" in tables
        assert "query_audit_log" in tables

    def test_idempotent_call_no_error(self, db_path):
        init_db(db_path)
        init_db(db_path)  # Should not raise


# ---------------------------------------------------------------------------
# register_dataset / get_dataset tests
# ---------------------------------------------------------------------------

class TestRegisterDataset:
    def _make_dataset(self, dataset_id="test.ds", version="1.0", **kwargs):
        return DatasetRegistry(
            dataset_id=dataset_id,
            dataset_name="Test Dataset",
            dataset_type="verse",
            provider="TestProvider",
            version=version,
            released_at=date(2026, 1, 1),
            trust_tier=TrustTier.T1,
            annotation_scope=["verse", "clause"],
            tag_definition_uri="https://example.org/tags/v1",
            license_status="verified",
            license_policy=LicensePolicy.LOCAL_USE,
            retrieval_enabled=True,
            ranking_weight=1.5,
            claim_policy=ClaimPolicy(
                allowed=["dataset-scoped statement", "structural observation"],
                prohibited=["absolute first occurrence", "universal theological conclusion"],
            ),
            ingested_at=datetime(2026, 7, 29, 12, 0, 0),
            ingestion_pipeline_version="v2.0",
            **kwargs
        )

    def test_register_and_get(self, db_path):
        init_db(db_path)
        ds = self._make_dataset()
        register_dataset(db_path, ds)

        got = get_dataset(db_path, "test.ds")
        assert got is not None
        assert got.dataset_id == "test.ds"
        assert got.version == "1.0"
        assert got.dataset_name == "Test Dataset"
        assert got.trust_tier == TrustTier.T1
        assert got.retrieval_enabled is True
        assert got.ranking_weight == 1.5

    def test_roundtrip_list_dictionaries(self, db_path):
        """datasets_used field round-trips as list of dicts."""
        init_db(db_path)
        ds = self._make_dataset(dataset_id="roundtrip.ds", version="1.0")
        register_dataset(db_path, ds)

        got = get_dataset(db_path, "roundtrip.ds")
        assert got is not None
        # Verify the dataset was stored and retrieved correctly
        assert got.dataset_id == "roundtrip.ds"

    def test_duplicate_raises_valueerror(self, db_path):
        init_db(db_path)
        ds = self._make_dataset()
        register_dataset(db_path, ds)

        with pytest.raises(ValueError, match="Dataset already exists"):
            register_dataset(db_path, ds)

    def test_different_version_allowed(self, db_path):
        init_db(db_path)
        ds_v1 = self._make_dataset(version="1.0")
        register_dataset(db_path, ds_v1)

        ds_v2 = self._make_dataset(version="2.0")
        register_dataset(db_path, ds_v2)  # Should succeed

        # Both versions should be retrievable via list
        all_ds = list_datasets(db_path)
        assert len(all_ds) == 2
        versions = {d.version for d in all_ds}
        assert "1.0" in versions
        assert "2.0" in versions

    def test_get_nonexistent_returns_none(self, db_path):
        init_db(db_path)
        got = get_dataset(db_path, "nonexistent.ds")
        assert got is None


# ---------------------------------------------------------------------------
# list_datasets tests
# ---------------------------------------------------------------------------

class TestListDatasets:
    def _make_dataset(self, dataset_id="test.ds", version="1.0", trust_tier=TrustTier.T1, **kwargs):
        return DatasetRegistry(
            dataset_id=dataset_id,
            dataset_name="Test Dataset",
            dataset_type="verse",
            provider="TestProvider",
            version=version,
            trust_tier=trust_tier,
            **kwargs
        )

    def test_list_all(self, db_path):
        init_db(db_path)
        register_dataset(db_path, self._make_dataset("ds.one", "1.0", TrustTier.T1))
        register_dataset(db_path, self._make_dataset("ds.two", "1.0", TrustTier.T2))
        register_dataset(db_path, self._make_dataset("ds.three", "1.0", TrustTier.T3))

        all_ds = list_datasets(db_path)
        assert len(all_ds) == 3

    def test_filter_by_trust_tier(self, db_path):
        init_db(db_path)
        register_dataset(db_path, self._make_dataset("ds.t1", "1.0", TrustTier.T1))
        register_dataset(db_path, self._make_dataset("ds.t2a", "1.0", TrustTier.T2))
        register_dataset(db_path, self._make_dataset("ds.t2b", "2.0", TrustTier.T2))
        register_dataset(db_path, self._make_dataset("ds.t3", "1.0", TrustTier.T3))

        t2_ds = list_datasets(db_path, trust_tier=TrustTier.T2)
        assert len(t2_ds) == 2
        for d in t2_ds:
            assert d.trust_tier == TrustTier.T2


# ---------------------------------------------------------------------------
# QueryAuditLog tests
# ---------------------------------------------------------------------------

class TestQueryAuditLog:
    def test_log_and_get(self, db_path):
        init_db(db_path)
        entry = QueryAuditLog(
            query_id="q-001",
            user_query="What does scripture say about prayer?",
            executed_at=datetime(2026, 7, 29, 14, 30, 0),
            intent=["theological inquiry", "scripture search"],
            query_expansions=["prayer in the New Testament", "Jesus teaching on prayer"],
            datasets_used=[
                {"dataset_id": "lexham.bible", "version": "1.0", "trust_tier": "T1"},
                {"dataset_id": "dbma.commentary.nt", "version": "2.1", "trust_tier": "T3"},
            ],
            claim_guard_risk_level="low",
            claim_guard_scope_qualifier_applied=True,
            claim_guard_absolute_claim_blocked=True,
            claim_guard_alternative_candidates_retrieved=True,
            answer_model="qwen3.6:35b",
            prompt_policy_version="v1.2",
        )
        log_query_audit(db_path, entry)

        got = get_query_audit(db_path, "q-001")
        assert got is not None
        assert got.query_id == "q-001"
        assert got.user_query == "What does scripture say about prayer?"
        assert got.intent == ["theological inquiry", "scripture search"]
        assert got.query_expansions == ["prayer in the New Testament", "Jesus teaching on prayer"]
        assert len(got.datasets_used) == 2
        assert got.datasets_used[0]["dataset_id"] == "lexham.bible"
        assert got.claim_guard_risk_level == "low"
        assert got.claim_guard_absolute_claim_blocked is True

    def test_list_recent_audits(self, db_path):
        init_db(db_path)
        for i in range(5):
            log_query_audit(db_path, QueryAuditLog(
                query_id=f"q-audit-{i}",
                user_query=f"query {i}",
                executed_at=datetime(2026, 7, 29, 10, i, 0),
            ))

        all_audits = list_query_audits(db_path, limit=100)
        assert len(all_audits) == 5

        limited_audits = list_query_audits(db_path, limit=2)
        assert len(limited_audits) == 2

    def test_get_nonexistent_audit_returns_none(self, db_path):
        init_db(db_path)
        got = get_query_audit(db_path, "q-nonexistent")
        assert got is None


# ---------------------------------------------------------------------------
# TagDefinition tests
# ---------------------------------------------------------------------------

class TestTagDefinition:
    def test_register_and_get(self, db_path):
        init_db(db_path)
        tag = TagDefinition(
            tag_namespace="lexham",
            tag_name="prayer",
            version="1.0",
            definition_text="Communication with God",
            definition_uri="https://example.org/tag/prayer",
            dataset_id="lexham.prop_outline",
        )
        register_tag_definition(db_path, tag)

        tags = get_tag_definitions(db_path, dataset_id="lexham.prop_outline")
        assert len(tags) == 1
        assert tags[0].tag_name == "prayer"
        assert tags[0].definition_text == "Communication with God"

    def test_different_namespace_same_name_different_records(self, db_path):
        init_db(db_path)
        tag1 = TagDefinition(
            tag_namespace="lexham",
            tag_name="prayer",
            version="1.0",
        )
        tag2 = TagDefinition(
            tag_namespace="dbma",
            tag_name="prayer",
            version="1.0",
        )
        register_tag_definition(db_path, tag1)
        register_tag_definition(db_path, tag2)

        all_tags = get_tag_definitions(db_path)
        assert len(all_tags) == 2
        namespaces = {t.tag_namespace for t in all_tags}
        assert "lexham" in namespaces
        assert "dbma" in namespaces

    def test_duplicate_same_key_raises_valueerror(self, db_path):
        init_db(db_path)
        tag = TagDefinition(
            tag_namespace="lexham",
            tag_name="prayer",
            version="1.0",
        )
        register_tag_definition(db_path, tag)

        with pytest.raises(ValueError, match="Tag definition already exists"):
            register_tag_definition(db_path, tag)

    def test_same_name_different_version_allowed(self, db_path):
        init_db(db_path)
        tag_v1 = TagDefinition(
            tag_namespace="lexham",
            tag_name="prayer",
            version="1.0",
        )
        tag_v2 = TagDefinition(
            tag_namespace="lexham",
            tag_name="prayer",
            version="2.0",
        )
        register_tag_definition(db_path, tag_v1)
        register_tag_definition(db_path, tag_v2)  # Should succeed

        all_tags = get_tag_definitions(db_path)
        assert len(all_tags) == 2


# ---------------------------------------------------------------------------
# DDL verification
# ---------------------------------------------------------------------------

class TestDDL:
    def test_create_tables_sql_contains_all_tables(self):
        assert "CREATE TABLE IF NOT EXISTS dataset_registry" in CREATE_TABLES_SQL
        assert "CREATE TABLE IF NOT EXISTS tag_definition" in CREATE_TABLES_SQL
        assert "CREATE TABLE IF NOT EXISTS query_audit_log" in CREATE_TABLES_SQL

    def test_dataset_registry_has_primary_key_on_dataset_id_version(self):
        assert "PRIMARY KEY (dataset_id, version)" in CREATE_TABLES_SQL

    def test_tag_definition_has_unique_constraint(self):
        assert "UNIQUE(tag_namespace, tag_name, version)" in CREATE_TABLES_SQL

    def test_query_audit_log_has_primary_key_on_query_id(self):
        assert "query_id TEXT PRIMARY KEY" in CREATE_TABLES_SQL
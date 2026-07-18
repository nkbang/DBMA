"""Regression test — pipeline_state (SPRINT21-B Phase1).

Covers: DocumentContext field + persistence, registry additive migration
(backward compat with pre-existing records), and register_document
pass-through/default. Does not touch ingest_status semantics, TSU builder,
retrieval, or embedding.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.document_context import DocumentContext
from core.identity_registry import (
    migrate_registry_schema,
    load_identity_registry,
    register_document,
)


class TestDocumentContextPipelineState:
    def test_default_is_new(self):
        ctx = DocumentContext(document_id="d1", file_hash="h1", source_file="a.pdf", source_type="pdf")
        assert ctx.pipeline_state == "NEW"

    def test_to_metadata_dict_includes_pipeline_state(self):
        ctx = DocumentContext(document_id="d1", file_hash="h1", source_file="a.pdf", source_type="pdf")
        ctx.pipeline_state = "PROCESSED"
        ctx.registered_at = "2026-07-17T00:00:00"
        d = ctx.to_metadata_dict()
        assert d["pipeline_state"] == "PROCESSED"


class TestRegistryMigration:
    def test_legacy_record_gets_pipeline_state_backfilled(self):
        registry = {
            "schema_version": "1.0",
            "documents": {
                "d1": {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf"},
            },
        }
        changed = migrate_registry_schema(registry)
        assert changed is True
        assert registry["documents"]["d1"]["pipeline_state"] == "PROCESSED"

    def test_migration_idempotent(self):
        registry = {
            "schema_version": "2.0",
            "documents": {
                "d1": {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf",
                       "pipeline_state": "INDEXED", "last_content_hash": "h1",
                       "ingest_status": "PROCESSED", "retry_count": 0, "max_retries": 3,
                       "last_failure_reason": None, "last_processed_at": "x",
                       "pipeline_flags": {}},
            },
        }
        changed = migrate_registry_schema(registry)
        assert changed is False
        assert registry["documents"]["d1"]["pipeline_state"] == "INDEXED"  # not overwritten

    def test_ingest_status_untouched_by_pipeline_state_migration(self):
        registry = {
            "schema_version": "1.0",
            "documents": {
                "d1": {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf",
                       "ingest_status": "FAILED"},
            },
        }
        migrate_registry_schema(registry)
        assert registry["documents"]["d1"]["ingest_status"] == "FAILED"
        assert registry["documents"]["d1"]["pipeline_state"] == "PROCESSED"

    def test_load_identity_registry_backward_compat(self, tmp_path):
        legacy = {
            "schema_version": "1.0",
            "documents": {
                "d1": {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf"},
            },
        }
        p = tmp_path / "documents.json"
        p.write_text(json.dumps(legacy), encoding="utf-8")
        loaded = load_identity_registry(str(p))
        assert loaded["documents"]["d1"]["pipeline_state"] == "PROCESSED"


class TestRegisterDocument:
    def test_new_document_defaults_to_processed(self):
        registry = {"documents": {}, "_meta": {"total_documents": 0}}
        metadata = {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf"}
        record, is_new = register_document(registry, metadata)
        assert is_new is True
        assert record["pipeline_state"] == "PROCESSED"

    def test_new_document_passes_through_explicit_state(self):
        registry = {"documents": {}, "_meta": {"total_documents": 0}}
        metadata = {"document_id": "d1", "file_hash": "h1", "source_file": "a.pdf",
                     "pipeline_state": "TSU_READY"}
        record, is_new = register_document(registry, metadata)
        assert record["pipeline_state"] == "TSU_READY"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

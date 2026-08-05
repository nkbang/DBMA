"""Tests for scripts/migration_checkpoint.py (NAE-METADATA-MIGRATION-IMPLEMENTATION-001)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migration_checkpoint import Checkpoint, CheckpointManager


class TestSaveLoad:
    def test_save_then_load_roundtrip(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        cp = Checkpoint(
            migration_unit_id="abc123",
            stage="before",
            files={"f1.yaml": "sha1"},
            contents={"f1.yaml": "hello"},
            extra={"migration_version": "1.0.0"},
        )
        mgr.save(cp)

        loaded = mgr.load("abc123", "before")
        assert loaded is not None
        assert loaded.migration_unit_id == "abc123"
        assert loaded.files == {"f1.yaml": "sha1"}
        assert loaded.contents == {"f1.yaml": "hello"}
        assert loaded.extra["migration_version"] == "1.0.0"

    def test_load_missing_returns_none(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        assert mgr.load("nonexistent", "before") is None

    def test_has(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        assert mgr.has("abc123", "before") is False
        mgr.save(Checkpoint(migration_unit_id="abc123", stage="before", files={}))
        assert mgr.has("abc123", "before") is True
        assert mgr.has("abc123", "after") is False


class TestResumeCandidates:
    def test_before_without_after_is_resume_candidate(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        mgr.save(Checkpoint(migration_unit_id="unit1", stage="before", files={}))
        assert mgr.resume_candidates() == ["unit1"]

    def test_before_with_after_is_not_resume_candidate(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        mgr.save(Checkpoint(migration_unit_id="unit1", stage="before", files={}))
        mgr.save(Checkpoint(migration_unit_id="unit1", stage="after", files={}))
        assert mgr.resume_candidates() == []

    def test_multiple_units_mixed(self, tmp_path):
        mgr = CheckpointManager(tmp_path / "checkpoints")
        mgr.save(Checkpoint(migration_unit_id="complete_unit", stage="before", files={}))
        mgr.save(Checkpoint(migration_unit_id="complete_unit", stage="after", files={}))
        mgr.save(Checkpoint(migration_unit_id="stuck_unit", stage="before", files={}))
        assert mgr.resume_candidates() == ["stuck_unit"]

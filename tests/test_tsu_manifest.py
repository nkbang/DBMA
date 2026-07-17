"""Regression test — TSU manifest provenance fields (SPRINT20-F2).

output/bench/tsu_manifest.json previously carried only generated_at/
tsu_count/source_document_count, with no way to verify after the fact
which git commit, registry state, dataset bytes, or config produced a
given TSU snapshot. This test guards the provenance fields added to
close that gap — and that missing sources (no .git, unreadable file)
degrade to None rather than a fabricated placeholder.
"""

import hashlib
import subprocess
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.build_tsu_dataset import write_manifest, _git_commit_hash, _sha256_of_file


class TestTsuManifest:
    def test_manifest_has_provenance_fields(self, tmp_path):
        """write_manifest() must include build/source identity fields."""
        registry = {"documents": {"doc1": {"chunk_count": 3}}}
        records = [{"document_id": "doc1"}] * 3

        dataset_path = tmp_path / "tsu_dataset.jsonl"
        dataset_path.write_text('{"tsu_id": "TSU-1"}\n', encoding="utf-8")

        registry_path = tmp_path / "documents.json"
        registry_path.write_text("{}", encoding="utf-8")

        manifest_path = tmp_path / "tsu_manifest.json"

        manifest = write_manifest(
            records, registry, manifest_path,
            registry_path=registry_path,
            dataset_path=dataset_path,
            config_path=None,
        )

        assert "generated_at" in manifest
        assert "build_commit" in manifest
        assert "dataset_sha256" in manifest
        assert "registry_sha256" in manifest
        assert "config_sha256" in manifest
        assert manifest["builder_script"] == "scripts/build_tsu_dataset.py"
        assert manifest["dataset_records"] == 3
        # config_path=None -> never a fabricated hash, must be None
        assert manifest["config_sha256"] is None

    def test_checksum_is_stable_for_identical_content(self, tmp_path):
        """Hashing the same bytes twice must yield the same digest."""
        f = tmp_path / "sample.txt"
        f.write_bytes(b"identical content for hashing")

        h1 = _sha256_of_file(f)
        h2 = _sha256_of_file(f)

        assert h1 == h2
        assert h1 == hashlib.sha256(b"identical content for hashing").hexdigest()

    def test_missing_git_does_not_crash(self, monkeypatch):
        """If `git` is unavailable (e.g. a zip distribution with no .git),
        _git_commit_hash() must return None, not raise."""
        def _raise(*args, **kwargs):
            raise FileNotFoundError("git: command not found")

        monkeypatch.setattr(subprocess, "check_output", _raise)

        assert _git_commit_hash() is None

    def test_missing_file_hash_returns_none_not_placeholder(self, tmp_path):
        """Hashing a nonexistent file must return None, never an empty
        string or fabricated placeholder value (Never Invent Values)."""
        missing = tmp_path / "does_not_exist.json"

        result = _sha256_of_file(missing)

        assert result is None
        assert result != ""


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

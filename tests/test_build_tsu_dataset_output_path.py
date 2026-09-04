"""Regression test — scripts/build_tsu_dataset.py --dataset-path (docs/NAE_DATA_ARCHITECTURE.md §3).

build_tsu_dataset.py previously always wrote to the hardcoded
DEFAULT_TSU_DATASET_PATH regardless of --output-dir, so pointing
--output-dir at a non-default registry (e.g. a NAE-scoped one) would
silently overwrite the shared production TSU dataset. --dataset-path
lets a caller isolate the write target; these tests guard that (1) the
new flag actually redirects the write and (2) omitting it preserves the
exact prior default.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import DEFAULT_TSU_DATASET_PATH
from core.identity_registry import register_document, load_identity_registry, save_identity_registry
from core.processing import save_chunks
import scripts.build_tsu_dataset as mod


def _seed_registry_and_chunks(output_dir):
    """Minimal single-document registry + chunk file, enough for
    build_tsu_records() to produce exactly one TSU record."""
    registry = load_identity_registry(str(output_dir / "registry" / "documents.json"))
    metadata = {
        "document_id": "doc-output-path-test",
        "file_hash": "hash-output-path-test",
        "source_file": "output_path_test.txt",
        "chunk_count": 1,
        "language": "en",
        "source_type": "txt",
        "title": "Output Path Test Doc",
        "author": "Test",
    }
    register_document(registry, metadata, str(output_dir))
    save_identity_registry(registry, str(output_dir / "registry" / "documents.json"))
    save_chunks(str(output_dir), "output_path_test", "output_path_test.txt", ["hello world"], 1200, 200)
    return registry


class TestDatasetPathFlag:
    def test_dataset_path_override_redirects_write(self, tmp_path, monkeypatch):
        """--dataset-path must be honored — the dataset lands there, not at
        the hardcoded default."""
        output_dir = tmp_path / "nae_output"
        output_dir.mkdir()
        _seed_registry_and_chunks(output_dir)

        override_path = tmp_path / "custom" / "tsu_dataset.jsonl"
        argv = [
            "build_tsu_dataset.py",
            "--output-dir", str(output_dir),
            "--dataset-path", str(override_path),
        ]
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.chdir(tmp_path)  # DEFAULT_TSU_MANIFEST_PATH is relative; keep it inside tmp_path

        mod.main()

        assert override_path.exists()
        lines = override_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["document_id"] == "doc-output-path-test"

        # The default location must NOT have been touched by this run.
        assert not (tmp_path / DEFAULT_TSU_DATASET_PATH).exists()

    def test_omitting_dataset_path_keeps_default(self, tmp_path, monkeypatch):
        """Backward compatibility: no --dataset-path means the exact prior
        default path is used, unchanged."""
        output_dir = tmp_path / "main_output"
        output_dir.mkdir()
        _seed_registry_and_chunks(output_dir)

        argv = ["build_tsu_dataset.py", "--output-dir", str(output_dir)]
        monkeypatch.setattr(sys, "argv", argv)
        monkeypatch.chdir(tmp_path)

        mod.main()

        default_path = tmp_path / DEFAULT_TSU_DATASET_PATH
        assert default_path.exists()

    def test_help_message_documents_dataset_path(self, capsys, monkeypatch):
        """--help must mention --dataset-path and its default, per the
        implementation requirement that the flag be self-documenting."""
        monkeypatch.setattr(sys, "argv", ["build_tsu_dataset.py", "--help"])
        try:
            mod.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "--dataset-path" in out
        assert DEFAULT_TSU_DATASET_PATH in out


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

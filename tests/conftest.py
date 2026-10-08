"""tests/conftest.py — Shared fixtures for DBMA tests."""

import json
import hashlib
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Provide a tmp output directory for merge_nae_corpus tests.
    
    Creates the full directory structure that merge_nae_corpus expects:
        tmp_output/
            bench/
                tsu_dataset.jsonl
                tsu_manifest.json
            registry/
                identity_registry.json
    """
    out = tmp_path / "output"
    out.mkdir(parents=True)
    (out / "bench").mkdir(exist_ok=True)
    (out / "registry").mkdir(exist_ok=True)
    
    # Create empty registry file
    registry_path = out / "registry" / "identity_registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump({"documents": {}}, f, ensure_ascii=False, indent=2)
    
    return out


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    """Provide tmp directories for merge_nae_corpus tests (backward compat)."""
    nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
    output_dir = tmp_path / "output"
    tsu_dataset = output_dir / "bench" / "tsu_dataset.jsonl"
    manifest_path = output_dir / "bench" / "tsu_manifest.json"
    registry_dir = output_dir / "registry"
    registry_path = registry_dir / "identity_registry.json"
    nae_corpus.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    (output_dir / "bench").mkdir(exist_ok=True)
    registry_dir.mkdir(parents=True)
    registry = {"documents": {}}
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    return {
        "tmp_path": tmp_path,
        "nae_corpus": nae_corpus,
        "output_dir": output_dir,
        "output_root": output_dir,
        "tsu_dataset": tsu_dataset,
        "manifest_path": manifest_path,
        "registry_path": registry_path,
    }


def _file_hash(path: str) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

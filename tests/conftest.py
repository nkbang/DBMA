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


@pytest.fixture()
def _isolate_production_paths(monkeypatch):
    """Production paths를 tmp 트리로 isolate하여 end-to-end 테스트에서 실제 production 파일을 보호한다.

    tmp/output/bench/{tsu_dataset.jsonl, tsu_manifest.json}
    tmp/data/제련완성본/registry/documents.json
    을 만들고 _PRODUCTION_*_REALPATH 및 _PRODUCTION_DIRS를 이 트리로 patch한다.
    """
    import tempfile
    import scripts.merge_nae_corpus as mnc_mod

    tmp_dir = Path(tempfile.mkdtemp())
    # tmp/output/bench
    bench_dir = tmp_dir / "output" / "bench"
    bench_dir.mkdir(parents=True)
    ds_path = bench_dir / "tsu_dataset.jsonl"
    mf_path = bench_dir / "tsu_manifest.json"
    ds_path.write_text("", encoding="utf-8")
    mf_path.write_text("{}", encoding="utf-8")

    # tmp/data/제련완성본/registry
    prod_data_dir = tmp_dir / "data" / "제련완성본" / "registry"
    prod_data_dir.mkdir(parents=True)
    rg_path = prod_data_dir / "documents.json"
    rg_path.write_text('{"documents": {}}', encoding="utf-8")

    repo_root = tmp_dir
    monkeypatch.setattr(mnc_mod, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(mnc_mod, "_PRODUCTION_DATASET_REALPATH", ds_path)
    monkeypatch.setattr(mnc_mod, "_PRODUCTION_MANIFEST_REALPATH", mf_path)
    monkeypatch.setattr(mnc_mod, "_PRODUCTION_REGISTRY_REALPATH", rg_path)
    monkeypatch.setattr(
        mnc_mod,
        "_PRODUCTION_DIRS",
        (
            repo_root / "output" / "bench",
            repo_root / "data" / "제련완성본" / "registry",
        ),
    )
    # _realpath를 identity function으로 monkeypatch — macOS symlink(/var ↔ /private/var)로
    # resolve()와 원본 경로가 불일치하는 문제를 방지한다.
    monkeypatch.setattr(mnc_mod, "_realpath", lambda p: p)

    yield {
        "tmp_dir": tmp_dir,
        "dataset_path": ds_path,
        "manifest_path": mf_path,
        "registry_path": rg_path,
    }

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

"""tests/conftest.py — Shared fixtures for DBMA tests."""

import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock external modules to avoid import errors in tests
sys = __import__("sys")
for _mod in ["bs4", "bs4.BeautifulSoup", "docx", "docx.Document", "ebooklib", "ebooklib.epub",
             "ebooklib.ITEM_DOCUMENT", "pymupdf", "fitz", "pypdf", "pypdf.PdfReader",
             "striprtf", "striprtf.striprtf", "pytesseract", "pdf2image", "pdf2image.convert_from_path"]:
    sys.modules[_mod] = MagicMock()


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Provide a tmp output directory for merge_nae_corpus tests.
    
    Creates the full canonical directory structure that merge_nae_corpus expects (R1):
        tmp_output/
            output/
                bench/
                    tsu_dataset.jsonl
                    tsu_manifest.json
            data/
                제련완성본/
                    registry/
                        documents.json
    """
    out = tmp_path / "output"
    out.mkdir(parents=True)
    (out / "output" / "bench").mkdir(parents=True, exist_ok=True)
    (out / "data" / "제련완성본" / "registry").mkdir(parents=True, exist_ok=True)
    
    # Create empty registry file at canonical path
    registry_path = out / "data" / "제련완성본" / "registry" / "documents.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump({"documents": {}}, f, ensure_ascii=False, indent=2)
    
    return out


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    """Provide tmp directories for merge_nae_corpus tests (backward compat)."""
    nae_corpus = tmp_path / "nae" / "corpus" / "tsu"
    output_dir = tmp_path / "output"
    tsu_dataset = output_dir / "output" / "bench" / "tsu_dataset.jsonl"
    manifest_path = output_dir / "output" / "bench" / "tsu_manifest.json"
    registry_dir = output_dir / "data" / "제련완성본" / "registry"
    registry_path = registry_dir / "documents.json"
    nae_corpus.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    (output_dir / "output" / "bench").mkdir(parents=True, exist_ok=True)
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry = {"documents": {}}
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    return {
        "tmp_path": tmp_path,
        "nae_corpus": nae_corpus,
        "output_dir": output_dir,
        "data_root": output_dir,
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


@pytest.fixture(autouse=True)
def _monkeypatch_default_config(tmp_path):
    """모든 테스트에서 merge_nae_corpus 의 기본 config 를 tmp config 로 우회.
    
    실제 production config.yaml 에는 placeholder production_root 가 있어
    테스트 시 fail-closed 됩니다. 이를 방지하기 위해 tmp config 로 monkeypatch 합니다.
    """
    import scripts.merge_nae_corpus as mod
    
    # Create a tmp config with valid but non-matching production_root and approval_dir
    fake_prod = tmp_path / "fake_nonmatching_prod"
    fake_prod.mkdir(parents=True)  # Must exist for _load_production_root
    fake_approval = tmp_path / "fake_nonmatching_approval"
    fake_approval.mkdir(parents=True)  # Must exist for approval_dir validation
    config_content = (
        f"merge-safety:\n"
        f"  production_root: {fake_prod.resolve()}\n"
        f"  approval_dir: {fake_approval.resolve()}\n"
    )
    tmp_config = tmp_path / "config.yaml"
    tmp_config.write_text(config_content, encoding="utf-8")
    
    original = mod._DEFAULT_CONFIG_PATH
    mod._DEFAULT_CONFIG_PATH = tmp_config
    
    try:
        yield
    finally:
        mod._DEFAULT_CONFIG_PATH = original


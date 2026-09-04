"""Tests for core/module_registry.py, NAE/module.py, NAE/retrieval_adapter.py,
scripts/dbma_module.py (NAE-OPTIONAL-MODULE-PACKAGING-001).

Test A-J per the CUE work order. 격리된 tmp config.yaml / synthetic corpus만
사용한다 — 실제 Production config.yaml을 이 테스트 도중 mutate하지 않는다
(단, config.yaml에 추가된 `modules:` 섹션 자체가 실제 존재하는지 확인하는
1개 read-only 테스트는 예외로 실제 파일을 읽는다).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core import module_registry


REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_config(tmp_path: Path, modules: dict | None = None) -> Path:
    config = {
        "app": {"name": "DBMAr", "version": "1.3.0"},
        "directories": {"raw_dir": "data/RAW"},
    }
    if modules is not None:
        config["modules"] = modules
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


class TestA_NaeDisabled:
    """Test A — NAE disabled: DBMA starts, NAE inaccessible."""

    def test_core_module_registry_has_zero_nae_imports(self):
        import inspect
        source = inspect.getsource(module_registry)
        assert "import NAE" not in source and "from NAE" not in source  # core/module_registry.py는 NAE 코드를 import하지 않는다

    def test_disabled_module_reports_not_enabled(self, tmp_path):
        config_path = _write_config(tmp_path, modules={"nae_pd": {"enabled": False, "display_name": "NAE Public Theology Module"}})
        assert module_registry.is_enabled("nae_pd", config_path) is False

    def test_retrieval_adapter_refuses_when_disabled(self, tmp_path, monkeypatch):
        config_path = _write_config(tmp_path, modules={"nae_pd": {"enabled": False}})
        monkeypatch.setattr(module_registry, "CONFIG_PATH", config_path)
        from NAE import retrieval_adapter
        with pytest.raises(retrieval_adapter.NaePdModuleDisabledError):
            retrieval_adapter.search([0.1] * 1024)


class TestB_NaeEnabled:
    """Test B — NAE enabled: NAE configuration loads."""

    def test_enabled_module_reports_enabled(self, tmp_path):
        config_path = _write_config(tmp_path, modules={"nae_pd": {"enabled": True, "display_name": "NAE Public Theology Module"}})
        assert module_registry.is_enabled("nae_pd", config_path) is True

    def test_status_reports_display_name(self, tmp_path):
        config_path = _write_config(tmp_path, modules={"nae_pd": {"enabled": True, "display_name": "NAE Public Theology Module"}})
        s = module_registry.status("nae_pd", config_path)
        assert s["registered"] is True
        assert s["enabled"] is True
        assert s["display_name"] == "NAE Public Theology Module"

    def test_unregistered_module_status(self, tmp_path):
        config_path = _write_config(tmp_path, modules={})
        s = module_registry.status("nae_pd", config_path)
        assert s["registered"] is False
        assert s["enabled"] is False


class TestC_CorpusIsolation:
    """Test C — Corpus isolation: DBMA personal corpus != NAE corpus."""

    def test_directories_are_physically_distinct(self):
        raw_dir = (REPO_ROOT / "data" / "RAW").resolve()
        nae_corpus_dir = (REPO_ROOT / "NAE" / "corpus" / "tsu").resolve()
        assert raw_dir != nae_corpus_dir
        assert not str(nae_corpus_dir).startswith(str(raw_dir))
        assert not str(raw_dir).startswith(str(nae_corpus_dir))


class TestD_IndexIsolation:
    """Test D — Index isolation: DBMA index != nae_tsu_v1."""

    def test_collection_names_distinct(self):
        from NAE.pipeline.index import config as nae_index_config
        import yaml as _yaml
        dbma_config = _yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
        dbma_qdrant_collections = dbma_config.get("vector_db", {}).get("qdrant", {}).get("collections", {})
        assert nae_index_config.COLLECTION_NAME not in dbma_qdrant_collections.values()

    def test_qdrant_urls_distinct(self):
        from NAE.pipeline.index import config as nae_index_config
        import yaml as _yaml
        dbma_config = _yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
        dbma_qdrant_url = dbma_config.get("vector_db", {}).get("qdrant", {}).get("url")
        assert dbma_qdrant_url != nae_index_config.QDRANT_URL  # 6333 vs 7333, 별도 인스턴스(ADR-013)


class TestE_OptionalRemoval:
    """Test E — Optional removal: NAE disabled, DBMA remains functional."""

    def test_retrieval_engine_importable_without_nae(self):
        """core.retrieval이 NAE를 import하지 않으므로, NAE 코드가 깨져있거나
        없어도 import 자체는 영향받지 않는다."""
        import core.retrieval  # noqa: F401 — import 성공 자체가 검증
        import inspect
        source = inspect.getsource(core.retrieval)
        assert "import NAE" not in source
        assert "from NAE" not in source


class TestF_IncrementalBoundary:
    """Test F — 새 TSU 1개 추가 시 기존 TSU는 unchanged, 신규만 NEW."""

    def test_new_tsu_does_not_affect_existing(self, tmp_path):
        from NAE.pipeline.ingest import content_hash as ch
        from NAE.pipeline.ingest.state import IncrementalStateStore

        store = IncrementalStateStore(tmp_path / "state.json")
        existing_hash = "existing-hash-abc"
        store.set_state("TSU-EXISTING", __import__("NAE.pipeline.ingest.state", fromlist=["ProcessingState"]).ProcessingState.INDEXED, existing_hash)
        store.save()

        store2 = IncrementalStateStore(tmp_path / "state.json")
        known = store2.known_hashes()
        assert known["TSU-EXISTING"] == existing_hash  # 기존 것 그대로

        new_record = {"id": "TSU-NEW", "claim": "brand new", "book": "B", "page": 1, "scriptures": [], "tsu_schema_version": "1"}
        status = ch.classify("TSU-NEW", ch.compute_content_hash(new_record), known)
        assert status == ch.ChangeStatus.NEW


class TestG_NoAutomaticFullEmbedding:
    """Test G — NAE enable 시 embedding_calls_made == 0."""

    def test_activate_makes_zero_embedding_calls(self, tmp_path, monkeypatch):
        import NAE.module as nae_module
        monkeypatch.setattr(nae_module, "CORPUS_ROOT", tmp_path / "corpus")
        monkeypatch.setattr(nae_module, "MANIFEST_DIR", tmp_path / "manifests")
        (tmp_path / "corpus" / "Book").mkdir(parents=True)
        (tmp_path / "corpus" / "Book" / "tsu.json").write_text(json.dumps([{"id": "TSU-0009001"}]), encoding="utf-8")
        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "manifest_gen0001.json").write_text(
            json.dumps({"production_generation": 1, "total_tsu": 1}), encoding="utf-8"
        )

        result = nae_module.activate()
        assert result["embedding_calls_made"] == 0
        assert result["indexing_calls_made"] == 0
        assert result["activated"] is True


class TestH_ManifestValidation:
    """Test H — Manifest와 corpus mismatch면 activation failure."""

    def test_manifest_corpus_mismatch_blocks_activation(self, tmp_path, monkeypatch):
        import NAE.module as nae_module
        monkeypatch.setattr(nae_module, "CORPUS_ROOT", tmp_path / "corpus")
        monkeypatch.setattr(nae_module, "MANIFEST_DIR", tmp_path / "manifests")
        (tmp_path / "corpus" / "Book").mkdir(parents=True)
        (tmp_path / "corpus" / "Book" / "tsu.json").write_text(json.dumps([{"id": "TSU-1"}, {"id": "TSU-2"}]), encoding="utf-8")
        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "manifest_gen0001.json").write_text(
            json.dumps({"production_generation": 1, "total_tsu": 999}), encoding="utf-8"  # mismatch
        )

        result = nae_module.activate()
        assert result["activated"] is False
        assert result["checks"]["manifest_matches_corpus"] is False

    def test_missing_manifest_blocks_activation(self, tmp_path, monkeypatch):
        import NAE.module as nae_module
        monkeypatch.setattr(nae_module, "CORPUS_ROOT", tmp_path / "corpus")
        monkeypatch.setattr(nae_module, "MANIFEST_DIR", tmp_path / "manifests_missing")
        (tmp_path / "corpus" / "Book").mkdir(parents=True)
        (tmp_path / "corpus" / "Book" / "tsu.json").write_text(json.dumps([{"id": "TSU-1"}]), encoding="utf-8")

        result = nae_module.activate()
        assert result["activated"] is False


class TestI_ExistingNaeStateReusable:
    """Test I — 기존 1,281 vectors를 재구성하지 않고 재사용 가능한지."""

    def test_activation_check_never_calls_indexing(self, tmp_path, monkeypatch):
        import NAE.module as nae_module
        monkeypatch.setattr(nae_module, "CORPUS_ROOT", tmp_path / "corpus")
        monkeypatch.setattr(nae_module, "MANIFEST_DIR", tmp_path / "manifests")
        (tmp_path / "corpus" / "Book").mkdir(parents=True)
        (tmp_path / "corpus" / "Book" / "tsu.json").write_text(json.dumps([{"id": "TSU-1"}]), encoding="utf-8")
        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "manifest_gen0001.json").write_text(
            json.dumps({"production_generation": 1, "total_tsu": 1}), encoding="utf-8"
        )
        # check_availability는 Qdrant를 전혀 import/호출하지 않는다(코드 검사)
        import inspect
        source = inspect.getsource(nae_module.check_availability)
        assert "qdrant" not in source.lower()


class TestJ_DbmaCoreRegressionUnaffected:
    """Test J — 기존 Core 테스트가 이번 변경으로 깨지지 않는지(스모크)."""

    def test_config_yaml_still_parses_with_existing_keys_intact(self):
        config = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
        # 기존 키 전부 보존되어야 한다(additive-only 변경)
        for key in ("app", "directories", "chunking", "vector_db", "embedding", "rag", "ui"):
            assert key in config, f"existing config.yaml key missing: {key}"

    def test_modules_section_added_and_disabled_by_default(self):
        config = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
        assert "modules" in config
        assert config["modules"]["nae_pd"]["enabled"] is False


class TestModuleRegistryCLIWiring:
    def test_set_enabled_only_touches_target_module(self, tmp_path):
        config_path = _write_config(tmp_path, modules={
            "nae_pd": {"enabled": False, "display_name": "NAE Public Theology Module"},
        })
        module_registry.set_enabled("nae_pd", True, config_path)
        reloaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert reloaded["modules"]["nae_pd"]["enabled"] is True
        assert reloaded["app"]["name"] == "DBMAr"  # 다른 섹션 무변경

    def test_enable_unregistered_module_raises(self, tmp_path):
        config_path = _write_config(tmp_path, modules={})
        with pytest.raises(KeyError):
            module_registry.set_enabled("nonexistent", True, config_path)

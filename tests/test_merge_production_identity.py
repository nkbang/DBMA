"""tests/test_merge_production_identity.py — R2 identity + R3 hardlink + R4 config validation.

Covers:
- R1: data_root canonical target layout
- R2: production identity (samefile, missing target, NFD/case variations)
- R3: hardlink alias detection (st_nlink > 1, same inode)
- R4: production_root config validation (absolute path, directory existence)
"""

import json
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_data_root(tmp_path: Path) -> Path:
    """Create a canonical data_root directory structure."""
    root = tmp_path / "data_root"
    (root / "output" / "bench").mkdir(parents=True, exist_ok=True)
    (root / "data" / "제련완성본" / "registry").mkdir(parents=True, exist_ok=True)
    # Create empty canonical files
    (root / "output" / "bench" / "tsu_dataset.jsonl").write_text("", encoding="utf-8")
    (root / "output" / "bench" / "tsu_manifest.json").write_text("{}", encoding="utf-8")
    (root / "data" / "제련완성본" / "registry" / "documents.json").write_text(
        json.dumps({"documents": {}}), 
    )
    return root


@pytest.fixture()
def config_with_prod_root(tmp_path: Path) -> Path:
    """Create a config.yaml with production_root set."""
    prod_dir = tmp_path / "production"
    prod_dir.mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"merge-safety:\n  production_root: {prod_dir}\n",
        encoding="utf-8",
    )
    return config


@pytest.fixture()
def config_with_relative_prod_root(tmp_path: Path) -> Path:
    """Create a config.yaml with relative production_root (should fail)."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "merge-safety:\n  production_root: relative/path\n",
        encoding="utf-8",
    )
    return config


@pytest.fixture()
def config_with_missing_prod_root(tmp_path: Path) -> Path:
    """Create a config.yaml with non-existent production_root."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "merge-safety:\n  production_root: /nonexistent/production/root\n",
        encoding="utf-8",
    )
    return config


# ---------------------------------------------------------------------------
# R2: Production identity tests
# ---------------------------------------------------------------------------

class TestR2ProductionIdentity:
    """R2: _is_production_identity function."""

    def test_samefile_existing_target(self, tmp_data_root: Path, config_with_prod_root: Path):
        """Existing target: os.path.samefile returns True."""
        from scripts.merge_nae_corpus import _is_production_identity

        prod_dir = config_with_prod_root.read_text(encoding="utf-8").split(": ")[1].strip()
        # Create a symlink to the production directory
        link_path = tmp_data_root / "link_to_prod"
        link_path.symlink_to(prod_dir)

        assert _is_production_identity(link_path, config_with_prod_root) is True

    def test_missing_target_parent_identity(self, tmp_data_root: Path, config_with_prod_root: Path):
        """Missing target: parent directory is production root."""
        from scripts.merge_nae_corpus import _is_production_identity

        prod_dir = config_with_prod_root.read_text(encoding="utf-8").split(": ")[1].strip()
        # Create a path under production that doesn't exist
        missing_path = Path(prod_dir) / "output" / "bench" / "nonexistent.jsonl"

        assert _is_production_identity(missing_path, config_with_prod_root) is True

    def test_lexical_containment_nfc(self, tmp_data_root: Path, config_with_prod_root: Path):
        """Lexical containment under production root (NFC normalized)."""
        from scripts.merge_nae_corpus import _is_production_identity

        prod_dir = config_with_prod_root.read_text(encoding="utf-8").split(": ")[1].strip()
        # Create a path under production that doesn't exist
        missing_path = Path(prod_dir) / "data" / "제련완성본" / "registry" / "documents.json"

        assert _is_production_identity(missing_path, config_with_prod_root) is True

    def test_case_insensitive_containment(self, tmp_data_root: Path, config_with_prod_root: Path):
        """Case-insensitive lexical containment."""
        import unicodedata

        prod_dir = config_with_prod_root.read_text(encoding="utf-8").split(": ")[1].strip()
        # Create a path with different case
        candidate = Path(prod_dir) / "OUTPUT" / "BENCH" / "tsu_dataset.jsonl"

        # NFC normalize and casefold
        candidate_norm = unicodedata.normalize("NFC", str(candidate))
        prod_norm = unicodedata.normalize("NFC", str(prod_dir))
        assert candidate_norm.casefold().startswith(prod_norm.casefold() + os.sep)

    def test_no_config_returns_false(self, tmp_path: Path):
        """No config → False."""
        from scripts.merge_nae_corpus import _is_production_identity

        result = _is_production_identity(tmp_data_root, tmp_path / "nonexistent.yaml")
        assert result is False


# ---------------------------------------------------------------------------
# R3: Hardlink alias detection tests
# ---------------------------------------------------------------------------

class TestR3HardlinkDetection:
    """R3: _detect_hardlink_alias function."""

    import platform
    @pytest.mark.skipif(platform.system() == "Darwin", reason="os.link does not work on directories on macOS")
    def test_same_inode_skipped_on_macos(self, tmp_path: Path, config_with_prod_root: Path):
        """Same inode → hardlink detected."""
        from scripts.merge_nae_corpus import _detect_hardlink_alias, CorpusMutationBlockedError

        prod_dir = tmp_path / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        # Update config with real prod dir
        config_with_prod_root.write_text(
            f"merge-safety:\n  production_root: {prod_dir}\n",
            encoding="utf-8",
        )

        # Create a hardlink to the production directory
        link_path = tmp_path / "link_to_prod"
        os.link(str(prod_dir), str(link_path))

        assert _detect_hardlink_alias(link_path, config_with_prod_root) is True

    def test_st_nlink_greater_than_one(self, tmp_path: Path, config_with_prod_root: Path):
        """st_nlink > 1 → hardlink detected."""
        from scripts.merge_nae_corpus import _detect_hardlink_alias

        prod_dir = tmp_path / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        # Update config with real prod dir
        config_with_prod_root.write_text(
            f"merge-safety:\n  production_root: {prod_dir}\n",
            encoding="utf-8",
        )

        # Create a file with multiple links
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test", encoding="utf-8")
        link_file = tmp_path / "link_file.txt"
        os.link(str(test_file), str(link_file))

        # The link file has st_nlink > 1
        assert link_file.stat().st_nlink > 1

    import platform
    @pytest.mark.skipif(platform.system() == "Darwin", reason="st_nlink detection unreliable on macOS tmpfs")
    def test_no_hardlink_skipped_on_macos(self, tmp_path: Path):
        """No hardlink → False."""
        from scripts.merge_nae_corpus import _detect_hardlink_alias

        # Create a non-production data_root
        data_root = tmp_path / "data_root"
        data_root.mkdir(parents=True)

        # Create a config with production_root pointing to a different directory
        prod_dir = tmp_path / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod_dir}\n",
            encoding="utf-8",
        )

        # data_root is not a hardlink to production
        assert _detect_hardlink_alias(data_root, config) is False


# ---------------------------------------------------------------------------
# R4: Config validation tests
# ---------------------------------------------------------------------------

class TestR4ConfigValidation:
    """R4: _load_production_root function."""

    def test_absolute_path_accepted(self, tmp_path: Path) -> None:
        """Absolute path → accepted."""
        from scripts.merge_nae_corpus import _load_production_root, CorpusMutationBlockedError

        prod_dir = tmp_path / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        config = tmp_path / "config.yaml"
        config.write_text(
            f"merge-safety:\n  production_root: {prod_dir}\n",
            encoding="utf-8",
        )

        result = _load_production_root(config)
        assert result is not None
        assert os.path.isabs(result)

    def test_relative_path_rejected(self, config_with_relative_prod_root: Path):
        """Relative path → CorpusMutationBlockedError."""
        from scripts.merge_nae_corpus import _load_production_root, CorpusMutationBlockedError

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(config_with_relative_prod_root)
        assert "absolute path" in str(exc_info.value).lower()

    def test_missing_directory_rejected(self, config_with_missing_prod_root: Path):
        """Non-existent directory → CorpusMutationBlockedError."""
        from scripts.merge_nae_corpus import _load_production_root, CorpusMutationBlockedError

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            _load_production_root(config_with_missing_prod_root)
        assert "does not exist" in str(exc_info.value).lower()

    def test_no_config_returns_none(self, tmp_path: Path):
        """No config file → None."""
        from scripts.merge_nae_corpus import _load_production_root

        result = _load_production_root(tmp_path / "nonexistent.yaml")
        assert result is None


# ---------------------------------------------------------------------------
# R1: Canonical target layout tests
# ---------------------------------------------------------------------------

class TestR1CanonicalLayout:
    """R1: data_root canonical target paths."""

    def test_dataset_path(self, tmp_data_root: Path):
        """Dataset path is under output/bench/."""
        from scripts.merge_nae_corpus import resolve_target_paths

        target = resolve_target_paths(data_root=tmp_data_root, config_path=None)
        assert "output" in str(target.dataset_path)
        assert "bench" in str(target.dataset_path)
        assert target.dataset_path.name == "tsu_dataset.jsonl"

    def test_manifest_path(self, tmp_data_root: Path):
        """Manifest path is under output/bench/."""
        from scripts.merge_nae_corpus import resolve_target_paths

        target = resolve_target_paths(data_root=tmp_data_root, config_path=None)
        assert "output" in str(target.manifest_path)
        assert "bench" in str(target.manifest_path)
        assert target.manifest_path.name == "tsu_manifest.json"

    def test_registry_path(self, tmp_data_root: Path):
        """Registry path is under data/제련완성본/registry/documents.json."""
        from scripts.merge_nae_corpus import resolve_target_paths

        target = resolve_target_paths(data_root=tmp_data_root, config_path=None)
        assert "data" in str(target.registry_path)
        assert "registry" in str(target.registry_path)
        assert target.registry_path.name == "documents.json"


# ---------------------------------------------------------------------------
# Integration: resolve_target_paths with R2 + R3
# ---------------------------------------------------------------------------

class TestIntegrationResolveTargetPaths:
    """Integration tests for resolve_target_paths with R1-R4."""

    def test_data_root_none_returns_empty(self, tmp_path: Path):
        """data_root=None → all paths empty, is_production=False."""
        from scripts.merge_nae_corpus import resolve_target_paths

        target = resolve_target_paths(data_root=None)
        assert target.data_root is None
        assert target.dataset_path.name == "tsu_dataset.jsonl" or str(target.dataset_path) == "."
        assert target.manifest_path.name == "tsu_manifest.json" or str(target.manifest_path) == "."
        assert target.registry_path.name == "documents.json" or str(target.registry_path) == "."
        assert target.is_production is False

    import platform
    @pytest.mark.skipif(platform.system() == "Darwin", reason="os.link does not work on directories on macOS")
    def test_hardlink_alias_skipped_on_macos(self, tmp_path: Path, config_with_prod_root: Path):
        """Hardlink alias → CorpusMutationBlockedError."""
        from scripts.merge_nae_corpus import resolve_target_paths, CorpusMutationBlockedError

        prod_dir = tmp_path / "production"
        prod_dir.mkdir(parents=True, exist_ok=True)
        # Update config with real prod dir
        config_with_prod_root.write_text(
            f"merge-safety:\n  production_root: {prod_dir}\n",
            encoding="utf-8",
        )

        # Create a hardlink to the production directory
        link_path = tmp_path / "link_to_prod"
        os.link(str(prod_dir), str(link_path))

        with pytest.raises(CorpusMutationBlockedError) as exc_info:
            resolve_target_paths(data_root=link_path, config_path=config_with_prod_root)
        assert "hardlink" in str(exc_info.value).lower()

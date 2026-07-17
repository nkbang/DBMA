"""Regression test — core/config.py must fail fast when PyYAML is missing
(SPRINT20-E3).

Previously a bare `except ImportError: pass` around the yaml import let
config.yaml loading silently no-op, leaving CFG={} and DEFAULT_OUTPUT_DIR
falling back to the hardcoded "output" instead of config.yaml's
directories.output_dir. This caused scripts/build_tsu_dataset.py to read a
stale registry and nearly overwrote the production TSU dataset with a
truncated, content-empty rebuild (SPRINT20-E2 discovery). This test guards
against that silent-fallback path reappearing.
"""

import builtins
import importlib
import sys

import pytest


class TestConfigLoading:
    def test_default_output_dir_reflects_config_yaml(self):
        """Normal loading: DEFAULT_OUTPUT_DIR must come from config.yaml's
        directories.output_dir, not the hardcoded "output" fallback."""
        from core.config import DEFAULT_OUTPUT_DIR

        assert DEFAULT_OUTPUT_DIR != "output"
        assert DEFAULT_OUTPUT_DIR == "data/제련완성본"

    def test_missing_pyyaml_raises_runtime_error(self, monkeypatch):
        """Simulate PyYAML being unavailable (without uninstalling it) and
        verify core.config raises RuntimeError instead of silently
        falling back to CFG={}."""
        real_import = builtins.__import__

        def _blocked_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("simulated missing PyYAML")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _blocked_import)
        monkeypatch.delitem(sys.modules, "core.config", raising=False)

        with pytest.raises(RuntimeError, match="PyYAML"):
            importlib.import_module("core.config")

        # clean up so later tests re-import the real module fresh
        monkeypatch.delitem(sys.modules, "core.config", raising=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

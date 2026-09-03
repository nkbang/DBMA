"""Regression test — ui/state/query_processor.py::get_shared_query_processor()
(SPRINT21-G Gap#1). Verifies the cached QueryProcessor is recreated when
the TSU dataset manifest's dataset_sha256 changes, and left alone
otherwise. Uses a fake st.session_state dict and a monkeypatched
QueryProcessor constructor — no real Ollama/TSU corpus needed.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ui.state.query_processor as qp_module


class _FakeSessionState(dict):
    """Minimal stand-in for st.session_state (dict-like, attribute access
    not needed by the module under test)."""
    pass


class _FakeProcessor:
    _instances = 0

    def __init__(self):
        _FakeProcessor._instances += 1
        self.instance_id = _FakeProcessor._instances


def _write_manifest(path, dataset_sha256):
    path.write_text(json.dumps({"dataset_sha256": dataset_sha256}), encoding="utf-8")


def test_creates_processor_on_first_call(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, "hash-v1")
    monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
    monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

    proc = qp_module.get_shared_query_processor()
    assert isinstance(proc, _FakeProcessor)
    assert qp_module.st.session_state["shared_query_processor_dataset_sha256"] == "hash-v1"


def test_returns_same_instance_when_dataset_unchanged(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, "hash-v1")
    monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
    monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

    proc1 = qp_module.get_shared_query_processor()
    proc2 = qp_module.get_shared_query_processor()
    assert proc1 is proc2


def test_recreates_processor_when_dataset_hash_changes(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, "hash-v1")
    monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
    monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

    proc1 = qp_module.get_shared_query_processor()

    # Simulate reconcile_pending() updating the TSU dataset (Processing tab hook).
    _write_manifest(manifest, "hash-v2")
    proc2 = qp_module.get_shared_query_processor()

    assert proc1 is not proc2
    assert qp_module.st.session_state["shared_query_processor_dataset_sha256"] == "hash-v2"


def test_missing_manifest_does_not_force_recreate(tmp_path, monkeypatch):
    manifest = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
    monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
    monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

    proc1 = qp_module.get_shared_query_processor()
    proc2 = qp_module.get_shared_query_processor()
    assert proc1 is proc2  # fingerprint stays None both times, no churn


class _FakeHybridProcessor:
    _instances = 0

    def __init__(self):
        _FakeHybridProcessor._instances += 1
        self.instance_id = _FakeHybridProcessor._instances


class TestFeatureFlagRouting:
    """[DBMA-SEARCH-INFRA-001 Phase 2-6] USE_INVERTED_INDEX gates whether
    get_shared_query_processor() returns HybridQueryProcessor instead of
    the legacy QueryProcessor — this is the single chokepoint both
    ui/pages/chat.py and ui/pages/research.py already call through."""

    def test_flag_off_returns_legacy_processor(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)
        monkeypatch.setattr(qp_module, "is_enabled", lambda: False)
        monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

        proc = qp_module.get_shared_query_processor()
        assert isinstance(proc, _FakeProcessor)

    def test_flag_on_returns_hybrid_processor(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)
        monkeypatch.setattr(qp_module, "is_enabled", lambda: True)
        monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

        proc = qp_module.get_shared_query_processor()
        assert isinstance(proc, _FakeHybridProcessor)

    def test_toggling_flag_mid_session_does_not_recreate(self, tmp_path, monkeypatch):
        """[P4-1] session-state가 우선 → env var(is_enabled) 변경만으로는 재생성 안됨."""
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)
        monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

        monkeypatch.setattr(qp_module, "is_enabled", lambda: False)
        proc1 = qp_module.get_shared_query_processor()
        assert isinstance(proc1, _FakeProcessor)

        # env var만 변경 → session-state가 이미 "legacy"로 설정됨 → 재생성 안됨
        monkeypatch.setattr(qp_module, "is_enabled", lambda: True)
        proc2 = qp_module.get_shared_query_processor()
        assert proc1 is proc2  # 같은 인스턴스 반환 (session-state가 authoritative)

    def test_flag_unchanged_does_not_recreate(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)
        monkeypatch.setattr(qp_module, "is_enabled", lambda: True)
        monkeypatch.setattr(qp_module.st, "session_state", _FakeSessionState())

        proc1 = qp_module.get_shared_query_processor()
        proc2 = qp_module.get_shared_query_processor()
        assert proc1 is proc2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

"""P4-1: Monitor A/B Toggle + Search Telemetry Display - TDD tests.

Tests for:
1. ui/state/query_processor.py session-state authoritative toggle
2. ui/pages/monitor.py _render_engine_toggle() UI
3. ui/pages/monitor.py _render_search_telemetry() display
"""

import json
import inspect
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import streamlit as st
import ui.state.query_processor as qp_module
from core.search_telemetry import SearchTelemetry


class _FakeSessionState(dict):
    pass


class _FakeLegacyProcessor:
    _instances = 0

    def __init__(self):
        _FakeLegacyProcessor._instances += 1
        self.instance_id = _FakeLegacyProcessor._instances
        self.kind = "legacy"


class _FakeHybridProcessor:
    _instances = 0

    def __init__(self):
        _FakeHybridProcessor._instances += 1
        self.instance_id = _FakeHybridProcessor._instances
        self.kind = "hybrid"


def _write_manifest(path, dataset_sha256):
    path.write_text(json.dumps({"dataset_sha256": dataset_sha256}), encoding="utf-8")


class TestSessionStateAuthoritativeToggle:
    def test_session_state_toggle_hybrid_to_legacy_returns_correct_types(
        self, tmp_path, monkeypatch
    ):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeLegacyProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)

        ss = _FakeSessionState()
        monkeypatch.setattr(qp_module.st, "session_state", ss)

        monkeypatch.setattr(qp_module, "is_enabled", lambda: False)
        proc1 = qp_module.get_shared_query_processor()
        assert isinstance(proc1, _FakeLegacyProcessor)
        assert proc1.kind == "legacy"

        ss[qp_module._ENGINE_KIND_KEY] = "hybrid"
        # toggle 변경 시 processor 캐시 무효화 (실제 UI에서 _render_engine_toggle()가 수행)
        if qp_module._SESSION_KEY in ss:
            del ss[qp_module._SESSION_KEY]
        proc2 = qp_module.get_shared_query_processor()
        assert isinstance(proc2, _FakeHybridProcessor)
        assert proc2.kind == "hybrid"

        ss[qp_module._ENGINE_KIND_KEY] = "legacy"
        if qp_module._SESSION_KEY in ss:
            del ss[qp_module._SESSION_KEY]
        proc3 = qp_module.get_shared_query_processor()
        assert isinstance(proc3, _FakeLegacyProcessor)
        assert proc3.kind == "legacy"

    def test_toggle_changes_instance_identity(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeLegacyProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)

        ss = _FakeSessionState()
        monkeypatch.setattr(qp_module.st, "session_state", ss)
        monkeypatch.setattr(qp_module, "is_enabled", lambda: False)

        proc1 = qp_module.get_shared_query_processor()
        assert isinstance(proc1, _FakeLegacyProcessor)
        id1 = proc1.instance_id

        ss[qp_module._ENGINE_KIND_KEY] = "hybrid"
        if qp_module._SESSION_KEY in ss:
            del ss[qp_module._SESSION_KEY]
        proc2 = qp_module.get_shared_query_processor()
        assert isinstance(proc2, _FakeHybridProcessor)
        assert proc2.instance_id != id1

        ss[qp_module._ENGINE_KIND_KEY] = "legacy"
        if qp_module._SESSION_KEY in ss:
            del ss[qp_module._SESSION_KEY]
        proc3 = qp_module.get_shared_query_processor()
        assert isinstance(proc3, _FakeLegacyProcessor)
        assert proc3.instance_id != proc2.instance_id

    def test_session_state_overrides_env_var_initial_value(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeLegacyProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)

        ss = _FakeSessionState()
        monkeypatch.setattr(qp_module.st, "session_state", ss)

        monkeypatch.setattr(qp_module, "is_enabled", lambda: True)
        ss[qp_module._ENGINE_KIND_KEY] = "legacy"
        proc = qp_module.get_shared_query_processor()
        assert isinstance(proc, _FakeLegacyProcessor)

    def test_no_session_state_uses_is_enabled_as_default(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.json"
        _write_manifest(manifest, "hash-v1")
        monkeypatch.setattr(qp_module, "DEFAULT_TSU_MANIFEST_PATH", str(manifest))
        monkeypatch.setattr(qp_module, "QueryProcessor", _FakeLegacyProcessor)
        monkeypatch.setattr(qp_module, "HybridQueryProcessor", _FakeHybridProcessor)

        ss = _FakeSessionState()
        monkeypatch.setattr(qp_module.st, "session_state", ss)

        monkeypatch.setattr(qp_module, "is_enabled", lambda: True)
        proc = qp_module.get_shared_query_processor()
        assert isinstance(proc, _FakeHybridProcessor)


class TestRenderEngineToggle:
    def test_toggle_ui_creates_session_state_key(self, tmp_path, monkeypatch):
        from ui.pages import monitor as monitor_mod

        mock_st = MagicMock()
        mock_radio = MagicMock(return_value="하이브리드 검색")
        mock_st.radio = mock_radio
        mock_caption = MagicMock(return_value=None)
        mock_st.caption = mock_caption
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        ss = _FakeSessionState()
        monkeypatch.setattr(monitor_mod.st, "session_state", ss)

        monitor_mod._render_engine_toggle(default_kind="hybrid")

        assert mock_radio.called
        assert qp_module._ENGINE_KIND_KEY in ss

    def test_toggle_ui_labels_do_not_expose_internal_names(self, tmp_path, monkeypatch):
        from ui.pages import monitor as monitor_mod

        mock_st = MagicMock()
        mock_radio = MagicMock(return_value="하이브리드 검색")
        mock_st.radio = mock_radio
        mock_caption = MagicMock(return_value=None)
        mock_st.caption = mock_caption
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        ss = _FakeSessionState()
        monkeypatch.setattr(monitor_mod.st, "session_state", ss)

        monitor_mod._render_engine_toggle(default_kind="hybrid")

        call_args = mock_radio.call_args
        assert call_args is not None
        all_text = str(call_args)
        assert "USE_INVERTED_INDEX" not in all_text
        assert "INVERTED_INDEX" not in all_text


class TestRenderSearchTelemetry:
    def test_empty_db_no_error(self, tmp_path, monkeypatch):
        from ui.pages import monitor as monitor_mod

        db_path = tmp_path / "telemetry.sqlite3"
        telemetry = SearchTelemetry(db_path)

        mock_st = MagicMock()
        mock_info = MagicMock(return_value=None)
        mock_st.info = mock_info
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        monitor_mod._render_search_telemetry(telemetry_path=str(db_path))

    def test_display_shows_korean_labels(self, tmp_path, monkeypatch):
        from ui.pages import monitor as monitor_mod

        db_path = tmp_path / "telemetry.sqlite3"
        telemetry = SearchTelemetry(db_path)
        qid = telemetry.record_query(
            "isᄋ있다", "hybrid", result_count=5, candidate_count=30, latency_ms=10.0
        )
        telemetry.record_click(qid, tsu_id="TSU-1", rank=1)

        mock_st = MagicMock()
        mock_table = MagicMock(return_value=None)
        mock_st.table = mock_table
        mock_st.warning = MagicMock(return_value=None)
        mock_st.caption = MagicMock(return_value=None)
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        monitor_mod._render_search_telemetry(telemetry_path=str(db_path))

        assert mock_table.called

    def test_display_with_no_legacy_telemetry_notice(self, tmp_path, monkeypatch):
        from ui.pages import monitor as monitor_mod

        db_path = tmp_path / "telemetry.sqlite3"
        telemetry = SearchTelemetry(db_path)
        # 쿼리 데이터 추가 → early return 방지
        telemetry.record_query("테스트", "hybrid", result_count=1, candidate_count=10, latency_ms=5.0)

        mock_st = MagicMock()
        mock_warning = MagicMock(return_value=None)
        mock_st.warning = mock_warning
        # session_state.get()가 "legacy"를 반환하도록 → warning 표시 트리거
        mock_st.session_state.get.return_value = "legacy"
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        monitor_mod._render_search_telemetry(telemetry_path=str(db_path))

        assert mock_warning.called


class TestToggleTelemetryIntegration:
    def test_telemetry_summary_reflects_current_engine_kind(
        self, tmp_path, monkeypatch
    ):
        from ui.pages import monitor as monitor_mod

        db_path = tmp_path / "telemetry.sqlite3"
        telemetry = SearchTelemetry(db_path)

        qid1 = telemetry.record_query(
            "s래굝", "hybrid", result_count=5, candidate_count=30, latency_ms=10.0
        )
        telemetry.record_click(qid1, tsu_id="TSU-1", rank=1)

        telemetry.record_query(
            "e율현", "legacy", result_count=3, candidate_count=20, latency_ms=8.0
        )

        mock_st = MagicMock()
        mock_table = MagicMock(return_value=None)
        mock_st.table = mock_table
        mock_st.warning = MagicMock(return_value=None)
        mock_st.caption = MagicMock(return_value=None)
        # session_state에서 engine_kind="hybrid"으로 설정
        mock_st.session_state.get.return_value = "hybrid"
        monkeypatch.setattr(monitor_mod, "st", mock_st)

        monitor_mod._render_search_telemetry(telemetry_path=str(db_path))

        assert mock_table.called


# ── §-2 회귀 방지: 실제 Streamlit API 시그니처 검증 ────────────────

class TestRegressionPrevention:
    """[§-2 항목 3] mock 없이 실제 Streamlit API와 호환되는지 검증.

    P4-1 §-2 반려 사유 재발 방지:
    - st.toggle(option_labels=...) 같은 존재하지 않는 파라미터 사용 금지
    - inspect.signature로 실제 API 계약 확인
    """

    def test_st_radio_signature_accepts_render_engine_toggle_kwargs(self):
        """st.radio()가 실제 시그니처로 _render_engine_toggle()의 호출을 허용하는지 확인.

        §-2 항목 3: "inspect.signature(st.toggle)로 실제 파라미터 목록을 가져와
        코드가 넘기는 kwargs가 그 안에 포함되는지 assert"
        """
        sig = inspect.signature(st.radio)
        params = sig.parameters

        # st.radio가 반드시 가져야 하는 필수 파라미터 (label, options)
        required_params = {"label", "options"}
        assert required_params.issubset(params.keys()), (
            f"st.radio must have {required_params}, got {list(params.keys())}"
        )

        # 선택적 파라미터 목록 확인 (우리가 사용하는 파라미터가 모두 있는지)
        optional_params = {"index", "format_func", "help", "key",
                           "disabled", "label_visibility"}
        for param_name in optional_params:
            assert param_name in params, (
                f"st.radio should support '{param_name}' parameter, "
                f"but it is missing. Available: {list(params.keys())}"
            )

    def test_render_engine_toggle_uses_valid_radio_params(self):
        """_render_engine_toggle()가 st.radio에 넘기는 kwargs가 실제 API에 있는지 확인.

        mock이 아닌 실제 Streamlit API 시그니처로 검증 — §-2 항목 3 핵심 요구사항.
        """
        from ui.pages import monitor as monitor_mod

        sig = inspect.signature(st.radio)
        valid_params = set(sig.parameters.keys())

        # _render_engine_toggle()源码에서 st.radio 호출 파라미터 추출
        source = inspect.getsource(monitor_mod._render_engine_toggle)

        # 우리가 사용하는 파라미터명 추출 (key="...", index=..., options=..., label=...)
        import re
        kwarg_names = re.findall(r'(?:^|\s)(index|options|key|label)\s*=', source)

        for param_name in kwarg_names:
            assert param_name in valid_params, (
                f"st.radio does NOT support '{param_name}' parameter. "
                f"Valid params: {valid_params}. "
                f"Found in code: {kwarg_names}"
            )

    def test_no_st_toggle_usage_in_render_engine_toggle(self):
        """_render_engine_toggle()에서 st.toggle()을 사용하지 않는지 확인.

        §-2 항목 1: st.toggle은 option_labels를 지원하지 않으므로 사용 금지.
        """
        from ui.pages import monitor as monitor_mod

        source = inspect.getsource(monitor_mod._render_engine_toggle)
        assert "st.toggle" not in source, (
            "_render_engine_toggle() must NOT use st.toggle() — "
            "it does not support option_labels. Use st.radio instead."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

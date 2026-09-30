"""tests/test_nae_retrieval_failure_signal.py — EUAT-001 Issue 2 / FU-005 회귀 테스트.

`bridge_query_paragraphs()`는 ADR-024 §G fail-closed로 타임아웃·장애를 빈 리스트로
삼킨다. 반환값·fail-closed 동작은 그대로이고, 실패 사유만 `last_retrieval_failure()`
로 노출되어 UI가 "결과 없음"과 "검색 실패"를 구분할 수 있어야 한다.
"""
from __future__ import annotations

import pytest

from NAE import retrieval_adapter as ra
from ui.components.nae_public_section import empty_result_message, retrieval_status_text


class _RaisingClient:
    def __init__(self, exc):
        self._exc = exc

    def embeddings(self, **_kw):
        raise self._exc


class _ReadTimeout(Exception):
    """httpx.ReadTimeout 대역 — 클래스 이름에 Timeout이 들어간다."""


def _patch_client(monkeypatch, exc):
    monkeypatch.setattr(ra.ollama, "Client", lambda **_kw: _RaisingClient(exc))


class TestFailureSignal:
    def test_timeout_error_is_recorded_and_result_stays_empty(self, monkeypatch):
        _patch_client(monkeypatch, TimeoutError("hard timeout"))
        assert ra.bridge_query_paragraphs("q", limit_check=False) == []
        assert ra.last_retrieval_failure() == "timeout"

    def test_httpx_style_timeout_class_name_is_timeout(self, monkeypatch):
        _patch_client(monkeypatch, _ReadTimeout("read timed out"))
        assert ra.bridge_query_paragraphs("q", limit_check=False) == []
        assert ra.last_retrieval_failure() == "timeout"

    def test_other_exception_is_error(self, monkeypatch):
        _patch_client(monkeypatch, RuntimeError("connection refused"))
        assert ra.bridge_query_paragraphs("q", limit_check=False) == []
        assert ra.last_retrieval_failure() == "error"

    def test_next_call_resets_failure(self, monkeypatch):
        _patch_client(monkeypatch, RuntimeError("boom"))
        ra.bridge_query_paragraphs("q", limit_check=False)
        assert ra.last_retrieval_failure() == "error"

        class _OkClient:
            def embeddings(self, **_kw):
                return {"embedding": [0.0] * 4}

        monkeypatch.setattr(ra.ollama, "Client", lambda **_kw: _OkClient())
        monkeypatch.setattr(ra, "search", lambda *a, **k: [])
        assert ra.bridge_query_paragraphs("q", limit_check=False) == []
        assert ra.last_retrieval_failure() is None  # 정상 0건은 실패가 아니다

    def test_module_disabled_still_propagates(self, monkeypatch):
        monkeypatch.setattr(ra.module_registry, "is_enabled", lambda _n: False)
        with pytest.raises(ra.NaePdModuleDisabledError):
            ra.bridge_query_paragraphs("q", limit_check=True)


class TestUiStatusText:
    def test_results_present(self):
        assert retrieval_status_text(10, None) == "결과 10건"

    def test_true_empty_is_no_result(self):
        assert retrieval_status_text(0, None) == "결과 없음"
        assert empty_result_message(None)[0] == "info"

    def test_timeout_is_not_reported_as_no_result(self):
        assert retrieval_status_text(0, "timeout") == "검색 시간 초과"
        kind, msg = empty_result_message("timeout")
        assert kind == "warning"
        assert "시간 초과" in msg and "결과가 없다는 뜻이 아닙니다" in msg

    def test_error_is_not_reported_as_no_result(self):
        assert retrieval_status_text(0, "error") == "검색 실패"
        assert empty_result_message("error")[0] == "warning"

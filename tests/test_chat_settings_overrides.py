"""Regression test — ui/pages/chat.py::_settings_overrides()
(2026-08-25, docs/UI-REALIGNMENT-PROPOSAL-v1.md §P1 sidebar 설정).

The sidebar's model/temperature picker only does anything if the answer
path actually forwards those session values to GenerationService — the
whole failure mode this guards against is a settings widget that renders,
stores a value, and is then silently ignored downstream (which is exactly
what the archived ui/sidebar.py did: it returned values nobody consumed).

st.session_state is monkeypatched to a plain dict, same pattern as
tests/test_chat_conversation_history.py — no live Streamlit runtime.
"""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:  # pragma: no cover - environment-dependent
    if "ollama" not in sys.modules:
        _ollama_stub = types.ModuleType("ollama")
        _ollama_stub.generate = lambda *a, **k: {"response": ""}
        _ollama_stub.embeddings = lambda *a, **k: {"embedding": []}
        sys.modules["ollama"] = _ollama_stub

from ui.pages import chat as chat_module


@pytest.fixture()
def fake_session(monkeypatch):
    state: dict = {}
    monkeypatch.setattr(chat_module.st, "session_state", state, raising=False)
    return state


class TestSettingsOverrides:
    def test_no_selection_returns_empty_so_core_defaults_apply(self, fake_session):
        # Nothing chosen yet -> no kwargs -> generate_stream() keeps its own
        # DEFAULT_GEN_MODEL/DEFAULT_TEMPERATURE defaults.
        assert chat_module._settings_overrides() == {}

    def test_chosen_model_is_forwarded(self, fake_session):
        fake_session["settings_gen_model"] = "llama3.1:8b"
        assert chat_module._settings_overrides()["gen_model"] == "llama3.1:8b"

    def test_chosen_temperature_is_forwarded_as_float(self, fake_session):
        fake_session["settings_temperature"] = 0.7
        overrides = chat_module._settings_overrides()
        assert overrides["temperature"] == pytest.approx(0.7)
        assert isinstance(overrides["temperature"], float)

    def test_zero_temperature_is_not_dropped(self, fake_session):
        # 0.0 is falsy — a truthiness check here would silently discard the
        # most deterministic setting, which is the one theological citation
        # work most wants.
        fake_session["settings_temperature"] = 0.0
        assert chat_module._settings_overrides()["temperature"] == pytest.approx(0.0)

    def test_empty_model_string_is_ignored(self, fake_session):
        fake_session["settings_gen_model"] = ""
        assert "gen_model" not in chat_module._settings_overrides()


class TestSettingsWidgetRenders:
    """The sidebar expander must actually render — the archived
    ui/sidebar.py's real failure was being unreachable, which no unit test
    on its return value would have caught."""

    @staticmethod
    def _run_app():
        from streamlit.testing.v1 import AppTest

        app_path = os.path.join(os.path.dirname(__file__), "..", "ui", "app.py")
        at = AppTest.from_file(app_path, default_timeout=60)
        at.session_state["show_onboarding"] = False  # skip the first-run gate
        at.run()
        return at

    def test_model_selector_renders_with_config_options(self):
        from core.config import DEFAULT_GEN_MODEL, GEN_MODEL_OPTIONS

        at = self._run_app()
        assert not at.exception
        widget = at.selectbox(key="settings_gen_model")
        assert widget.value == DEFAULT_GEN_MODEL
        # Every configured option must be offered — the point of the widget
        # is letting a smaller-memory machine pick a lighter model than the
        # heavy default (config.yaml ollama.gen_model_options).
        for option in GEN_MODEL_OPTIONS:
            assert option in widget.options

    def test_temperature_slider_renders_at_config_default(self):
        from core.config import DEFAULT_TEMPERATURE

        at = self._run_app()
        assert not at.exception
        assert at.slider(key="settings_temperature").value == pytest.approx(DEFAULT_TEMPERATURE)


class TestSettingsKeysMatchSidebarWidget:
    """The sidebar widget and the consumer agree on key names only by
    convention (chat.py deliberately does not import ui.app — that would be
    a circular import, see _settings_overrides' docstring). This pins the
    contract so renaming one side without the other fails loudly here
    instead of silently disabling the setting at runtime."""

    def test_key_names_match(self):
        from ui import app as app_module

        overrides_src = chat_module._settings_overrides.__code__.co_consts
        assert app_module.SETTINGS_GEN_MODEL_KEY == "settings_gen_model"
        assert app_module.SETTINGS_TEMPERATURE_KEY == "settings_temperature"
        assert app_module.SETTINGS_GEN_MODEL_KEY in overrides_src
        assert app_module.SETTINGS_TEMPERATURE_KEY in overrides_src

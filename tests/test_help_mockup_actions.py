"""tests/test_help_mockup_actions.py - 도움말 mockup 액션 회귀 테스트.

목업의 '보기' / '예제 보기' 동작을 실제 NAE 앱에서도 유지하도록 보장한다.
"""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "app.py")


def _run_help_page() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["show_onboarding"] = False
    at.session_state["nav_page"] = "도움말"
    at.run()
    return at


def test_help_page_uses_mockup_action_labels():
    at = _run_help_page()
    labels = {button.label for button in at.button}
    assert "보기" in labels
    assert "예제 보기" in labels


def test_help_page_can_expand_a_guide_card():
    at = _run_help_page()
    at.button(key="help_guide_intro").click().run()
    assert not at.exception
    assert at.session_state["help_open_guide"] == "intro"

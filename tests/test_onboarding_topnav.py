"""tests/test_onboarding_topnav.py - 랜딩 화면 상단 네비게이션 버튼 회귀 테스트.

원래 정적 <a href="#">/<button>로만 있어 클릭해도 아무 화면 전환이
일어나지 않던 버그를 실제 st.button + nav_page 전환으로 고친 뒤 추가함.
"""

import os

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "ui", "app.py")


def _run_onboarding() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["show_onboarding"] = True
    at.run()
    return at


def test_topnav_library_button_navigates_to_library():
    at = _run_onboarding()
    at.button(key="topnav_library").click().run()
    assert not at.exception
    assert at.session_state["show_onboarding"] is False
    assert at.session_state["nav_page"] == "Library"


def test_topnav_research_button_navigates_to_research():
    at = _run_onboarding()
    at.button(key="topnav_research").click().run()
    assert not at.exception
    assert at.session_state["nav_page"] == "Research"


def test_topnav_explore_button_navigates_to_ai_chat():
    at = _run_onboarding()
    at.button(key="topnav_explore").click().run()
    assert not at.exception
    assert at.session_state["nav_page"] == "AI에게 질문"


def test_topnav_login_button_is_disabled():
    at = _run_onboarding()
    assert at.button(key="topnav_login").disabled is True


def test_footer_help_button_navigates_to_help():
    at = _run_onboarding()
    at.button(key="footer_help").click().run()
    assert not at.exception
    assert at.session_state["show_onboarding"] is False
    assert at.session_state["nav_page"] == "도움말"

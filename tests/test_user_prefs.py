"""tests/test_user_prefs.py - 온보딩 완료 여부 영속화 회귀 테스트.

"나중에 하기" 등 온보딩 종료 버튼이 session_state만 바꾸고 디스크에는
아무것도 남기지 않아, 새로고침/재실행하면 온보딩이 되살아나던 버그의
회귀 방지 테스트.
"""

import pytest

import core.user_prefs


@pytest.fixture(autouse=True)
def _isolate_prefs_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        core.user_prefs, "_PREFS_PATH", str(tmp_path / "user_prefs.json")
    )


def test_defaults_to_not_dismissed():
    assert core.user_prefs.has_dismissed_onboarding() is False


def test_dismiss_persists_across_calls():
    core.user_prefs.dismiss_onboarding()
    assert core.user_prefs.has_dismissed_onboarding() is True


def test_missing_prefs_file_does_not_raise():
    # 파일이 아예 없는 최초 실행 상태를 시뮬레이션.
    assert core.user_prefs.has_dismissed_onboarding() is False

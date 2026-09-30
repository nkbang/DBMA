"""tests/test_user_prefs.py - 온보딩 완료 여부 영속화 회귀 테스트.

"연구 시작하기" 등 온보딩 종료 버튼이 session_state만 바꾸면, 브라우저를
새로고침할 때마다 온보딩이 되살아나던 버그의 회귀 방지 테스트. 프로세스
메모리(모듈 전역 dict)에 남기므로 서버 재시작 시에는 다시 초기화된다 —
그 경계는 여기서 검증하지 않는다(프로세스 재시작 자체를 흉내낼 수
없음); 테스트 간 격리만 신경 쓴다.
"""

import pytest

import core.user_prefs


@pytest.fixture(autouse=True)
def _isolate_prefs(monkeypatch):
    monkeypatch.setattr(core.user_prefs, "_prefs", {})


def test_defaults_to_not_dismissed():
    assert core.user_prefs.has_dismissed_onboarding() is False


def test_dismiss_persists_across_calls():
    core.user_prefs.dismiss_onboarding()
    assert core.user_prefs.has_dismissed_onboarding() is True


def test_missing_prefs_file_does_not_raise():
    # 파일이 아예 없는 최초 실행 상태를 시뮬레이션.
    assert core.user_prefs.has_dismissed_onboarding() is False

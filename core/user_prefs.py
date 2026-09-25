"""core/user_prefs.py — 로컬 사용자 선호 설정의 프로세스 메모리 기반 영속화.

Streamlit의 st.session_state는 브라우저 새로고침마다 새 세션으로
초기화된다. 온보딩 완료 여부처럼 "한 번만 보여주면 되는" 선택을
session_state에만 저장하면, 브라우저를 새로고침할 때마다 온보딩이
되살아나 "연구 시작하기" 등을 눌러도 무용지물처럼 보인다.

그렇다고 디스크에 영구 기록하면 반대 문제가 생긴다 — 앱(서버 프로세스)을
완전히 새로 켤 때조차 이전 실행에서 dismiss된 상태가 그대로 남아,
"앱을 처음 열면 온보딩이 뜬다"는 기대를 깨고 항상 대시보드로 바로
진입해버린다(실측 재발 이력 있음).

이 모듈은 그 중간 지점 — 서버 프로세스 메모리에만 남긴다:
  - 같은 서버가 떠 있는 동안 브라우저를 새로고침/재연결해도 dismiss가
    유지된다(session_state만으로는 안 되던 것).
  - 서버 프로세스를 재시작하면(= 앱을 새로 연다) 이 모듈도 다시
    import되어 초기화되므로, 온보딩이 다시 뜬다.
"""

_prefs: dict = {}


def has_dismissed_onboarding() -> bool:
    return bool(_prefs.get("onboarding_dismissed", False))


def dismiss_onboarding() -> None:
    _prefs["onboarding_dismissed"] = True

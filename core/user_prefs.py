"""core/user_prefs.py — 로컬 사용자 선호 설정의 단순 파일 기반 영속화.

Streamlit의 st.session_state는 브라우저 새로고침/서버 재시작마다 새
세션으로 초기화된다. 온보딩 완료 여부처럼 "한 번만 보여주면 되는" 선택을
session_state에만 저장하면, 새로고침할 때마다 온보딩이 되살아나
"나중에 하기"를 눌러도 무용지물처럼 보인다. 이 모듈은 그런 선택을
디스크에 남겨 다음 실행에서도 유지되게 한다.
"""

import json
import os

from core.config import DEFAULT_OUTPUT_DIR

_PREFS_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "user_prefs.json")


def _load() -> dict:
    try:
        with open(_PREFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def has_dismissed_onboarding() -> bool:
    return bool(_load().get("onboarding_dismissed", False))


def dismiss_onboarding() -> None:
    data = _load()
    data["onboarding_dismissed"] = True
    os.makedirs(os.path.dirname(_PREFS_PATH) or ".", exist_ok=True)
    with open(_PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

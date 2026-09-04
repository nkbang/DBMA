"""tests/test_extractors_surrogate_fix.py — core.extractors._fix_or_strip_
lone_surrogates() 검증.

실측 근거(2026-07-24): striprtf가 RTF의 이모지 \\uXXXX\\uXXXX(UTF-16
서로게이트 쌍) 이스케이프를 하나의 코드포인트로 합치지 못해 lone
surrogate가 남는 경우가 있고, 이는 UTF-8 인코딩 불가 — Streamlit
markdown 렌더링이 크래시했다("2025년 설교 모음.rtf", 29개 설교 중 5개
에서 발견).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.extractors import _fix_or_strip_lone_surrogates


def test_adjacent_surrogate_pair_is_recombined_into_emoji():
    broken = "안녕" + chr(0xD83D) + chr(0xDC49) + "하세요"
    fixed = _fix_or_strip_lone_surrogates(broken)
    assert fixed == "안녕👉하세요"
    fixed.encode("utf-8")  # 크래시하지 않아야 함


def test_multiple_emoji_pairs_in_long_text():
    broken = "시작" + chr(0xD83C) + chr(0xDFAF) + "중간" + chr(0xD83D) + chr(0xDCD6) + "끝"
    fixed = _fix_or_strip_lone_surrogates(broken)
    assert fixed == "시작🎯중간📖끝"
    fixed.encode("utf-8")


def test_unpaired_surrogate_is_stripped_not_crashed():
    # 쌍을 못 이루는 lone high surrogate — 복구 불가, 제거되어야 함.
    broken = "앞" + chr(0xD83D) + "뒤"
    fixed = _fix_or_strip_lone_surrogates(broken)
    assert "\ud83d" not in fixed
    fixed.encode("utf-8")  # 크래시하지 않아야 함


def test_clean_text_is_unchanged():
    clean = "평범한 한글 텍스트입니다."
    assert _fix_or_strip_lone_surrogates(clean) == clean


def test_empty_string():
    assert _fix_or_strip_lone_surrogates("") == ""


def test_real_emoji_already_correct_is_unaffected():
    # 이미 정상적으로 결합된 이모지(단일 코드포인트)는 그대로 유지.
    text = "정상 이모지 👉 텍스트"
    assert _fix_or_strip_lone_surrogates(text) == text

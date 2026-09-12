"""회귀 — 오염 문자 탐지 범위 확장 (2026-09-11, P0-5 A3 실측).

실제 답변에 키릴 문자("вопрос")가 섞여 나온 사례가 관측됐다.
_SCRIPT_CONTAMINATION_RE가 CJK/태국어만 잡던 것을 그리스·키릴·히브리·
아랍 문자까지 넓혔다. 한글·영문·숫자·구두점은 여전히 통과해야 한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.generation import _detect_script_contamination, _sanitize_script_contamination


def test_cyrillic_detected():
    assert _detect_script_contamination("이 вопрос에 답하기 부족합니다.") == ["в", "о", "п", "р", "с"]


def test_greek_and_hebrew_and_arabic_detected():
    assert _detect_script_contamination("λόγος 관련 내용") != []
    assert _detect_script_contamination("שלום 관련 내용") != []
    assert _detect_script_contamination("مرحبا 관련 내용") != []


def test_korean_english_numbers_punctuation_pass_clean():
    text = '한국어 문장입니다. Romans 8:1-4, John 3:16 — 100% 정상.'
    assert _detect_script_contamination(text) == []


def test_sanitize_removes_cyrillic_without_touching_korean():
    dirty = "질문은 вопрос 입니다."
    clean = _sanitize_script_contamination(dirty)
    assert "в" not in clean and "о" not in clean.replace("질문은", "").replace("입니다", "")
    assert "질문은" in clean and "입니다" in clean

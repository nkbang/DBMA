"""규칙 기반 답변 완결성 판정 검증 — core/evaluation/answer_completeness.py
(PM 정렬 감사 선결 #4 / 옵션 A, Task Order §5-1 산출물).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.evaluation.answer_completeness import evaluate_completeness

_GOOD = (
    "회심하지 않은 죄인에게도 그리스도를 믿을 의무가 있습니다. "
    "풀러는 이 의무가 복음의 명령에서 직접 나온다고 보았습니다.\n\n"
    "따라서 설교자는 청중에게 믿음을 촉구할 수 있습니다. "
    "이는 인간의 능력이 아니라 하나님의 명령에 근거합니다."
)


def test_well_formed_answer_passes():
    r = evaluate_completeness(_GOOD)
    assert r.passed, r.violations
    assert r.paragraph_count == 2
    assert r.sentence_count >= 4


def test_empty_answer_fails():
    r = evaluate_completeness("")
    assert not r.passed
    assert "빈 답변" in r.violations[0]


def test_foreign_script_flagged():
    r = evaluate_completeness(_GOOD + "\n\n그리고 一部 내용이 섞였습니다.")
    assert not r.passed
    assert any("비한국어 문자" in v for v in r.violations)


def test_long_untranslated_english_flagged():
    bad = _GOOD + "\n\nThe original English sentence runs on for far more than forty characters here."
    r = evaluate_completeness(bad)
    assert not r.passed
    assert any("영어 원문 스팬" in v for v in r.violations)


def test_unfinished_sentence_flagged():
    bad = "이 문장은 완결 어미 없이 끊기고\n\n두 번째 문단도 마찬가지로 어색하게"
    r = evaluate_completeness(bad)
    assert not r.passed
    assert any("완결 어미 없는 문장" in v for v in r.violations)


def test_single_paragraph_flagged():
    r = evaluate_completeness("한 문단짜리 답변만 있습니다. 문단이 하나뿐입니다.")
    assert not r.passed
    assert any("문단 수" in v for v in r.violations)


def test_no_honorific_flagged():
    r = evaluate_completeness("죄인은 믿어야 한다.\n\n설교자는 이를 촉구한다.")
    assert not r.passed
    assert any("경어체" in v for v in r.violations)


def test_caption_only_when_failed():
    assert evaluate_completeness(_GOOD).as_caption() == ""
    assert evaluate_completeness("").as_caption().startswith("답변 완결성 점검:")

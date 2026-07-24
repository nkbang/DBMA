"""Regression test — core/noise_classifier.py (SPRINT28-B).
Verifies classify() as a pure label function (no mutation, no deletion)
against the real content shapes found in SPRINT27-Beta Analysis and
SPRINT28-A's Beta Corpus Validation (KHAT abbreviations page, standalone
Hebrew fragment, bibliography citation).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.noise_classifier import classify
from core.repetition_detector import RepetitionSignal


def test_original_language_fragment_is_preserved():
    # Real Beta corpus noise sample: a standalone Hebrew fragment.
    result = classify("א ני כי")
    assert result.noise_type == "ORIGINAL_LANGUAGE"
    assert result.policy == "PRESERVE"
    assert result.quality_score == 1.0


def test_abbreviation_list_is_downweighted():
    # Real Beta corpus noise sample (2 Chronicles WBC front matter miss).
    text = (
        "KHAT Kurzer Handcommentar zum Alten Testament KVHS Korte "
        "verklaring der Heilige Schrift Leš Lešonénu LTQ Lexington "
        "Theological Quarterly OTS Oudtestamentische Studien"
    )
    result = classify(text)
    assert result.noise_type == "ABBREVIATION"
    assert result.policy == "DOWNWEIGHT"
    assert result.section_type == "abbreviation"


def test_bibliography_citation_is_downweighted():
    text = (
        "This chronological data is simply a vehicle by which the author "
        "demonstrates again the validity of retribution theology (Dillard, 1987). "
        "See also the discussion in Williamson (1982) and the commentary "
        "series edited by Hubbard and Barker (1985)."
    )
    result = classify(text)
    assert result.noise_type == "BIBLIOGRAPHY"
    assert result.policy == "DOWNWEIGHT"


def test_page_number_only_chunk_is_removable():
    result = classify("123")
    assert result.noise_type == "PAGE_NUMBER"
    assert result.policy == "REMOVE"
    assert result.quality_score == 0.0

    result2 = classify("Page 45")
    assert result2.noise_type == "PAGE_NUMBER"


def test_normal_korean_prose_is_normal_content():
    text = (
        "로마서 8장 1절부터 11절은 숨결마다 복음의 능력을 전달한다. "
        "교회가 이 본문을 통해 성령의 인도하심을 깊이 이해할 수 있으며, "
        "그리스도 안에서 정죄함이 없다는 확신을 얻게 된다."
    )
    result = classify(text)
    assert result.noise_type == "NORMAL_CONTENT"
    assert result.policy == "NORMAL"
    assert result.quality_score == 1.0
    assert result.section_type == "body"


def test_normal_english_prose_is_normal_content():
    text = (
        "Imagine there were seventy-two thousand mighty spirits ready to "
        "intervene in Jesus' defense, but the legions never came because "
        "the Son of God chose the path of obedience instead of rescue."
    )
    result = classify(text)
    assert result.noise_type == "NORMAL_CONTENT"


def test_classify_does_not_mutate_input():
    text = "KHAT Kurzer Handcommentar zum Alten Testament"
    before = text
    classify(text)
    assert text == before  # pure function, no side effects


def test_empty_text_is_page_number_type():
    result = classify("")
    assert result.noise_type == "PAGE_NUMBER"
    assert result.policy == "REMOVE"


def test_repetition_signal_omitted_preserves_existing_behavior():
    # A long, sentence-bearing paragraph would never trip the byline
    # heuristic — confirms the additive param changes nothing when absent.
    text = "이것은 충분히 긴 일반 산문 본문이며 문장부호를 포함하고 있어서 헤더로 오판되지 않아야 한다."
    result = classify(text)
    assert result.noise_type == "NORMAL_CONTENT"


def test_repetition_signal_repeat_marks_header_footer():
    text = "이것은 충분히 긴 일반 산문 본문이며 문장부호를 포함하고 있어서 헤더로 오판되지 않아야 한다."
    signal = RepetitionSignal(is_repeat=True, occurrences=2, distance_since_last=25)
    result = classify(text, repetition_signal=signal)
    assert result.noise_type == "HEADER_FOOTER"
    assert result.policy == "REMOVE"


def test_repetition_signal_non_repeat_does_not_force_header_footer():
    text = "이것은 충분히 긴 일반 산문 본문이며 문장부호를 포함하고 있어서 헤더로 오판되지 않아야 한다."
    signal = RepetitionSignal(is_repeat=False, occurrences=1, distance_since_last=None)
    result = classify(text, repetition_signal=signal)
    assert result.noise_type == "NORMAL_CONTENT"

"""
tests/test_repetition_detector.py — ADR-011 제안 4 §1: RepetitionTracker
unit tests, reproducing the "2 Kings, Volume 13" running-header pattern
(same running header text + changing page number, repeat distance
median=25, majority 9~56 candidates per ADR-011 Context). Synthetic
candidates model the pattern; production untouched (core/ does not
import this module elsewhere yet).
"""

from core.repetition_detector import RepetitionTracker, _normalize_for_repetition


def _filler(n: int) -> list[str]:
    return [f"본문 문단 내용 {i}번째 후보 텍스트입니다." for i in range(n)]


def test_first_occurrence_is_not_a_repeat():
    tracker = RepetitionTracker()
    signal = tracker.observe("2 Kings, Volume 13 — 749")
    assert signal.is_repeat is False
    assert signal.occurrences == 1
    assert signal.distance_since_last is None


def test_running_header_with_changing_page_number_is_detected_as_repeat():
    tracker = RepetitionTracker(window=80, similarity_threshold=0.9)
    tracker.observe("2 Kings, Volume 13 — 749")
    for text in _filler(24):
        tracker.observe(text)
    signal = tracker.observe("2 Kings, Volume 13 — 750")
    assert signal.is_repeat is True
    assert signal.occurrences == 2
    assert signal.distance_since_last == 25


def test_repeat_outside_window_is_not_detected():
    tracker = RepetitionTracker(window=10, similarity_threshold=0.9)
    tracker.observe("2 Kings, Volume 13 — 749")
    for text in _filler(15):
        tracker.observe(text)
    signal = tracker.observe("2 Kings, Volume 13 — 780")
    assert signal.is_repeat is False


def test_dissimilar_text_is_not_a_false_positive():
    tracker = RepetitionTracker()
    tracker.observe("2 Kings, Volume 13 — 749")
    signal = tracker.observe("완전히 다른 본문 내용, 러닝헤더가 아님")
    assert signal.is_repeat is False


def test_normalize_masks_digits_only():
    assert _normalize_for_repetition("2 Kings, Volume 13 — 749") == "# Kings, Volume # — #"
    assert _normalize_for_repetition("  padded  ") == "padded"


def test_multiple_documents_require_separate_tracker_instances():
    doc1 = RepetitionTracker()
    doc2 = RepetitionTracker()
    doc1.observe("Document One Header — 1")
    signal = doc2.observe("Document One Header — 1")
    assert signal.is_repeat is False
    assert signal.occurrences == 1

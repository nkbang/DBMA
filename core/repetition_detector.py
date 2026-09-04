"""
core/repetition_detector.py — RepetitionTracker (ADR-011 제안 1).

Dormant, standalone module — NOT yet wired into core/noise_classifier.py
or core/semantic_boundary_detector.py (that is ADR-011 제안 2/3, separate
HQ approval). This is step 1 of ADR-011's approved rollout order: a single
shared stateful detector for cross-page repeated text (running headers),
so the noise-classification and chunking-boundary consumers do not each
reimplement repetition tracking independently.

A page-number-bearing running header (e.g. "요한복음 주석 — 749") repeats
almost verbatim except for the digits that change per page. Detection
therefore masks digits before comparing (`re.sub(r"\\d+", "#", text)`) and
compares against a sliding window of the most recently observed candidates
— not the whole document — since headers repeat at a roughly page-sized
cadence (ADR-011 Context: median distance 25, majority 9~56 candidates).

One instance per document; do not reuse across documents (§Risk in
ADR-011) — the window would otherwise mix repetition signals from
unrelated texts.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Deque, Optional, Tuple

_DIGIT_RE = re.compile(r"\d+")

DEFAULT_WINDOW = 80
DEFAULT_SIMILARITY_THRESHOLD = 0.9


def _normalize_for_repetition(text: str) -> str:
    return _DIGIT_RE.sub("#", text.strip())


@dataclass(frozen=True)
class RepetitionSignal:
    is_repeat: bool
    occurrences: int
    distance_since_last: Optional[int]


class RepetitionTracker:
    """Sliding-window cross-candidate repetition detector.

    One instance per document. Call observe() once per candidate, in
    document order — order-dependent, since distance_since_last counts
    candidates observed since the last (near-)match.
    """

    def __init__(self, window: int = DEFAULT_WINDOW, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self._window = window
        self._similarity_threshold = similarity_threshold
        self._history: Deque[Tuple[str, int]] = deque(maxlen=window)
        self._position = 0
        self._occurrences: dict[str, int] = {}

    def observe(self, text: str) -> RepetitionSignal:
        normalized = _normalize_for_repetition(text)
        position = self._position
        self._position += 1

        best_match: Optional[Tuple[str, int]] = None
        best_ratio = 0.0
        for hist_text, hist_position in self._history:
            ratio = SequenceMatcher(None, normalized, hist_text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (hist_text, hist_position)

        is_repeat = best_match is not None and best_ratio >= self._similarity_threshold
        distance = position - best_match[1] if is_repeat and best_match else None

        occurrence_key = normalized
        self._occurrences[occurrence_key] = self._occurrences.get(occurrence_key, 0) + 1
        occurrences = self._occurrences[occurrence_key]

        self._history.append((normalized, position))

        return RepetitionSignal(
            is_repeat=is_repeat,
            occurrences=occurrences,
            distance_since_last=distance,
        )

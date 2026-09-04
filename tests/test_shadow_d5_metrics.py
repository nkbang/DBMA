"""Unit tests — D-5 metrics formal evaluation driver (SPRINT33-D Phase
3-A). Diagnostic-only, not production code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from shadow_d5_metrics import SAFETY_CAP, classify_profile, unsplittable_outliers


class TestClassifyProfile:
    def test_profile_a_when_all_candidates_under_safety_cap(self):
        candidates = [("x" * 100, 0), ("y" * (SAFETY_CAP - 1), 200)]
        assert classify_profile(candidates) == "A"

    def test_profile_b_when_any_candidate_exceeds_safety_cap(self):
        candidates = [("x" * 100, 0), ("y" * (SAFETY_CAP + 1), 200)]
        assert classify_profile(candidates) == "B"

    def test_profile_a_for_empty_candidates(self):
        assert classify_profile([]) == "A"


class TestUnsplittableOutliers:
    def test_zero_when_no_candidate_exceeds_safety_cap(self):
        candidates = [("문단입니다.", 0), ("또다른 문단입니다.", 20)]
        assert unsplittable_outliers(candidates) == 0

    def test_counts_long_candidate_with_no_sentence_boundary(self):
        # No sentence-ending punctuation anywhere -- split_sentences_mixed
        # should return it as a single unsplittable piece.
        long_no_punct = "가나다라마바사아자차카타파하 " * 200
        assert len(long_no_punct) > SAFETY_CAP
        candidates = [(long_no_punct, 0)]
        assert unsplittable_outliers(candidates) == 1

    def test_single_line_prose_with_sentence_endings_is_now_splittable(self):
        # [ADR-008 제안 4 수정, 2026-07-21] 이전에는 이 사례가
        # "unsplittable로 카운트되는 게 실제 동작(버그 아님)"으로
        # 문서화돼 있었다 — split_sentences_mixed()가 개행 기준으로만
        # 나눴기 때문. 이제 마침표류 문장부호로도 나뉘도록 수정됐으므로
        # (core/text_normalizer.py::_split_line_on_sentence_end), 문장
        # 종결부호가 있는 단일 줄 프로즈는 더 이상 unsplittable이 아니다.
        sentence = "이것은 완전한 문장입니다. "
        long_single_line_prose = sentence * 200
        assert len(long_single_line_prose) > SAFETY_CAP
        candidates = [(long_single_line_prose, 0)]
        assert unsplittable_outliers(candidates) == 0

    def test_multi_line_prose_is_splittable(self):
        # Contrast case: an embedded newline is genuinely required.
        sentence = "이것은 완전한 문장입니다.\n"
        long_multi_line_prose = sentence * 200
        assert len(long_multi_line_prose) > SAFETY_CAP
        candidates = [(long_multi_line_prose, 0)]
        assert unsplittable_outliers(candidates) == 0

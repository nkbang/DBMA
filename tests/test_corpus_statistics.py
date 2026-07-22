"""Regression tests — sermon_corpus/analyzer/corpus_statistics.py.

두 가지 실제 버그를 고정한다:
1. compute_correlation_matrix()가 (book, chapter) 튜플을 JSON 딕셔너리
   키로 써서 save_statistics()가 항상 TypeError로 크래시하던 것.
2. _categorize_title()이 제목의 첫 단어만 검사해 대부분의 한국어 설교
   제목에서 카테고리 매칭이 사실상 작동하지 않던 것.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.analyzer.corpus_statistics import CorpusStatisticsAnalyzer


def _analyzer_with_records() -> CorpusStatisticsAnalyzer:
    a = CorpusStatisticsAnalyzer()
    a.load_records([
        {"bible_book": "Romans", "chapter_start": 8, "verse_start": 28, "verse_end": None,
         "title": "고난 중에도 믿음으로 사는 삶"},
        {"bible_book": "Romans", "chapter_start": 8, "verse_start": 1, "verse_end": 4,
         "title": "십자가의 사랑과 용서"},
        {"bible_book": "1 Corinthians", "chapter_start": 13, "verse_start": 4, "verse_end": 7,
         "title": "사랑은 오래 참고"},
    ])
    return a


class TestCorrelationMatrixJsonBugFix:
    def test_save_statistics_does_not_raise(self, tmp_path):
        a = _analyzer_with_records()
        a.save_statistics(tmp_path)  # 이전에는 여기서 TypeError
        assert (tmp_path / "correlation_matrix.json").exists()

    def test_correlation_matrix_keys_are_json_safe_strings(self):
        a = _analyzer_with_records()
        matrix = a.compute_correlation_matrix()
        for category, passages in matrix.items():
            for key in passages:
                assert isinstance(key, str)
                json.dumps({key: 1.0})  # 직렬화 가능해야 함

    def test_correlation_matrix_passage_key_format(self):
        a = _analyzer_with_records()
        matrix = a.compute_correlation_matrix()
        all_keys = {k for passages in matrix.values() for k in passages}
        assert "Romans:8" in all_keys


class TestCategorizeTitleBugFix:
    def test_matches_keyword_not_in_first_word(self):
        a = CorpusStatisticsAnalyzer()
        # "사랑"이 첫 단어가 아님 — 이전 버그였다면 None을 반환했을 것.
        assert a._categorize_title("오늘 우리가 나눌 말씀은 사랑입니다") == "love"

    def test_no_matching_keyword_returns_none(self):
        # 주의: CATEGORY_PATTERNS["justice"]에 "의" 한 글자가 패턴으로
        # 들어있어(원본 설계, 이번 수정 범위 밖) "의"가 들어간 단어는
        # 대부분 오탐으로 "justice"에 걸린다 — 그 글자를 피한 문자열 사용.
        a = CorpusStatisticsAnalyzer()
        assert a._categorize_title("가나다라마바사") is None

    def test_empty_title_returns_none(self):
        a = CorpusStatisticsAnalyzer()
        assert a._categorize_title("") is None

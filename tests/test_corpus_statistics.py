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
    # [버그 수정 회귀 대응] CorpusStatisticsAnalyzer.load_records()가
    # published_date/passage_raw/title/preacher 중 하나라도 없는 레코드를
    # 걸러내도록 바뀌어서, 이 필드들이 없던 기존 fixture는 전부 필터링돼
    # 통계가 항상 빈 값이 됐다 — 네 필드를 모두 채움.
    a = CorpusStatisticsAnalyzer()
    a.load_records([
        {"bible_book": "Romans", "chapter_start": 8, "verse_start": 28, "verse_end": None,
         "title": "고난 중에도 믿음으로 사는 삶", "passage_raw": "로마서 8:28",
         "preacher": "김목사", "published_date": "2026-01-01"},
        {"bible_book": "Romans", "chapter_start": 8, "verse_start": 1, "verse_end": 4,
         "title": "십자가의 사랑과 용서", "passage_raw": "로마서 8:1-4",
         "preacher": "이목사", "published_date": "2026-01-08"},
        {"bible_book": "1 Corinthians", "chapter_start": 13, "verse_start": 4, "verse_end": 7,
         "title": "사랑은 오래 참고", "passage_raw": "고린도전서 13:4-7",
         "preacher": "박목사", "published_date": "2026-01-15"},
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


class TestPassageRawNormalization:
    """[기능 추가] passage_raw("로마서 9:11-16" 등, 책명이 섞인 원본
    표기)에서 책명은 bible_book으로, passage_raw는 "장:절-절" 숫자
    형식으로 분리·통일한다."""

    def test_strips_book_name_leaving_chapter_verse_range(self):
        a = CorpusStatisticsAnalyzer()
        a.load_records([{
            "bible_book": "Romans", "chapter_start": 9, "verse_start": 11, "verse_end": 16,
            "title": "제목", "passage_raw": "로마서 9:11-16",
            "preacher": "김목사", "published_date": "2026-01-01",
        }])
        assert a.records[0]["passage_raw"] == "9:11-16"
        assert a.records[0]["bible_book"] == "Romans"

    def test_single_verse_no_range(self):
        a = CorpusStatisticsAnalyzer()
        a.load_records([{
            "bible_book": "Mark", "chapter_start": 10, "verse_start": 46, "verse_end": None,
            "title": "제목", "passage_raw": "마가복음 10:46",
            "preacher": "이목사", "published_date": "2026-01-01",
        }])
        assert a.records[0]["passage_raw"] == "10:46"

    def test_chapter_only_no_verse(self):
        a = CorpusStatisticsAnalyzer()
        a.load_records([{
            "bible_book": "Jonah", "chapter_start": 1, "verse_start": None, "verse_end": None,
            "title": "제목", "passage_raw": "요나 1장",
            "preacher": "박목사", "published_date": "2026-01-01",
        }])
        assert a.records[0]["passage_raw"] == "1"

    def test_missing_chapter_leaves_passage_raw_untouched(self):
        # 장 정보가 아예 없으면 지어내지 않고 원본을 그대로 둔다.
        a = CorpusStatisticsAnalyzer()
        a.load_records([{
            "bible_book": "Romans", "chapter_start": None,
            "title": "제목", "passage_raw": "로마서 어딘가",
            "preacher": "김목사", "published_date": "2026-01-01",
        }])
        assert a.records[0]["passage_raw"] == "로마서 어딘가"

    def test_chapter_zero_sentinel_is_not_treated_as_real_chapter(self):
        # [버그 수정] 일부 수집기(youtube.py)는 성구를 못 찾으면
        # chapter_start를 None이 아니라 0으로 채운다
        # (`bible_ref.get("chapter_start") or 0`) — chapter_start=0을
        # 진짜 1장인 것처럼 오인해 passage_raw="0"을 지어낸 뒤(존재하지
        # 않는 값), 그 "0"이 비어있지 않은 문자열이라 필수 필드 검사도
        # 통과해버려 실제로 우리 DB에 154건이나 섞여 있었다. chapter=0
        # 이면 "장 정보 없음"으로 취급해 원본 passage_raw를 그대로
        # 두고(빈 문자열이면 그대로 필수 필드 검사에서 걸러짐), 절대
        # "0"을 만들어내지 않는다.
        a = CorpusStatisticsAnalyzer()
        n = a.load_records([{
            "bible_book": "Unknown", "chapter_start": 0,
            "title": "제목", "passage_raw": "",
            "preacher": "김목사", "published_date": "2026-01-01",
        }])
        assert n == 0
        assert a.records == []


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

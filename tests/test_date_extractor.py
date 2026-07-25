"""tests/test_date_extractor.py — core.date_extractor 검증.

패턴은 실제 설교 파일(data/RAW/2025년 설교 모음.rtf, striprtf 추출
결과) 대조로 확정한 것 — 개인 설교 원문은 테스트에 포함하지 않고,
동일한 구조적 패턴을 재현한 합성 텍스트만 사용한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.date_extractor import extract_date_from_line, find_nearest_date


class TestExtractDateFromLine:
    def test_iso_format(self):
        assert extract_date_from_line("2025-01-05") == "2025-01-05"

    def test_korean_format(self):
        assert extract_date_from_line("2026년 2월 11일") == "2026-02-11"

    def test_no_date_returns_none(self):
        assert extract_date_from_line("사랑하는 성도 여러분") is None

    def test_invalid_month_day_returns_none(self):
        assert extract_date_from_line("2025-13-40") is None

    def test_single_digit_month_day_korean(self):
        assert extract_date_from_line("2025년 1월 5일") == "2025-01-05"


class TestFindNearestDate:
    def test_date_immediately_before_anchor(self):
        lines = ["2025-01-05", "2025-01-05", "제목: 새해"]
        assert find_nearest_date(lines, anchor_index=2) == "2025-01-05"

    def test_date_several_lines_before_with_noise_between(self):
        # 실측 패턴: 날짜와 제목 사이에 교회명/이전 문장 등이 낌
        lines = [
            "2025-01-12",
            "교회 버몬트 한인 침례교회",
            "제목: 하나님은 여러분을 아실까요?",
        ]
        assert find_nearest_date(lines, anchor_index=2) == "2025-01-12"

    def test_no_date_within_lookback_returns_none(self):
        lines = ["필러"] * 15 + ["제목: 제목없는날짜"]
        assert find_nearest_date(lines, anchor_index=15, max_lookback=10) is None

    def test_does_not_cross_previous_sermon_boundary(self):
        # stop_index를 넘어(이전 설교 쪽) 날짜를 찾지 않아야 한다 —
        # 그 날짜는 이전 설교의 것이지 이번 설교의 것이 아니다.
        lines = [
            "2025-01-05",          # 이전 설교의 날짜
            "제목: 이전 설교",       # 이전 설교 제목 (stop_index=1)
            "본문 내용",
            "제목: 이번 설교",       # 이번 설교 제목 (anchor_index=3)
        ]
        assert find_nearest_date(lines, anchor_index=3, stop_index=1) is None

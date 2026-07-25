"""tests/test_multi_doc_splitter.py — core.multi_doc_splitter 검증.

합성 텍스트로 실제 설교 모음 파일에서 실측된 패턴(제목 100% 안정,
날짜/성구 위치 가변, "본문 말씀:" 변형, 제목+본문 한 줄 결합)을
재현한다 — 개인 설교 원문은 포함하지 않는다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.multi_doc_splitter import split_sermon_collection


class TestSplitSermonCollection:
    def test_no_title_lines_returns_empty(self):
        """"제목:" 줄이 없으면 — 단일 문서라는 뜻, 빈 리스트로 안전
        폴백(예외 아님) — 기존 단일-설교 파일에 잘못 적용해도 안전."""
        text = "그냥 평범한 설교 본문입니다.\n제목이 없습니다."
        assert split_sermon_collection(text) == []

    def test_two_sermons_clean_case(self):
        text = "\n".join([
            "2025년",
            "",
            "2025-01-05",
            "2025-01-05",
            "제목: 하나님 뜻을 내 계획에 담는 새해",
            "본문: 마태복음 22장 34-40절",
            "첫 번째 설교 본문입니다.",
            "둘째 줄입니다.",
            "2025-01-12",
            "교회 버몬트 한인 침례교회",
            "제목: 하나님은 여러분을 아실까요?",
            "본문 말씀: 요한복음 10장 7-14절",
            "두 번째 설교 본문입니다.",
        ])
        records = split_sermon_collection(text)
        assert len(records) == 2

        first = records[0]
        assert first.title == "하나님 뜻을 내 계획에 담는 새해"
        assert first.date == "2025-01-05"
        assert first.scripture == "마태복음 22장 34-40절"
        assert "첫 번째 설교 본문입니다." in first.body
        assert "둘째 줄입니다." in first.body
        assert "본문:" not in first.body  # 성구 줄은 본문에서 제외

        second = records[1]
        assert second.title == "하나님은 여러분을 아실까요?"
        assert second.date == "2025-01-12"
        assert second.scripture == "요한복음 10장 7-14절"  # "본문 말씀:" 변형도 인식
        assert "두 번째 설교 본문입니다." in second.body

    def test_title_and_scripture_on_same_line(self):
        text = "\n".join([
            "2025-04-27",
            "제목: 부활하신 주님과 동행하는 길 본문: 누가복음 24:13-35",
            "본문 내용입니다.",
        ])
        records = split_sermon_collection(text)
        assert len(records) == 1
        assert records[0].title == "부활하신 주님과 동행하는 길"
        assert records[0].scripture == "누가복음 24:13-35"

    def test_missing_scripture_is_none_not_error(self):
        """실측: 29건 중 일부는 성구를 못 찾음 — 실패 아니라 None."""
        text = "\n".join([
            "제목: 성구 없는 설교",
            "본문 내용만 있습니다.",
        ])
        records = split_sermon_collection(text)
        assert len(records) == 1
        assert records[0].scripture is None

    def test_missing_date_is_none_not_error(self):
        text = "\n".join([
            "제목: 날짜 없는 설교",
            "본문: 창세기 1:1",
            "내용",
        ])
        records = split_sermon_collection(text)
        assert records[0].date is None

    def test_date_does_not_leak_across_sermons(self):
        """이전 설교의 날짜가 다음 설교로 잘못 붙지 않아야 한다."""
        text = "\n".join([
            "2025-01-05",
            "제목: 첫 설교",
            "본문 내용",
            "제목: 날짜없는 둘째 설교",
            "본문 내용2",
        ])
        records = split_sermon_collection(text)
        assert len(records) == 2
        assert records[0].date == "2025-01-05"
        assert records[1].date is None

"""tests/test_multi_doc_splitter.py — core.multi_doc_splitter 검증.

합성 텍스트로 실제 설교 모음 파일에서 실측된 패턴(제목 100% 안정,
날짜/성구 위치 가변, "본문 말씀:" 변형, 제목+본문 한 줄 결합)을
재현한다 — 개인 설교 원문은 포함하지 않는다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.multi_doc_splitter import split_sermon_collection, manual_split, SermonRecord


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


class TestManualSplit:
    """리뷰 화면에서 자동 분리가 놓친 2건짜리 SermonRecord를 사용자가
    지정한 지점에서 수동으로 나누는 기능."""

    def _record(self, body_lines):
        return SermonRecord(
            title="합쳐진 설교", date="2025-06-01", scripture="시편 23편",
            body="\n".join(body_lines), start_line=0, end_line=10,
        )

    def test_split_in_the_middle(self):
        record = self._record(["첫 설교 1줄", "첫 설교 2줄", "둘째 설교 1줄", "둘째 설교 2줄"])
        first, second = manual_split(
            record, cut_line=2, new_title="두 번째 설교",
            new_date="2025-06-08", new_scripture="로마서 1:1",
        )

        assert first.body == "첫 설교 1줄\n첫 설교 2줄"
        assert second.body == "둘째 설교 1줄\n둘째 설교 2줄"

    def test_first_part_keeps_original_metadata(self):
        record = self._record(["A", "B"])
        first, _ = manual_split(
            record, cut_line=1, new_title="새 설교",
            new_date="2025-06-08", new_scripture="로마서 1:1",
        )
        assert first.title == "합쳐진 설교"
        assert first.date == "2025-06-01"
        assert first.scripture == "시편 23편"

    def test_second_part_uses_new_metadata(self):
        record = self._record(["A", "B"])
        _, second = manual_split(record, cut_line=1, new_title="새 설교", new_date="2025-06-08", new_scripture="로마서 1:1")
        assert second.title == "새 설교"
        assert second.date == "2025-06-08"
        assert second.scripture == "로마서 1:1"

    def test_missing_date_raises(self):
        """[2026-07-24, 사용자 요청] 제목/날짜/성구 중 하나라도 없으면
        분할 자체를 실행하지 않는다."""
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="날짜"):
            manual_split(record, cut_line=1, new_title="새 설교", new_scripture="로마서 1:1")

    def test_missing_scripture_raises(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="성구"):
            manual_split(record, cut_line=1, new_title="새 설교", new_date="2025-06-08")

    def test_missing_title_raises(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="제목"):
            manual_split(record, cut_line=1, new_title="", new_date="2025-06-08", new_scripture="로마서 1:1")

    def test_blank_whitespace_fields_also_raise(self):
        """빈 문자열뿐 아니라 공백만 있는 입력도 "없음"으로 취급."""
        record = self._record(["A", "B"])
        with pytest.raises(ValueError):
            manual_split(record, cut_line=1, new_title="새 설교", new_date="   ", new_scripture="로마서 1:1")

    def test_all_fields_missing_lists_all_in_message(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError) as exc_info:
            manual_split(record, cut_line=1, new_title="")
        message = str(exc_info.value)
        assert "제목" in message and "날짜" in message and "성구" in message

    def test_cut_line_zero_raises(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="cut_line"):
            manual_split(record, cut_line=0, new_title="x", new_date="2025-06-08", new_scripture="로마서 1:1")

    def test_cut_line_at_end_raises(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="cut_line"):
            manual_split(record, cut_line=2, new_title="x", new_date="2025-06-08", new_scripture="로마서 1:1")

    def test_cut_line_beyond_length_raises(self):
        record = self._record(["A", "B"])
        with pytest.raises(ValueError, match="cut_line"):
            manual_split(record, cut_line=99, new_title="x", new_date="2025-06-08", new_scripture="로마서 1:1")

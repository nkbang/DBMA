"""Regression tests — sermon_corpus/collector/youtube.py.

세 가지 실제 버그를 고정한다:
1. api_key_env(환경변수 "이름" 문자열)을 그대로 api_key로 써버려 실제
   키 값이 조회되지 않던 버그 — os.environ에서 실제 값을 읽도록 수정.
2. sources.yml의 channels가 문자열 리스트인데 코드는 {"id","name"}
   딕셔너리를 기대해 channel.get("id") 호출 시 AttributeError로
   죽던 버그 — 문자열이면 {"name": ...}로 정규화.
3. 채널명 문자열 매칭(설정된 이름 vs 실제 유튜브 채널명)이 항상
   실패해 특정 채널이 지정된 경우 결과가 0건이 되던 문제 — 실제
   채널 ID가 없으면 채널명 매칭 없이 검색 결과를 그대로 채택.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sermon_corpus.collector.youtube import YouTubeSermonCollector


class TestApiKeyEnvBugFix:
    def test_reads_actual_env_var_value_not_its_name(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_YT_KEY", "real-secret-value")
        collector = YouTubeSermonCollector({"api_key_env": "MY_TEST_YT_KEY"})
        assert collector.api_key == "real-secret-value"

    def test_missing_env_var_leaves_api_key_falsy(self, monkeypatch):
        monkeypatch.delenv("SOME_UNSET_YT_KEY", raising=False)
        collector = YouTubeSermonCollector({"api_key_env": "SOME_UNSET_YT_KEY"})
        assert not collector.api_key

    def test_explicit_api_key_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_YT_KEY", "from-env")
        collector = YouTubeSermonCollector({"api_key": "explicit-key", "api_key_env": "MY_TEST_YT_KEY"})
        assert collector.api_key == "explicit-key"


class TestChannelNormalization:
    def test_string_channels_do_not_crash(self):
        collector = YouTubeSermonCollector({"channels": ["Some Channel Name"]})
        assert collector.channels == [{"name": "Some Channel Name"}]

    def test_dict_channels_pass_through_unchanged(self):
        collector = YouTubeSermonCollector({"channels": [{"id": "UCxxx", "name": "Real Channel"}]})
        assert collector.channels == [{"id": "UCxxx", "name": "Real Channel"}]

    def test_mixed_channel_list(self):
        collector = YouTubeSermonCollector({"channels": ["Plain Name", {"id": "UCyyy", "name": "With ID"}]})
        assert collector.channels == [
            {"name": "Plain Name"},
            {"id": "UCyyy", "name": "With ID"},
        ]


class TestExtractPreacher:
    def test_finds_name_before_title_with_space(self):
        collector = YouTubeSermonCollector({})
        assert collector.extract_preacher("은혜로 사는 삶 - 유기성 목사 설교") == "유기성"

    def test_finds_name_before_title_without_space(self):
        collector = YouTubeSermonCollector({})
        assert collector.extract_preacher("이재철목사 명설교 최근말씀") == "이재철"

    def test_no_match_returns_none(self):
        collector = YouTubeSermonCollector({})
        assert collector.extract_preacher("아무 관련 없는 제목입니다") is None


class TestExtractBibleReferencesChapterSanityCheck:
    """[버그 수정] 권명 뒤 숫자를 장 번호로 채택할 때 그 책의 실제 장
    수를 넘는지 검증하지 않아 "민수기 787237장", "이사야서 2026장" 같은
    터무니없는 값이 그대로 passage_raw에 들어갔다(설명란의 구독자 수/
    연도 등이 우연히 "권명+숫자+장" 형태로 걸림, 실제 유튜브 API로 실측
    확인). 그 책의 실제 최대 장 수를 넘으면 채택하지 않아야 한다."""

    def test_rejects_chapter_number_beyond_books_actual_chapter_count(self):
        collector = YouTubeSermonCollector({})
        # 민수기는 36장까지만 있음
        result = collector.extract_bible_references(
            "정상 제목", "민수기 787237장 무관한 설명 텍스트"
        )
        assert result["bible_book"] is None
        assert result["chapter_start"] is None

    def test_accepts_valid_chapter_number_within_range(self):
        collector = YouTubeSermonCollector({})
        result = collector.extract_bible_references("로마서 8:28 설교", "")
        assert result["bible_book"] == "롬"
        assert result["chapter_start"] == 8
        assert result["verse_start"] == 28

    def test_abbreviation_strategy_requires_explicit_chapter_marker(self):
        # [버그 수정] "(?:장|편)?"이 완전 선택적이라 "장"/"편" 표시 없이
        # 약어 뒤 숫자만 있어도 통과했다 — 명시적 표시가 없으면 거부.
        collector = YouTubeSermonCollector({})
        result = collector.extract_bible_references("무관한 제목", "시 787237 무관한 숫자")
        assert result["bible_book"] is None

    def test_abbreviation_strategy_rejects_out_of_range_chapter(self):
        collector = YouTubeSermonCollector({})
        # 시편은 150편까지만 있음
        result = collector.extract_bible_references("무관한 제목", "시 999편 무관한 텍스트")
        assert result["bible_book"] is None


def _fake_search_item(video_id: str, title: str, channel_title: str) -> dict:
    return {
        "id": {"videoId": video_id},
        "snippet": {
            "title": title,
            "description": "",
            "publishedAt": "2026-01-01T00:00:00Z",
            "channelTitle": channel_title,
        },
    }


class TestCollectAllWithoutChannelFilter:
    """[버그 수정] 설정된 채널명이 실제 유튜브 채널명과 달라(실측 확인)
    이름 매칭이 항상 실패, collect_all()이 항상 0건을 반환하던 문제.
    실제 채널 ID가 없으면 채널명 매칭 없이 검색 결과를 그대로 채택한다."""

    def test_accepts_any_channel_when_no_real_channel_id_configured(self):
        collector = YouTubeSermonCollector({
            "channels": ["Yoido Full Gospel Church"],  # 실제 유튜브 채널명과 다름
            "search_keywords": ["설교"],
        })
        fake_items = [
            _fake_search_item("v1", "은혜로 사는 삶 - 설교", "갓피플TV"),
            _fake_search_item("v2", "다른 설교 영상", "복음훈련소"),
        ]
        with patch.object(collector, "fetch_with_search", return_value=fake_items):
            records = collector.collect_all(api_key="dummy")

        assert len(records) == 2
        channel_names = {r["channel_name"] for r in records}
        # 설정된 "Yoido Full Gospel Church"가 아니라 검색 결과의 실제 채널명이 쓰여야 함
        assert channel_names == {"갓피플TV", "복음훈련소"}

    def test_bible_book_is_canonical_english_name_not_korean_abbreviation(self):
        # [버그 수정] _build_records()가 extract_bible_references()의
        # 한글 1글자 약어("롬","막","요" 등)를 그대로 bible_book에 넣어
        # DBMA 전체가 쓰는 영문 canonical 이름("Romans" 등)과 안 맞고,
        # 그래서 성경 권별 통계에서 유튜브 레코드만 매칭이 안 됐다.
        collector = YouTubeSermonCollector({"channels": ["Any"], "search_keywords": ["설교"]})
        fake_items = [_fake_search_item("v1", "로마서 8:28 설교 - 김목사", "채널A")]
        with patch.object(collector, "fetch_with_search", return_value=fake_items):
            records = collector.collect_all(api_key="dummy")

        assert records[0]["bible_book"] == "Romans"

    def test_deduplicates_by_title_and_video_id(self):
        collector = YouTubeSermonCollector({"channels": ["Any"], "search_keywords": ["설교"]})
        fake_items = [
            _fake_search_item("v1", "같은 제목", "채널A"),
            _fake_search_item("v1", "같은 제목", "채널A"),
        ]
        with patch.object(collector, "fetch_with_search", return_value=fake_items):
            records = collector.collect_all(api_key="dummy")

        assert len(records) == 1

    def test_uses_real_channel_id_path_when_configured(self):
        collector = YouTubeSermonCollector({
            "channels": [{"id": "UCxxx", "name": "실제 채널"}],
        })
        fake_videos = [{
            "video_id": "v1",
            "title": "제목",
            "description": "",
            "published_at": "2026-01-01T00:00:00Z",
        }]
        with patch.object(collector, "fetch_with_api", return_value=fake_videos):
            records = collector.collect_all(api_key="dummy")

        assert len(records) == 1
        assert records[0]["channel_name"] == "실제 채널"

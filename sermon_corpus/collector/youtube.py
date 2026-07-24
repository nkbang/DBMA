# DBMA Sermon Corpus - YouTube 대형교회 설교 수집기
# YouTube Data API v3 또는 비공식 스크래핑을 통해 대형교회 설교 메타데이터 수집

import json
import os
import time
import random
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer

try:
    import httpx
except ImportError:
    httpx = None


class YouTubeSermonCollector:
    """
    YouTube에서 대형교회 설교 영상을 수집합니다.
    
    - YouTube Data API v3 지원 (API 키 필요)
    - 비공식 웹 스크래핑 폴백 (api_key 없음)
    - 설교 제목 + 본문 참조 추출
    - 중복 제거
    """
    
    # 한국 대형교회 유튜브 채널 목록
    LARGE_CHURCH_CHANNELS = [
        {"id": "UC_rWlYRgaEkptJmoBQLXwzA", "name": "중앙성교회", "language": "ko"},
        {"id": "UC89MmUiJTR4fMt0yMRE6nxg", "name": "여의도순복음교회", "language": "ko"},
        {"id": "UCqQI2sHvX7oQnHGyF2GxO3A", "name": "서울중앙성교회", "language": "ko"},
        {"id": "UCmJi5gMJ8VcKKn1BXz6KlEA", "name": "GC예수교회", "language": "ko"},
        {"id": "UCt7B9qJpGZxJuAYfIgE3bOw", "name": "안산역광장교회", "language": "ko"},
        {"id": "UC4HjRyKNtFWYF0kbSxWfX7A", "name": "다림교회", "language": "ko"},
        {"id": "UCv2maLsLkJKkmMnO8BfJpKw", "name": "함성교회", "language": "ko"},
        # 국제 대형교회
        {"id": "UCuOhqbHMm1xvjNS67nLqRwQ", "name": "Elevation Church", "language": "en"},
        {"id": "UCEJlbDO3ax0POKtFAA8VhHg", "name": "Hillsong Church", "language": "en"},
        {"id": "UCvBqzzv3LgI04K7eQxWmgNA", "name": "Passion Church", "language": "en"},
    ]
    
    # 성경 권 목록 (한국어/영어)
    BIBLE_BOOKS_KO = {
        "창세기는": {"abbr": "창", "chapters": 50, "testament": "OT"},
        "출애굽기는": {"abbr": "출", "chapters": 40, "testament": "OT"},
        "레기는": {"abbr": "레", "chapters": 27, "testament": "OT"},
        "민수기는": {"abbr": "민", "chapters": 36, "testament": "OT"},
        "신명기는": {"abbr": "신", "chapters": 34, "testament": "OT"},
        "여호수아기는": {"abbr": "수", "chapters": 24, "testament": "OT"},
        "사사기는": {"abbr": "삐", "chapters": 21, "testament": "OT"},
        "룻기는": {"abbr": "룻", "chapters": 4, "testament": "OT"},
        "사무엘상은": {"abbr": "상", "chapters": 31, "testament": "OT"},
        "사무엘하는": {"abbr": "하", "chapters": 31, "testament": "OT"},
        "열왕기는": {"abbr": "왕", "chapters": 22, "testament": "OT"},
        "역대상은": {"abbr": "상", "chapters": 29, "testament": "OT"},
        "역대하는": {"abbr": "하", "chapters": 29, "testament": "OT"},
        "에스라는": {"abbr": "느", "chapters": 10, "testament": "OT"},
        "느헤미야는": {"abbr": "느", "chapters": 13, "testament": "OT"},
        "에스더는": {"abbr": "에스", "chapters": 10, "testament": "OT"},
        "욥기는": {"abbr": "욥", "chapters": 42, "testament": "OT"},
        "시편은": {"abbr": "시", "chapters": 150, "testament": "OT"},
        "잠언은": {"abbr": "잠", "chapters": 31, "testament": "OT"},
        "전도서에는": {"abbr": "전", "chapters": 12, "testament": "OT"},
        "아름의 노래에는": {"abbr": "아신", "chapters": 8, "testament": "OT"},
        "이사야서는": {"abbr": "사", "chapters": 66, "testament": "OT"},
        "예레미야서는": {"abbr": "렘", "chapters": 52, "testament": "OT"},
        "예레미야애서는": {"abbr": "애", "chapters": 5, "testament": "OT"},
        "에스겔서는": {"abbr": "겔", "chapters": 48, "testament": "OT"},
        "다니엘서는": {"abbr": "단", "chapters": 12, "testament": "OT"},
        "호세아서는": {"abbr": "호", "chapters": 14, "testament": "OT"},
        "요엘서는": {"abbr": "욜", "chapters": 3, "testament": "OT"},
        "아모스서는": {"abbr": "암", "chapters": 9, "testament": "OT"},
        "오바디아서는": {"abbr": "옵", "chapters": 1, "testament": "OT"},
        "요나는": {"abbr": "욘", "chapters": 4, "testament": "OT"},
        "미가는": {"abbr": "미", "chapters": 7, "testament": "OT"},
        "나훤서는": {"abbr": "눙", "chapters": 3, "testament": "OT"},
        "하박국은": {"abbr": "합", "chapters": 3, "testament": "OT"},
        "스바냐서는": {"abbr": "습", "chapters": 3, "testament": "OT"},
        "학개서는": {"abbr": "학", "chapters": 2, "testament": "OT"},
        "스가랴서는": {"abbr": "슥", "chapters": 14, "testament": "OT"},
        "말라기는": {"abbr": "말", "chapters": 4, "testament": "OT"},
        "마태복음은": {"abbr": "마", "chapters": 28, "testament": "NT"},
        "마가복음은": {"abbr": "막", "chapters": 16, "testament": "NT"},
        "누가는": {"abbr": "눅", "chapters": 24, "testament": "NT"},
        "요한복음은": {"abbr": "요", "chapters": 21, "testament": "NT"},
        "사도행전은": {"abbr": "행", "chapters": 28, "testament": "NT"},
        "로마서는": {"abbr": "롬", "chapters": 16, "testament": "NT"},
        "고전에는": {"abbr": "고전", "chapters": 16, "testament": "NT"},
        "후에는": {"abbr": "고후", "chapters": 13, "testament": "NT"},
        "갈라디아서에는": {"abbr": "갈", "chapters": 6, "testament": "NT"},
        "에베소서에는": {"abbr": "엡", "chapters": 6, "testament": "NT"},
        "빌립보서에는": {"abbr": "빌", "chapters": 4, "testament": "NT"},
        "골로새서에는": {"abbr": "골", "chapters": 4, "testament": "NT"},
        "데살로니전후서에는": {"abbr": "살전후", "chapters": 5, "testament": "NT"},
        "디모데전서에는": {"abbr": "전", "chapters": 6, "testament": "NT"},
        "디모데후서에는": {"abbr": "후", "chapters": 4, "testament": "NT"},
        "디도서에는": {"abbr": "딛", "chapters": 3, "testament": "NT"},
        "히브리서에는": {"abbr": "히", "chapters": 13, "testament": "NT"},
        "야고보서에는": {"abbr": "야", "chapters": 5, "testament": "NT"},
        "베전에는": {"abbr": "전", "chapters": 5, "testament": "NT"},
        "후에는": {"abbr": "후", "chapters": 5, "testament": "NT"},
        "요한일서에는": {"abbr": "일", "chapters": 5, "testament": "NT"},
        "요한이서에는": {"abbr": "이", "chapters": 1, "testament": "NT"},
        "요한삼서에는": {"abbr": "삼", "chapters": 1, "testament": "NT"},
        "유다서에는": {"abbr": "유", "chapters": 1, "testament": "NT"},
        "요한계시록은": {"abbr": "계", "chapters": 22, "testament": "NT"},
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get("source_id", "youtube")
        # [버그 수정] config.get("api_key_env")는 sources.yml에 적힌
        # 환경변수 "이름"(예: "YOUTUBE_API_KEY") 문자열 자체를 그대로
        # api_key로 써버렸다 — 실제 키 값이 아니라 변수명 문자열이
        # API에 전달돼 모든 호출이 실패했을 것이다. os.environ에서
        # 그 이름으로 실제 값을 조회하도록 수정.
        api_key_env_name = config.get("api_key_env", "YOUTUBE_API_KEY")
        self.api_key = config.get("api_key") or os.environ.get(api_key_env_name)
        # [버그 수정] sources.yml의 channels는 채널명 문자열 리스트인데
        # (["Yoido Full Gospel Church", ...]) 코드는 {"id":.., "name":..}
        # 딕셔너리를 기대해서 collect_from_channel()의 channel.get("id")가
        # 문자열에 호출돼 AttributeError로 죽었다 — 문자열이면
        # {"name": 문자열}로 정규화(그러면 API 채널ID 없이도 기존
        # 검색 폴백 경로로 자연스럽게 넘어감).
        self.channels = self._normalize_channels(
            config.get("channels", self.LARGE_CHURCH_CHANNELS)
        )
        self.search_keywords = config.get("search_keywords", ["설교", "sermon"])
        self.storage_path = Path(config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/youtube.jsonl"
        ))
        self.max_results_per_channel = config.get("max_results_per_channel", 50)
        self.delay_between_requests = config.get("delay_between_requests", 1.5)
        
        # 통계
        self.stats = {
            "channels_processed": 0,
            "videos_collected": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "api_calls": 0,
        }
        self._seen_titles: set = set()

    @staticmethod
    def _normalize_channels(raw_channels) -> List[Dict]:
        """채널 목록을 {"id":.., "name":..} 딕셔너리 리스트로 통일한다.

        sources.yml처럼 채널명 문자열만 있는 경우 "id" 없이 "name"만
        채워서, API 채널ID가 없어도 collect_from_channel()의 검색
        폴백 경로가 정상 동작하도록 한다."""
        normalized = []
        for ch in raw_channels:
            if isinstance(ch, dict):
                normalized.append(ch)
            else:
                normalized.append({"name": str(ch)})
        return normalized

    def generate_dedupe_key(self, title: str, video_id: str) -> str:
        """중복 제거 키"""
        raw = f"{title}|{video_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def is_duplicate(self, dedupe_key: str) -> bool:
        if dedupe_key in self._seen_titles:
            return True
        self._seen_titles.add(dedupe_key)
        return False
    
    # [기능 추가] 설교자 이름 추출 — "유기성 목사", "이재철목사"(공백 없음),
    # "정동수 목사님", "OOO 전도사" 등 제목/설명에 흔히 붙는 패턴에서
    # 이름만 뽑는다. CorpusStatisticsAnalyzer가 preacher 필드를 필수로
    # 요구하도록 바뀐 뒤로 유튜브 레코드는 이 필드가 항상 비어있어 전부
    # 걸러지고 있었음 — 못 찾으면 None(추측해서 채우지 않음).
    PREACHER_PATTERN = re.compile(r"([가-힣]{2,4})\s?(목사님|목사|전도사님|전도사|장로님|장로)")

    def extract_preacher(self, title: str, description: str = "") -> Optional[str]:
        """제목/설명에서 설교자 이름을 추출합니다. 못 찾으면 None."""
        text = f"{title} {description}"
        match = self.PREACHER_PATTERN.search(text)
        return match.group(1) if match else None

    def extract_bible_references(self, title: str, description: str = "") -> Dict:
        """
        설교 제목/설명에서 성경 본문 참조를 추출합니다.
        
        YouTube 영상 제목/설명에서는 다음과 같은 다양한 형식이 사용됩니다:
        - "요한복음 3장 설교" -> 요한복음, 3
        - "요한복음 3:16" -> 요한복음, 3, 16
        - "3장 - 은혜" -> (이전 권명에서 이어짐)
        - "롬 8:28" -> 로마서, 8, 28 (약어)
        - "창 1:1" -> 창세기, 1, 1 (약어 + 콜론)
        - "Genesis 3:16" -> 영어 권명 매칭
        
        Returns:
            bible_book: 권 약어 (예: "요", "창", "롬")
            chapter_start: 장 번호
            verse_start: 절 번호 (있는 경우)
            passage_raw: 원본 본문 참조 문자열
        """
        result = {
            "bible_book": None,
            "chapter_start": None,
            "verse_start": None,
            "passage_raw": None,
        }
        
        # 제목 + 설명 결합
        text = f"{title} {description}"
        # 대소문자 정규화 (영어 매칭용)
        text_lower = text.lower()
        
        # ============================================================
        # 전략 1: 영어 권명 패턴 (가장 명확 — 한글과 충돌 없음)
        # "John 3:16", "Genesis 1:1", "Romans 8:28" 등
        # 먼저 시도하여 한글 매칭과 충돌 방지
        # ============================================================
        english_books = {
            "genesis": {"abbr": "창", "chapters": 50},
            "exodus": {"abbr": "출", "chapters": 40},
            "leviticus": {"abbr": "레", "chapters": 27},
            "numbers": {"abbr": "민", "chapters": 36},
            "deuteronomy": {"abbr": "신", "chapters": 34},
            "john": {"abbr": "요", "chapters": 21},
            "romans": {"abbr": "롬", "chapters": 16},
            "1 corinthians": {"abbr": "고전", "chapters": 16},
            "2 corinthians": {"abbr": "고후", "chapters": 13},
            "matthew": {"abbr": "마", "chapters": 28},
            "mark": {"abbr": "막", "chapters": 16},
            "luke": {"abbr": "눅", "chapters": 24},
            "acts": {"abbr": "행", "chapters": 28},
            "psalm": {"abbr": "시", "chapters": 150},
            "psalms": {"abbr": "시", "chapters": 150},
            "proverbs": {"abbr": "잠", "chapters": 31},
            "revelation": {"abbr": "계", "chapters": 22},
        }
        
        for eng_name, info in english_books.items():
            if eng_name in text_lower:
                # "John 3:16" 패턴 — re.IGNORECASE로 대소문자 구분 없이 매칭
                pat = rf"{re.escape(eng_name)}\s*(\d+)[\:]\s*(\d+)"
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    result["bible_book"] = info["abbr"]
                    result["chapter_start"] = int(match.group(1))
                    result["verse_start"] = int(match.group(2))
                    result["passage_raw"] = f"{eng_name} {match.group(1)}:{match.group(2)}"
                    return result
                
                # "John 3" 패턴 — "Psalm 23편" 등 "편/장" 접미사도 허용
                pat_ch = rf"{re.escape(eng_name)}\s*(\d+)\s*(?:장|편)?\b"
                match = re.search(pat_ch, text, re.IGNORECASE)
                if match:
                    result["bible_book"] = info["abbr"]
                    chapter_text = match.group(0)
                    ch = match.group(1)
                    result["chapter_start"] = int(ch)
                    if "편" in chapter_text:
                        result["passage_raw"] = f"{eng_name} {ch}편"
                    else:
                        result["passage_raw"] = f"{eng_name} {ch}"
                    return result
        
        # ============================================================
        # 전략 2: 한글 권명 + 장 번호 패턴 (가장 일반적)
        # "요한복음 3장", "창세기 1:1", "시편 23편" 등
        # ============================================================
        
        # 권명 목록: '는/은/가/편' 접미사 제거 버전도 포함
        book_patterns = []
        for book_name, info in self.BIBLE_BOOKS_KO.items():
            # '는/은/가' 접미사 제거
            base_name = re.sub(r'[는은가]$', '', book_name)
            book_patterns.append((book_name, base_name, info))
        
        for full_name, base_name, info in book_patterns:
            # 완전 일치 (예: "요한복음은")
            if full_name in text:
                # 장 번호 추출: "요한복음은 3장", "요한복음은 3:16"
                # [버그 수정] "권명 + 아무 숫자"(구분자 없음) 폴백
                # 패턴이 있어서, 설명란에 있는 구독자 수/조회수 같은
                # 무관한 큰 숫자가 우연히 권명 바로 뒤에 오면 그걸
                # 장 번호로 잘못 채택했다(실측: "민수기 787237장" 등
                # 터무니없는 값 확인). "장"이나 ":" 같은 명확한 구분자가
                # 있을 때만 인정 — 없으면 차라리 못 찾은 것으로 둔다.
                patterns_to_try = [
                    rf"{re.escape(full_name)}\s*(\d+)[:::\s]\s*(\d+)",  # 권명 3:16
                    rf"{re.escape(full_name)}\s*(\d+)\s*장",             # 권명 3장
                ]
                for pat in patterns_to_try:
                    match = re.search(pat, text)
                    if not match:
                        continue
                    ch_num = int(match.group(1))
                    # [버그 수정] "이사야서 2026장"처럼 그 책의 실제
                    # 장 수를 훌쩍 넘는 값도 여전히 나왔다(구독자 수,
                    # 연도 등 설명란의 다른 숫자가 우연히 "권명+숫자+장"
                    # 형태로 걸림) — 그 책의 실제 최대 장 수를 넘으면
                    # 채택하지 않고 다음 패턴/후보로 넘어간다.
                    if not (1 <= ch_num <= info["chapters"]):
                        continue
                    result["bible_book"] = info["abbr"]
                    result["chapter_start"] = ch_num
                    if len(match.groups()) > 1 and match.group(2):
                        result["verse_start"] = int(match.group(2))
                    # passage_raw 생성
                    vr = match.group(2) if len(match.groups()) > 1 and match.group(2) else None
                    if vr:
                        result["passage_raw"] = f"{base_name} {ch_num}:{vr}"
                    else:
                        result["passage_raw"] = f"{base_name} {ch_num}장"
                    return result
                break
            
            # 접미사 제거 버전 매칭 (예: "요한복음 3장" — "은" 없이)
            if base_name in text and full_name not in text:
                patterns_to_try = [
                    rf"{re.escape(base_name)}\s*(\d+)[:::\s]\s*(\d+)",
                    rf"{re.escape(base_name)}\s*(\d+)\s*장",
                ]
                for pat in patterns_to_try:
                    match = re.search(pat, text)
                    if not match:
                        continue
                    ch_num = int(match.group(1))
                    if not (1 <= ch_num <= info["chapters"]):
                        continue
                    result["bible_book"] = info["abbr"]
                    result["chapter_start"] = ch_num
                    if len(match.groups()) > 1 and match.group(2):
                        result["verse_start"] = int(match.group(2))
                    vr = match.group(2) if len(match.groups()) > 1 and match.group(2) else None
                    if vr:
                        result["passage_raw"] = f"{base_name} {ch_num}:{vr}"
                    else:
                        result["passage_raw"] = f"{base_name} {ch_num}장"
                    return result

        # ============================================================
        # 전략 3: 한글 약어 패턴 (예: "요 3:16", "창 1:1", "시 23")
        # ============================================================
        if not result["bible_book"]:
            # 약어 매핑 (약어 -> (완전권명, 기본권명))
            abbrev_to_full = {}
            for book_name, info in self.BIBLE_BOOKS_KO.items():
                base_name = re.sub(r'[는은가]$', '', book_name)
                abbrev_to_full[info["abbr"]] = (book_name, base_name, info["chapters"])

            # 약어 + 장:절 패턴 (예: "요 3:16", "창 1:1")
            for abbr, (full_name, base_name, max_chapters) in abbrev_to_full.items():
                # "약어 장:절" 패턴
                pat_with_verse = rf"{re.escape(abbr)}\s*(\d+)[::]\s*(\d+)"
                match = re.search(pat_with_verse, text)
                if match:
                    ch_num = int(match.group(1))
                    if 1 <= ch_num <= max_chapters:
                        result["bible_book"] = abbr
                        result["chapter_start"] = ch_num
                        result["verse_start"] = int(match.group(2))
                        result["passage_raw"] = f"{base_name} {ch_num}:{match.group(2)}"
                        return result

                # [버그 수정] "(?:장|편)?"이 완전히 선택적이라 "장"/"편"
                # 표시 없이 약어 뒤에 아무 숫자만 있어도 통과했다 — 짧은
                # 1글자 약어("민","시" 등)는 본문과 무관한 문맥에도 흔히
                # 등장해서 오탐이 매우 잦다(실측: "민수기 787237장" 등
                # 확인). "장"/"편" 표시를 필수로 요구 + 그 책의 실제
                # 최대 장 수를 넘으면 거부.
                pat_chapter_only = rf"{re.escape(abbr)}\s*(\d+)\s*(장|편)"
                match = re.search(pat_chapter_only, text)
                if match:
                    ch_num = int(match.group(1))
                    if 1 <= ch_num <= max_chapters:
                        result["bible_book"] = abbr
                        result["chapter_start"] = ch_num
                        marker = match.group(2)
                        result["passage_raw"] = f"{base_name} {ch_num}{marker}"
                        return result
        
        # ============================================================
        # 전략 4: 독립된 장 번호 패턴 (예: "3장 설교", "Chapter 3")
        # 이전 컨텍스트에서 권명이 이미 발견된 경우에만 사용
        # ============================================================
        # 이 전략은 현재 skip (권명 없이 장 번호만으로는 불명확)
        
        return result
    
    def fetch_with_api(self, api_key: str, channel_id: str, max_results: int = 50) -> List[Dict]:
        """YouTube Data API v3를 사용하여 설교 영상 목록을 가져옵니다"""
        if httpx is None:
            return []
        
        videos = []
        base_url = "https://www.googleapis.com/youtube/v3/search"
        
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "maxResults": min(max_results, 50),
            "key": api_key,
            "order": "date",  # 최신순
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(base_url, params=params)
                
                if resp.status_code == 200:
                    self.stats["api_calls"] += 1
                    data = resp.json()
                    items = data.get("items", [])
                    
                    for item in items:
                        snippet = item.get("snippet", {})
                        video_id = item.get("id", {}).get("videoId", "")
                        title = snippet.get("title", "")
                        description = snippet.get("description", "")
                        published_at = snippet.get("publishedAt", "")
                        
                        if video_id and title:
                            videos.append({
                                "video_id": video_id,
                                "title": title,
                                "description": description,
                                "published_at": published_at,
                                "channel_title": snippet.get("channelTitle", ""),
                            })
                elif resp.status_code == 403:
                    self.stats["errors"] += 1
        except Exception as e:
            self.stats["errors"] += 1
        
        return videos
    
    def fetch_with_search(self, api_key: str, keywords: List[str], max_results: int = 50) -> List[Dict]:
        """키워드 검색으로 설교 영상을 가져옵니다"""
        if httpx is None:
            return []
        
        all_videos = []
        base_url = "https://www.googleapis.com/youtube/v3/search"
        
        for keyword in keywords:
            params = {
                "part": "snippet",
                "q": f"{keyword} 설교",
                "type": "video",
                "maxResults": min(max_results, 50),
                "key": api_key,
                "order": "relevance",
            }
            
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(base_url, params=params)
                    
                    if resp.status_code == 200:
                        self.stats["api_calls"] += 1
                        data = resp.json()
                        all_videos.extend(data.get("items", []))
                    elif resp.status_code == 403:
                        self.stats["errors"] += 1
                        break
            except Exception as e:
                self.stats["errors"] += 1
            
            time.sleep(self.delay_between_requests)
            
            if len(all_videos) >= max_results:
                break
        
        return all_videos
    
    def collect_from_channel(self, channel: Dict, api_key: str) -> List[Dict]:
        """특정 채널에서 설교 영상을 수집합니다"""
        videos = []
        
        # API 키가 있으면 API 사용
        if api_key and channel.get("id"):
            videos = self.fetch_with_api(api_key, channel["id"], self.max_results_per_channel)
        
        # API 키가 없거나 결과가 없으면 검색 사용
        if not videos:
            videos_data = self.fetch_with_search(api_key or "", self.search_keywords, self.max_results_per_channel)
            # 채널 필터링
            for item in videos_data:
                channel_title = item.get("snippet", {}).get("channelTitle", "")
                if channel["name"] in channel_title or channel_title in channel["name"]:
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    videos.append({
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "channel_title": channel_title,
                    })
        
        return videos
    
    def _build_records(self, videos: List[Dict], default_channel_name: Optional[str]) -> List[Dict]:
        """영상 메타데이터 목록을 SermonRecord 스타일 dict로 변환합니다
        (중복 제거 + 성경 본문 참조 추출 포함)."""
        records = []
        for video in videos:
            dedupe_key = self.generate_dedupe_key(video["title"], video["video_id"])
            if self.is_duplicate(dedupe_key):
                continue

            bible_ref = self.extract_bible_references(
                video["title"], video.get("description", "")
            )
            preacher = self.extract_preacher(video["title"], video.get("description", ""))

            # [버그 수정] extract_bible_references()가 "롬"/"막"/"요"
            # 같은 한글 1글자 약어를 그대로 bible_book에 넣었다 —
            # DBMA 전체(FrequencyAnalyzer/book_themes.py/sermonbank.py)는
            # "Romans"/"Mark"/"John" 같은 정경 영문 canonical 이름을
            # 기준으로 쓰므로, 이대로면 성경 권별 빈도/핵심 주제 등
            # 모든 통계에서 유튜브 레코드만 매칭이 안 되고 빠진다.
            # FrequencyAnalyzer의 한글 별칭 매핑으로 영문 canonical
            # 이름으로 변환(매핑에 없는 값은 원본 그대로 — 추측하지 않음).
            bible_book_raw = bible_ref.get("bible_book")
            bible_book = (
                FrequencyAnalyzer.KOREAN_ABBREVIATIONS.get(bible_book_raw, bible_book_raw)
                if bible_book_raw else None
            )

            # [버그 수정] YouTube API의 publishedAt("2026-01-01T00:00:00Z")을
            # "published_at"으로만 저장했는데, 코퍼스가 요구하는 필수
            # 필드명은 sermonbank 등 다른 출처와 동일한 "published_date"
            # (YYYY-MM-DD)다 — 이름이 달라 항상 누락 처리돼 필터링됐다.
            published_at = video.get("published_at", "")
            published_date = published_at[:10] if published_at else ""

            records.append({
                "record_id": f"yt_{dedupe_key}",
                "source": self.source_id,
                # 특정 채널을 지정해 수집한 경우 그 이름을, 아니면 검색
                # 결과가 실제로 알려주는 채널명을 그대로 사용.
                "channel_name": default_channel_name or video.get("channel_title", "Unknown"),
                "video_id": video["video_id"],
                "title": video["title"],
                "description": video.get("description", ""),
                "preacher": preacher,
                "passage_raw": bible_ref.get("passage_raw") or "",
                "bible_book": bible_book or "Unknown",
                "chapter_start": bible_ref.get("chapter_start") or 0,
                "chapter_end": bible_ref.get("chapter_end"),
                "verse_start": bible_ref.get("verse_start") or 0,
                "verse_end": bible_ref.get("verse_end"),
                "published_at": published_at,
                "published_date": published_date,
                "collected_at": datetime.utcnow().isoformat(),
            })
            self.stats["videos_collected"] += 1
        return records

    def collect_all(self, api_key: Optional[str] = None) -> List[Dict]:
        """
        설교 데이터를 수집합니다.

        [기능 변경] 이전에는 self.channels에 등록된 이름과 검색 결과의
        실제 채널명이 문자열로 일치해야만 채택했다 — sources.yml의
        채널명("Yoido Full Gospel Church" 등)이 실제 유튜브 채널명과
        달라(실측: 검색 결과는 "갓피플TV" 등으로 나옴) 항상 0건이었다.
        "특정 채널 제한 없이 설교 관련 영상이면 된다"는 요청에 따라,
        실제 채널 ID가 없는 한(self.channels에 "id"가 있는 항목이 없는
        한) 채널명 매칭 없이 검색 키워드로만 수집하도록 변경 — 결과의
        channel_title은 검색 결과가 알려주는 실제 채널명을 그대로 쓴다.

        Args:
            api_key: YouTube Data API 키 (없으면 검색 모드)

        Returns:
            설교 영상 메타데이터 목록
        """
        effective_key = api_key or self.api_key
        has_real_channel_ids = any(ch.get("id") for ch in self.channels)

        if has_real_channel_ids:
            all_records = []
            for channel in self.channels:
                print(f"  채널 수집 중: {channel.get('name', 'Unknown')}")
                videos = self.collect_from_channel(channel, effective_key)
                all_records.extend(
                    self._build_records(videos, default_channel_name=channel.get("name", "Unknown"))
                )
                self.stats["channels_processed"] += 1
                time.sleep(self.delay_between_requests)
            return all_records

        # 채널 ID가 없음 — 특정 채널 제한 없이 검색 키워드로 수집하되,
        # [기능 추가] 채널명에 "교회"/"church"가 없는 결과는 제외한다.
        # "설교"/"sermon" 검색만으로는 "갓피플TV", "복음훈련소" 같은
        # 유명 목사 설교 모음/큐레이션 채널이 많이 걸려서 특정 유명인
        # 콘텐츠 위주가 됐다 — 실제 교회가 운영하는 채널(채널명에
        # 교회명이 들어감, 예: "분당우리교회", "여의도순복음교회")만
        # 남기도록. 채널 ID를 임의로 지어내지 않고, API가 실제로
        # 알려주는 채널명으로 판별하는 방식이라 검증 가능함.
        print("  교회 공식 채널 대상으로 키워드 검색 수집 중 (유명인 큐레이션 채널 제외)")
        raw_items = self.fetch_with_search(
            effective_key or "", self.search_keywords, self.max_results_per_channel
        )
        videos = []
        for item in raw_items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            title = snippet.get("title", "")
            channel_title = snippet.get("channelTitle", "Unknown")
            if video_id and title and self._is_church_channel(channel_title):
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "channel_title": channel_title,
                })

        all_records = self._build_records(videos, default_channel_name=None)
        self.stats["channels_processed"] += 1
        return all_records

    @staticmethod
    def _is_church_channel(channel_title: str) -> bool:
        """채널명이 실제 교회 채널로 보이는지 판단(유명인 설교 모음/
        큐레이션 채널 제외용). 채널명에 "교회" 또는 "church"가 있으면
        교회 채널로 간주 — 추측이 아니라 API가 실제로 준 채널명 기준."""
        name = (channel_title or "").lower()
        return "교회" in channel_title or "church" in name
    
    def save_to_jsonl(self, records: List[Dict], path: Optional[Path] = None) -> int:
        """기록을 JSONL 파일에 저장합니다"""
        if path is None:
            path = self.storage_path
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                saved_count += 1
        
        return saved_count
    
    def get_stats(self) -> Dict:
        """수집 통계 반환"""
        return dict(self.stats)


# ============================================================
# 시드 데이터 생성기 (대안 데이터소스)
# ============================================================

SEED_SERMON_DATA = [
    # OT 율법서 (창세기 - 신명기)
    {"title": "창조의 기쁨 — 창세기 1:1-5", "passage_raw": "창세기 1:1-5", "bible_book": "창", "chapter_start": 1, "testament": "OT", "theme": "창조", "keywords": ["창조", "빛", "초시작", "하나님의 권능"]},
    {"title": "아담과 하와의 실패 — 창세기 3:1-13", "passage_raw": "창세기 3:1-13", "bible_book": "창", "chapter_start": 3, "testament": "OT", "theme": "죄와 타락", "keywords": ["죄", "타락", "유혹", "순종"]},
    {"title": "노아의 방주와 언약 — 창세기 6:9-22", "passage_raw": "창세기 6:9-22", "bible_book": "창", "chapter_start": 6, "testament": "OT", "theme": "언약과 구원", "keywords": ["언약", "구원", "순종", "심판"]},
    {"title": "아브라함의 믿음의 여정 — 창세기 12:1-9", "passage_raw": "창세기 12:1-9", "bible_book": "창", "chapter_start": 12, "testament": "OT", "theme": "믿음과 순종", "keywords": ["믿음", "부름", "약속", "순종"]},
    {"title": "하나님의 약속의 성취 — 창세기 21:1-7", "passage_raw": "창세기 21:1-7", "bible_book": "창", "chapter_start": 21, "testament": "OT", "theme": "약속의 성취", "keywords": ["약속", "아들", "이삭", "기적"]},
    {"title": "모세의 부르심 — 출애굽기 3:1-10", "passage_raw": "출애굽기 3:1-10", "bible_book": "출", "chapter_start": 3, "testament": "OT", "theme": "부르심", "keywords": ["부르심", "모세", "하나님의 이름", "해방"]},
    {"title": "십계명과 삶의 기준 — 출애굽기 20:1-17", "passage_raw": "출애굽기 20:1-17", "bible_book": "출", "chapter_start": 20, "testament": "OT", "theme": "율법과 거룩함", "keywords": ["십계명", "율법", "거룩", "하나님의 뜻"]},
    {"title": "제사制度和 은혜 — 레위기 1:1-7", "passage_raw": "레위기 1:1-7", "bible_book": "레", "chapter_start": 1, "testament": "OT", "theme": "제사와 예배", "keywords": ["제사", "헌신", "거룩함", "예배"]},
    {"title": "광야의 인도하심 — 민수기 6:22-27", "passage_raw": "민수기 6:22-27", "bible_book": "민", "chapter_start": 6, "testament": "OT", "theme": "하나님의 인도", "keywords": ["축복", "인도", "광야", "하나님의 동행"]},
    {"title": "약속의 땅으로 — 신명기 6:1-9", "passage_raw": "신명기 6:1-9", "bible_book": "신", "chapter_start": 6, "testament": "OT", "theme": "하나님의 말씀 사랑", "keywords": ["사랑", "명령", "순종", "복"]},
    
    # 역사서
    {"title": "여호수아의 용기 — 여호수아기 1:1-9", "passage_raw": "여호수아기 1:1-9", "bible_book": "수", "chapter_start": 1, "testament": "OT", "theme": "용기와 담대함", "keywords": ["용기", "약속", "정복", "하나님의 동행"]},
    {"title": "룻의 충성 — 룻기는 1:16-18", "passage_raw": "룻기는 1:16-18", "bible_book": "룻", "chapter_start": 1, "testament": "OT", "theme": "충성과 사랑", "keywords": ["충성", "사랑", "속량", "믿음"]},
    {"title": "다윗의 왕권 — 사무엘상 16:1-13", "passage_raw": "사무엘상은 16:1-13", "bible_book": "상", "chapter_start": 16, "testament": "OT", "theme": "하나님의 선택", "keywords": ["다윗", "기름 부음", "왕", "하나님의 선택"]},
    {"title": "다윗의 회개 — 사무엘하 12:1-13", "passage_raw": "사무엘하는 12:1-13", "bible_book": "하", "chapter_start": 12, "testament": "OT", "theme": "회개와 용서", "keywords": ["회개", "용서", "다윗", "회복"]},
    {"title": "성전 건축의 꿈 — 열왕기상 8:22-30", "passage_raw": "열왕기는 8:22-30", "bible_book": "왕", "chapter_start": 8, "testament": "OT", "theme": "기도와 예배", "keywords": ["성전", "기도", "예배", "하나님의 임재"]},
    
    # 시가서
    {"title": "다윗의 찬양 — 시편 23편", "passage_raw": "시편은 23편", "bible_book": "시", "chapter_start": 23, "testament": "OT", "theme": "주님의 목자", "keywords": ["찬양", "목자", "인도", "평화"]},
    {"title": "지혜의 시작 — 잠언은 1:7", "passage_raw": "잠언은 1:7", "bible_book": "잠", "chapter_start": 1, "testament": "OT", "theme": "지혜와 경외", "keywords": ["지혜", "경외", "주님", "학습"]},
    {"title": "시간의 의미 — 전도서에는 3:1-8", "passage_raw": "전도서에는 3:1-8", "bible_book": "전", "chapter_start": 3, "testament": "OT", "theme": "시의와 하나님의 주권", "keywords": ["시간", "시", "주권", "하나님의 계획"]},
    {"title": "고난의 시편 — 시편 22편", "passage_raw": "시편은 22편", "bible_book": "시", "chapter_start": 22, "testament": "OT", "theme": "고난과 신뢰", "keywords": ["고난", "신뢰", "구원", "찬양"]},
    {"title": "사랑의 찬가 — 고전 13:1-13", "passage_raw": "고전에는 13:1-13", "bible_book": "고전", "chapter_start": 13, "testament": "NT", "theme": "사랑", "keywords": ["사랑", "인내", "희생", "영원"]},
    
    # 예언서
    {"title": "메시아의 약속 — 이사야서는 9:2-7", "passage_raw": "이사야서는 9:2-7", "bible_book": "사", "chapter_start": 9, "testament": "OT", "theme": "메시아 예언", "keywords": ["메시아", "구주", "평화", "왕국"]},
    {"title": "새 언약의 예언 — 예레미야서는 31:31-34", "passage_raw": "예레미야서는 31:31-34", "bible_book": "렘", "chapter_start": 31, "testament": "OT", "theme": "새 언약", "keywords": ["새 언약", "용서", "하나님의 법", "회복"]},
    {"title": "하나님의 회복 계획 — 에스겔서는 36:24-28", "passage_raw": "에스겔서는 36:24-28", "bible_book": "겔", "chapter_start": 36, "testament": "OT", "theme": "회복과 새심", "keywords": ["회복", "새심", "성령", "하나님의 백성"]},
    {"title": "손바닥에 새긴 사랑 — 이사야서는 49:14-16", "passage_raw": "이사야서는 49:14-16", "bible_book": "사", "chapter_start": 49, "testament": "OT", "theme": "하나님의 사랑", "keywords": ["사랑", "기억", "위로", "약속"]},
    {"title": "회복의 예언 — 다니엘서는 9:4-10", "passage_raw": "다니엘서는 9:4-10", "bible_book": "단", "chapter_start": 9, "testament": "OT", "theme": "회개와 회복", "keywords": ["회개", "회복", "기도", "하나님의 자비"]},
    
    # 신약 사복음서
    {"title": "산상 설교 — 마태복음은 5:1-12", "passage_raw": "마태복음은 5:1-12", "bible_book": "마", "chapter_start": 5, "testament": "NT", "theme": "복음의 핵심", "keywords": ["산상설교", "복", "제자", "왕국"]},
    {"title": "사랑의 명령 — 요한복음은 13:31-35", "passage_raw": "요한복음은 13:31-35", "bible_book": "요", "chapter_start": 13, "testament": "NT", "theme": "서로 사랑하라", "keywords": ["사랑", "명령", "발 씻김", "제자도"]},
    {"title": "선한 사마리아인 — 누가는 10:25-37", "passage_raw": "누가는 10:25-37", "bible_book": "눅", "chapter_start": 10, "testament": "NT", "theme": "이웃 사랑", "keywords": ["이웃", "자비", "사랑", "실천"]},
    {"title": "잃어버린 양의 비유 — 누가는 15:1-7", "passage_raw": "누가는 15:1-7", "bible_book": "눅", "chapter_start": 15, "testament": "NT", "theme": "구원과 기쁨", "keywords": ["잃어버린", "구원", "기쁨", "목자"]},
    {"title": "부활의 믿음 — 요한복음은 11:17-27", "passage_raw": "요한복음은 11:17-27", "bible_book": "요", "chapter_start": 11, "testament": "NT", "theme": "부활과 생명", "keywords": ["부활", "생명", "라자로", "믿음"]},
    
    # 바울 서신서
    {"title": "믿음으로 사는 삶 — 로마서는 1:16-17", "passage_raw": "로마서는 1:16-17", "bible_book": "롬", "chapter_start": 1, "testament": "NT", "theme": "복음의 능력", "keywords": ["복음", "믿음", "구원", "의"]},
    {"title": "성령의 열매 — 갈라디아서에는 5:22-23", "passage_raw": "갈라디아서에는 5:22-23", "bible_book": "갈", "chapter_start": 5, "testament": "NT", "theme": "성령의 열매", "keywords": ["성령", "열매", "사랑", "기쁨"]},
    {"title": "그리스도의 몸 — 에베소서에는 4:1-6", "passage_raw": "에베소서에는 4:1-6", "bible_book": "엡", "chapter_start": 4, "testament": "NT", "theme": "교회의 통일", "keywords": ["통일", "몸", "은사", "화평"]},
    {"title": "기쁨의 생활 — 빌립보서에는 4:4-7", "passage_raw": "빌립보서에는 4:4-7", "bible_book": "빌", "chapter_start": 4, "testament": "NT", "theme": "기쁨과 평안", "keywords": ["기쁨", "평안", "기도", "감사"]},
    {"title": "새 사람을 입으라 — 골로새서에는 3:12-17", "passage_raw": "골로새서에는 3:12-17", "bible_book": "골", "chapter_start": 3, "testament": "NT", "theme": "새 사람", "keywords": ["자비", "은혜", "사랑", "화평"]},
    
    # 교회사 및 목회 서신
    {"title": "기도의 능력 — 데살로니전후서에는 5:12-28", "passage_raw": "데살로니전후서에는 5:12-28", "bible_book": "살전후", "chapter_start": 5, "testament": "NT", "theme": "기도와 생활", "keywords": ["기도", "감사", "기대", "준비"]},
    {"title": "목사의 사명 — 디모데전서에는 3:1-7", "passage_raw": "디모데전서에는 3:1-7", "bible_book": "딤전", "chapter_start": 3, "testament": "NT", "theme": "목회자의 자질", "keywords": ["목사", "자질", "봉사", "거룩"]},
    {"title": "믿음의 싸움 — 디모데후서에는 4:1-8", "passage_raw": "디모데후서에는 4:1-8", "bible_book": "딤후", "chapter_start": 4, "testament": "NT", "theme": "믿음의 완주", "keywords": ["싸움", "달린", "믿음", "면류관"]},
    
    # 히브리서 및 일반 서신
    {"title": "믿음의 용사들 — 히브리서에는 11:1-6", "passage_raw": "히브리서에는 11:1-6", "bible_book": "히", "chapter_start": 11, "testament": "NT", "theme": "믿음의 본", "keywords": ["믿음", "용사", "인내", "약속"]},
    {"title": "시험과 인내 — 야고보서에는 1:2-4", "passage_raw": "야고보서에는 1:2-4", "bible_book": "야", "chapter_start": 1, "testament": "NT", "theme": "시험과 인내", "keywords": ["시험", "인내", "지혜", "완전"]},
    {"title": "거룩한 생활 — 베전에는 2:9-10", "passage_raw": "베전에는 2:9-10", "bible_book": "벧전", "chapter_start": 2, "testament": "NT", "theme": "거룩한 제사장", "keywords": ["거룩", "제사장", "백성", "찬미"]},
    
    # 요한 서신 및 계시록
    {"title": "사랑 안의 거함 — 요한일서에는 4:7-12", "passage_raw": "요한일서에는 4:7-12", "bible_book": "일", "chapter_start": 4, "testament": "NT", "theme": "하나님의 사랑", "keywords": ["사랑", "하나님", "보내심", "생명"]},
    {"title": "새 하늘과 새 땅 — 요한계시록은 21:1-7", "passage_raw": "요한계시록은 21:1-7", "bible_book": "계", "chapter_start": 21, "testament": "NT", "theme": "새 예루살렘", "keywords": ["새 하늘", "새 땅", "예루살렘", "하나님의 임재"]},
    {"title": "주의 오심을 기다리며 — 요한계시록은 22:12-21", "passage_raw": "요한계시록은 22:12-21", "bible_book": "계", "chapter_start": 22, "testament": "NT", "theme": "재림과 감사", "keywords": ["재림", "기다림", "감사", "은혜"]},
    
    # 추가 데이터 (한국 설교 특화)
    {"title": "새해 기도 — 시편은 90:1-6", "passage_raw": "시편은 90:1-6", "bible_book": "시", "chapter_start": 90, "testament": "OT", "theme": "새해 기도", "keywords": ["새해", "기도", "시간", "영원"]},
    {"title": "부활절 설교 — 요한복음은 20:1-10", "passage_raw": "요한복음은 20:1-10", "bible_book": "요", "chapter_start": 20, "testament": "NT", "theme": "부활", "keywords": ["부활절", "무덤", "부활", "믿음"]},
    {"title": "성령 강림 — 사도행전은 2:1-21", "passage_raw": "사도행전은 2:1-21", "bible_book": "행", "chapter_start": 2, "testament": "NT", "theme": "오순절", "keywords": ["성령", "오순절", "전도", "능력"]},
    {"title": "가족 예배 — 데살로니전후서에는 5:23-28", "passage_raw": "데살로니전후서에는 5:23-28", "bible_book": "살전후", "chapter_start": 5, "testament": "NT", "theme": "가족 예배", "keywords": ["가족", "예배", "거룩", "통합"]},
    {"title": "청년의 삶 — 디모데전서에는 4:12-16", "passage_raw": "디모데전서에는 4:12-16", "bible_book": "딤전", "chapter_start": 4, "testament": "NT", "theme": "청년의 본", "keywords": ["청년", "본", "사랑", "믿음"]},
    
    # 추가 OT 데이터
    {"title": "하나님의 말씀의 힘 — 히브리서에는 4:12-13", "passage_raw": "히브리서에는 4:12-13", "bible_book": "히", "chapter_start": 4, "testament": "NT", "theme": "말씀의 권위", "keywords": ["말씀", "권위", "심판", "생명"]},
    {"title": "하나님의 보호 — 시편은 91:1-16", "passage_raw": "시편은 91:1-16", "bible_book": "시", "chapter_start": 91, "testament": "OT", "theme": "하나님의 보호", "keywords": ["보호", "피난", "신뢰", "안전"]},
    {"title": "용서의 가르침 — 마태복음은 18:21-35", "passage_raw": "마태복음은 18:21-35", "bible_book": "마", "chapter_start": 18, "testament": "NT", "theme": "용서", "keywords": ["용서", "은혜", "관계", "화해"]},
    {"title": "기도의 모델 — 누가는 11:1-4", "passage_raw": "누가는 11:1-4", "bible_book": "눅", "chapter_start": 11, "testament": "NT", "theme": "주기도", "keywords": ["기도", "주기도", "예배", "간구"]},
    {"title": "평화의 왕 — 이사야서는 11:1-9", "passage_raw": "이사야서는 11:1-9", "bible_book": "사", "chapter_start": 11, "testament": "OT", "theme": "메시아의 평화", "keywords": ["평화", "메시아", "정의", "왕국"]},
    
    # 더 많은 데이터 (총 100건 목표)
    {"title": "하나님의 약속 — 창세기 15:1-6", "passage_raw": "창세기 15:1-6", "bible_book": "창", "chapter_start": 15, "testament": "OT", "theme": "약속의 신뢰", "keywords": ["약속", "신뢰", "믿음", "별"]},
    {"title": "소금과 빛 — 마태복음은 5:13-16", "passage_raw": "마태복음은 5:13-16", "bible_book": "마", "chapter_start": 5, "testament": "NT", "theme": "세상의 소금과 빛", "keywords": ["소금", "빛", "증거", "선한 행위"]},
    {"title": "하나님의 나라 비유 — 마태복음은 13:1-30", "passage_raw": "마태복음은 13:1-30", "bible_book": "마", "chapter_start": 13, "testament": "NT", "theme": "하나님의 나라", "keywords": ["비유", "나라", "종자", "수확"]},
    {"title": "회개의 메시지 — 호세아서는 6:1-6", "passage_raw": "호세아서는 6:1-6", "bible_book": "호", "chapter_start": 6, "testament": "OT", "theme": "회개와 회복", "keywords": ["회개", "돌이킴", "사랑", "자비"]},
    {"title": "하나님의 위로 — 이사야서는 40:25-31", "passage_raw": "이사야서는 40:25-31", "bible_book": "사", "chapter_start": 40, "testament": "OT", "theme": "하나님의 위로와 힘", "keywords": ["위로", "힘", "기다림", "새 힘"]},
    {"title": "하나님의 사랑 — 요한복음은 3:16-21", "passage_raw": "요한복음은 3:16-21", "bible_book": "요", "chapter_start": 3, "testament": "NT", "theme": "하나님의 사랑", "keywords": ["사랑", "구원", "믿음", "영생"]},
    {"title": "복된 삶 — 시편은 1:1-6", "passage_raw": "시편은 1:1-6", "bible_book": "시", "chapter_start": 1, "testament": "OT", "theme": "복된 사람", "keywords": ["복", "법", "의인", "불경한"]},
    {"title": "교회의 본 — 고전에는 12:12-31", "passage_raw": "고전에는 12:12-31", "bible_book": "고전", "chapter_start": 12, "testament": "NT", "theme": "몸의 통일", "keywords": ["몸", "은사", "통일", "봉사"]},
    {"title": "기도의 생활 — 빌립보서에는 1:3-11", "passage_raw": "빌립보서에는 1:3-11", "bible_book": "빌", "chapter_start": 1, "testament": "NT", "theme": "감사와 기도", "keywords": ["감사", "기도", "사랑", "지혜"]},
    {"title": "믿음의 훈련 — 디모데후서에는 2:1-13", "passage_raw": "디모데후서에는 2:1-13", "bible_book": "딤후", "chapter_start": 2, "testament": "NT", "theme": "믿음의 훈련", "keywords": ["훈련", "싸움", "충성", "참참"]},
    {"title": "희생의 예배 — 로마서는 12:1-3", "passage_raw": "로마서는 12:1-3", "bible_book": "롬", "chapter_start": 12, "testament": "NT", "theme": "산 제사", "keywords": ["제사", "희생", "변화", "하나님의 뜻"]},
    {"title": "하나님의 능력 — 고후에는 12:7-10", "passage_raw": "후에는 12:7-10", "bible_book": "고후", "chapter_start": 12, "testament": "NT", "theme": "약함 가운데 능력", "keywords": ["능력", "약함", "은혜", "그리스도"]},
    {"title": "기다림의 설교 — 슥야서는 9:9-10", "passage_raw": "스가랴서는 9:9-10", "bible_book": "슥", "chapter_start": 9, "testament": "OT", "theme": "겸손한 왕", "keywords": ["겸손", "왕", "구주", "평화"]},
    {"title": "하나님의 심판 — 예레미야서는 17:5-10", "passage_raw": "예레미야서는 17:5-10", "bible_book": "렘", "chapter_start": 17, "testament": "OT", "theme": "인간의 마음", "keywords": ["심판", "마음", "신뢰", "주님"]},
    {"title": "회복의 하나님 — 아모스서는 9:11-15", "passage_raw": "아모스서는 9:11-15", "bible_book": "암", "chapter_start": 9, "testament": "OT", "theme": "다시 세우심", "keywords": ["회복", "세우심", "복", "바퀴"]},
    {"title": "하나님의 자비 — 요나는 4:1-11", "passage_raw": "요나는 4:1-11", "bible_book": "욘", "chapter_start": 4, "testament": "OT", "theme": "하나님의 자비", "keywords": ["자비", "회개", "니느바", "용서"]},
    {"title": "지혜의 본 — 잠언은 3:1-12", "passage_raw": "잠언은 3:1-12", "bible_book": "잠", "chapter_start": 3, "testament": "OT", "theme": "지혜의 본", "keywords": ["지혜", "명령", "신뢰", "건강"]},
    {"title": "하나님의 임재 — 시편은 46:1-11", "passage_raw": "시편은 46:1-11", "bible_book": "시", "chapter_start": 46, "testament": "OT", "theme": "하나님의 임재", "keywords": ["임재", "피난", "세력", "평화"]},
    {"title": "기적의 밤 — 출애굽기 12:1-14", "passage_raw": "출애굽기 12:1-14", "bible_book": "출", "chapter_start": 12, "testament": "OT", "theme": "유월절", "keywords": ["유월절", "피", "구원", "기념"]},
    {"title": "기도의 사람 — 다니엘서는 6:10-23", "passage_raw": "다니엘서는 6:10-23", "bible_book": "단", "chapter_start": 6, "testament": "OT", "theme": "기도와 용기", "keywords": ["기도", "용기", "사자", "신뢰"]},
    {"title": "하나님의 영광 — 시편은 19:1-6", "passage_raw": "시편은 19:1-6", "bible_book": "시", "chapter_start": 19, "testament": "OT", "theme": "창조의 영광", "keywords": ["영광", "창조", "하늘", "하나님"]},
    {"title": "예수님의 슬픔 — 마가복음은 14:32-42", "passage_raw": "마가복음은 14:32-42", "bible_book": "막", "chapter_start": 14, "testament": "NT", "theme": "겟세마네 기도", "keywords": ["겟세마네", "기도", "고난", "순종"]},
    {"title": "믿음의 아버지 — 로마서는 4:1-12", "passage_raw": "로마서는 4:1-12", "bible_book": "롬", "chapter_start": 4, "testament": "NT", "theme": "아브라함의 믿음", "keywords": ["아브라함", "믿음", "의", "약속"]},
    {"title": "성령의 인도 — 갈라디아서에는 5:16-26", "passage_raw": "갈라디아서에는 5:16-26", "bible_book": "갈", "chapter_start": 5, "testament": "NT", "theme": "성령과 육", "keywords": ["성령", "육", "자유", "열매"]},
    {"title": "하나님의 집 — 에베소서에는 2:19-22", "passage_raw": "에베소서에는 2:19-22", "bible_book": "엡", "chapter_start": 2, "testament": "NT", "theme": "하나님의 집", "keywords": ["집", "돌", "성전", "하나님"]},
    {"title": "감사의 생활 — 데살로니전후서에는 5:16-28", "passage_raw": "데살로니전후서에는 5:16-28", "bible_book": "살전후", "chapter_start": 5, "testament": "NT", "theme": "항상 기뻐하라", "keywords": ["감사", "기쁨", "기도", "준비"]},
    {"title": "믿음의 유산 — 디모데전서에는 4:6-16", "passage_raw": "디모데전서에는 4:6-16", "bible_book": "딤전", "chapter_start": 4, "testament": "NT", "theme": "믿음의 유산", "keywords": ["유산", "훈련", "경건", "구원"]},
    {"title": "희망의 말씀 — 히브리서에는 6:13-20", "passage_raw": "히브리서에는 6:13-20", "bible_book": "히", "chapter_start": 6, "testament": "NT", "theme": "소망의 확신", "keywords": ["소망", "약속", "희망", "피난"]},
    {"title": "시험 이기기 — 야고보서에는 5:7-12", "passage_raw": "야고보서에는 5:7-12", "bible_book": "야", "chapter_start": 5, "testament": "NT", "theme": "인내와 기도", "keywords": ["인내", "기도", "기다림", "주"]},
    {"title": "고난의 의미 — 베전에는 4:12-19", "passage_raw": "베전에는 4:12-19", "bible_book": "벧전", "chapter_start": 4, "testament": "NT", "theme": "고난과 기쁨", "keywords": ["고난", "기쁨", "그리스도", "영광"]},
    {"title": "거짓 교사 경고 — 유다서는 1:17-25", "passage_raw": "유다서는 1:17-25", "bible_book": "유", "chapter_start": 1, "testament": "NT", "theme": "거짓 교사 경고", "keywords": ["경고", "거짓", "보존", "영광"]},
    {"title": "주의 재림 — 요한계시록은 22:7-21", "passage_raw": "요한계시록은 22:7-21", "bible_book": "계", "chapter_start": 22, "testament": "NT", "theme": "재림의 소망", "keywords": ["재림", "소망", "빨리", "아멘"]},
    {"title": "하나님의 언약 — 창세기 17:1-14", "passage_raw": "창세기 17:1-14", "bible_book": "창", "chapter_start": 17, "testament": "OT", "theme": "할례의 언약", "keywords": ["언약", "할례", "약속", "아브라함"]},
    {"title": "기도의 성전 — 열왕기하 8:22-30", "passage_raw": "열왕기하 8:22-30", "bible_book": "왕", "chapter_start": 8, "testament": "OT", "theme": "성전의 기도", "keywords": ["성전", "기도", "영광", "하나님"]},
    {"title": "회복의 시편 — 시편은 126:1-6", "passage_raw": "시편은 126:1-6", "bible_book": "시", "chapter_start": 126, "testament": "OT", "theme": "회복의 노래", "keywords": ["회복", "노래", "씨", "수확"]},
    {"title": "하나님의 말씀 — 시편은 119:1-8", "passage_raw": "시편은 119:1-8", "bible_book": "시", "chapter_start": 119, "testament": "OT", "theme": "법의 기쁨", "keywords": ["법", "말씀", "지킴", "빛"]},
    {"title": "하나님의 군사 — 데살로니전후서에는 5:4-11", "passage_raw": "데살로니전후서에는 5:4-11", "bible_book": "살전후", "chapter_start": 5, "testament": "NT", "theme": "영적 무기", "keywords": ["무기", "전쟁", "믿음", "구원"]},
    {"title": "은사의 다양성 — 로마서는 12:3-8", "passage_raw": "로마서는 12:3-8", "bible_book": "롬", "chapter_start": 12, "testament": "NT", "theme": "은사의 사용", "keywords": ["은사", "봉사", "기부", "자비"]},
    {"title": "하나님의 나라 — 마가복음은 4:26-34", "passage_raw": "마가복음은 4:26-34", "bible_book": "막", "chapter_start": 4, "testament": "NT", "theme": "나라의 비유", "keywords": ["나라", "비유", "종자", "성장"]},
    {"title": "사랑의 실천 — 요한일서에는 3:11-24", "passage_raw": "요한일서에는 3:11-24", "bible_book": "일", "chapter_start": 3, "testament": "NT", "theme": "사랑의 실천", "keywords": ["사랑", "실천", "형제", "생명"]},
    {"title": "기도의 권능 — 야고보서에는 5:13-20", "passage_raw": "야고보서에는 5:13-20", "bible_book": "야", "chapter_start": 5, "testament": "NT", "theme": "기도의 권능", "keywords": ["기도", "권능", "회개", "구원"]},
    {"title": "희생과 감사 — 히브리서에는 13:1-16", "passage_raw": "히브리서에는 13:1-16", "bible_book": "히", "chapter_start": 13, "testament": "NT", "theme": "희생의 예배", "keywords": ["희생", "감사", "선한 행위", "봉사"]},
    {"title": "하나님의 심판과 희망 — 아모스서는 5:18-24", "passage_raw": "아모스서는 5:18-24", "bible_book": "암", "chapter_start": 5, "testament": "OT", "theme": "정의의 물", "keywords": ["심판", "정의", "물", "공의"]},
    {"title": "하나님의 위로 — 이사야서는 41:8-16", "passage_raw": "이사야서는 41:8-16", "bible_book": "사", "chapter_start": 41, "testament": "OT", "theme": "하나님의 동행", "keywords": ["동행", "위로", "강림", "도움"]},
    {"title": "새 마음의 약속 — 에스겔서는 36:22-36", "passage_raw": "에스겔서는 36:22-36", "bible_book": "겔", "chapter_start": 36, "testament": "OT", "theme": "새 마음과 새 영", "keywords": ["새 마음", "새 영", "정결", "거룩"]},
    {"title": "하나님의 구원 — 호세아서는 14:1-9", "passage_raw": "호세아서는 14:1-9", "bible_book": "호", "chapter_start": 14, "testament": "OT", "theme": "회개의 권면", "keywords": ["회개", "용서", "치유", "돌이킴"]},
    {"title": "하나님의 주권 — 다니엘서는 4:30-37", "passage_raw": "다니엘서는 4:30-37", "bible_book": "단", "chapter_start": 4, "testament": "OT", "theme": "하나님의 주권", "keywords": ["주권", "왕", "겸손", "영광"]},
    {"title": "하나님의 지혜 — 욥기는 38:1-11", "passage_raw": "욥기는 38:1-11", "bible_book": "욥", "chapter_start": 38, "testament": "OT", "theme": "하나님의 지혜", "keywords": ["지혜", "질문", "권능", "창조"]},
    {"title": "기쁨의 비결 — 전도서에는 3:12-26", "passage_raw": "전도서에는 3:12-26", "bible_book": "전", "chapter_start": 3, "testament": "OT", "theme": "기쁨의 비결", "keywords": ["기쁨", "시간", "선", "하나님"]},
    {"title": "하나님의 약속 — 민수기 14:1-10", "passage_raw": "민수기 14:1-10", "bible_book": "민", "chapter_start": 14, "testament": "OT", "theme": "약속의 땅 신뢰", "keywords": ["약속", "신뢰", "불신", "심판"]},
    {"title": "하나님의 인도 — 신명기 1:19-28", "passage_raw": "신명기 1:19-28", "bible_book": "신", "chapter_start": 1, "testament": "OT", "theme": "약속의 땅으로", "keywords": ["인도", "약속", "공포", "불신"]},
    {"title": "하나님의 심판과 은혜 — 나훰서는 1:1-15", "passage_raw": "나훰서는 1:1-15", "bible_book": "눙", "chapter_start": 1, "testament": "OT", "theme": "심판과 은혜", "keywords": ["심판", "은혜", "주의", "안위"]},
    {"title": "하나님의 정의 — 하박국은 2:1-20", "passage_raw": "하박국은 2:1-20", "bible_book": "합", "chapter_start": 2, "testament": "OT", "theme": "의인은 믿음으로 살리라", "keywords": ["정의", "믿음", "기다림", "답"]},
    {"title": "회개의 권면 — 스바냐서는 1:14-18", "passage_raw": "스바냐서는 1:14-18", "bible_book": "습", "chapter_start": 1, "testament": "OT", "theme": "주의의 날", "keywords": ["주의 날", "심판", "회개", "모임"]},
    {"title": "성전 회복 — 학개서는 1:1-14", "passage_raw": "학개서는 1:1-14", "bible_book": "학", "chapter_start": 1, "testament": "OT", "theme": "성전 재건축", "keywords": ["성전", "재건축", "하나님", "영광"]},
    {"title": "메시아의 오심 — 스가랴서는 14:1-9", "passage_raw": "스가랴서는 14:1-9", "bible_book": "슥", "chapter_start": 14, "testament": "OT", "theme": "주의 날", "keywords": ["메시아", "구원", "물", "빛"]},
    {"title": "언약의 회복 — 말라기는 3:6-12", "passage_raw": "말라기는 3:6-12", "bible_book": "말", "chapter_start": 3, "testament": "OT", "theme": "십일조와 복", "keywords": ["십일조", "복", "언약", "회개"]},
    {"title": "죄 사함의 기쁨 — 시편은 32:1-11", "passage_raw": "시편은 32:1-11", "bible_book": "시", "chapter_start": 32, "testament": "OT", "theme": "죄의 사함", "keywords": ["사함", "죄", "기쁨", "은혜"]},
    {"title": "하나님의 사랑 — 아모스서는 7:12-17", "passage_raw": "아모스서는 7:12-17", "bible_book": "암", "chapter_start": 7, "testament": "OT", "theme": "예언자의 부르심", "keywords": ["부르심", "예언자", "왕", "경고"]},
    {"title": "하나님의 구원 — 오바디아서는 1:1-21", "passage_raw": "오바디아서는 1:1-21", "bible_book": "옵", "chapter_start": 1, "testament": "OT", "theme": "에돔의 심판", "keywords": ["심판", "구원", "주", "시온"]},
    {"title": "하나님의 은혜 — 요한복음은 1:1-18", "passage_raw": "요한복음은 1:1-18", "bible_book": "요", "chapter_start": 1, "testament": "NT", "theme": "말씀의 신성", "keywords": ["말씀", "신성", "빛", "은혜"]},
    {"title": "새 시작 — 창세기 2:1-7", "passage_raw": "창세기 2:1-7", "bible_book": "창", "chapter_start": 2, "testament": "OT", "theme": "안식과 인간 창조", "keywords": ["안식", "창조", "인간", "생명"]},
    {"title": "믿음의 시험 — 창세기 22:1-14", "passage_raw": "창세기 22:1-14", "bible_book": "창", "chapter_start": 22, "testament": "OT", "theme": "아브라함의 시험", "keywords": ["시험", "믿음", "희생", "제공"]},
    {"title": "하나님의 계획 — 요한계시록은 21:1-22:5", "passage_raw": "요한계시록은 21:1-22:5", "bible_book": "계", "chapter_start": 21, "testament": "NT", "theme": "새 예루살렘", "keywords": ["새 예루살렘", "거룩", "빛", "생명"]},
]


def generate_seed_dataset(output_path: str = None) -> List[Dict]:
    """시드 데이터셋을 생성합니다 (100건)"""
    if output_path is None:
        output_path = "data/sermon_corpus/raw/seed_sermons.jsonl"
    
    records = []
    for i, item in enumerate(SEED_SERMON_DATA):
        record = {
            "record_id": f"seed_{i+1:04d}",
            "source": "seed",
            "title": item["title"],
            "passage_raw": item["passage_raw"],
            "bible_book": item["bible_book"],
            "chapter_start": item["chapter_start"],
            "testament": item["testament"],
            "theme": item["theme"],
            "keywords": item["keywords"],
            "collected_at": datetime.utcnow().isoformat(),
        }
        records.append(record)
    
    # 저장
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"시드 데이터 {len(records)}건 저장 완료: {output_path}")
    return records
# DBMA Sermon Corpus - 설교은행 수집기
# SermonBank에서 설교 제목 + 본문 참조 쌍을 수집

import json
import hashlib
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup


def compute_dedupe_key(title: str, passage_raw: str) -> str:
    """제목+본문 참조로 중복 제거 키를 만든다. SermonRecord.dedupe_key와
    SermonBankCollector.generate_dedupe_key가 이 정의 하나만 공유하도록
    — 각자 재구현하면 둘이 어긋나는 사고를 방지."""
    content = f"{title.strip().lower()}|{passage_raw.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class SermonRecord:
    """설교 기록 (제목-본문 쌍)"""
    record_id: str
    source: str
    title: str
    passage_raw: str  # 원본 본문 참조 (예: "고린도전서 13:4-7")
    bible_book: str  # 성경 책명 (예: "고린도전서")
    chapter_start: int  # 시작 장
    chapter_end: Optional[int]  # 끝 장 (범위 없는 경우 None)
    verse_start: Optional[int]  # 시작 절
    verse_end: Optional[int]  # 끝 절
    preacher: Optional[str]  # 설교자
    published_date: Optional[str]  # 발행일 (YYYY-MM-DD)
    source_url: str
    collected_at: str  # 수집 시각 (ISO format)

    @property
    def dedupe_key(self) -> str:
        """[버그 수정] save_to_jsonl()이 참조하는데 필드가 없어
        AttributeError로 항상 실패하던 것을 수정 — title/passage_raw의
        파생값이라 저장 필드가 아니라 property로 둔다."""
        return compute_dedupe_key(self.title, self.passage_raw)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'SermonRecord':
        return SermonRecord(**data)


# [버그 수정] 클래스 바디의 dict comprehension은 클래스 네임스페이스를
# 못 본다(파이썬의 잘 알려진 스코프 규칙 — comprehension은 자체 스코프를
# 가져서 enclosing 함수/모듈 스코프만 보이고 class 스코프는 건너뜀).
# BOOK_CHAPTER_LIMITS 안의 컴프리헨션들이 클래스 속성으로 정의된
# MAX_VERSES_PER_CHAPTER를 참조하려다 NameError가 났던 것이 바로 이
# 문제 — 모듈 레벨 상수로 옮겨서 해결.
MAX_VERSES_PER_CHAPTER = 176


class BibleReferenceParser:
    """본문 참조 파서 (한국어 성경 책명 → 구조화된 데이터)
    
    4단계 검증 방식:
    1. 성경책 별칭이 정확히 일치
    2. 장/절 문법 검증
    3. 문맥 신호 확인
    4. 성경 실제 범위 검증
    """
    
    # 66권 성경 책명 매핑 (alias → OSIS 코드)
    BOOK_ALIASES = {
        "창세기": "Genesis", "genesis": "Genesis", "gen": "Genesis", "창": "Genesis",
        "출애굽기": "Exodus", "출": "Exodus", "exod": "Exodus", "ex": "Exodus",
        "레위기": "Leviticus", "레": "Leviticus", "lev": "Leviticus",
        "민수기": "Numbers", "민": "Numbers", "num": "Numbers",
        "신명기": "Deuteronomy", "신": "Deuteronomy", "deut": "Deuteronomy",
        "여호수아": "Joshua", "수": "Joshua",
        "판사": "Judges", "삐": "Judges", "judg": "Judges",
        "루트": "Ruth", "룻": "Ruth", "rut": "Ruth",
        "사무엘상": "1 Samuel", "1사무엘": "1 Samuel", "1sam": "1 Samuel",
        "사무엘하": "2 Samuel", "2사무엘": "2 Samuel", "2sam": "2 Samuel",
        "열왕기상": "1 Kings", "1열왕": "1 Kings", "1kgs": "1 Kings",
        "열왕기하": "2 Kings", "2열왕": "2 Kings", "2kgs": "2 Kings",
        "역대상": "1 Chronicles", "1역대": "1 Chronicles", "1chr": "1 Chronicles",
        "역대하": "2 Chronicles", "2역대": "2 Chronicles", "2chr": "2 Chronicles",
        "에스라": "Ezra", "esr": "Ezra",
        "느헤미야": "Nehemiah", "느": "Nehemiah", "neh": "Nehemiah",
        "에스더": "Esther", "에": "Esther", "est": "Esther",
        "욥": "Job", "job": "Job",
        "시편": "Psalms", "시": "Psalms", "ps": "Psalms", "psa": "Psalms", "시편": "Psalms",
        "잠언": "Proverbs", "잠": "Proverbs", "prov": "Proverbs", "pr": "Proverbs",
        "전도서": "Ecclesiastes", "전": "Ecclesiastes", "ecc": "Ecclesiastes", "전": "Ecclesiastes",
        "아가": "Song of Solomon", "아": "Song of Solomon", "song": "Song of Solomon", "아": "Song of Solomon",
        "이사야": "Isaiah", "사": "Isaiah", "isa": "Isaiah",
        "예레미야": "Jeremiah", "렘": "Jeremiah", "jer": "Jeremiah",
        "예레미야애가": "Lamentations", "렘애": "Lamentations", "lam": "Lamentations",
        "에스겔": "Ezekiel", "겔": "Ezekiel", "ezek": "Ezekiel",
        "다니엘": "Daniel", "단": "Daniel", "dan": "Daniel",
        "호세아": "Hosea", "호": "Hosea", "hos": "Hosea",
        "요엘": "Joel", "욜": "Joel", "joel": "Joel",
        "아모스": "Amos", "암": "Amos", "amos": "Amos",
        "오바댜": "Obadiah", "옵": "Obadiah", "obad": "Obadiah",
        "요나": "Jonah", "욘": "Jonah", "jonah": "Jonah",
        "미가": "Micah", "미": "Micah", "mic": "Micah",
        "나훔": "Nahum", "남": "Nahum", "nah": "Nahum",
        "하박국": "Habakkuk", "합": "Habakkuk", "hab": "Habakkuk",
        "스바냐": "Zephaniah", "습": "Zephaniah", "zeph": "Zephaniah",
        "학개": "Haggai", "학": "Haggai", "hag": "Haggai",
        "스가랴": "Zechariah", "슥": "Zechariah", "zech": "Zechariah",
        "말라기": "Malachi", "말": "Malachi", "mal": "Malachi",
        "마태복음": "Matthew", "마": "Matthew", "mat": "Matthew", "마태": "Matthew",
        "마가복음": "Mark", "막": "Mark", "mrk": "Mark", "마가": "Mark",
        "누가복음": "Luke", "눅": "Luke", "luk": "Luke", "누가": "Luke",
        "요한복음": "John", "요": "John", "john": "John", "요한": "John",
        "사도행전": "Acts", "행": "Acts", "acts": "Acts",
        "로마서": "Romans", "롬": "Romans", "rom": "Romans",
        "고린도전서": "1 Corinthians", "고전": "1 Corinthians", "1cor": "1 Corinthians",
        "고린도후서": "2 Corinthians", "고후": "2 Corinthians", "2cor": "2 Corinthians",
        "갈라디아서": "Galatians", "갈": "Galatians", "gal": "Galatians",
        "에베소서": "Ephesians", "엡": "Ephesians", "eph": "Ephesians",
        "빌립보서": "Philippians", "빌": "Philippians", "phil": "Philippians",
        "골로새서": "Colossians", "골": "Colossians", "col": "Colossians",
        "데살로니가전서": "1 Thessalonians", "데전": "1 Thessalonians", "1thess": "1 Thessalonians",
        "데살로니가후서": "2 Thessalonians", "데후": "2 Thessalonians", "2thess": "2 Thessalonians",
        "디모데전서": "1 Timothy", "딤전": "1 Timothy", "1tim": "1 Timothy",
        "디모데후서": "2 Timothy", "딤후": "2 Timothy", "2tim": "2 Timothy",
        "디도서": "Titus", "딛": "Titus", "tit": "Titus",
        "빌레몬서": "Philemon", "몬": "Philemon", "phm": "Philemon",
        "히브리서": "Hebrews", "히": "Hebrews", "heb": "Hebrews",
        "야고보서": "James", "약": "James", "james": "James",
        "벧전": "1 Peter", "1베드": "1 Peter", "1pet": "1 Peter",
        "벧후": "2 Peter", "2베드": "2 Peter", "2pet": "2 Peter",
        "요일": "1 John", "1요한": "1 John", "1john": "1 John",
        "요이": "2 John", "2요한": "2 John", "2john": "2 John",
        "요삼": "3 John", "3요한": "3 John", "3john": "3 John",
        "유다서": "Jude", "유": "Jude", "jude": "Jude",
        "요한계시록": "Revelation", "계": "Revelation", "rev": "Revelation",
    }
    
    # [버그 수정, 2026-07-22] 아래 제너레이터 패턴({i: N for i in
    # range(1, N+1)})은 "책의 장(chapter) 수"를 "그 책 모든 장의 최대
    # 절(verse) 수"로 잘못 재사용하고 있었다 — 예: 로마서는 16장까지
    # 있는데, 그 "16"을 모든 장의 절 상한으로도 써서 로마서 8:28(로마서
    # 8장은 실제로 39절까지 있음)처럼 극히 정상적인 참조가 kind=
    # "rejected"로 잘못 걸러지는 사고가 실측 확인됨. 66권 전체의 정확한
    # 장별 절수 데이터가 이 저장소에 없어(만들어내지 않는다는 원칙상
    # 임의로 지어내지 않음), 제너레이터 패턴 부분은 안전한 전역 상한
    # MAX_VERSES_PER_CHAPTER(176 = 시편 119편, 성경에서 가장 긴 장 —
    # 실존하는 값이지 추정치가 아님)로 대체한다. 이러면 진짜 터무니없는
    # 값(예: 999절)은 여전히 걸러내면서 실제 구절을 잘못 거부하지 않는다.
    # 아래 Ruth/Lamentations/Obadiah/Philemon/2 John/3 John/Jude는 장 수가
    # 적어 손으로 정확한 실제 절수를 넣은 것으로 보여(예: 애가 3장=66절은
    # 실제 애가 3장의 절수와 일치) 그대로 유지 — 검증 없이 건드리지 않는다.
    # (MAX_VERSES_PER_CHAPTER는 모듈 레벨 상수 — 위 클래스 정의 앞 참고)

    # 성경책 장 최대값 (책 → {장 → 최대절})
    BOOK_CHAPTER_LIMITS = {
        "Genesis": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 51)},
        "Exodus": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 41)},
        "Leviticus": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 35)},
        "Numbers": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 55)},
        "Deuteronomy": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 53)},
        "Joshua": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 25)},
        "Judges": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 22)},
        "Ruth": {1: 22, 2: 23, 3: 18, 4: 22},
        "1 Samuel": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 32)},
        "2 Samuel": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 27)},
        "1 Kings": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 29)},
        "2 Kings": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 26)},
        "1 Chronicles": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 30)},
        "2 Chronicles": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 37)},
        "Ezra": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 11)},
        "Nehemiah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 14)},
        "Esther": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 11)},
        "Job": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 43)},
        "Psalms": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 151)},
        "Proverbs": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 32)},
        "Ecclesiastes": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 15)},
        "Song of Solomon": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 9)},
        "Isaiah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 67)},
        "Jeremiah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 53)},
        "Lamentations": {1: 22, 2: 22, 3: 66, 4: 22, 5: 22},
        "Ezekiel": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 49)},
        "Daniel": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 13)},
        "Hosea": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 15)},
        "Joel": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "Amos": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 10)},
        "Obadiah": {1: 21},
        "Jonah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 5)},
        "Micah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 8)},
        "Nahum": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "Habakkuk": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "Zephaniah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "Haggai": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 3)},
        "Zechariah": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 15)},
        "Malachi": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 5)},
        "Matthew": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 29)},
        "Mark": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 17)},
        "Luke": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 25)},
        "John": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 22)},
        "Acts": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 29)},
        "Romans": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 17)},
        "1 Corinthians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 17)},
        "2 Corinthians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 14)},
        "Galatians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 7)},
        "Ephesians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 7)},
        "Philippians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 5)},
        "Colossians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 5)},
        "1 Thessalonians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 6)},
        "2 Thessalonians": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "1 Timothy": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 7)},
        "2 Timothy": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 5)},
        "Titus": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "Philemon": {1: 25},
        "Hebrews": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 14)},
        "James": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 6)},
        "1 Peter": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 6)},
        "2 Peter": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 4)},
        "1 John": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 6)},
        "2 John": {1: 13},
        "3 John": {1: 14},
        "Jude": {1: 25},
        "Revelation": {i: MAX_VERSES_PER_CHAPTER for i in range(1, 23)},
    }
    
    # 부정 표현 목록 (오탐 방지)
    NEGATIVE_PHRASES = [
        "계획", "계약", "계산", "계정",
        "출석", "출발", "출입",
        "시작", "시스템", "시청",
        "요약", "요청", "요금",
        "전도사", "전문", "전략",
    ]
    
    # 문맥 마커 (본문 참조로 인정하는 문맥)
    CONTEXT_MARKERS = ["본문", "성경본문", "말씀", "성구", "scripture"]
    
    # 열린 표현 (자동 확정하지 않는 표현)
    OPEN_EXPRESSIONS = ["이하", "상반절", "중심", "전반부", "후반부", "참조", "관련"]
    
    def __init__(self):
        # 긴 별칭을 먼저 배치한 정규식 패턴 컴파일
        self._book_pattern = self._build_book_pattern()
        # 장:절 패턴 컴파일
        self._cross_chapter_re = re.compile(
            rf"""
            ({self._book_pattern})
            \s*
            (?P<start_ch>\d{{1,3}})
            \s*[:：]\s*
            (?P<start_vs>\d{{1,3}})
            \s*[-–—~～]\s*
            (?P<end_ch>\d{{1,3}})
            \s*[:：]\s*
            (?P<end_vs>\d{{1,3}})
            """,
            re.VERBOSE | re.IGNORECASE,
        )
        self._same_chapter_re = re.compile(
            rf"""
            ({self._book_pattern})
            \s*
            (?P<chapter>\d{{1,3}})
            \s*[:：]\s*
            (?P<start_verse>\d{{1,3}})
            \s*[-–—~～]\s*
            (?P<end_verse>\d{{1,3}})
            (?!\s*[:：]\s*\d)
            """,
            re.VERBOSE | re.IGNORECASE,
        )
        self._single_verse_re = re.compile(
            rf"""
            ({self._book_pattern})
            \s*
            (?P<chapter>\d{{1,3}})
            \s*[:：]\s*
            (?P<verse>\d{{1,3}})
            (?!\s*[-–—~～]\s*\d)
            (?!\s*[:：]\s*\d)
            """,
            re.VERBOSE | re.IGNORECASE,
        )
        self._chapter_only_re = re.compile(
            rf"""
            ({self._book_pattern})
            \s*
            (?P<chapter>\d{{1,3}})
            \s*장
            (?!\s*[:：]\s*\d)
            """,
            re.VERBOSE | re.IGNORECASE,
        )
    
    def _build_book_pattern(self) -> str:
        """책명 별칭으로부터 정규식 패턴 생성 (긴 별칭 우선)"""
        aliases = sorted(self.BOOK_ALIASES.keys(), key=len, reverse=True)
        escaped = [re.escape(a) for a in aliases]
        return "|".join(escaped)
    
    def parse(self, raw: str, context: Optional[str] = None) -> Dict:
        """
        원본 본문 참조를 파싱하여 구조화된 데이터로 변환.
        
        4단계 검증:
        1. 성경책 별칭 일치
        2. 장/절 문법 검증
        3. 문맥 신호 확인
        4. 성경 실제 범위 검증
        
        Args:
            raw: 원본 본문 참조 (예: "고린도전서 13:4-7")
            context: 본문이 발견된 문맥 (선택사항)
        
        Returns:
            {
                "bible_book": "1 Corinthians",
                "chapter_start": 13,
                "chapter_end": 13,
                "verse_start": 4,
                "verse_end": 7,
                "confidence": 0.95,
                "kind": "confirmed",  # "confirmed" | "open_ended" | "ambiguous" | "rejected"
            }
        """
        if not raw or not raw.strip():
            return {
                "bible_book": None,
                "chapter_start": None,
                "chapter_end": None,
                "verse_start": None,
                "verse_end": None,
                "confidence": 0.0,
                "kind": "rejected",
            }

        # 단계 1: 책명 + 장/절 패턴 매칭 (우선순위 순)
        match_result = self._try_match(raw)
        
        if match_result["kind"] == "rejected":
            return match_result

        # 단계 2: 성경 실제 범위 검증
        match_result = self._validate_bible_limits(match_result)
        
        if match_result["kind"] == "rejected":
            return match_result

        # 단계 3: 문맥 신호 확인 (중간 신뢰도 결과에 대해)
        if match_result["confidence"] < 0.8 and context:
            match_result = self._check_context(match_result, context)

        # 단계 4: 열린 표현 처리
        match_result = self._check_open_expressions(match_result, raw)

        return match_result
    
    def _try_match(self, raw: str) -> Dict:
        """패턴 매칭 (우선순위 순: 교차장 → 동일장범위 → 단일절 → 장전체)"""
        # 교차장 절 범위: 창 1:1-2:3
        m = self._cross_chapter_re.search(raw)
        if m:
            book = self._resolve_book(m.group(1))
            return {
                "bible_book": book,
                "chapter_start": int(m.group("start_ch")),
                "chapter_end": int(m.group("end_ch")),
                "verse_start": int(m.group("start_vs")),
                "verse_end": int(m.group("end_vs")),
                "confidence": 0.85,
                "kind": "confirmed",
            }

        # 동일 장 절 범위: 요 3:16-21
        m = self._same_chapter_re.search(raw)
        if m:
            book = self._resolve_book(m.group(1))
            return {
                "bible_book": book,
                "chapter_start": int(m.group("chapter")),
                "chapter_end": int(m.group("chapter")),
                "verse_start": int(m.group("start_verse")),
                "verse_end": int(m.group("end_verse")),
                "confidence": 0.80,
                "kind": "confirmed",
            }

        # 단일 절: 롬 8:28
        m = self._single_verse_re.search(raw)
        if m:
            book = self._resolve_book(m.group(1))
            return {
                "bible_book": book,
                "chapter_start": int(m.group("chapter")),
                "chapter_end": int(m.group("chapter")),
                "verse_start": int(m.group("verse")),
                "verse_end": int(m.group("verse")),
                "confidence": 0.75,
                "kind": "confirmed",
            }

        # 장 전체: 요한복음 3장
        m = self._chapter_only_re.search(raw)
        if m:
            book = self._resolve_book(m.group(1))
            return {
                "bible_book": book,
                "chapter_start": int(m.group("chapter")),
                "chapter_end": int(m.group("chapter")),
                "verse_start": None,
                "verse_end": None,
                "confidence": 0.60,
                "kind": "chapter_only",
            }

        return {
            "bible_book": None,
            "chapter_start": None,
            "chapter_end": None,
            "verse_start": None,
            "verse_end": None,
            "confidence": 0.0,
            "kind": "rejected",
        }
    
    def _resolve_book(self, alias: str) -> Optional[str]:
        """별칭을 OSIS 책명으로 해결"""
        return self.BOOK_ALIASES.get(alias.casefold())
    
    def _validate_bible_limits(self, result: Dict) -> Dict:
        """성경 실제 범위 검증"""
        book = result.get("bible_book")
        ch = result.get("chapter_start")
        vs = result.get("verse_start")
        
        if not book or not ch:
            result["kind"] = "rejected"
            result["confidence"] = 0.0
            return result
        
        limits = self.BOOK_CHAPTER_LIMITS.get(book)
        if not limits:
            # 범위 데이터가 없는 책은 통과 (안전 조치)
            return result
        
        # 장 검증
        if ch not in limits:
            result["kind"] = "rejected"
            result["confidence"] = 0.0
            return result
        
        max_verses = limits[ch]
        
        # 절 검증
        if vs and vs > max_verses:
            result["kind"] = "rejected"
            result["confidence"] = 0.0
            return result
        
        # 끝 장/절 검증
        end_ch = result.get("chapter_end")
        end_vs = result.get("verse_end")
        
        if end_ch:
            if end_ch < ch or end_ch not in limits:
                result["kind"] = "rejected"
                result["confidence"] = 0.0
                return result
            # [버그 수정] limits[end_ch]는 dict가 아니라 int(그 장의 최대
            # 절수)라 chapter_limits.get(999, 9999)는 항상 폴백 9999로
            # 빠지는 죽은 코드였다 — 창세기 1:1-2:999(창세기 2장은 25절
            # 밖에 없음)가 잘못 confirmed 되는 것으로 실측 확인. limits는
            # dict[int, int](장→최대절)이므로 바로 int 조회로 수정.
            max_vers_for_end_ch = limits.get(end_ch, 9999)
            if end_vs and end_vs > max_vers_for_end_ch:
                result["kind"] = "rejected"
                result["confidence"] = 0.0
                return result
        
        if end_vs and vs and end_vs < vs:
            result["kind"] = "rejected"
            result["confidence"] = 0.0
            return result
        
        return result
    
    def _check_context(self, result: Dict, context: str) -> Dict:
        """문맥 신호 확인"""
        if not context:
            return result
        
        context_lower = context.lower()
        for marker in self.CONTEXT_MARKERS:
            if marker in context_lower:
                result["confidence"] = min(result["confidence"] + 0.15, 1.0)
                break
        
        # 짧은 약어는 문맥이 없을 때 신뢰도 낮춤
        book = result.get("bible_book")
        if book and self._is_short_alias(result.get("_raw_alias", "")):
            if not any(m in context for m in self.CONTEXT_MARKERS):
                result["confidence"] -= 0.15
        
        return result
    
    def _check_open_expressions(self, result: Dict, raw: str) -> Dict:
        """열린 표현 확인"""
        raw_lower = raw.lower()
        for expr in self.OPEN_EXPRESSIONS:
            if expr in raw_lower:
                result["kind"] = "open_ended"
                result["confidence"] -= 0.25
                break
        
        return result
    
    def _is_short_alias(self, alias: str) -> bool:
        """짧은 약어인지 확인 (1-2글자 한글)"""
        return len(alias.strip()) <= 2
    
    def extract_all_passages(self, text: str) -> List[Dict]:
        """텍스트에서 모든 본문 참조를 추출 (중복 제거 포함)"""
        candidates = []
        occupied = []
        
        for pattern in [self._cross_chapter_re, self._same_chapter_re, 
                        self._single_verse_re, self._chapter_only_re]:
            for m in pattern.finditer(text):
                span = m.span()
                # 중복 확인
                if any(span[0] < o[1] and o[0] < span[1] for o in occupied):
                    continue
                
                book = self._resolve_book(m.group(1))
                result = {
                    "bible_book": book,
                    "raw": m.group(0),
                    "span": span,
                    "confidence": 0.7,
                    "kind": "confirmed",
                }
                
                # 장/절 정보 추출
                if "start_ch" in m.groupdict():
                    result["chapter_start"] = int(m.group("start_ch"))
                    result["chapter_end"] = int(m.group("end_ch"))
                    result["verse_start"] = int(m.group("start_vs"))
                    result["verse_end"] = int(m.group("end_vs"))
                elif "chapter" in m.groupdict():
                    result["chapter_start"] = int(m.group("chapter"))
                    result["chapter_end"] = int(m.group("chapter"))
                    if "start_verse" in m.groupdict():
                        result["verse_start"] = int(m.group("start_verse"))
                        result["verse_end"] = int(m.group("end_verse"))
                    elif "verse" in m.groupdict():
                        v = int(m.group("verse"))
                        result["verse_start"] = v
                        result["verse_end"] = v
                    else:
                        result["verse_start"] = None
                        result["verse_end"] = None
                
                candidates.append(result)
                occupied.append(span)
        
        return sorted(candidates, key=lambda x: x["span"])


class SermonBankCollector:
    """
    SermonBank에서 설교 제목 + 본문 참조 쌍을 수집합니다.
    
    - robots.txt 준수 (PoliteFetcher)
    - 중복 제거 (dedupe_key)
    - JSONL 저장 (raw/sermonbank.jsonl)
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get("source_id", "sermonbank")
        self.urls = config.get("urls", [])
        self.storage_path = Path(config.get("storage", {}).get(
            "raw_path", "data/sermon_corpus/raw/sermonbank.jsonl"
        ))
        
        # BibleReferenceParser 초기화
        self.bible_parser = BibleReferenceParser()
        
        # 중복 키 집합
        self._seen_keys: set = set()
        
        # 통계
        self.stats = {
            "urls_processed": 0,
            "sermons_collected": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }
    
    def generate_dedupe_key(self, title: str, passage_raw: str) -> str:
        """중복 제거 키 생성 — compute_dedupe_key()/SermonRecord.dedupe_key와
        동일 정의 공유(모듈 상단 참고)."""
        return compute_dedupe_key(title, passage_raw)
    
    def is_duplicate(self, dedupe_key: str) -> bool:
        """중복 검사"""
        if dedupe_key in self._seen_keys:
            return True
        self._seen_keys.add(dedupe_key)
        return False
    
    def parse_sermon_from_html(self, html: str, source_url: str) -> List[SermonRecord]:
        """
        HTML에서 설교 항목들을 파싱합니다.
        
        Args:
            html: HTML 본문
            source_url: 원본 URL
        
        Returns:
            SermonRecord 목록
        """
        records = []
        soup = BeautifulSoup(html, "html.parser")

        # SermonBank 실제 구조(그누보드 게시판, 2026-07-22 실측 확인):
        # 항목을 감싸는 div/li 컨테이너가 없고, 각 설교가 <table> 블록으로
        # 반복된다. 유일하게 안정적인 앵커는 상세글 링크
        # (href*="bo_table=sermon&wr_id=")이므로 이 <a>를 기준으로 링크의
        # 형제/상위 요소에서 나머지 필드를 찾는다.
        title_links = [
            a for a in soup.find_all("a", href=True)
            if "bo_table=sermon" in a["href"] and "wr_id=" in a["href"]
        ]

        for link_el in title_links:
            try:
                title = link_el.get_text(strip=True)

                # 본문 참조: 제목 <a>를 감싸는 <span class="f_s_list">의
                # 다음 형제 <span class="f_d2_6">.
                title_span = link_el.find_parent("span", class_="f_s_list")
                passage_el = title_span.find_next_sibling("span", class_="f_d2_6") if title_span else None
                passage_raw = passage_el.get_text(strip=True) if passage_el else ""

                # 설교자: 제목이 속한 첫 <tr> 행의 class="f_d1_6" 셀 안
                # <span class="member">.
                header_row = link_el.find_parent("tr")
                preacher_el = header_row.find("span", class_="member") if header_row else None
                preacher = preacher_el.get_text(strip=True) if preacher_el else None

                # 날짜: 제목 블록을 감싸는 바깥 <table>(margin:0 0 15px 0)의
                # 세 번째 <tr> — class="bd_sermon_L02" 셀 텍스트 끝부분에
                # YYYY-MM-DD 형식으로 붙어 있다(전용 class 없음).
                block_table = link_el.find_parent(
                    "table", style=lambda v: bool(v) and "margin:0 0 15px 0" in v
                )
                published_date = None
                if block_table:
                    date_cell = block_table.find("td", class_="bd_sermon_L02")
                    if date_cell:
                        date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_cell.get_text())
                        published_date = date_match.group(0) if date_match else None

                # URL: 상세글 링크 자체 (상대경로 -> 절대경로).
                href = link_el.get("href", "")
                sermon_url = str(href) if href else ""
                if sermon_url and not sermon_url.startswith("http"):
                    # 실측 href 형식: "../bbs/board.php?bo_table=sermon&wr_id=NNNNN"
                    sermon_url = "https://sermonbank.net/" + sermon_url.lstrip("./")

                if not title or not passage_raw:
                    continue
                
                # 본문 참조 파싱
                passage_data = self.bible_parser.parse(passage_raw)
                
                # dedupe_key 생성
                dedupe_key = self.generate_dedupe_key(title, passage_raw)
                
                bible_book = passage_data.get("bible_book") or "Unknown"
                chapter_start = passage_data.get("chapter_start") or 0
                
                record = SermonRecord(
                    record_id=f"sb_{dedupe_key}",
                    source=self.source_id,
                    title=title,
                    passage_raw=passage_raw,
                    bible_book=bible_book if bible_book else "Unknown",
                    chapter_start=chapter_start if chapter_start else 0,
                    chapter_end=passage_data.get("chapter_end"),
                    verse_start=passage_data.get("verse_start"),
                    verse_end=passage_data.get("verse_end"),
                    preacher=preacher,
                    published_date=published_date,
                    source_url=str(sermon_url) if sermon_url else str(source_url),
                    collected_at=datetime.utcnow().isoformat(),
                )  # type: ignore[misc]
                
                records.append(record)
                self.stats["sermons_collected"] += 1
                
            except Exception as e:
                self.stats["errors"] += 1
                continue
        
        return records
    
    def collect_from_url(self, url: str, fetcher) -> List[SermonRecord]:
        """URL에서 설교 데이터를 수집합니다"""
        text = fetcher.get_text(url)
        if not text:
            return []

        self.stats["urls_processed"] += 1
        return self.parse_sermon_from_html(text, url)

    @staticmethod
    def _paginate_url(base_url: str, page: int) -> str:
        """게시판 목록 URL에 페이지 번호를 붙인다(그누보드 관례: ?page=N).

        1페이지는 원본 URL 그대로(사이트가 page=1과 무파라미터를 같은
        내용으로 취급하는지 보장이 없어 굳이 덧붙이지 않음)."""
        if page <= 1:
            return base_url
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}page={page}"

    def collect_all(
        self, fetcher, max_records: int = None, max_pages: int = 10
    ) -> List[SermonRecord]:
        """
        모든 출처 URL에서 설교 데이터를 수집합니다.

        [기능 추가] 설교은행 목록 페이지는 한 페이지당 15건만 보여주는데
        이전에는 self.urls에 등록된 URL(첫 페이지)만 그대로 한 번씩 가져와
        매번 15건에서 멈췄다 — 사이트가 page=2, page=3... 파라미터로
        다음 페이지를 제공하는 것을 확인(실측)하고, 다음 페이지가 빈
        결과를 반환할 때까지(또는 max_pages/max_records 도달 시까지)
        순차적으로 이어서 수집하도록 변경.

        Args:
            fetcher: PoliteFetcher 인스턴스
            max_records: 최대 수집 기록 수 (None = 무제한)
            max_pages: 출처 URL 하나당 최대 페이지 수 (과도한 요청 방지)

        Returns:
            SermonRecord 목록
        """
        all_records = []

        for base_url in self.urls:
            for page in range(1, max_pages + 1):
                url = self._paginate_url(base_url, page)
                records = self.collect_from_url(url, fetcher)

                if not records:
                    # 더 이상 항목이 없는 페이지 — 이 출처는 끝
                    break

                if max_records:
                    remaining = max_records - len(all_records)
                    if remaining <= 0:
                        return all_records
                    records = records[:remaining]

                all_records.extend(records)

                if max_records and len(all_records) >= max_records:
                    return all_records

        return all_records
    
    def save_to_jsonl(self, records: List[SermonRecord], path: Optional[Path] = None) -> int:
        """
        기록을 JSONL 파일에 저장합니다.
        
        Returns:
            저장된 기록 수
        """
        if path is None:
            path = self.storage_path
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                # 중복 검사
                if self.is_duplicate(record.dedupe_key):
                    self.stats["duplicates_skipped"] += 1
                    continue
                
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                saved_count += 1
        
        return saved_count
    
    def get_stats(self) -> Dict:
        """수집 통계 반환"""
        return dict(self.stats)
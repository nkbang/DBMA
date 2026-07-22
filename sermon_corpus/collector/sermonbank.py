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


class BibleReferenceParser:
    """본문 참조 파서 (한국어 성경 책명 → 구조화된 데이터)"""
    
    # 한국어 성경 책명 매핑
    BOOK_ALIASES = {
        "창세기": "Genesis",
        "genesis": "Genesis",
        "gen": "Genesis",
        "출애굽기": "Exodus",
        "출": "Exodus",
        "ex": "Exodus",
        "레위기": "Leviticus",
        "레": "Leviticus",
        "lev": "Leviticus",
        "민수기": "Numbers",
        "민": "Numbers",
        "num": "Numbers",
        "신명기": "Deuteronomy",
        "신": "Deuteronomy",
        "deut": "Deuteronomy",
        "여호수아": "Joshua",
        "수": "Joshua",
        "judg": "Judges",
        "사무엘상": "1 Samuel",
        "1사무엘": "1 Samuel",
        "1sam": "1 Samuel",
        "사무엘하": "2 Samuel",
        "2사무엘": "2 Samuel",
        "2sam": "2 Samuel",
        "열왕기상": "1 Kings",
        "1열왕": "1 Kings",
        "1kgs": "1 Kings",
        "열왕기하": "2 Kings",
        "2열왕": "2 Kings",
        "2kgs": "2 Kings",
        "역대상": "1 Chronicles",
        "1역대": "1 Chronicles",
        "1chr": "1 Chronicles",
        "역대하": "2 Chronicles",
        "2역대": "2 Chronicles",
        "2chr": "2 Chronicles",
        "에스라": "Ezra",
        "에스": "Ezra",
        "esd": "Ezra",
        "느헤미야": "Nehemiah",
        "느": "Nehemiah",
        "neh": "Nehemiah",
        "에스더": "Esther",
        "에스": "Esther",
        "est": "Esther",
        "욥": "Job",
        "job": "Job",
        "시편": "Psalms",
        "시": "Psalms",
        "ps": "Psalms",
        "psa": "Psalms",
        "잠언": "Proverbs",
        "잠": "Proverbs",
        "prov": "Proverbs",
        "전도서": "Ecclesiastes",
        "전": "Ecclesiastes",
        "ecc": "Ecclesiastes",
        "아가": "Song of Solomon",
        "아": "Song of Solomon",
        "song": "Song of Solomon",
        "이사야": "Isaiah",
        "사": "Isaiah",
        "isa": "Isaiah",
        "예레미야": "Jeremiah",
        "렘": "Jeremiah",
        "jer": "Jeremiah",
        "예레미야애가": "Lamentations",
        "렘애": "Lamentations",
        "lam": "Lamentations",
        "에스겔": "Ezekiel",
        "겔": "Ezekiel",
        "ezek": "Ezekiel",
        "다니엘": "Daniel",
        "단": "Daniel",
        "dan": "Daniel",
        "호세아": "Hosea",
        "호": "Hosea",
        "hos": "Hosea",
        "요엘": "Joel",
        "욜": "Joel",
        "joel": "Joel",
        "아모스": "Amos",
        "암": "Amos",
        "amos": "Amos",
        "오바댜": "Obadiah",
        "옵": "Obadiah",
        "obad": "Obadiah",
        "요나": "Jonah",
        "욘": "Jonah",
        "jonah": "Jonah",
        "미가": "Micah",
        "미": "Micah",
        "mic": "Micah",
        "나훔": "Nahum",
        "남": "Nahum",
        "nah": "Nahum",
        "하박국": "Habakkuk",
        "합": "Habakkuk",
        "hab": "Habakkuk",
        "스바냐": "Zephaniah",
        "습": "Zephaniah",
        "zeph": "Zephaniah",
        "하갈": "Haggai",
        "학": "Haggai",
        "hag": "Haggai",
        "스가랴": "Zechariah",
        "슥": "Zechariah",
        "zech": "Zechariah",
        "말라기": "Malachi",
        "말": "Malachi",
        "mal": "Malachi",
        "마태복음": "Matthew",
        "마": "Matthew",
        "mat": "Matthew",
        "마태": "Matthew",
        "마가복음": "Mark",
        "막": "Mark",
        "mrk": "Mark",
        "마가": "Mark",
        "누가복음": "Luke",
        "눅": "Luke",
        "luk": "Luke",
        "누가": "Luke",
        "요한복음": "John",
        "요": "John",
        "john": "John",
        "사도행전": "Acts",
        "행": "Acts",
        "acts": "Acts",
        "로마서": "Romans",
        "롬": "Romans",
        "rom": "Romans",
        "고린도전서": "1 Corinthians",
        "고전": "1 Corinthians",
        "1cor": "1 Corinthians",
        "고린도후서": "2 Corinthians",
        "고후": "2 Corinthians",
        "2cor": "2 Corinthians",
        "갈라디아서": "Galatians",
        "갈": "Galatians",
        "gal": "Galatians",
        "에베소서": "Ephesians",
        "엡": "Ephesians",
        "eph": "Ephesians",
        "빌립보서": "Philippians",
        "빌": "Philippians",
        "phil": "Philippians",
        "골로새서": "Colossians",
        "골": "Colossians",
        "col": "Colossians",
        "데살로니가전서": "1 Thessalonians",
        "데전": "1 Thessalonians",
        "1thess": "1 Thessalonians",
        "데살로니가후서": "2 Thessalonians",
        "데후": "2 Thessalonians",
        "2thess": "2 Thessalonians",
        "디모데전서": "1 Timothy",
        "딤전": "1 Timothy",
        "1tim": "1 Timothy",
        "디모데후서": "2 Timothy",
        "딤후": "2 Timothy",
        "2tim": "2 Timothy",
        "디도서": "Titus",
        "딛": "Titus",
        "tit": "Titus",
        "빌레몬서": "Philemon",
        "몬": "Philemon",
        "phm": "Philemon",
        "히브리서": "Hebrews",
        "히": "Hebrews",
        "heb": "Hebrews",
        "야고보서": "James",
        "약": "James",
        "james": "James",
        "벧전": "1 Peter",
        "1베드": "1 Peter",
        "1pet": "1 Peter",
        "벧후": "2 Peter",
        "2베드": "2 Peter",
        "2pet": "2 Peter",
        "요일": "1 John",
        "1요한": "1 John",
        "1john": "1 John",
        "요이": "2 John",
        "2요한": "2 John",
        "2john": "2 John",
        "요삼": "3 John",
        "3요한": "3 John",
        "3john": "3 John",
        "유다서": "Jude",
        "유": "Jude",
        "jude": "Jude",
        "요한계시록": "Revelation",
        "계": "Revelation",
        "rev": "Revelation",
    }
    
    # OSIS 책명 → 한국어 책명 역매핑
    REVERSE_ALIASES = {v: k for k, v in BOOK_ALIASES.items()}
    
    def parse(self, raw: str) -> Dict:
        """
        원본 본문 참조를 파싱하여 구조화된 데이터로 변환.
        
        Args:
            raw: 원본 본문 참조 (예: "고린도전서 13:4-7")
        
        Returns:
            {
                "bible_book": "1 Corinthians",
                "chapter_start": 13,
                "chapter_end": 13,
                "verse_start": 4,
                "verse_end": 7,
            }
        """
        if not raw or not raw.strip():
            return {
                "bible_book": None,
                "chapter_start": None,
                "chapter_end": None,
                "verse_start": None,
                "verse_end": None,
            }

        # 책명 추출
        bible_book = None
        remainder = raw

        # 한국어 책명 매핑 시도
        for ko_name, osis_book in self.BOOK_ALIASES.items():
            if raw.startswith(ko_name):
                bible_book = osis_book
                remainder = raw[len(ko_name):].strip()
                break

        if bible_book is None:
            # 영어 책명 시도
            for ko_name, osis_book in self.BOOK_ALIASES.items():
                if osis_book.lower() in raw.lower():
                    bible_book = osis_book
                    remainder = raw
                    break
            else:
                # 기본값
                bible_book = "Unknown"
                remainder = raw

        # [버그 수정] 이전에는 이 반환값을 어디에도 대입하지 않아
        # chapter_start/verse_start 등이 항상 None으로 남아있었다 —
        # 책명이 어느 쪽 분기에서 잡혔든(한국어/영어/Unknown) 항상
        # 장/절 파싱을 시도한다.
        chapter_start, chapter_end, verse_start, verse_end = self._extract_chapter_verse(remainder)

        return {
            "bible_book": bible_book,
            "chapter_start": chapter_start,
            "chapter_end": chapter_end,
            "verse_start": verse_start,
            "verse_end": verse_end,
        }

    def _extract_chapter_verse(self, raw: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """장/절 정보를 추출합니다. 반환: (chapter_start, chapter_end,
        verse_start, verse_end) — 문자열이 아니라 실제 정수 튜플([버그
        수정] 이전에는 포맷된 문자열만 반환하고 호출부가 이를 버렸다)."""
        # 패턴: 장:절 또는 장:절-절 (예: 13:4-7)
        match = re.search(r'(\d+):(\d+)(?:-(\d+))?', raw)
        if match:
            chapter_start = int(match.group(1))
            verse_start = int(match.group(2))
            verse_end = int(match.group(3)) if match.group(3) else None
            chapter_end = chapter_start  # 범위 없는 경우
            return chapter_start, chapter_end, verse_start, verse_end

        # 장만 있는 경우 (예: "고린도전서 13")
        match = re.search(r'(\d+)$', raw.strip())
        if match:
            chapter_start = int(match.group(1))
            return chapter_start, chapter_start, None, None

        return None, None, None, None


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
        
        # SermonBank 구조에 맞는 선택자 (실제 사이트 구조에 따라 조정 필요)
        sermon_items = soup.find_all("div", class_=["sermon-item", "sermon-card", "item"])
        
        if not sermon_items:
            # 대체 선택자
            sermon_items = soup.find_all("li", class_=["sermon", "item"])
        
        for item in sermon_items:
            try:
                # 제목 추출
                title_el = item.find(class_=["sermon-title", "title", "heading"])
                if not title_el:
                    title_el = item.find("h2") or item.find("h3") or item.find("a")
                title = title_el.get_text(strip=True) if title_el else ""
                
                # 본문 참조 추출
                passage_el = item.find(class_=["sermon-passage", "passage", "scripture"])
                passage_raw = passage_el.get_text(strip=True) if passage_el else ""
                
                # 설교자 추출
                preacher_el = item.find(class_=["sermon-preacher", "preacher", "speaker"])
                preacher = preacher_el.get_text(strip=True) if preacher_el else None
                
                # 날짜 추출
                date_el = item.find(class_=["sermon-date", "date", "published"])
                published_date = date_el.get_text(strip=True) if date_el else None
                
                # URL 추출
                link_el = item.find("a")
                sermon_url = link_el.get("href", "") if link_el else ""
                if sermon_url and not sermon_url.startswith("http"):
                    sermon_url = f"https://sermonbank.net{sermon_url}"
                
                if not title or not passage_raw:
                    continue
                
                # 본문 참조 파싱
                passage_data = self.bible_parser.parse(passage_raw)
                
                # dedupe_key 생성
                dedupe_key = self.generate_dedupe_key(title, passage_raw)
                
                record = SermonRecord(
                    record_id=f"sb_{dedupe_key}",
                    source=self.source_id,
                    title=title,
                    passage_raw=passage_raw,
                    bible_book=passage_data.get("bible_book"),
                    chapter_start=passage_data.get("chapter_start"),
                    chapter_end=passage_data.get("chapter_end"),
                    verse_start=passage_data.get("verse_start"),
                    verse_end=passage_data.get("verse_end"),
                    preacher=preacher,
                    published_date=published_date,
                    source_url=sermon_url or source_url,
                    collected_at=datetime.utcnow().isoformat(),
                )
                
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
    
    def collect_all(self, fetcher, max_records: int = None) -> List[SermonRecord]:
        """
        모든 출처 URL에서 설교 데이터를 수집합니다.
        
        Args:
            fetcher: PoliteFetcher 인스턴스
            max_records: 최대 수집 기록 수 (None = 무제한)
        
        Returns:
            SermonRecord 목록
        """
        all_records = []
        
        for url in self.urls:
            records = self.collect_from_url(url, fetcher)
            
            if max_records:
                remaining = max_records - len(all_records)
                if remaining <= 0:
                    break
                records = records[:remaining]
            
            all_records.extend(records)
        
        return all_records
    
    def save_to_jsonl(self, records: List[SermonRecord], path: Path = None) -> int:
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
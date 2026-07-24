# DBMA Sermon Corpus - 설교 빈도 분석기
# 성경 권별/장별 설교 빈도를 계산합니다.

from collections import Counter, defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PassageFrequency:
    """본문 빈도 기록"""
    bible_book: str  # 성경 책명
    chapter: Optional[int]  # 장 (None인 경우 권 수준)
    verse_range: Optional[str]  # 절 범위 (예: "4-7")
    count: int  # 빈도 수
    percentage: float  # 전체 대비 비율 (%)


@dataclass
class BookLevelFrequency:
    """권별 빈도"""
    bible_book: str
    testament: str  # 구약/신약
    book_number: int  # 성경 내 책 순서 (1-66)
    total_sermons: int
    percentage: float


class FrequencyAnalyzer:
    """
    설교 본문 빈도 분석기.
    
    - 권별 빈도 (book-level)
    - 장별 빈도 (chapter-level)
    - 절별 빈도 (verse-level)
    - 언약별 통계 (구약/신약)
    """
    
    # 성경 책 순서 및 언약 매핑
    BIBLE_BOOKS = [
        # 구약 (39권)
        ("Genesis", 1, "OT"), ("Exodus", 2, "OT"), ("Leviticus", 3, "OT"),
        ("Numbers", 4, "OT"), ("Deuteronomy", 5, "OT"), ("Joshua", 6, "OT"),
        ("Judges", 7, "OT"), ("Ruth", 8, "OT"), ("1 Samuel", 9, "OT"),
        ("2 Samuel", 10, "OT"), ("1 Kings", 11, "OT"), ("2 Kings", 12, "OT"),
        ("1 Chronicles", 13, "OT"), ("2 Chronicles", 14, "OT"), ("Ezra", 15, "OT"),
        ("Nehemiah", 16, "OT"), ("Esther", 17, "OT"), ("Job", 18, "OT"),
        ("Psalms", 19, "OT"), ("Proverbs", 20, "OT"), ("Ecclesiastes", 21, "OT"),
        ("Song of Solomon", 22, "OT"), ("Isaiah", 23, "OT"), ("Jeremiah", 24, "OT"),
        ("Lamentations", 25, "OT"), ("Ezekiel", 26, "OT"), ("Daniel", 27, "OT"),
        ("Hosea", 28, "OT"), ("Joel", 29, "OT"), ("Amos", 30, "OT"),
        ("Obadiah", 31, "OT"), ("Jonah", 32, "OT"), ("Micah", 33, "OT"),
        ("Nahum", 34, "OT"), ("Habakkuk", 35, "OT"), ("Zephaniah", 36, "OT"),
        ("Haggai", 37, "OT"), ("Zechariah", 38, "OT"), ("Malachi", 39, "OT"),
        # 신약 (27권)
        ("Matthew", 40, "NT"), ("Mark", 41, "NT"), ("Luke", 42, "NT"),
        ("John", 43, "NT"), ("Acts", 44, "NT"), ("Romans", 45, "NT"),
        ("1 Corinthians", 46, "NT"), ("2 Corinthians", 47, "NT"), ("Galatians", 48, "NT"),
        ("Ephesians", 49, "NT"), ("Philippians", 50, "NT"), ("Colossians", 51, "NT"),
        ("1 Thessalonians", 52, "NT"), ("2 Thessalonians", 53, "NT"), ("1 Timothy", 54, "NT"),
        ("2 Timothy", 55, "NT"), ("Titus", 56, "NT"), ("Philemon", 57, "NT"),
        ("Hebrews", 58, "NT"), ("James", 59, "NT"), ("1 Peter", 60, "NT"),
        ("2 Peter", 61, "NT"), ("1 John", 62, "NT"), ("2 John", 63, "NT"),
        ("3 John", 64, "NT"), ("Jude", 65, "NT"), ("Revelation", 66, "NT"),
    ]
    
    # 한국어 약어/전체명 -> 영어 전체명 매핑
    KOREAN_ABBREVIATIONS = {
        # 구약 약어
        "창": "Genesis", "창세기": "Genesis",
        "출": "Exodus", "출애굽기": "Exodus",
        "레": "Leviticus", "레위기": "Leviticus",
        "민": "Numbers", "민수기": "Numbers",
        "신": "Deuteronomy", "신명기": "Deuteronomy",
        "수": "Joshua", "여호수아": "Joshua",
        "사": "Judges", "사사기": "Judges",
        "룻": "Ruth", "룻": "Ruth",
        "상": "1 Samuel", "1사무엘": "1 Samuel", "상": "1 Samuel",
        "하": "2 Samuel", "2사무엘": "2 Samuel", "하": "2 Samuel",
        "왕": "1 Kings", "열왕기상": "1 Kings",
        "왕하": "2 Kings", "열왕기하": "2 Kings",
        "상": "1 Chronicles", "대상": "1 Chronicles", "1역사": "1 Chronicles",
        "하": "2 Chronicles", "대하": "2 Chronicles", "2역사": "2 Chronicles",
        "애": "Ezra", "에스라": "Ezra",
        "느": "Nehemiah", "느헤미야": "Nehemiah",
        "에": "Esther", "에스더": "Esther",
        "욥": "Job", "욥": "Job",
        "시": "Psalms", "시편": "Psalms",
        "잠": "Proverbs", "잠언": "Proverbs",
        "전": "Ecclesiastes", "전도서": "Ecclesiastes",
        "송": "Song of Solomon", "찬가": "Song of Solomon", "솔로찬가": "Song of Solomon", "아가": "Song of Solomon",
        "사": "Isaiah", "이사야": "Isaiah",
        "렘": "Jeremiah", "예레미야": "Jeremiah",
        "애": "Lamentations", "예레애가": "Lamentations", "예레미야애가": "Lamentations",
        "겔": "Ezekiel", "에스겔": "Ezekiel",
        "단": "Daniel", "다니엘": "Daniel",
        "호": "Hosea", "호세아": "Hosea",
        " Joel": "Joel", "요엘": "Joel",
        "암": "Amos", "아모스": "Amos",
        "옵": "Obadiah", "오바댜": "Obadiah", "오바디아": "Obadiah",
        "욘": "Jonah", "요나": "Jonah",
        "미": "Micah", "미가": "Micah",
        "눙": "Nahum", "나훰": "Nahum", "나훔": "Nahum",
        "합": "Habakkuk", "하박국": "Habakkuk",
        "습": "Zephaniah", "스바냐": "Zephaniah",
        "학": "Haggai", "학개": "Haggai",
        "슥": "Zechariah", "스가랴": "Zechariah",
        "말": "Malachi", "말라기": "Malachi",
        # 신약 약어
        "마": "Matthew", "마태복음": "Matthew",
        "막": "Mark", "마가복음": "Mark",
        "눅": "Luke", "누가복음": "Luke",
        "요": "John", "요한복음": "John", "요": "John",
        "행": "Acts", "사도행전": "Acts",
        "롬": "Romans", "로마서": "Romans",
        "고전": "1 Corinthians", "고린도전서": "1 Corinthians",
        "고후": "2 Corinthians", "고린도후서": "2 Corinthians",
        "갈": "Galatians", "갈라디아서": "Galatians",
        "엡": "Ephesians", "에베소서": "Ephesians",
        "빌": "Philippians", "빌립보서": "Philippians",
        "골": "Colossians", "골로새서": "Colossians",
        "살전": "1 Thessalonians", "살레전": "1 Thessalonians", "살전후": "1 Thessalonians", "데살로니가전서": "1 Thessalonians",
        "살후": "2 Thessalonians", "살레후": "2 Thessalonians", "데살로니가후서": "2 Thessalonians",
        "딤전": "1 Timothy", "디모데전서": "1 Timothy", "딤전": "1 Timothy",
        "딤후": "2 Timothy", "디모데후서": "2 Timothy", "딤후": "2 Timothy",
        "딛": "Titus", "디도서": "Titus",
        "몬": "Philemon", "빌레몬서": "Philemon",
        "히": "Hebrews", "히브리서": "Hebrews",
        "야": "James", "야고보서": "James", "야": "James",
        "벧전": "1 Peter", "베드로전서": "1 Peter", "벧전": "1 Peter",
        "벧후": "2 Peter", "베드로후서": "2 Peter", "벧후": "2 Peter",
        "일": "1 John", "요한일서": "1 John", "일": "1 John",
        "이": "2 John", "요한이서": "2 John",
        "삼": "3 John", "요한삼서": "3 John",
        "유": "Jude", "유다": "Jude",
        "계": "Revelation", "요한계시록": "Revelation", "계시록": "Revelation", "계": "Revelation",
        # seed_generator에서 사용하는 전체명 매핑 추가
        "아라의 노래": "Song of Solomon",
        "데살로니전전": "1 Thessalonians",
        "데살로니전후": "2 Thessalonians",
        "디모데전": "1 Timothy",
        "디모데후": "2 Timothy",
        "베전전": "1 Peter",
        "베전후": "2 Peter",
        "요한일서": "1 John",
        "요한이서": "2 John",
        "요한삼서": "3 John",
        "요한계시록": "Revelation",
        # 시드 데이터의 일부 Unknown 처리를 위한 추가 매핑
        "에스라": "Ezra",
        "사무엘하": "2 Samuel",
        "열왕기하": "2 Kings",
        "역대상": "1 Chronicles",
        "역대하": "2 Chronicles",
        "디도서": "Titus",
        # 시드 데이터의 2글자 약어 추가 (중복 방지)
        "에스": "Ezra",
        # 시드 데이터의 일부 bible_book 추가
        "다니": "Daniel",
        "디모": "1 Timothy",
        "베전": "1 Peter",
        "로마": "Romans",
        "사도": "Acts",
        "데살": "1 Thessalonians",
        "빌레": "Philemon",
        "유다": "Jude",
        # 시드 데이터의 3글자 bible_book 추가
        "사무엘상": "1 Samuel",
        "역대": "1 Chronicles",
    }
    
    def __init__(self):
        self.book_counter: Counter = Counter()
        self.chapter_counter: Counter = Counter()
        self.verse_counter: Counter = Counter()
        self.testament_counter: Counter = Counter()
        self.total_sermons: int = 0
    
    def add_record(self, bible_book: Optional[str], chapter: Optional[int], 
                   verse_start: Optional[int], verse_end: Optional[int]) -> None:
        """단일 기록을 빈도 카운터에 추가합니다"""
        if not bible_book:
            return
        
        self.total_sermons += 1
        
        # 권별 카운터
        self.book_counter[bible_book] += 1
        
        # 언약별 카운터
        testament = self._get_testament(bible_book)
        self.testament_counter[testament] += 1
        
        # 장별 카운터
        if chapter:
            key = (bible_book, chapter)
            self.chapter_counter[key] += 1
        
        # 절별 카운터
        if verse_start and verse_end:
            key = (bible_book, chapter, f"{verse_start}-{verse_end}")
            self.verse_counter[key] += 1
        elif verse_start:
            key = (bible_book, chapter, str(verse_start))
            self.verse_counter[key] += 1
    
    def add_records(self, records: List[dict]) -> None:
        """여러 기록을 빈도 카운터에 추가합니다"""
        for record in records:
            self.add_record(
                bible_book=record.get("bible_book"),
                chapter=record.get("chapter_start"),
                verse_start=record.get("verse_start"),
                verse_end=record.get("verse_end"),
            )
    
    def get_book_frequencies(self, top_k: Optional[int] = None) -> List[Dict]:
        """
        권별 빈도 상위 K개를 반환합니다.
        
        Args:
            top_k: 반환할 최대 항목 수 (None = 전체)
        
        Returns:
            [{bible_book, count, percentage, testament, book_number}, ...]
        """
        results = []
        for book_name, count in self.book_counter.most_common(top_k):
            testament = self._get_testament(book_name)
            book_number = self._get_book_number(book_name)
            percentage = (count / self.total_sermons * 100) if self.total_sermons > 0 else 0
            
            results.append({
                "bible_book": book_name,
                "count": count,
                "percentage": round(percentage, 2),
                "testament": testament,
                "book_number": book_number,
            })
        
        return results
    
    def get_chapter_frequencies(self, top_k: Optional[int] = None) -> List[Dict]:
        """
        장별 빈도 상위 K개를 반환합니다.
        
        Returns:
            [(bible_book, chapter), count, percentage}]
        """
        results = []
        for (book, chapter), count in self.chapter_counter.most_common(top_k):
            percentage = (count / self.total_sermons * 100) if self.total_sermons > 0 else 0
            
            results.append({
                "bible_book": book,
                "chapter": chapter,
                "count": count,
                "percentage": round(percentage, 2),
            })
        
        return results
    
    def get_testament_frequencies(self) -> Dict:
        """언약별 빈도 반환"""
        total = sum(self.testament_counter.values())
        result = {}
        for testament, count in self.testament_counter.items():
            result[testament] = {
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 2),
            }
        return result
    
    def get_summary(self) -> Dict:
        """전체 빈도 요약 반환"""
        return {
            "total_sermons": self.total_sermons,
            "unique_books": len(self.book_counter),
            "unique_chapters": len(self.chapter_counter),
            "book_frequencies": self.get_book_frequencies(),
            "chapter_frequencies": self.get_chapter_frequencies(top_k=50),
            "testament_frequencies": self.get_testament_frequencies(),
        }
    
    def _normalize_book_name(self, book_name: str) -> str:
        """한국어 약어를 영어 전체명으로 정규화"""
        if not book_name:
            return book_name
        
        # 먼저 직접 매칭
        for book, _, _ in self.BIBLE_BOOKS:
            if book == book_name:
                return book
        
        # 약어 매칭
        normalized = self.KOREAN_ABBREVIATIONS.get(book_name)
        if normalized:
            return normalized
        
        # 부분 매칭 (예: "시편" -> "Psalms")
        for book, _, _ in self.BIBLE_BOOKS:
            if book_name in book or book.lower() in book_name.lower():
                return book
        
        return book_name
    
    def _get_testament(self, book_name: str) -> str:
        """성경 책명이 구약인지 신약인지 반환 (정규화 후)"""
        normalized = self._normalize_book_name(book_name)
        for book, _, testament in self.BIBLE_BOOKS:
            if book == normalized:
                return testament
        return "Unknown"
    
    def _get_book_number(self, book_name: str) -> int:
        """성경 내 책 순서 반환 (정규화 후)"""
        normalized = self._normalize_book_name(book_name)
        for book, number, _ in self.BIBLE_BOOKS:
            if book == normalized:
                return number
        return 0

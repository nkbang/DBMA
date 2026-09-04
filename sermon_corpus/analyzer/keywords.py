# DBMA Sermon Corpus - 설교 제목 키워드 추출기
# 설교 제목에서 핵심 키워드를 추출하고 빈도를 분석합니다.

import re
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class Keyword:
    """키워드 기록"""
    word: str
    frequency: int
    percentage: float
    category: str  # 주제 카테고리
    confidence: float  # 추출 신뢰도 (0.0-1.0)


# 한국어 설교 제목용 불용어 (stopwords)
KOREAN_STOPWORDS = {
    "의", "를", "이", "가", "은", "는", "과", "와", "및", "등",
    "하고", "하며", "에서", "으로", "로", "에", "의해서", "으로써",
    "through", "by", "in", "on", "at", "to", "for", "with", "the",
    "a", "an", "and", "or", "but", "of", "from", "as", "into",
    "하기", "하기란", "적인", "적인", "적인것", "같은", "것", "것은",
    "것들", "등", "때문", "때문에", "없이", "없이할",
}

# 주제 카테고리 매핑 (단순 키워드 기반 분류)
CATEGORY_PATTERNS = {
    "faith": ["믿음", "신앙", "faith", "belief", "trust", "신뢰"],
    "prayer": ["기도", "prayer", "intercession", "간구"],
    "love": ["사랑", "love", "charity", "agape"],
    "forgiveness": ["용서", "forgiveness", "mercy", "자비"],
    "salvation": ["구원", "salvation", "save", "구원받", "구원하"],
    "spirit": ["성령", "spirit", "pentecost", "오순절"],
    "kingdom": ["천국", "나라", "kingdom", "heaven", "왕국"],
    "law": ["율법", "law", "moses", "모세", "계명"],
    "covenant": ["언약", "covenant", "promise", "약속"],
    "grace": ["은혜", "grace", "favor", "은사"],
    "wisdom": ["지혜", "wisdom", "proverbs", "잠언"],
    "judgment": ["심판", "judgment", "judge", "재림"],
    "resurrection": ["부활", "resurrection", "rise", "생명"],
    "cross": ["십자가", "cross", "sacrifice", "희생"],
    "hope": ["소망", "hope", "promise", "약속"],
    "worship": ["예배", "worship", "praise", "찬양"],
    "justice": ["정의", "justice", "righteousness"],
    "creation": ["창조", "creation", "genesis", "창세기"],
    "exodus": ["출애굽", "exodus", "deliverance", "해방"],
    "prophet": ["예언", "prophet", "isaiah", "이사야"],
}

# 영어 카테고리 -> 한글 카테고리명 매핑
CATEGORY_KOREAN_MAP = {
    "faith": "믿음",
    "prayer": "기도",
    "love": "사랑",
    "forgiveness": "용서",
    "salvation": "구원",
    "spirit": "성령",
    "kingdom": "천국/왕국",
    "law": "율법",
    "covenant": "언약",
    "grace": "은혜",
    "wisdom": "지혜",
    "judgment": "심판",
    "resurrection": "부활",
    "cross": "십자가",
    "hope": "소망",
    "worship": "예배",
    "justice": "정의",
    "creation": "창조",
    "exodus": "출애굽",
    "prophet": "예언",
    "other": "기타",
}

# 영어 성경 책명 -> 한글 성경 책명 매핑
BIBLE_BOOK_KOREAN_MAP = {
    # 구약
    "Genesis": "창세기", "Exodus": "출애굽기", "Leviticus": "레위기",
    "Numbers": "민수기", "Deuteronomy": "신명기", "Joshua": "여호수아",
    "Judges": "사사기", "Ruth": "룻",
    "1 Samuel": "사무엘상", "2 Samuel": "사무엘하",
    "1 Kings": "열왕기상", "2 Kings": "열왕기하",
    "1 Chronicles": "역대상", "2 Chronicles": "역대하",
    "Ezra": "에스라", "Nehemiah": "느헤미야", "Esther": "에스더",
    "Job": "욥", "Psalms": "시편", "Proverbs": "잠언",
    "Ecclesiastes": "전도서", "Song of Solomon": "아가",
    "Isaiah": "이사야", "Jeremiah": "예레미야", "Lamentations": "예레미야애가",
    "Ezekiel": "에스겔", "Daniel": "다니엘",
    "Hosea": "호세아", "Joel": "요엘", "Amos": "아모스",
    "Obadiah": "오바댜", "Jonah": "요나", "Micah": "미가",
    "Nahum": "나훔", "Habakkuk": "하박국", "Zephaniah": "스바냐",
    "Haggai": "학개", "Zechariah": "스가랴", "Malachi": "말라기",
    # 신약
    "Matthew": "마태복음", "Mark": "마가복음", "Luke": "누가복음",
    "John": "요한복음", "Acts": "사도행전", "Romans": "로마서",
    "1 Corinthians": "고린도전서", "2 Corinthians": "고린도후서",
    "Galatians": "갈라디아서", "Ephesians": "에베소서",
    "Philippians": "빌립보서", "Colossians": "골로새서",
    "1 Thessalonians": "데살로니가전서", "2 Thessalonians": "데살로니가후서",
    "1 Timothy": "디모데전서", "2 Timothy": "디모데후서",
    "Titus": "디도서", "Philemon": "빌레몬서", "Hebrews": "히브리서",
    "James": "야고보서", "1 Peter": "베드로전서", "2 Peter": "베드로후서",
    "1 John": "요한일서", "2 John": "요한이서", "3 John": "요한삼서",
    "Jude": "유다", "Revelation": "요한계시록",
}


class KeywordExtractor:
    """
    설교 제목에서 키워드를 추출하는 클래스.
    
    - 한국어 형태소 분석 (단어 단위 분할)
    - 불용어 필터링
    - 카테고리 매칭
    - TF 기반 빈도 분석
    """
    
    def __init__(self):
        self.keyword_counter: Counter = Counter()
        self.category_counter: Counter = Counter()
        self.total_titles: int = 0
    
    def extract_keywords_from_title(self, title: str) -> List[str]:
        """
        단일 제목에서 키워드를 추출합니다.
        
        Args:
            title: 설교 제목
        
        Returns:
            추출된 키워드 목록
        """
        if not title or not title.strip():
            return []
        
        # 단어 분할 (한국어는 띄어쓰기 기반)
        words = self._tokenize(title)
        
        # 불용어 필터링 및 정규화
        keywords = []
        for word in words:
            cleaned = self._clean_word(word)
            if cleaned and len(cleaned) >= 2 and cleaned.lower() not in KOREAN_STOPWORDS:
                keywords.append(cleaned.lower())
        
        return keywords
    
    def add_title(self, title: str) -> None:
        """단일 제목을 키워드 카운터에 추가합니다"""
        if not title or not title.strip():
            return
        
        self.total_titles += 1
        keywords = self.extract_keywords_from_title(title)
        
        for keyword in keywords:
            self.keyword_counter[keyword] += 1
            
            # 카테고리 매칭
            category = self._categorize_keyword(keyword)
            if category:
                self.category_counter[category] += 1
    
    def add_titles(self, titles: List[str]) -> None:
        """여러 제목을 키워드 카운터에 추가합니다"""
        for title in titles:
            self.add_title(title)
    
    def get_top_keywords(self, top_k: int = 50) -> List[Dict]:
        """
        상위 K개 키워드를 반환합니다.
        
        Returns:
            [{word, frequency, percentage, category}, ...]
        """
        results = []
        for word, freq in self.keyword_counter.most_common(top_k):
            percentage = (freq / self.total_titles * 100) if self.total_titles > 0 else 0
            category = self._categorize_keyword(word)
            
            results.append({
                "word": word,
                "frequency": freq,
                "percentage": round(percentage, 2),
                "category": category or "other",
                "confidence": min(1.0, freq / 10),  # 빈도 기반 신뢰도
            })
        
        return results
    
    def get_top_categories(self, top_k: int = 20) -> List[Dict]:
        """
        상위 K개 카테고리 빈도를 반환합니다.
        
        Returns:
            [{category, count, percentage}, ...]
        """
        total = sum(self.category_counter.values())
        results = []
        for category, count in self.category_counter.most_common(top_k):
            percentage = (count / total * 100) if total > 0 else 0
            
            results.append({
                "category": category,
                "count": count,
                "percentage": round(percentage, 2),
            })
        
        return results
    
    def get_keyword_category_correlation(self, bible_book: Optional[str] = None) -> Dict:
        """
        본문과 키워드 카테고리의 상관관계를 분석합니다.
        
        Args:
            bible_book: 특정 성경 책명 (None = 전체)
        
        Returns:
            {category: {book: count, ...}, ...}
        """
        # 이 기능은 CorpusStatistics에서 더 잘 처리됨
        return {}
    
    def get_summary(self) -> Dict:
        """키워드 요약 반환"""
        return {
            "total_titles": self.total_titles,
            "unique_keywords": len(self.keyword_counter),
            "top_keywords": self.get_top_keywords(),
            "top_categories": self.get_top_categories(),
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """텍스트를 단어 단위로 분할합니다"""
        # 간단한 띄어쓰기 기반 분할
        return text.split()
    
    def _clean_word(self, word: str) -> str:
        """단어를 정리 (특수문자 제거, 소문자 변환)"""
        # 특수문자 제거
        cleaned = re.sub(r'[^a-zA-Z가-힣\s]', '', word)
        return cleaned.strip().lower()
    
    def _categorize_keyword(self, keyword: str) -> Optional[str]:
        """키워드를 카테고리로 매칭합니다.

        [버그 수정] "성경 책별 핵심 주제"가 사실상 대부분의 책에서
        "justice"로 쏠려 나오던 원인 — 여기서 pattern이 keyword
        문자열 어디에든("in") 있으면 매칭시켰다. "정의"(justice)처럼
        짧은 2글자 한국어 패턴은 "가정의"("of the family", "가정"+
        조사 "의")처럼 뜻이 전혀 다른 단어 중간/끝에 우연히 포함되는
        경우가 많아 실제로 "아담의 갈비뼈로 지으신 하와와 가정의
        제도" 같은 무관한 제목이 justice로 잘못 분류됨을 확인했다.
        한국어 단어는 "패턴+조사"(정의를/정의가) 형태가 대부분이므로
        "포함"이 아니라 "~로 시작하는지"로 바꿔 오탐을 없앤다.
        """
        keyword_lower = keyword.lower()

        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if keyword_lower.startswith(pattern.lower()):
                    return category
        
        return None
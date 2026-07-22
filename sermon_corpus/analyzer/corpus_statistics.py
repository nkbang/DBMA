# DBMA Sermon Corpus - 코퍼스 통계 분석기
# 본문과 설교 제목의 상관관계를 통계적으로 분석합니다.

import json
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
from sermon_corpus.analyzer.keywords import KeywordExtractor


@dataclass
class PassageThemeCorrelation:
    """본문-주제 상관관계 기록"""
    bible_book: str
    chapter: Optional[int]
    dominant_category: str  # 주요 주제 카테고리
    category_percentage: float  # 해당 카테고리 비율
    top_keywords: List[str]  # 주요 키워드
    sample_titles: List[str]  # 샘플 제목 (최대 5개)
    total_sermons: int


@dataclass
class CorpusStatistics:
    """코퍼스 전체 통계"""
    total_records: int
    unique_books: int
    unique_chapters: int
    testament_distribution: Dict
    book_frequencies: List[Dict]
    chapter_frequencies: List[Dict]
    keyword_summary: Dict
    passage_theme_correlations: List[Dict]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def save(self, path: Path) -> None:
        """통계 결과를 JSON 파일로 저장"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class CorpusStatisticsAnalyzer:
    """
    코퍼스 전체 통계 분석기.
    
    - 빈도 분석 (FrequencyAnalyzer 통합)
    - 키워드 분석 (KeywordExtractor 통합)
    - 본문-주제 상관관계 분석
    - JSONL 데이터 로드 및 처리
    """
    
    def __init__(self):
        self.frequency_analyzer = FrequencyAnalyzer()
        self.keyword_extractor = KeywordExtractor()
        
        # 본문별 카테고리 매핑 (상관관계 분석용)
        self.passage_categories: Dict[Tuple[str, Optional[int]], Counter] = defaultdict(Counter)
        
        # 샘플 제목 저장 (시각화용)
        self.sample_titles: Dict[Tuple[str, Optional[int]], List[str]] = defaultdict(list)
        
        # 전체 통계
        self.total_records: int = 0
    
    def load_jsonl(self, path: Path) -> int:
        """
        JSONL 파일에서 기록을 로드합니다.
        
        Returns:
            로드된 기록 수
        """
        loaded = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    record = json.loads(line)
                    self._process_record(record)
                    loaded += 1
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return loaded
    
    def load_records(self, records: List[dict]) -> int:
        """
        기록 목록을 로드합니다.
        
        Returns:
            로드된 기록 수
        """
        for record in records:
            self._process_record(record)
        
        return len(records)
    
    def _process_record(self, record: dict) -> None:
        """단일 기록을 처리하여 각 분석기에 추가합니다"""
        self.total_records += 1
        
        # 빈도 분석기
        self.frequency_analyzer.add_record(
            bible_book=record.get("bible_book"),
            chapter=record.get("chapter_start"),
            verse_start=record.get("verse_start"),
            verse_end=record.get("verse_end"),
        )
        
        # 키워드 추출기
        title = record.get("title", "")
        if title:
            self.keyword_extractor.add_title(title)
            
            # 카테고리 매칭 (설교 제목 기반)
            category = self._categorize_title(title)
            if category:
                book = record.get("bible_book")
                chapter = record.get("chapter_start")
                self.passage_categories[(book, chapter)][category] += 1
                
                # 샘플 제목 저장 (최대 5개)
                if len(self.sample_titles[(book, chapter)]) < 5:
                    self.sample_titles[(book, chapter)].append(title)
    
    def _categorize_title(self, title: str) -> Optional[str]:
        """설교 제목을 카테고리로 분류합니다.

        [버그 수정] 이전에는 제목의 첫 단어(title.split()[0])만 검사했다
        — 한국어 설교 제목은 핵심 키워드가 조사/연결어 뒤에 오는 경우가
        많아 사실상 거의 매칭되지 않았다. 제목 전체를 KeywordExtractor로
        토큰화한 뒤, 각 단어의 매칭 카테고리 중 가장 많이 나온 것을
        고른다(단순 다수결 — 첫 매칭 단어 우선이 아니라 빈도 기반)."""
        keywords = self.keyword_extractor.extract_keywords_from_title(title)
        if not keywords:
            return None

        category_votes: Counter = Counter()
        for kw in keywords:
            category = self.keyword_extractor._categorize_keyword(kw)
            if category:
                category_votes[category] += 1

        if not category_votes:
            return None
        return category_votes.most_common(1)[0][0]
    
    def get_passage_theme_correlation(self, bible_book: Optional[str] = None) -> List[Dict]:
        """
        본문-주제 상관관계를 분석합니다.
        
        Args:
            bible_book: 특정 성경 책명 (None = 전체)
        
        Returns:
            [{bible_book, chapter, dominant_category, category_percentage, 
               top_keywords, sample_titles, total_sermons}, ...]
        """
        results = []
        
        for (book, chapter), category_counter in self.passage_categories.items():
            # 특정 책 필터링
            if bible_book and book != bible_book:
                continue
            
            total = sum(category_counter.values())
            if total == 0:
                continue
            
            # 주요 카테고리
            dominant_category, dominant_count = category_counter.most_common(1)[0]
            dominant_percentage = (dominant_count / total * 100) if total > 0 else 0
            
            # 상위 키워드
            top_keywords = list(category_counter.keys())[:5]
            
            # 샘플 제목
            sample_titles = self.sample_titles.get((book, chapter), [])
            
            results.append({
                "bible_book": book,
                "chapter": chapter,
                "dominant_category": dominant_category,
                "category_percentage": round(dominant_percentage, 2),
                "top_keywords": top_keywords,
                "sample_titles": sample_titles,
                "total_sermons": total,
            })
        
        # 총 수 기준 내림차순 정렬
        results.sort(key=lambda x: x["total_sermons"], reverse=True)
        
        return results
    
    def get_full_statistics(self) -> CorpusStatistics:
        """전체 통계 반환"""
        return CorpusStatistics(
            total_records=self.total_records,
            unique_books=len(self.frequency_analyzer.book_counter),
            unique_chapters=len(self.frequency_analyzer.chapter_counter),
            testament_distribution=self.frequency_analyzer.get_testament_frequencies(),
            book_frequencies=self.frequency_analyzer.get_book_frequencies(),
            chapter_frequencies=self.frequency_analyzer.get_chapter_frequencies(top_k=50),
            keyword_summary=self.keyword_extractor.get_summary(),
            passage_theme_correlations=self.get_passage_theme_correlation(),
        )
    
    def compute_correlation_matrix(self) -> Dict:
        """
        본문(권/장)과 키워드 카테고리 간의 상관관계 행렬을 계산합니다.

        Returns:
            {category: {"book:chapter": normalized_count, ...}, ...}
        """
        # 각 본문별 카테고리 비율 계산
        # [버그 수정] 이전에는 (book, chapter) 튜플을 내부 딕셔너리 키로
        # 써서 save_statistics()가 json.dump()할 때
        # "keys must be str, int, float, bool or None, not tuple"로
        # 항상 크래시했다 — 문자열 키("책:장")로 변경.
        matrix = defaultdict(lambda: defaultdict(float))

        for (book, chapter), category_counter in self.passage_categories.items():
            total = sum(category_counter.values())
            if total == 0:
                continue

            passage_key = f"{book}:{chapter if chapter is not None else '?'}"
            for category, count in category_counter.items():
                matrix[category][passage_key] = count / total
        
        return {cat: dict(books) for cat, books in matrix.items()}
    
    def compute_key_themes_per_book(self) -> Dict[str, List[str]]:
        """
        각 성경 책별 핵심 주제 키워드를 도출합니다.
        
        Returns:
            {bible_book: [top_keywords], ...}
        """
        book_themes = defaultdict(Counter)
        
        for (book, chapter), category_counter in self.passage_categories.items():
            if not book:
                continue
            
            # 상위 카테고리 3개를 키워드로 사용
            top_categories = [cat for cat, _ in category_counter.most_common(3)]
            for cat in top_categories:
                book_themes[book][cat] += 1
        
        # 각 책별 상위 카테고리 5개 추출
        result = {}
        for book, theme_counter in book_themes.items():
            result[book] = [cat for cat, _ in theme_counter.most_common(5)]
        
        return result
    
    def save_statistics(self, output_dir: Path) -> None:
        """통계 결과를 파일로 저장합니다"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 전체 통계
        stats = self.get_full_statistics()
        stats.save(output_dir / "corpus_statistics.json")
        
        # 상관관계
        correlations = self.get_passage_theme_correlation()
        with open(output_dir / "passage_theme_correlations.json", "w", encoding="utf-8") as f:
            json.dump(correlations, f, ensure_ascii=False, indent=2)
        
        # 핵심 주제
        key_themes = self.compute_key_themes_per_book()
        with open(output_dir / "key_themes_per_book.json", "w", encoding="utf-8") as f:
            json.dump(key_themes, f, ensure_ascii=False, indent=2)
        
        # 상관관계 행렬
        matrix = self.compute_correlation_matrix()
        with open(output_dir / "correlation_matrix.json", "w", encoding="utf-8") as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2)
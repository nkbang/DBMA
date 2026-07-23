# DBMA Sermon Corpus - 코퍼스 통계 분석기
# 본문과 설교 제목의 상관관계를 통계적으로 분석합니다.

import json
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
from sermon_corpus.analyzer.keywords import KeywordExtractor, CATEGORY_KOREAN_MAP
from sermon_corpus.analyzer.book_themes import BOOK_KEY_THEMES


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

    # [기능 추가] 날짜/본문/제목/설교자 중 하나라도 없는 레코드는 통계에
    # 포함시키지 않는다 — 코퍼스에 들어오는 모든 경로(load_jsonl,
    # load_records)가 공통으로 거치도록 여기 한 곳에 고정.
    REQUIRED_FIELDS = ["published_date", "passage_raw", "title", "preacher"]

    def __init__(self):
        self.frequency_analyzer = FrequencyAnalyzer()
        self.keyword_extractor = KeywordExtractor()
        
        # 본문별 카테고리 매핑 (상관관계 분석용)
        self.passage_categories: Dict[Tuple[str, Optional[int]], Counter] = defaultdict(Counter)
        
        # 샘플 제목 저장 (시각화용)
        self.sample_titles: Dict[Tuple[str, Optional[int]], List[str]] = defaultdict(list)
        
        # 전체 통계
        self.total_records: int = 0
        
        # 원본 기록 저장 (대시보드 시각화용)
        self.records: List[dict] = []
    
    def load_jsonl(self, path: Path) -> int:
        """
        JSONL 파일에서 기록을 로드합니다.

        Returns:
            로드된 기록 수 (필수 필드 누락 레코드 제외)
        """
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return self.load_records(records)

    def load_records(self, records: List[dict]) -> int:
        """
        기록 목록을 로드합니다.

        [기능 추가] 날짜(published_date)/본문(passage_raw)/제목(title)/
        설교자(preacher) 중 하나라도 비어있는 레코드는 통계·시각화에서
        제외한다 — self.records에도 필터링된 것만 남긴다.

        [기능 추가] passage_raw에 책명이 섞여 있으면(예: "로마서 9:11-16")
        책명은 bible_book 필드로, passage_raw는 "장:절-절" 숫자 형식으로
        분리·통일한다.

        Returns:
            로드된 기록 수 (필수 필드 누락 레코드 제외)
        """
        normalized = [self._normalize_passage_raw(r) for r in records]
        complete_records = [r for r in normalized if self._has_required_fields(r)]

        for record in complete_records:
            self._process_record(record)

        # 원본 기록 저장 (대시보드 시각화용) — 필터링된 것만
        self.records = complete_records

        return len(complete_records)

    @classmethod
    def _has_required_fields(cls, record: dict) -> bool:
        """REQUIRED_FIELDS가 전부 값이 있는지(None/빈 문자열이 아닌지) 확인"""
        for field in cls.REQUIRED_FIELDS:
            value = record.get(field)
            if value is None:
                return False
            if isinstance(value, str) and not value.strip():
                return False
        return True

    @staticmethod
    def _normalize_passage_raw(record: dict) -> dict:
        """passage_raw("로마서 9:11-16" 등, 책명이 섞인 원본 표기)를
        bible_book(이미 각 수집기가 별도로 채워둔 필드)과 분리해
        passage_raw는 "장:절-절"(또는 "장"만) 숫자 형식으로 통일한다.

        문자열에서 책명을 잘라내는 방식이 아니라, chapter_start/
        verse_start/verse_end(BibleReferenceParser 등이 이미 신뢰성
        있게 파싱해둔 값)로 다시 조립한다 — 텍스트 패턴 매칭보다
        안전하고, 값을 지어내지 않는다(장 정보가 아예 없으면 원본
        passage_raw를 그대로 둔다).
        """
        chapter = record.get("chapter_start")
        if chapter is None or record.get("passage_raw") is None:
            return record

        verse_start = record.get("verse_start")
        verse_end = record.get("verse_end")

        if verse_start and verse_end and verse_end != verse_start:
            new_passage = f"{chapter}:{verse_start}-{verse_end}"
        elif verse_start:
            new_passage = f"{chapter}:{verse_start}"
        else:
            new_passage = str(chapter)

        normalized = dict(record)
        normalized["passage_raw"] = new_passage
        return normalized
    
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
            [{bible_book, chapter, dominant_category(korean), category_percentage, 
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
            
            # 주요 카테고리 (한글 매핑)
            dominant_category_raw, dominant_count = category_counter.most_common(1)[0]
            dominant_category = CATEGORY_KOREAN_MAP.get(dominant_category_raw, dominant_category_raw)
            dominant_percentage = (dominant_count / total * 100) if total > 0 else 0
            
            # 상위 키워드 (카테고리 이름은 한글로)
            top_keywords = [CATEGORY_KOREAN_MAP.get(cat, cat) for cat in category_counter.keys()][:5]
            
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
        각 성경 책별 핵심 주제를 반환합니다.

        [설계 변경] 예전에는 설교 제목에 등장한 단어를 20개 고정
        카테고리와 매칭해 다수결로 뽑았다 — 설교 수가 적은 책은
        우연히 붙은 단어 하나에 좌우되고, 제목에 분류 키워드가 전혀
        없으면 아예 결과에서 빠지는 구조적 문제가 있었다(실측 결과
        전체 설교의 80% 이상이 미분류로 빠짐). 성경 각 권의 핵심
        주제는 설교 제목 통계로 매번 다시 추정할 대상이 아니라
        조직신학/성서신학이 이미 정해둔 것이므로, book_themes.py의
        고정 상수(BOOK_KEY_THEMES)를 그대로 반환한다 — 실제 설교
        데이터에 등장하는 책에 한해서만 표시.

        Returns:
            {bible_book: [theme]}  — 책마다 정해진 핵심 주제 1개
        """
        result = {}
        for book in self.frequency_analyzer.book_counter:
            theme = BOOK_KEY_THEMES.get(book)
            if theme:
                result[book] = [theme]
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
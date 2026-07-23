#!/usr/bin/env python3
"""
DBMA Sermon Corpus - 대시보드 웹 애플리케이션
============================================

설교 빈도 및 키워드 시각화 대시보드 (Streamlit 기반)

사용법:
    streamlit run sermon_corpus/dashboard/web_app.py [--data PATH]

예시:
    streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/raw/sermonbank.jsonl
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
from sermon_corpus.analyzer.keywords import KeywordExtractor
from sermon_corpus.analyzer.corpus_statistics import CorpusStatisticsAnalyzer
from sermon_corpus.collector.background_collector import DataStore


# ============================================================
# 진행률 상태 클래스
# ============================================================

@dataclass
class ProgressState:
    """파일 처리 진행률 상태"""
    current: int = 0
    total: int = 0
    message: str = ""
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)
    
    @property
    def is_complete(self) -> bool:
        return self.current >= self.total


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="DBMA 설교 대시보드",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 필드 매핑 정의
# ============================================================

# 성경 책 필드명 매핑
BIBLE_BOOK_FIELDS = [
    "bible_book", "bibleBook", "BibleBook", "book", "book_name", 
    "bookName", "성경책", "성경", "책", "book_title"
]

# 장 필드명 매핑
CHAPTER_FIELDS = [
    "chapter_start", "chapterStart", "ChapterStart", "chapter", "Chapter",
    "장", "chap_start", "chapStart", "chapter_begin"
]

# 설교 제목 필드명 매핑
TITLE_FIELDS = [
    "title", "sermon_title", "sermonTitle", "SermonTitle", "Title",
    "설교제목", "제목", "subject", "topic"
]

# 본문 필드명 매핑 (raw passage)
PASSAGE_FIELDS = [
    "passage_raw", "passageRaw", "PassageRaw", "passage", "Passage",
    "본문", "scripture", "text"
]

# 설교자 필드명 매핑
PREACHER_FIELDS = [
    "preacher", "preacher_name", "preacherName", "PreacherName", "Preacher",
    "설교자", "목사", "speaker", "pastor"
]

# 날짜 필드명 매핑
DATE_FIELDS = [
    "published_date", "publishedDate", "PublishedDate", "date", "Date",
    "pub_date", "pubDate", " preaching_date", "설교일", "날짜"
]

# 교회 필드명 매핑
CHURCH_FIELDS = [
    "church", "church_name", "churchName", "ChurchName", "Church",
    "교회", " congregation"
]

# 연도/연대 계산용 필드
DATE_CALC_FIELDS = DATE_FIELDS  # 날짜에서 연도/연대 추출


def detect_field_mapping(headers: List[str]) -> Dict[str, str]:
    """CSV 헤더에서 필드 매핑을 자동 감지합니다.
    
    Returns:
        매핑 딕셔너리: { 표준필드명: 실제헤더명 }
    """
    mapping = {}
    headers_lower = [h.lower().strip() for h in headers]
    
    # 각 필드 유형별로 매핑 시도
    for field_list, standard_name in [
        (BIBLE_BOOK_FIELDS, "bible_book"),
        (CHAPTER_FIELDS, "chapter"),
        (TITLE_FIELDS, "title"),
        (PASSAGE_FIELDS, "passage_raw"),
        (PREACHER_FIELDS, "preacher"),
        (DATE_FIELDS, "date"),
        (CHURCH_FIELDS, "church"),
    ]:
        for header in headers_lower:
            for pattern in field_list:
                if pattern.lower() in header or header in pattern.lower():
                    # 실제 헤더 인덱스 찾기
                    idx = headers_lower.index(header)
                    mapping[standard_name] = headers[idx]
                    break
            if standard_name in mapping:
                break
    
    return mapping


def normalize_record(record: dict, field_mapping: Dict[str, str]) -> dict:
    """CSV 레코드를 표준 형식으로 변환합니다"""
    normalized = {}
    
    # bible_book
    bb_key = field_mapping.get("bible_book")
    normalized["bible_book"] = record.get(bb_key, "") if bb_key else ""
    
    # chapter
    ch_key = field_mapping.get("chapter")
    try:
        val = record.get(ch_key, 0) if ch_key else 0
        normalized["chapter_start"] = int(val) if val else 1
        normalized["chapter_end"] = normalized["chapter_start"]
    except (ValueError, TypeError):
        normalized["chapter_start"] = 1
        normalized["chapter_end"] = 1
    
    # title
    tl_key = field_mapping.get("title")
    normalized["title"] = str(record.get(tl_key, "")) if tl_key else ""
    
    # passage_raw (제목에서 본문 추출 시도)
    ps_key = field_mapping.get("passage_raw")
    if ps_key and record.get(ps_key):
        normalized["passage_raw"] = str(record[ps_key])
    elif normalized["title"]:
        # 제목에서 본문 정보 추출 (예: "창세기 1장 - 창조")
        normalized["passage_raw"] = normalized["title"]
    else:
        normalized["passage_raw"] = f"{normalized['bible_book']} {normalized['chapter_start']}장"
    
    # preacher
    pr_key = field_mapping.get("preacher")
    normalized["preacher"] = str(record.get(pr_key, "")) if pr_key else ""
    
    # date
    dt_key = field_mapping.get("date")
    normalized["published_date"] = str(record.get(dt_key, "")) if dt_key else ""
    
    # church
    ch_key = field_mapping.get("church")
    normalized["church"] = str(record.get(ch_key, "")) if ch_key else ""
    
    # 연도/연대 계산
    normalized["year"], normalized["decade"] = compute_year_decade(normalized["published_date"])
    
    return normalized


def compute_year_decade(date_str: str) -> tuple:
    """날짜 문자열에서 연도와 연대를 추출합니다"""
    if not date_str:
        return None, None
    
    # 다양한 날짜 형식 시도
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y"]:
        try:
            year = int(date_str[:4])
            decade = (year // 10) * 10
            return year, decade
        except (ValueError, IndexError):
            continue
    
    return None, None


@st.cache_data(ttl=3600)
def load_data(data_path: str, progress: Optional[ProgressState] = None) -> Optional[List[dict]]:
    """다양한 파일 형식에서 데이터를 로드합니다.
    
    지원 형식:
    - JSONL (한 줄당 JSON 객체)
    - CSV (콤마/탭 구분자, 필드 자동 감지)
    - TSV (탭 구분자)
    - XLSX (엑셀)
    - TXT (TSV로 간주)
    - SQLite (DB 파일)
    
    CSV 필드 자동 감지:
    - bible_book, chapter, title, preacher, date 등 주요 필드명 패턴 매칭
    - 여러 필드명 변형 지원 (예: bible_book, BibleBook, 성경책 등)
    """
    if not data_path or not Path(data_path).exists():
        return None
    
    path = Path(data_path)
    ext = path.suffix.lower()
    
    try:
        if ext == ".jsonl" or ext == ".json":
            # JSONL 형식 - 표준 필드명 가정
            records = []
            total_lines = sum(1 for _ in open(data_path, "r", encoding="utf-8"))
            
            with open(data_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if progress:
                        progress.current = i + 1
                        progress.message = f"JSONL 처리 중: {i+1}/{total_lines}"
                    
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        # 연도/연대 계산
                        date_str = record.get("published_date", "") or record.get("date", "")
                        year, decade = compute_year_decade(str(date_str))
                        record["year"] = year
                        record["decade"] = decade
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            return records if records else None
        
        elif ext in (".csv", ".tsv", ".txt"):
            # CSV/TSV/TXT 형식 - 필드 자동 감지
            import pandas as pd
            
            # 구분자 자동 감지
            with open(data_path, "r", encoding="utf-8") as f:
                sample = f.read(4096)
            
            sep = "\t" if "\t" in sample[:1024] else ","
            
            df = pd.read_csv(data_path, sep=sep, encoding="utf-8")
            
            if df.empty or df.columns.tolist() == [""]:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환 (진행률 업데이트)
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"CSV 변환 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        elif ext == ".xlsx":
            # 엑셀 형식
            import pandas as pd
            
            df = pd.read_excel(data_path, engine="openpyxl")
            
            if df.empty:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"엑셀 변환 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                # NaN 처리
                record = {k: (None if v != v else v) for k, v in record.items()}
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        elif ext == ".db" or ext == ".sqlite" or ext == ".sqlite3":
            # SQLite 형식
            import pandas as pd
            import sqlite3
            
            conn = sqlite3.connect(data_path)
            cursor = conn.cursor()
            
            # 테이블 목록 조회
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                st.error("데이터베이스에 테이블이 없습니다.")
                return None
            
            # 첫 번째 테이블 사용 (또는 선택 가능)
            table_name = tables[0][0]
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
            
            if df.empty:
                return None
            
            total_rows = len(df)
            
            # 필드 매핑 감지
            field_mapping = detect_field_mapping(df.columns.tolist())
            
            # 표준 형식으로 변환
            records = []
            for i, (_, row) in enumerate(df.iterrows()):
                if progress:
                    progress.current = i + 1
                    progress.message = f"SQLite 처리 중: {i+1}/{total_rows}"
                
                record = row.to_dict()
                record = {k: (None if v != v else v) for k, v in record.items()}
                normalized = normalize_record(record, field_mapping)
                records.append(normalized)
            
            return records if records else None
        
        else:
            # 알 수 없는 형식 - JSONL로 시도
            records = []
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return records if records else None
    
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        return None


def deduplicate_records(records: List[dict]) -> tuple:
    """중복 데이터를 제거합니다.
    
    중복 조건: title + passage_raw 가 동일한 경우
    
    Returns:
        (중복제거된_records, 원본_건수, 제거된_건수)
    """
    seen = set()
    unique_records = []
    duplicate_count = 0
    
    for record in records:
        # [버그 수정] record.get("title", "")의 기본값 ""는 키가 아예
        # 없을 때만 적용된다 — JSONL 업로드 경로는 CSV/엑셀 경로와 달리
        # 필드를 문자열로 정규화하지 않아 title이 명시적으로 null(None)
        # 이면 그대로 통과, .strip()에서 AttributeError로 업로드 전체가
        # 크래시했다. `or ""`로 None도 함께 처리.
        title = (record.get("title") or "").strip().lower()
        passage = (record.get("passage_raw") or "").strip().lower()
        key = (title, passage)
        
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicate_count += 1
    
    return unique_records, len(records), duplicate_count


@st.cache_resource(ttl=3600)
def analyze_data(records: List[dict]) -> CorpusStatisticsAnalyzer:
    """데이터를 분석합니다"""
    analyzer = CorpusStatisticsAnalyzer()
    analyzer.load_records(records)
    return analyzer


def get_background_data_path() -> Optional[str]:
    """백그라운드 수집 데이터 파일 경로를 반환합니다"""
    data_path = Path(__file__).parent.parent / "data" / "collected_sermons.jsonl"
    return str(data_path) if data_path.exists() else None


# ============================================================
# UI 레이아웃
# ============================================================

def render_sidebar(analyzer: CorpusStatisticsAnalyzer):
    """사이드바를 렌더링합니다"""
    with st.sidebar:
        st.header("📊 필터")
        
        # 성경 권 필터
        book_frequencies = analyzer.frequency_analyzer.get_book_frequencies()
        all_books = [b["bible_book"] for b in book_frequencies]
        selected_books = st.multiselect(
            "성경 책 선택",
            options=all_books,
            default=all_books[:10] if len(all_books) > 10 else all_books,
            help="분석할 성경 책을 선택하세요",
        )
        
        # 언약 필터
        testament_filter = st.multiselect(
            "언약 필터",
            options=["OT", "NT"],
            default=["OT", "NT"],
            help="구약/신약 필터",
        )
        
        st.divider()
        
        # 통계 요약
        st.header("📈 통계 요약")
        stats = analyzer.get_full_statistics()
        st.metric("총 설교 수", f"{stats.total_records:,}")
        st.metric("독립된 성경 책", stats.unique_books)
        st.metric("독립된 장", stats.unique_chapters)


def render_overview(stats: CorpusStatisticsAnalyzer):
    """전체 개요를 렌더링합니다"""
    st.header("📖 DBMA 설교 대시보드")
    st.markdown("""
    **설교 본문-제목 데이터셋**의 통계 분석 대시보드입니다.
    
    - 성경 권별/장별 설교 빈도
    - 설교 제목 핵심 키워드
    - 본문과 설교 주제의 상관관계
    """)
    
    # 통계 요약 카드
    summary = stats.get_full_statistics()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 설교 수", f"{summary.total_records:,}")
    col2.metric("성경 책 수", summary.unique_books)
    col3.metric("성경 장 수", summary.unique_chapters)
    col4.metric("키워드 수", summary.keyword_summary.get("unique_keywords", 0))


def render_testament_distribution(stats: CorpusStatisticsAnalyzer):
    """언약별 분포를 렌더링합니다"""
    st.subheader("📜 언약별 설교 분포")
    
    testament_freq = stats.frequency_analyzer.get_testament_frequencies()
    
    if not testament_freq:
        st.warning("언약 데이터가 없습니다.")
        return
    
    # 파이 차트
    data = [
        {"언약": t, "설교 수": d["count"], "비율 (%)": d["percentage"]}
        for t, d in testament_freq.items()
    ]
    df = pd.DataFrame(data)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=df["언약"],
            values=df["설교 수"],
            hole=0.4,
            textposition="inside",
            textinfo="percent",
        )])
        fig_pie.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.dataframe(df, hide_index=True, use_container_width=True)


def render_book_frequencies(stats: CorpusStatisticsAnalyzer):
    """권별 설교 빈도를 렌더링합니다"""
    st.subheader("📚 권별 설교 빈도 (Top 30)")
    
    book_freq = stats.frequency_analyzer.get_book_frequencies(top_k=30)
    
    if not book_freq:
        st.warning("권별 데이터가 없습니다.")
        return
    
    # 막대 차트
    df = pd.DataFrame(book_freq)

    # [버그 수정] 이전에 있던 df["testament"] 계산은 문자열 x를
    # BIBLE_BOOKS(튜플 리스트)와 직접 비교해 항상 거짓이 되는 죽은
    # 코드였다 — book → testament 딕셔너리 매핑 하나로 정리.
    testament_map = {}
    for book, _, testament in stats.frequency_analyzer.BIBLE_BOOKS:
        testament_map[book] = testament
    
    df["testament_ko"] = df["bible_book"].apply(lambda x: "구약" if testament_map.get(x) == "OT" else "신약")
    
    fig = px.bar(
        df,
        x="bible_book",
        y="count",
        color="testament_ko",
        hover_data={"percentage": ":.2f"},
        title="성경 책별 설교 빈도 (Top 30)",
    )
    fig.update_layout(xaxis_tickangle=-45, height=500, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


def render_chapter_frequencies(stats: CorpusStatisticsAnalyzer):
    """장별 설교 빈도를 렌더링합니다"""
    st.subheader("📏 장별 설교 빈도 (Top 20)")
    
    chapter_freq = stats.frequency_analyzer.get_chapter_frequencies(top_k=20)
    
    if not chapter_freq:
        st.warning("장별 데이터가 없습니다.")
        return
    
    df = pd.DataFrame(chapter_freq)
    df["passage"] = df.apply(lambda r: f"{r['bible_book']} {r['chapter']}장", axis=1)
    
    fig = px.bar(
        df,
        x="passage",
        y="count",
        hover_data={"percentage": ":.2f"},
        title="장별 설교 빈도 (Top 20)",
    )
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_keyword_analysis(stats: CorpusStatisticsAnalyzer):
    """키워드 분석을 렌더링합니다"""
    st.subheader("🔑 설교 제목 키워드 분석")
    
    # 상위 키워드
    top_keywords = stats.keyword_extractor.get_top_keywords(top_k=30)
    
    if not top_keywords:
        st.warning("키워드 데이터가 없습니다.")
        return
    
    # 단어 구름
    word_data = [(kw["word"], kw["frequency"]) for kw in top_keywords]
    fig_wordcloud = px.treemap(
        pd.DataFrame(word_data, columns=["word", "freq"]),
        path=["word"],
        values="freq",
        title="설교 제목 키워드 트리맵",
    )
    fig_wordcloud.update_layout(height=400)
    st.plotly_chart(fig_wordcloud, use_container_width=True)
    
    # 카테고리 분포
    st.markdown("#### 주제 카테고리 분포")
    top_categories = stats.keyword_extractor.get_top_categories(top_k=15)
    
    if top_categories:
        cat_df = pd.DataFrame(top_categories)
        fig_cat = px.bar(
            cat_df,
            x="category",
            y="count",
            hover_data={"percentage": ":.2f"},
            title="주제 카테고리 분포",
        )
        fig_cat.update_layout(xaxis_tickangle=-30, height=350)
        st.plotly_chart(fig_cat, use_container_width=True)


def render_passage_theme_correlation(stats: CorpusStatisticsAnalyzer):
    """본문-주제 상관관계를 렌더링합니다"""
    st.subheader("🔗 본문-주제 상관관계")
    
    correlations = stats.get_passage_theme_correlation()
    
    if not correlations:
        st.warning("상관관계 데이터가 없습니다.")
        return
    
    # 상위 본문-주제 매핑
    df = pd.DataFrame(correlations)[:30]
    
    # 히트맵
    st.markdown("#### 본문별 주요 주제 히트맵 (Top 10 본문)")
    
    heatmap_data = correlations[:10]
    heat_df = pd.DataFrame([
        {
            "본문": f"{r['bible_book']} {'?' if r['chapter'] is None else r['chapter']}장",
            "주요 주제": r["dominant_category"],
            "비율 (%)": r["category_percentage"],
            "설교 수": r["total_sermons"],
        }
        for r in heatmap_data
    ])
    
    st.dataframe(heat_df, hide_index=True, use_container_width=True)
    
    # 핵심 주제 per book
    st.markdown("#### 성경 책별 핵심 주제")
    key_themes = stats.compute_key_themes_per_book()
    
    theme_cols = st.columns(min(len(key_themes), 5))
    for i, (book, themes) in enumerate(key_themes.items()):
        with theme_cols[i % 5]:
            st.markdown(f"**{book}**")
            for theme in themes[:3]:
                st.caption(f"- {theme}")


def render_year_decade_statistics(stats: CorpusStatisticsAnalyzer):
    """연도/연대별 설교 통계를 렌더링합니다"""
    st.subheader("📅 연도/연대별 설교 통계")
    
    # 원본 데이터를 직접 접근
    records = stats.records
    
    if not records:
        st.warning("데이터가 없습니다.")
        return
    
    import pandas as pd
    
    df = pd.DataFrame(records)
    
    # 연도별 통계
    st.markdown("### 연도별 설교 수")
    if "year" in df.columns:
        year_freq = df.groupby("year").size().reset_index(name="설교 수")
        year_freq = year_freq.sort_values("year")
        
        # 누적 합계
        year_freq["누적 설교 수"] = year_freq["설교 수"].cumsum()
        year_freq["비율 (%)"] = (year_freq["설교 수"] / year_freq["설교 수"].sum() * 100).round(1)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_year = px.bar(
                year_freq,
                x="year",
                y="설교 수",
                title="연도별 설교 빈도",
                hover_data=["누적 설교 수", "비율 (%)"],
            )
            fig_year.update_layout(xaxis_tickangle=-45, height=350)
            st.plotly_chart(fig_year, use_container_width=True)
        
        with col2:
            st.dataframe(year_freq, hide_index=True, use_container_width=True)
    
    # 연대별 통계
    st.markdown("### 연대별 설교 수")
    if "decade" in df.columns:
        decade_freq = df.groupby("decade").size().reset_index(name="설교 수")
        decade_freq = decade_freq.sort_values("decade")
        decade_freq["연대"] = decade_freq["decade"].apply(lambda x: f"{x}s")
        
        fig_decade = px.pie(
            decade_freq,
            values="설교 수",
            names="연대",
            title="연대별 설교 분포",
            hole=0.4,
        )
        fig_decade.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_decade, use_container_width=True)
        
        # 연대별 핵심 키워드
        st.markdown("#### 연대별 핵심 키워드")
        decade_keywords = {}
        for decade in sorted(df["decade"].unique()):
            decade_df = df[df["decade"] == decade]
            decade_records = decade_df.to_dict("records")
            
            # 간단한 키워드 빈도 계산
            keyword_counts = {}
            for record in decade_records:
                title = record.get("title", "")
                for kw in ["은혜", "믿음", "기도", "사랑", "구원", "소망", "예배", "성령"]:
                    if kw in title:
                        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            
            # 상위 5개 키워드
            top_kws = sorted(keyword_counts.items(), key=lambda x: -x[1])[:5]
            decade_keywords[f"{decade}s"] = [kw for kw, _ in top_kws]
        
        kw_cols = st.columns(min(len(decade_keywords), 4))
        for i, (decade, kws) in enumerate(decade_keywords.items()):
            with kw_cols[i % 4]:
                st.markdown(f"**{decade}**")
                for kw in kws:
                    st.caption(f"- {kw}")
    
    # 연도 × 성경 책 히트맵
    st.markdown("### 연도 × 성경 책별 설교 빈도 (Top 10 책)")
    if "year" in df.columns and "bible_book" in df.columns:
        top_books = df["bible_book"].value_counts().head(10).index.tolist()
        heatmap_df = df[df["bible_book"].isin(top_books)].groupby(["year", "bible_book"]).size().unstack(fill_value=0)
        
        if not heatmap_df.empty:
            fig_heatmap = px.imshow(
                heatmap_df.values,
                labels=dict(x=heatmap_df.columns, y=heatmap_df.index, color="설교 수"),
                x=[str(b) for b in heatmap_df.columns],
                y=[str(y) for y in heatmap_df.index],
                title="연도 × 성경 책별 설교 빈도 (Top 10)",
                color_continuous_scale="Blues",
            )
            fig_heatmap.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_heatmap, use_container_width=True)


def render_data_table(stats: CorpusStatisticsAnalyzer):
    """데이터 테이블을 렌더링합니다"""
    st.subheader("📋 데이터 미리보기")
    
    # 샘플 데이터
    sample = []
    for (book, chapter), titles in list(stats.sample_titles.items())[:20]:
        for title in titles:
            sample.append({
                "성경 책": book or "Unknown",
                "장": chapter or "N/A",
                "설교 제목": title,
            })
    
    if sample:
        df = pd.DataFrame(sample)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("샘플 데이터가 없습니다.")


# ============================================================
# 메인 애플리케이션
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="DBMA 설교 대시보드")
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="데이터 파일 경로 (JSONL, CSV, XLSX, TXT, SQLite 지원)",
    )
    args, unknown = parser.parse_known_args()
    
    # 진행률 상태
    progress = ProgressState()
    
    # 파일 업로드 또는 명령줄 인자
    uploaded_file = None
    data_path = args.data or os.environ.get("DBMA_SERMON_DATA")
    
    st.header("📖 DBMA 설교 대시보드")
    st.markdown("**설교 본문-제목 데이터셋**의 통계 분석 대시보드입니다.")
    
    # 파일 업로드 섹션
    st.markdown("---")
    st.subheader("📂 데이터 로드")
    
    col_upload, col_info = st.columns([1, 2])
    
    with col_upload:
        file_types = [".jsonl", ".json", ".csv", ".tsv", ".txt", ".xlsx", ".db", ".sqlite", ".sqlite3"]
        uploaded_file = st.file_uploader(
            "파일 업로드", 
            type=file_types,
            help="JSONL, CSV, XLSX, TXT, SQLite 파일 지원\n중복 데이터는 자동으로 제거됩니다"
        )
    
    with col_info:
        st.info("""
        **표준 필드 구조:**
        - `bible_book` 또는 `book`: 성경 책명 (예: Genesis, 창)
        - `chapter_start` 또는 `chapter`: 장 번호
        - `title` 또는 `sermon_title`: 설교 제목
        - `passage_raw` 또는 `passage`: 본문 정보
        - `preacher` 또는 `speaker`: 설교자
        - `published_date` 또는 `date`: 날짜
        
        **자동 필드 감지:** 다양한 필드명을 자동으로 감지하여 표준 형식으로 변환합니다.
        
        **중복 제거:** 제목 + 본문이 동일한 데이터는 자동으로 머지됩니다.
        """)
    
    # 데이터 로드 및 처리
    records = None
    original_count = 0
    duplicate_count = 0
    
    if uploaded_file is not None:
        # 진행률 표시
        progress.message = "파일 업로드 중..."
        progress.total = 1
        progress.current = 0
        
        # 임시 파일로 저장
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        progress.message = "데이터 처리 중..."
        
        # 데이터 로드
        records = load_data(tmp_path, progress)
        
        if records is None:
            st.error("데이터를 로드할 수 없습니다. 파일 형식이나 필드 구조를 확인하세요.")
        else:
            original_count = len(records)
            progress.current = progress.total
            progress.message = "중복 제거 중..."
            
            # 중복 제거
            records, original_count, duplicate_count = deduplicate_records(records)
            
            progress.message = "분석 완료!"
            
            # 성공 메시지
            st.success(f"✅ {original_count + duplicate_count}건 로드 완료 (중복 {duplicate_count}건 제거, 최종 {len(records)}건)")
            
            # 진행률 표시
            st.progress(1.0)
            st.text(f"📊 현재 처리 중: {len(records)} / {original_count + duplicate_count} ({progress.percentage:.1f}%)")
        
        # 임시 파일 삭제
        os.unlink(tmp_path)
    
    elif data_path:
        # 명령줄 인자에서 파일 로드
        progress.message = "파일 로드 중..."
        records = load_data(data_path, progress)
        
        if records is None:
            st.error(f"데이터 파일을 로드할 수 없습니다: {data_path}")
            st.stop()
        else:
            original_count = len(records)
            records, original_count, duplicate_count = deduplicate_records(records)
            st.info(f"📂 {original_count + duplicate_count}건 로드 완료 (중복 {duplicate_count}건 제거)")
    else:
        st.warning("⚠️ 데이터 파일이 지정되지 않았습니다. 파일을 업로드하거나 `--data PATH` 옵션을 사용하세요.")
        st.info("예시: streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/raw/sermonbank.jsonl")
        return
    
    if not records:
        st.error("로드된 데이터가 없습니다.")
        st.stop()
    
    # 분석
    analyzer = analyze_data(records)
    
    # 중복 제거 통계 표시
    if duplicate_count > 0:
        st.warning(f"⚠️ **중복 데이터 {duplicate_count}건**이 제거되었습니다. (중복 조건: 제목 + 본문)")
    
    # 사이드바
    render_sidebar(analyzer)
    
    # 메인 콘텐츠
    render_overview(analyzer)
    
    st.divider()
    
    # 언약별 분포
    render_testament_distribution(analyzer)
    
    # 권별 빈도
    render_book_frequencies(analyzer)
    
    # 장별 빈도
    render_chapter_frequencies(analyzer)
    
    # 키워드 분석
    render_keyword_analysis(analyzer)
    
    # 본문-주제 상관관계
    render_passage_theme_correlation(analyzer)
    
    # 연도/연대별 통계 (NEW!)
    render_year_decade_statistics(analyzer)
    
    # 데이터 테이블
    render_data_table(analyzer)
    
    # 백그라운드 수집기 상태
    st.divider()
    _render_background_collector_status()


def _render_background_collector_status():
    """백그라운드 수집기 상태를 렌더링합니다"""
    st.header("🔄 백그라운드 데이터 수집기")
    
    bg_data_path = get_background_data_path()
    
    if bg_data_path:
        data_store = DataStore(bg_data_path)
        stats = data_store.get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 데이터 건수", f"{stats['total_records']:,}")
        col2.metric("파일 크기", f"{stats['file_size_bytes'] / 1024:.1f} KB")
        col3.metric("마지막 수정", stats['last_modified'] or "N/A")
        
        # 수동 수집 버튼
        if st.button("📥 수동 데이터 수집 실행", key="manual_collect"):
            st.info("수동 수집이 시작되었습니다. 콘솔을 확인하세요.")
    else:
        st.info("""
        **백그라운드 수집 데이터 파일이 없습니다.**
        
        데이터를 수집하려면 다음 명령을 실행하세요:
        ```bash
        cd ~/DBMA
        source ~/envs/dbma311/bin/activate
        python scripts/background_collector.py --once
        ```
        
        또는 데몬 모드로 지속적으로 실행:
        ```bash
        python scripts/background_collector.py --daemon
        ```
        """)


if __name__ == "__main__":
    main()

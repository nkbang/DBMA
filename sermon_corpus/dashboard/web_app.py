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
from typing import Dict, List, Optional

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sermon_corpus.analyzer.frequency import FrequencyAnalyzer
from sermon_corpus.analyzer.keywords import KeywordExtractor
from sermon_corpus.analyzer.corpus_statistics import CorpusStatisticsAnalyzer


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
# 데이터 로드
# ============================================================

@st.cache_data(ttl=3600)
def load_data(data_path: str) -> Optional[List[dict]]:
    """JSONL 파일에서 데이터를 로드합니다"""
    if not data_path or not Path(data_path).exists():
        return None
    
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


@st.cache_resource(ttl=3600)
def analyze_data(records: List[dict]) -> CorpusStatisticsAnalyzer:
    """데이터를 분석합니다"""
    analyzer = CorpusStatisticsAnalyzer()
    analyzer.load_records(records)
    return analyzer


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
        help="JSONL 데이터 파일 경로",
    )
    args, unknown = parser.parse_known_args()
    
    # 데이터 로드
    data_path = args.data or os.environ.get("DBMA_SERMON_DATA")
    
    if data_path:
        records = load_data(data_path)
        if records is None:
            st.error(f"데이터 파일을 로드할 수 없습니다: {data_path}")
            st.stop()
    else:
        st.warning("⚠️ 데이터 파일이 지정되지 않았습니다. `--data PATH` 옵션을 사용하세요.")
        st.info("예시: streamlit run sermon_corpus/dashboard/web_app.py --data data/sermon_corpus/raw/sermonbank.jsonl")
        return
    
    if not records:
        st.error("로드된 데이터가 없습니다.")
        st.stop()
    
    # 분석
    analyzer = analyze_data(records)
    
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
    
    # 데이터 테이블
    render_data_table(analyzer)


if __name__ == "__main__":
    main()
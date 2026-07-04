#!/usr/bin/env python3
"""
DBMA RAG Benchmark Dashboard — Streamlit UI

실행: streamlit run scripts/rag_benchmark_dashboard.py -- --output output/bench/rag_bench
"""

import sys
import os
import json
from pathlib import Path

import streamlit as st
import numpy as np

# ═══════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="DBMA RAG Benchmark Dashboard",
    page_icon="📊",
    layout="wide",
)

# 명령줄 인자 파싱
args = sys.argv[1:]
output_dir = Path("output/bench/rag_bench")
i = 0
while i < len(args):
    if args[i] == "--output" and i + 1 < len(args):
        output_dir = Path(args[i + 1])
        i += 2
    else:
        i += 1


# ═══════════════════════════════════════════════════════════
# 헬퍼 함수들
# ═══════════════════════════════════════════════════════════

def load_summary(output_dir: Path) -> dict:
    """벤치마크 요약 데이터 로드"""
    summary_path = output_dir / "rag_benchmark_summary.json"
    if not summary_path.exists():
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_detailed_results(output_dir: Path) -> list:
    """상세 결과 로드"""
    csv_path = output_dir / "rag_benchmark_detailed.csv"
    if not csv_path.exists():
        return []
    
    results = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if len(lines) < 2:
            return []
        
        headers = [h.strip() for h in lines[0].split(',')]
        
        for line in lines[1:]:
            values = [v.strip() for v in line.split(',')]
            if len(values) == len(headers):
                results.append(dict(zip(headers, values)))
    
    return results


def load_test_queries(output_dir: Path) -> list:
    """테스트 쿼리 로드"""
    queries_path = output_dir / "test_queries.json"
    if not queries_path.exists():
        return []
    
    with open(queries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('queries', [])


# ═══════════════════════════════════════════════════════════
# UI 렌더링
# ═══════════════════════════════════════════════════════════

st.title("📊 DBMA RAG Benchmark Dashboard")
st.caption("고급 RAG 시스템 성능 벤치마킹 — 청킹 전략 × 임베딩 모델 비교")


# 1. 데이터 로드
summary = load_summary(output_dir)
detailed_results = load_detailed_results(output_dir)
test_queries = load_test_queries(output_dir)

if not summary:
    st.error(f"벤치마크 결과를 찾지 못했습니다: {output_dir}")
    st.info("먼저 `python scripts/rag_benchmark.py --run` 명령으로 벤치마크를 실행하세요.")
else:
    # 2. 요약 섹션
    st.header("📈 Performance Summary")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Successful Runs", f'{summary.get("successful", 0)}')
    c2.metric("Failed Runs", f'{summary.get("failed", 0)}')
    c3.metric("Documents Tested", f'{summary.get("total_documents", 0)}')
    c4.metric("Test Queries", f'{summary.get("total_queries", 0)}')
    
    st.divider()
    
    # 3. 문서 유형별 최적 조합
    st.header("🏆 Best Combo by Document Type")
    
    by_type = summary.get("by_doc_type", {})
    
    if by_type:
        for doc_type, best in by_type.items():
            st.subheader(f"{doc_type.title()} Documents")
            
            if best and isinstance(best, dict):
                cols = st.columns(5)
                cols[0].metric("Hit@1", f'{best.get("hit@1", 0):.2%}')
                cols[1].metric("Hit@3", f'{best.get("hit@3", 0):.2%}')
                cols[2].metric("Hit@5", f'{best.get("hit@5", 0):.2%}')
                cols[3].metric("MRR", f'{best.get("mrr", 0):.3f}')
                cols[4].metric("Best Combo", best.get("combo", "N/A"))
    else:
        st.warning("문서 유형별 데이터가 없습니다.")
    
    st.divider()
    
    # 4. 전체 비교 행렬
    st.header("📋 Comparison Matrix")
    
    matrix = summary.get("comparison_matrix", {})
    
    if matrix:
        rows_data = []
        
        for doc_type, combos in matrix.items():
            for (chunk_name, embed_name), metrics in combos.items():
                row = {
                    "Doc Type": doc_type,
                    "Chunk Strategy": chunk_name,
                    "Embed Model": embed_name,
                    "Avg Hit@1": metrics.get("avg_hit@1", 0),
                    "Avg Hit@3": metrics.get("avg_hit@3", 0),
                    "Avg Hit@5": metrics.get("avg_hit@5", 0),
                    "Avg MRR": metrics.get("avg_mrr", 0),
                    "Avg Latency(s)": metrics.get("avg_latency_sec", 0),
                }
                rows_data.append(row)
        
        if rows_data:
            # 정렬 옵션 (Hit@5 내림차순)
            sort_by = st.selectbox(
                "정렬 기준",
                ["Avg Hit@5", "Avg Hit@3", "Avg Hit@1", "Avg MRR", "Avg Latency(s)"],
                index=2,
            )
            
            # 데이터프레임 정렬
            df = __import__('pandas', fromlist=['DataFrame'])
            df_data = df.DataFrame(rows_data)
            if sort_by in df_data.columns:
                df_data = df_data.sort_values(by=sort_by, ascending=(sort_by == "Avg Latency(s)"))
            
            st.dataframe(df_data, use_container_width=True, height=600)
    
    st.divider()
    
    # 5. 테스트 쿼리셋
    st.header("📝 Test Queries (Ground Truth)")
    
    if test_queries:
        for q in test_queries:
            with st.expander(f"{q.get('query_id', '?')}: {q.get('question', '')[:80]}..."):
                st.write(f"**Question:** {q.get('question', 'N/A')}")
                st.write(f"**Relevant Doc:** {q.get('relevant_doc_stem', 'N/A')}")
                st.write(f"**Expected Keywords:** {', '.join(q.get('expected_keywords', []))}")
    else:
        st.info("테스트 쿼리가 없습니다.")
    
    st.divider()
    
    # 6. 상세 결과 분석
    st.header("🔍 Detailed Results Analysis")
    
    if detailed_results:
        df_detail = __import__('pandas', fromlist=['DataFrame'])
        df_res = df_detail.DataFrame(detailed_results)
        
        # 필터 옵션
        col_filter1, col_filter2 = st.columns(2)
        chunk_options = df_res['chunk_config'].unique() if 'chunk_config' in df_res.columns else []
        embed_options = df_res['embed_config'].unique() if 'embed_config' in df_res.columns else []
        
        selected_chunk = col_filter1.selectbox("청킹 전략 필터", ['All'] + list(chunk_options))
        selected_embed = col_filter2.selectbox("임베딩 모델 필터", ['All'] + list(embed_options))
        
        # 필터 적용
        filtered = df_res
        if selected_chunk != 'All':
            filtered = filtered[filtered['chunk_config'] == selected_chunk]
        if selected_embed != 'All':
            filtered = filtered[filtered['embed_config'] == selected_embed]
        
        # 지표 표시
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        if 'success' in filtered.columns:
            col_m1.metric("Success Rate", f'{(filtered["success"].sum() / len(filtered) * 100):.1f}%')
        
        for metric_col, col_m in zip(['hit@1', 'hit@3', 'hit@5', 'mrr'], [col_m2, col_m3, col_m4]):
            col_name = f'avg_{metric_col}' if f'avg_{metric_col}' not in filtered.columns else metric_col
            if col_name in filtered.columns:
                col_m.metric(f"Avg {metric_col.upper()}", f'{filtered[col_name].mean():.4f}')
        
        st.dataframe(filtered, use_container_width=True, height=400)
    
    # 7. 데이터 다운로드
    st.header("📥 Download Results")
    
    csv_path = output_dir / "rag_benchmark_detailed.csv"
    json_path = output_dir / "rag_benchmark_summary.json"
    
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8') as f:
            st.download_button(
                "Download Detailed Results (CSV)",
                f.read(),
                file_name="rag_benchmark_detailed.csv",
                mime="text/csv",
            )
    
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            st.download_button(
                "Download Summary (JSON)",
                f.read(),
                file_name="rag_benchmark_summary.json",
                mime="application/json",
            )


# 8. 푸터 정보
st.divider()
st.caption(f"Dashboard Version 1.0 | Data Source: {output_dir}")
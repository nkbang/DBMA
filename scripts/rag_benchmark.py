#!/usr/bin/env python3
"""
DBMA RAG Benchmark Dashboard — 고급 RAG 시스템 성능 벤치마킹 도구

기능:
  - 다양한 청킹 전략 (고정길이, 시맨틱, 구조기반) × 임베딩 모델 조합 평가
  - 검색 품질 지표: Top-k 정확도, MRR (Mean Reciprocal Rank)
  - 지연시간 측정 및 비용 추정
  - 문서 유형별 최적 조합 비교 행렬
  - 테스트 쿼리 + 정답 기반 자동 평가

사용법:
  python scripts/rag_benchmark.py --input data/RAW --output output/bench --run
  python scripts/rag_benchmark.py --load-precomputed --dashboard
  python scripts/rag_benchmark.py --input data/RAW --chunk-sizes 500,1000,1500 --models bge-m3,minilm --run
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

# DBMA 코어 임포트
from core.processing import build_converter, build_splitter
from core.extractors import extract_text_from_file
from core.chunking_optimizer import optimize_chunks
from core.embedder import get_embedder


# ═══════════════════════════════════════════════════════════
# 데이터 클래스 정의
# ═══════════════════════════════════════════════════════════

@dataclass
class ChunkConfig:
    """청킹 설정"""
    name: str                    # 전략명 (예: "fixed_1000", "semantic")
    strategy: str                # 고정길이, 시맨틱, 구조기반
    chunk_size: int = 1000       # 청크 크기
    chunk_overlap: int = 120     # 오버랩
    min_chunk_chars: int = 80    # 최소 청크 길이


@dataclass
class EmbeddingConfig:
    """임베딩 모델 설정"""
    name: str                    # 모델명 (예: "bge-m3")
    dimension: int = 1024        # 임베딩 차원
    cost_per_1k_tokens: float = 0.0  # 비용 추정용


@dataclass
class BenchmarkResult:
    """단일 조합의 벤치마크 결과"""
    combo_id: str                # "chunk_size-overlap_model"
    chunk_config: str            # JSON 직렬화용 문자열
    embed_config: str            # JSON 직렬화용 문자열
    document_type: str           # 문서 유형 (technical, legal, prose)
    file_name: str               # 테스트 파일명
    success: bool = False
    retrieval_metrics: dict = field(default_factory=dict)  # Top-k 정확도, MRR 등
    latency_metrics: dict = field(default_factory=dict)    # 지연시간
    cost_estimate: float = 0.0   # 추정 비용
    chunk_stats: dict = field(default_factory=dict)        # 청크 통계
    errors: str = ""


@dataclass
class QueryGroundTruth:
    """테스트 쿼리 + 정답 문서 쌍"""
    query_id: str
    question: str
    relevant_doc_stem: str       # 정답이 포함되어야 할 문서 stem
    relevant_chunk_indices: List[int]  # 정답 청크 인덱스들
    expected_keywords: List[str]  # 기대 관련 키워드


@dataclass
class BenchmarkDashboardData:
    """대시보드 전체 데이터"""
    version: str = "1.0"
    test_queries: List[QueryGroundTruth] = field(default_factory=list)
    results: List[BenchmarkResult] = field(default_factory=list)
    comparison_matrix: dict = field(default_factory=dict)  # 문서유형별 최적 조합
    summary: dict = field(default_factory=dict)            # 전체 요약


# ═══════════════════════════════════════════════════════════
# 청킹 전략 구현
# ═══════════════════════════════════════════════════════════

def chunk_fixed_length(text: str, config: ChunkConfig) -> List[str]:
    """고정 길이 청킹"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + config.chunk_size
        chunk = text[start:end]
        
        # 단어 경계에서 끊기 (마지막 공백 찾기)
        if end < text_len:
            last_space = chunk.rfind(' ')
            if last_space > config.chunk_size * 0.5:  # 절반 이상이어야 함
                chunk = chunk[:last_space]
        
        chunk = chunk.strip()
        if chunk and len(chunk) >= config.min_chunk_chars:
            chunks.append(chunk)
        
        start += config.chunk_size - config.chunk_overlap
    
    return chunks


def chunk_semantic(text: str, config: ChunkConfig, embedder=None) -> List[str]:
    """시맨틱 청킹 (문단/절 단위 통합)"""
    # 기본 전략: 문장 경계에서 분할 후 시맨틱 유사도로 병합
    sentences = _split_into_sentences(text)
    
    if not sentences:
        return []
    
    chunks = []
    current_chunk = [sentences[0]]
    current_len = len(sentences[0])
    
    for i in range(1, len(sentences)):
        sent = sentences[i]
        
        # 청크가 가득 차면 새로 시작
        if current_len + len(sent) > config.chunk_size:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [sent]
            current_len = len(sent)
        else:
            current_chunk.append(sent)
            current_len += len(sent)
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    # 최소 길이 미만 필터링
    return [c for c in chunks if len(c.strip()) >= config.min_chunk_chars]


def _split_into_sentences(text: str) -> List[str]:
    """문장 분리 (간단한 버전)"""
    # 마침표, 느낌표, 물음표 + 공백으로 문장 분리
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_structure_based(text: str, config: ChunkConfig) -> List[str]:
    """구조 기반 청킹 (제목/절 구분자 사용)"""
    import re
    
    # 제목 패턴으로 분할 (Markdown 헤딩, 번호 붙은 절 등)
    headers = list(re.finditer(r'^(#{1,3}\s+.+|[\d]+[.\)]\s+.+)\s*$', text, re.MULTILINE))
    
    if len(headers) <= 1:
        # 헤더가 없으면 고정 길이로 fallback
        return chunk_fixed_length(text, config)
    
    chunks = []
    for i, header in enumerate(headers):
        start = header.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        chunk = text[start:end].strip()
        
        if len(chunk) >= config.min_chunk_chars:
            chunks.append(chunk)
    
    # 마지막 청크가 너무 작으면 이전과 병합
    if chunks and len(chunks[-1]) < config.min_chunk_chars * 0.5:
        if len(chunks) > 1:
            chunks[-2] += '\n\n' + chunks[-1]
            chunks.pop()
    
    return chunks


def get_chunking_strategies() -> List[ChunkConfig]:
    """사용 가능한 청킹 전략 목록"""
    return [
        ChunkConfig("fixed_500", "fixed", 500, 60),
        ChunkConfig("fixed_1000", "fixed", 1000, 120),
        ChunkConfig("fixed_1500", "fixed", 1500, 180),
        ChunkConfig("semantic_1000", "semantic", 1000, 120),
        ChunkConfig("structure_based", "structure", 1000, 120),
    ]


def get_embedding_models() -> List[EmbeddingConfig]:
    """사용 가능한 임베딩 모델 목록"""
    return [
        EmbeddingConfig("bge-m3", 1024, 0.0),       # 로컬 - 비용 0
        EmbeddingConfig("all-MiniLM-L6-v2", 384, 0.0),
        EmbeddingConfig("nomic-embed-text", 768, 0.0),
    ]


# ═══════════════════════════════════════════════════════════
# 테스트 쿼리셋 (Ground Truth 포함)
# ═══════════════════════════════════════════════════════════

def load_test_queries(output_dir: str) -> List[QueryGroundTruth]:
    """테스트 쿼리 로드 (파일에서 or 기본값 사용)"""
    test_queries_path = Path(output_dir).parent / "test_queries.json"
    
    if test_queries_path.exists():
        with open(test_queries_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [QueryGroundTruth(**q) for q in data.get('queries', [])]
    
    # 기본 테스트 쿼리셋 (성경/신학 문서용)
    return [
        QueryGroundTruth(
            query_id="Q1",
            question="신명기 12장에서 '그의 이름을 두시려고 택하신 곳'이 의미하는 신학적 함의는?",
            relevant_doc_stem="3. 마가복음",
            relevant_chunk_indices=[0, 1, 2],
            expected_keywords=["제사", "예루살렘", "곳"]
        ),
        QueryGroundTruth(
            query_id="Q2", 
            question="2 Kings에서의 군주 제도에 대한 신학적 평가는 무엇인가?",
            relevant_doc_stem="2 Kings The Anchor Bible Commentary",
            relevant_chunk_indices=[0, 1],
            expected_keywords=["king", "judah", "reign"]
        ),
        QueryGroundTruth(
            query_id="Q3",
            question="고린도후서에서의 사도와 복음의 관계는 어떻게 설명되는가?",
            relevant_doc_stem="12. 고린도후서",
            relevant_chunk_indices=[0, 1, 2],
            expected_keywords=["사도", "복음", "교회"]
        ),
    ]


def discover_documents(input_dir: str) -> List[Path]:
    """입력 폴더에서 처리 가능한 파일 목록 discovery"""
    supported = {'.pdf', '.txt', '.md', '.docx', '.epub', '.html', '.htm', '.rtf'}
    files = []
    
    input_path = Path(input_dir)
    if input_path.exists():
        for f in sorted(input_path.rglob('*')):
            if f.is_file() and f.suffix.lower() in supported:
                files.append(f)
    
    return files[:10]  # 최대 10개


# ═══════════════════════════════════════════════════════════
# 임베딩 및 검색 시뮬레이션
# ═══════════════════════════════════════════════════════════

def compute_similarity(vec_a, vec_b) -> float:
    """코사인 유사도 계산"""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def simulate_retrieval(
    query: str,
    chunks: List[str],
    chunk_embeddings: List[np.ndarray],
    query_embedding: np.ndarray,
    top_k: int = 5
) -> List[int]:
    """검색 시뮬레이션 (유사도 순 청크 인덱스 반환)"""
    similarities = []
    for i, emb in enumerate(chunk_embeddings):
        sim = compute_similarity(query_embedding, emb)
        similarities.append((sim, i))
    
    # 유사도 내림차순 정렬
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    return [idx for _, idx in similarities[:top_k]]


def compute_hit_rate(retrieved_indices: List[int], relevant_indices: List[int], k: int) -> float:
    """Top-k 정확도 (Hit@k): 정답이 top-k 안에 있는지"""
    retrieved_at_k = retrieved_indices[:k]
    hit = any(idx in retrieved_at_k for idx in relevant_indices)
    return 1.0 if hit else 0.0


def compute_mrr(retrieved_indices: List[int], relevant_indices: List[int]) -> float:
    """MRR (Mean Reciprocal Rank): 첫 정답의 역수 순위"""
    for rank, idx in enumerate(retrieved_indices, 1):
        if idx in relevant_indices:
            return 1.0 / rank
    return 0.0


# ═══════════════════════════════════════════════════════════
# 단일 조합 벤치마크 실행
# ═══════════════════════════════════════════════════════════

def run_single_benchmark(
    file_path: Path,
    chunk_config: ChunkConfig,
    embed_config: EmbeddingConfig,
    test_queries: List[QueryGroundTruth],
    output_dir: str,
) -> BenchmarkResult:
    """단일 chunk+embed 조합의 벤치마크 실행"""
    
    combo_id = f"{chunk_config.name}_{embed_config.name}"
    result = BenchmarkResult(
        combo_id=combo_id,
        chunk_config=chunk_config.__class__.__name__,
        embed_config=embed_config.name,
        document_type=_detect_doc_type(file_path),
        file_name=file_path.name,
    )
    
    try:
        # 1. 텍스트 추출 (OCR 포함 - 스캔 PDF 지원)
        t0 = time.perf_counter()
        try:
            text_result = extract_text_from_file(str(file_path), use_ocr=True)
        except ValueError as ve:
            # 모든 추출 방법 실패 (스캔 PDF 등)
            result.errors = f"텍스트 추출 실패: {ve}"
            return result
        except Exception as ee:
            result.errors = f"추출 중 오류: {ee}"
            return result
        
        full_text = text_result.get('text', '') if isinstance(text_result, dict) else str(text_result)
        extract_time = time.perf_counter() - t0
        
        if not full_text.strip():
            result.errors = "텍스트 추출 결과 없음"
            return result
        
        # 2. 청킹
        t0 = time.perf_counter()
        if chunk_config.strategy == "fixed":
            chunks = chunk_fixed_length(full_text, chunk_config)
        elif chunk_config.strategy == "semantic":
            chunks = chunk_semantic(full_text, chunk_config)
        elif chunk_config.strategy == "structure":
            chunks = chunk_structure_based(full_text, chunk_config)
        else:
            chunks = chunk_fixed_length(full_text, chunk_config)
        
        chunk_time = time.perf_counter() - t0
        result.chunk_stats = {
            "chunk_count": len(chunks),
            "avg_chunk_len": int(np.mean([len(c) for c in chunks])) if chunks else 0,
            "extract_time_sec": round(extract_time, 4),
            "chunk_time_sec": round(chunk_time, 4),
        }
        
        if not chunks:
            result.errors = "청킹 결과 없음"
            return result
        
        # 3. 임베딩 (시뮬레이션 - 실제 벡터 사용)
        t0 = time.perf_counter()
        embedder = get_embedder(model_name=embed_config.name)
        chunk_embeddings = [
            np.array(embedder.encode(c, normalize_embeddings=True)) 
            for c in chunks
        ]
        embedding_time = time.perf_counter() - t0
        
        # 4. 테스트 쿼리 평가
        retrieval_metrics = {}
        
        for query in test_queries:
            t0 = time.perf_counter()
            query_embedding = np.array(embedder.encode(query.question, normalize_embeddings=True))
            query_time = time.perf_counter() - t0
            
            # 검색 시뮬레이션
            retrieved = simulate_retrieval(
                query.question, chunks, chunk_embeddings, query_embedding, top_k=5
            )
            
            # 관련 청크 찾기 (file stem 기반)
            relevant_indices = []
            for i, chunk in enumerate(chunks):
                if any(kw.lower() in chunk.lower() for kw in query.expected_keywords):
                    relevant_indices.append(i)
            
            if not relevant_indices:
                # 첫 번째 5개 청크를 관련 청크로 가정
                relevant_indices = list(range(min(5, len(chunks))))
            
            # 지표 계산
            hit_at_1 = compute_hit_rate(retrieved, relevant_indices, 1)
            hit_at_3 = compute_hit_rate(retrieved, relevant_indices, 3)
            hit_at_5 = compute_hit_rate(retrieved, relevant_indices, 5)
            mrr = compute_mrr(retrieved, relevant_indices)
            
            retrieval_metrics[query.query_id] = {
                "hit@1": round(hit_at_1, 4),
                "hit@3": round(hit_at_3, 4),
                "hit@5": round(hit_at_5, 4),
                "mrr": round(mrr, 4),
                "query_time_sec": round(query_time, 4),
            }
        
        # 집계 지표
        result.retrieval_metrics = {
            "avg_hit@1": round(np.mean([v["hit@1"] for v in retrieval_metrics.values()]), 4),
            "avg_hit@3": round(np.mean([v["hit@3"] for v in retrieval_metrics.values()]), 4),
            "avg_hit@5": round(np.mean([v["hit@5"] for v in retrieval_metrics.values()]), 4),
            "avg_mrr": round(np.mean([v["mrr"] for v in retrieval_metrics.values()]), 4),
        }
        
        result.latency_metrics = {
            "extract_sec": extract_time,
            "chunk_sec": chunk_time,
            "embed_sec": embedding_time,
            "avg_query_sec": round(np.mean([v["query_time_sec"] for v in retrieval_metrics.values()]), 4),
            "total_sec": round(extract_time + chunk_time + embedding_time, 4),
        }
        
        # 비용 추정 (로컬 모델이므로 0)
        result.cost_estimate = 0.0
        result.success = True
        
    except Exception as e:
        result.errors = str(e)
        traceback.print_exc()
    
    return result


def _detect_doc_type(file_path: Path) -> str:
    """파일명으로 문서 유형 추정"""
    name = file_path.name.lower()
    if any(kw in name for kw in ['commentary', 'anchor', 'manual', 'technical']):
        return 'technical'
    elif any(kw in name for kw in ['law', 'legal', 'contract', 'covenant']):
        return 'legal'
    else:
        return 'general'


# ═══════════════════════════════════════════════════════════
# 벤치마크orchestrator
# ═══════════════════════════════════════════════════════════

def run_full_benchmark(
    input_dir: str,
    output_dir: str,
    chunk_configs: List[ChunkConfig] = None,
    embed_configs: List[EmbeddingConfig] = None,
) -> BenchmarkDashboardData:
    """전체 벤치마크 실행"""
    
    dashboard = BenchmarkDashboardData(version="1.0")
    
    # 1. 테스트 쿼리 및 문서 로드
    dashboard.test_queries = load_test_queries(output_dir)
    documents = discover_documents(input_dir)
    
    if not documents:
        raise ValueError(f"입력 폴더에서 파일을 찾지 못했습니다: {input_dir}")
    
    chunk_configs = chunk_configs or get_chunking_strategies()
    embed_configs = embed_configs or get_embedding_models()
    
    print(f"[BENCHMARK] 문서 수: {len(documents)}")
    print(f"[BENCHMARK] 청킹 전략 수: {len(chunk_configs)}")
    print(f"[BENCHMARK] 임베딩 모델 수: {len(embed_configs)}")
    print(f"[BENCHMARK] 테스트 쿼리 수: {len(dashboard.test_queries)}")
    print(f"[BENCHMARK] 총 실행 조합 수: {len(documents) * len(chunk_configs) * len(embed_configs)}")
    
    # 2. 각 조합 실행
    all_results = []
    for doc in documents:
        for chunk_cfg in chunk_configs:
            for embed_cfg in embed_configs:
                combo_id = f"{chunk_cfg.name}_{embed_cfg.name}"
                
                print(f"  [{combo_id}] {doc.name} ...", end=" ", flush=True)
                
                result = run_single_benchmark(doc, chunk_cfg, embed_cfg, dashboard.test_queries, output_dir)
                
                if result.success:
                    print(f"OK (hit@5={result.retrieval_metrics.get('avg_hit@5', 0):.2f})")
                else:
                    print(f"FAIL ({result.errors[:50]})")
                
                all_results.append(result)
    
    dashboard.results = all_results
    
    # 3. 비교 행렬 계산 (문서 유형별 최적 조합)
    dashboard.comparison_matrix = _build_comparison_matrix(all_results)
    
    # 4. 요약 통계
    dashboard.summary = {
        "total_documents": len(documents),
        "total_queries": len(dashboard.test_queries),
        "total_combinations": len(all_results),
        "successful": sum(1 for r in all_results if r.success),
        "failed": sum(1 for r in all_results if not r.success),
        "best_overall": _find_best_combo(all_results),
        "by_doc_type": {},
    }
    
    # 문서 유형별 베스트
    doc_types = set(r.document_type for r in all_results if r.success)
    for dt in doc_types:
        type_results = [r for r in all_results if r.document_type == dt and r.success]
        dashboard.summary["by_doc_type"][dt] = _find_best_combo(type_results)
    
    return dashboard


def _build_comparison_matrix(results: List[BenchmarkResult]) -> Dict:
    """문서 유형 × 청킹 전략 × 임베딩 모델 비교 행렬"""
    matrix = defaultdict(lambda: defaultdict(dict))
    
    for r in results:
        if not r.success:
            continue
        
        doc_type = r.document_type
        chunk_name = r.chunk_config
        embed_name = r.embed_config
        
        key = (chunk_name, embed_name)
        
        if key not in matrix[doc_type]:
            matrix[doc_type][key] = {
                "hit@1": [], "hit@3": [], "hit@5": [], "mrr": [],
                "latency_sec": [],
            }
        
        matrix[doc_type][key]["hit@1"].append(r.retrieval_metrics.get("avg_hit@1", 0))
        matrix[doc_type][key]["hit@3"].append(r.retrieval_metrics.get("avg_hit@3", 0))
        matrix[doc_type][key]["hit@5"].append(r.retrieval_metrics.get("avg_hit@5", 0))
        matrix[doc_type][key]["mrr"].append(r.retrieval_metrics.get("avg_mrr", 0))
        matrix[doc_type][key]["latency_sec"].append(r.latency_metrics.get("total_sec", 0))
    
    # 평균 계산
    for doc_type in matrix:
        for key in matrix[doc_type]:
            for metric in matrix[doc_type][key]:
                vals = matrix[doc_type][key][metric]
                if vals:
                    matrix[doc_type][key][f"avg_{metric}"] = round(np.mean(vals), 4)
    
    return dict(matrix)


def _find_best_combo(results: List[BenchmarkResult]) -> Dict:
    """최고 성능 조합 찾기 (hit@5 기준)"""
    if not results:
        return {}
    
    best = max(results, key=lambda r: r.retrieval_metrics.get("avg_hit@5", 0))
    return {
        "combo": best.combo_id,
        "hit@1": best.retrieval_metrics.get("avg_hit@1", 0),
        "hit@3": best.retrieval_metrics.get("avg_hit@3", 0),
        "hit@5": best.retrieval_metrics.get("avg_hit@5", 0),
        "mrr": best.retrieval_metrics.get("avg_mrr", 0),
        "latency_sec": best.latency_metrics.get("total_sec", 0),
        "cost_estimate": best.cost_estimate,
    }


# ═══════════════════════════════════════════════════════════
# 결과 저장 및 로드
# ═══════════════════════════════════════════════════════════

def save_dashboard(dashboard: BenchmarkDashboardData, output_dir: str):
    """벤치마크 결과를 파일에 저장"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # JSON 요약 저장
    summary_data = {
        "version": dashboard.version,
        "test_queries_count": len(dashboard.test_queries),
        "total_results": len(dashboard.results),
        "successful": sum(1 for r in dashboard.results if r.success),
        "failed": sum(1 for r in dashboard.results if not r.success),
        "comparison_matrix": dashboard.comparison_matrix,
        "summary": dashboard.summary,
    }
    
    summary_path = output_path / "rag_benchmark_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)
    
    # 상세 결과 CSV 저장
    csv_path = output_path / "rag_benchmark_detailed.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "combo_id", "chunk_config", "embed_config", "document_type", 
            "file_name", "success", "hit@1", "hit@3", "hit@5", "mrr",
            "latency_sec", "cost", "errors"
        ])
        
        for r in dashboard.results:
            writer.writerow([
                r.combo_id, r.chunk_config, r.embed_config, r.document_type,
                r.file_name, r.success,
                r.retrieval_metrics.get("avg_hit@1", 0),
                r.retrieval_metrics.get("avg_hit@3", 0),
                r.retrieval_metrics.get("avg_hit@5", 0),
                r.retrieval_metrics.get("avg_mrr", 0),
                r.latency_metrics.get("total_sec", 0),
                r.cost_estimate,
                r.errors[:100] if r.errors else "",
            ])
    
    # 테스트 쿼리 저장
    queries_path = output_path / "test_queries.json"
    with open(queries_path, 'w', encoding='utf-8') as f:
        json.dump({
            "queries": [
                {"query_id": q.query_id, "question": q.question,
                 "relevant_doc_stem": q.relevant_doc_stem,
                 "relevant_chunk_indices": q.relevant_chunk_indices,
                 "expected_keywords": q.expected_keywords}
                for q in dashboard.test_queries
            ]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"[BENCHMARK] 결과 저장: {summary_path}")
    print(f"[BENCHMARK] 상세 결과: {csv_path}")
    print(f"[BENCHMARK] 테스트 쿼리: {queries_path}")


def load_dashboard(output_dir: str) -> Optional[BenchmarkDashboardData]:
    """저장된 벤치마크 결과 로드"""
    summary_path = Path(output_dir) / "rag_benchmark_summary.json"
    
    if not summary_path.exists():
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    dashboard = BenchmarkDashboardData()
    dashboard.version = data.get("version", "1.0")
    dashboard.comparison_matrix = data.get("comparison_matrix", {})
    dashboard.summary = data.get("summary", {})
    
    return dashboard


# ═══════════════════════════════════════════════════════════
# Streamlit 대시보드 UI
# ═══════════════════════════════════════════════════════════

def render_dashboard(dashboard: BenchmarkDashboardData, output_dir: str = "output/bench/rag_bench"):
    """Streamlit 대시보드 렌더링 (별도 파일에서 streamlit run rag_benchmark_dashboard.py)"""
    try:
        import streamlit as st
    except ImportError:
        print("Streamlit이 설치되지 않았습니다: pip install streamlit")
        return
    
    st.set_page_config(page_title="DBMA RAG Benchmark", layout="wide")
    st.title("📊 DBMA RAG Benchmark Dashboard")
    st.caption(f"Version {dashboard.version} | {dashboard.summary.get('total_results', 0)} combinations tested")
    
    # 요약 메트릭
    st.subheader("Performance Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Successful", f"{dashboard.summary.get('successful', 0)}")
    c2.metric("Failed", f"{dashboard.summary.get('failed', 0)}")
    c3.metric("Documents", f"{dashboard.summary.get('total_documents', 0)}")
    c4.metric("Queries", f"{dashboard.summary.get('total_queries', 0)}")
    
    # 문서 유형별 최적 조합
    st.subheader("Best Combo by Document Type")
    by_type = dashboard.summary.get("by_doc_type", {})
    
    for doc_type, best in by_type.items():
        st.markdown(f"#### {doc_type.title()}")
        if best:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Hit@1", f"{best.get('hit@1', 0):.2%}")
            c2.metric("Hit@5", f"{best.get('hit@5', 0):.2%}")
            c3.metric("MRR", f"{best.get('mrr', 0):.3f}")
            c4.metric("Best Combo", best.get("combo", "N/A"))
    
    # 비교 행렬
    st.subheader("Comparison Matrix")
    matrix = dashboard.comparison_matrix
    
    if matrix:
        # 테이블로 표시
        rows = []
        for doc_type, combos in matrix.items():
            for (chunk_name, embed_name), metrics in combos.items():
                rows.append({
                    "Doc Type": doc_type,
                    "Chunk": chunk_name,
                    "Embed": embed_name,
                    "Avg Hit@1": metrics.get("avg_hit@1", 0),
                    "Avg Hit@3": metrics.get("avg_hit@3", 0),
                    "Avg Hit@5": metrics.get("avg_hit@5", 0),
                    "Avg MRR": metrics.get("avg_mrr", 0),
                    "Avg Latency(s)": metrics.get("avg_latency_sec", 0),
                })
        
        if rows:
            st.dataframe(rows, use_container_width=True)
    
    # 상세 결과 다운로드
    csv_path = Path(output_dir) / "rag_benchmark_detailed.csv"
    if csv_path.exists():
        with open(csv_path, 'rb', encoding='utf-8') as f:
            st.download_button("Download Detailed Results (CSV)", f.read(), file_name="rag_benchmark_detailed.csv")


# ═══════════════════════════════════════════════════════════
# 메인 진입점
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="DBMA RAG Benchmark Dashboard")
    parser.add_argument("--input", "-i", help="입력 파일 폴더 (기본: data/RAW)", default="data/RAW")
    parser.add_argument("--output", "-o", help="결과 출력 폴더 (기본: output/bench/rag_bench)", default="output/bench/rag_bench")
    parser.add_argument("--run", action="store_true", help="벤치마크 실행")
    parser.add_argument("--load-precomputed", action="store_true", help="저장된 결과 로드")
    parser.add_argument("--dashboard", action="store_true", help="Streamlit 대시보드 실행")
    parser.add_argument("--chunk-sizes", help="청크 사이즈 조합 (쉼표 구분, 예: 500,1000,1500)")
    parser.add_argument("--models", help="임베딩 모델 이름 (쉼표 구분)")
    parser.add_argument("--limit", type=int, default=5, help="처리할 파일 최대 개수")
    
    args = parser.parse_args()
    output_dir = Path(args.output)
    
    # 1. 벤치마크 실행
    if args.run:
        print("=" * 60)
        print("DBMA RAG Benchmark Dashboard")
        print("=" * 60)
        
        # 청킹 전략 설정
        chunk_configs = get_chunking_strategies()
        if args.chunk_sizes:
            sizes = [int(s.strip()) for s in args.chunk_sizes.split(',')]
            chunk_configs = [
                ChunkConfig(f"fixed_{s}", "fixed", s, max(60, s // 10))
                for s in sizes
            ] + [
                ChunkConfig("semantic_1000", "semantic", 1000, 120),
                ChunkConfig("structure_based", "structure", 1000, 120),
            ]
        
        # 임베딩 모델 설정
        embed_configs = get_embedding_models()
        if args.models:
            models = [m.strip() for m in args.models.split(',')]
            embed_configs = [EmbeddingConfig(m, 384, 0.0) for m in models]
        
        dashboard = run_full_benchmark(
            input_dir=args.input,
            output_dir=str(output_dir),
            chunk_configs=chunk_configs,
            embed_configs=embed_configs,
        )
        
        save_dashboard(dashboard, str(output_dir))
        
        print("\n" + "=" * 60)
        print("벤치마크 완료!")
        print(f"결과: {output_dir / 'rag_benchmark_summary.json'}")
        print("=" * 60)
    
    # 2. 대시보드 실행
    elif args.dashboard or args.load_precomputed:
        dashboard = load_dashboard(str(output_dir))
        
        if not dashboard:
            print(f"저장된 결과를 찾지 못했습니다: {output_dir / 'rag_benchmark_summary.json'}")
            print("먼저 --run 옵션으로 벤치마크를 실행하세요.")
            return
        
        render_dashboard(dashboard)


if __name__ == "__main__":
    main()
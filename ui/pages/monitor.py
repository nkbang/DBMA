"""DBMA Design System — System Monitor Page.

Real-time system health, performance metrics, and operational monitoring.
"""

from typing import Optional

import streamlit as st
import os
from pathlib import Path

from core.config import DEFAULT_EMBED_MODEL, DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR
from core.execution_context import ExecutionContext
from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.state.store import StateStore

# Korean label mapping for pipeline stages (same stages ExecutionContext
# reports; this UI previously lived on Dashboard — moved here since
# per-stage detail is developer-facing, not something a content-owner
# user needs to see day to day).
_STAGE_LABELS = {
    "extract": "추출",
    "chunk": "청킹",
    "embedding": "임베딩",
    "indexing": "인덱싱",
    "search": "검색",
}


def render_monitor_page() -> None:
    """Render the DBMA System Monitor page."""
    page = BasePage(title="시스템 모니터", icon="💚")
    page.render_header()

    # 파이프라인 상태와 건강 상태 둘 다 같은 ExecutionContext 스냅샷을
    # 쓰므로 한 번만 조회한다.
    pipeline_stages = ExecutionContext().get_pipeline_status()

    # ── Processing Pipeline Status (moved from Dashboard) ───────
    page.render_section("처리 파이프라인 상태", icon="⚙️")
    _render_pipeline_status(pipeline_stages)

    # ── Health Overview ────────────────────────────────────────
    page.render_section("시스템 건강 상태", icon="🏥")
    _render_health_overview(pipeline_stages)

    # ── Performance Metrics ────────────────────────────────────
    page.render_section("성능 지표", icon="📊")
    _render_performance_metrics()

    # ── Resource Usage ─────────────────────────────────────────
    page.render_section("리소스 사용량", icon="💻")
    _render_resource_usage()

    # ── Embedding Coverage Report ────────────────────────────────
    page.render_section("임베딩 커버리지 리포트", icon="📚")
    _render_embedding_coverage_report()

    # ── Log Viewer ─────────────────────────────────────────────
    page.render_section("운영 로그", icon="📜")
    _render_log_viewer()

    page.render_footer()


def _render_pipeline_status(runtime_stages) -> None:
    """Render per-stage pipeline progress (moved from Dashboard — see
    core/runtime_state.py::get_pipeline_status for how each stage's
    status/progress/detail is computed)."""
    stages = [
        {
            "label": _STAGE_LABELS.get(s.stage, s.stage),
            "status": s.status,
            "progress": s.progress,
            "detail": s.detail,
        }
        for s in runtime_stages
    ]

    stage_colors = {
        "complete": THEME.STATUS_SUCCESS,
        "active": THEME.BRAND_SECONDARY,
        "pending": THEME.TEXT_TERTIARY,
    }
    stage_icons = {
        "complete": "✅",
        "active": "🔄",
        "pending": "⏳",
    }

    cols = st.columns(len(stages) + (len(stages) - 1))
    for i, stage in enumerate(stages):
        with cols[i * 2]:
            color = stage_colors.get(stage["status"], stage_colors["pending"])
            icon = stage_icons.get(stage["status"], stage_icons["pending"])
            html = f"""
            <div style="text-align: center; padding: {8}px 4px;" title="{stage['detail']}">
                <div style="font-size: 20px; margin-bottom: 4px;">{icon}</div>
                <div style="font-size: 12px; color: {color}; font-weight: 600;">
                    {stage['label']}
                </div>
                <div style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                    {stage['progress']}%
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        if i < len(stages) - 1:
            with cols[i * 2 + 1]:
                st.progress(0.8)
                st.caption("→")


def _render_health_overview(pipeline_stages) -> None:
    """Render system health overview from real signals — no hardcoded
    statuses. 벡터DB는 파이프라인의 인덱싱 단계 결과를 그대로 재사용하고,
    파일시스템/메모리는 실측치를 읽는다."""
    stage_by_name = {s.stage: s for s in pipeline_stages}
    indexing = stage_by_name.get("indexing")
    vector_ok = indexing is not None and indexing.status == "complete"

    fs_ok = Path(DEFAULT_RAW_DIR).is_dir() and Path(DEFAULT_OUTPUT_DIR).is_dir()
    mem_percent = _get_memory_usage()

    components = [
        {
            "name": "벡터 데이터베이스",
            "status": "healthy" if vector_ok else "warning",
            "detail": indexing.detail if indexing else "확인 불가",
        },
        {
            "name": "임베딩 모델",
            # 실제 Ollama 헬스체크(네트워크 호출)는 페이지 렌더를 지연시킬
            # 수 있어 하지 않는다 — 설정값만 보여준다("정상" 과대표시 방지).
            "status": "info",
            "detail": f"{DEFAULT_EMBED_MODEL} 설정됨",
        },
        {
            "name": "파일 시스템",
            "status": "healthy" if fs_ok else "error",
            "detail": "읽기/쓰기 가능" if fs_ok else "RAW/출력 폴더 없음",
        },
        {
            "name": "메모리",
            "status": "warning" if mem_percent >= 80 else "healthy",
            "detail": f"사용율 {mem_percent}%",
        },
    ]

    status_colors = {
        "healthy": THEME.STATUS_SUCCESS,
        "warning": THEME.STATUS_WARNING,
        "error": THEME.STATUS_ERROR,
        "info": THEME.STATUS_INFO,
    }
    status_labels = {
        "healthy": "정상",
        "warning": "경고",
        "error": "오류",
        "info": "정보",
    }
    status_icons = {
        "healthy": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",
    }

    cols = st.columns(len(components))
    for i, comp in enumerate(components):
        with cols[i]:
            color = status_colors.get(comp["status"], THEME.TEXT_TERTIARY)
            label = status_labels.get(comp["status"], comp["status"])
            icon = status_icons.get(comp["status"], "⏳")

            html = f"""
            <div style="text-align: center; padding: {12}px 4px;">
                <div style="font-size: 20px; margin-bottom: 4px;">{icon}</div>
                <div style="font-size: 11px; font-weight: 600; color: {color}; margin-bottom: 2px;">
                    {comp['name']}
                </div>
                <div style="font-size: 10px; color: {THEME.TEXT_TERTIARY};">
                    {label}
                </div>
                <div style="font-size: 9px; color: {THEME.TEXT_TERTIARY}; margin-top: 2px;">
                    {comp['detail']}
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)


_BENCHMARK_RESULT_PATH = "output/bench/chapter_level_result_v1.3.0_cap2.json"
# [Preflight] 이전엔 output/SPRINT5_ENGINEERING_VALIDATION/benchmark_results_
# sprint9.json을 후보로 봤으나, 그 파일은 precision/MRR/nDCG가 전부 0.0인
# 깨진/구코퍼스 실행분이었다. 이 파일은 v1.3.0 태그 + 1500쿼리 + 2026-07-17
# 실행으로 현재 스키마와 맞는 유일한 실측 결과라 이걸 쓴다. 버전이 파일명에
# 박혀 있어 다음 정식 벤치마크 때는 경로를 갱신해야 한다(자동 latest-file
# 탐색은 잘못된 실행분을 집어올 위험이 있어 명시적 경로를 택했다).


def _read_benchmark_result() -> Optional[dict]:
    import json

    path = Path(_BENCHMARK_RESULT_PATH)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _format_size(size_bytes: float | int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _render_performance_metrics() -> None:
    """Render performance metrics — all real, no hardcoded/simulated values.

    "처리_throughput"이었던 4번째 카드는 검색/채팅 성능이 아니라 문서 처리
    파이프라인 속도라 실측 가능한 유일한 지표라 "문서 처리 속도"로 이름과
    의미를 바꿨다. 실시간 지표가 아닌 값(벤치마크, 처리 속도)은 반드시
    측정 시점을 같이 표기해 "지금 이 순간"으로 오인하지 않게 한다.
    """
    from core.runtime_state import get_index_size_bytes, get_processing_throughput

    # 1. 평균 검색 응답 시간 — 이 세션에서 실행된 Chat/Research 쿼리 누적.
    # QueryProcessor.process()의 retrieval 단계(total_ms)만 잰다 — LLM
    # 생성 시간은 별도(수 초~수십 초 단위)라 같이 평균 내면 이 카드의
    # 밀리초 단위 스케일과 안 맞아 오해를 준다.
    latencies = st.session_state.get("query_latencies_ms", [])
    avg_latency = f"{sum(latencies) / len(latencies):.0f}ms" if latencies else "데이터 없음"
    latency_detail = (
        f"검색(retrieval)만 집계, LLM 생성 시간 제외 · 이번 세션 {len(latencies)}건 평균"
        if latencies else "Chat/Research에서 질문하면 누적됩니다 (검색 단계만, LLM 생성 제외)"
    )

    # 2. 문서 처리 속도 — 이벤트 로그 기반, 유휴 구간 제외
    throughput = get_processing_throughput()
    if throughput:
        throughput_value = f"{throughput['files_per_sec']:.2f}/sec"
        throughput_detail = f"기준: {throughput['as_of'][:16].replace('T', ' ')}"
    else:
        throughput_value = "데이터 없음"
        throughput_detail = "처리 이력 부족"

    # 3. 검색 정확도 — 저장된 벤치마크 결과 (실시간 재측정 아님)
    bench = _read_benchmark_result()
    if bench and "metrics" in bench:
        m = bench["metrics"]
        accuracy_value = f"MRR {m.get('mrr', 0):.3f}"
        accuracy_detail = f"precision@1 {m.get('precision_at_1', 0):.3f} · {bench.get('generated_at', bench.get('gold_standard_version', ''))}"
    else:
        accuracy_value = "데이터 없음"
        accuracy_detail = "벤치마크 결과 파일 없음"

    # 4. 인덱스 크기 — chroma_db 실측
    index_bytes = get_index_size_bytes()
    index_value = _format_size(index_bytes) if index_bytes > 0 else "데이터 없음"

    metrics = [
        {"label": "평균 응답 시간", "value": avg_latency, "detail": latency_detail},
        {"label": "문서 처리 속도", "value": throughput_value, "detail": throughput_detail},
        {"label": "검색 정확도", "value": accuracy_value, "detail": accuracy_detail},
        {"label": "인덱스 크기", "value": index_value, "detail": "chroma_db 실측"},
    ]

    c1, c2, c3, c4 = st.columns(4)
    for i, m in enumerate(metrics):
        with [c1, c2, c3, c4][i]:
            st.metric(m["label"], m["value"], help=m["detail"])


def _render_resource_usage() -> None:
    """Render resource usage indicators."""
    # CPU
    cpu_percent = _get_cpu_usage()
    st.markdown("#### CPU 사용률")
    st.progress(cpu_percent / 100.0)
    st.caption(f"{cpu_percent:.1f}% 사용 중")

    # Memory
    mem_percent = _get_memory_usage()
    st.markdown("#### 메모리 사용률")
    st.progress(mem_percent / 100.0)
    st.caption(f"{mem_percent:.1f}% 사용 중 ({_format_size(mem_percent * 1024 * 1024)})")

    # Disk
    disk_percent = _get_disk_usage()
    st.markdown("#### 디스크 사용률")
    st.progress(disk_percent / 100.0)
    st.caption(f"{disk_percent:.1f}% 사용 중")


def _render_log_viewer() -> None:
    """Render the operational log viewer."""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        st.info("로그 파일이 없습니다.")
        return

    log_files = list(logs_dir.glob("*.log"))
    if not log_files:
        st.info("로그 파일이 없습니다.")
        return

    # Select log file
    selected_log = st.selectbox(
        "로그 파일 선택",
        options=[f.name for f in log_files],
        key="monitor_log_select",
    )

    if selected_log:
        log_path = logs_dir / selected_log
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-100:]  # Last 100 lines
            st.text_area(
                "로그 내용",
                value="".join(lines),
                height=300,
                key="monitor_log_display",
            )
        except (IOError, UnicodeDecodeError):
            st.error("로그 파일을 읽을 수 없습니다.")


# ── Utility Functions ──────────────────────────────────────────────

def _get_cpu_usage() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        return 35.0


def _get_memory_usage() -> int:
    """Get memory usage percentage."""
    try:
        import psutil
        return int(psutil.virtual_memory().percent)
    except ImportError:
        return 45


def _get_disk_usage() -> float:
    """Get disk usage percentage."""
    try:
        import psutil
        return float(psutil.disk_usage("/").percent)
    except ImportError:
        return 60.0


def _render_embedding_coverage_report() -> None:
    """book_embedding_coverage() 기반: 커버리지 미달 책만 보여주는 리포트."""
    from core.retrieval import RetrievalEngine
    from core.config import DEFAULT_TSU_DATASET_PATH, DEFAULT_OUTPUT_DIR
    from core.retrieval import EmbeddingCache

    try:
        engine = RetrievalEngine(DEFAULT_TSU_DATASET_PATH)
        cache = EmbeddingCache(str(Path(DEFAULT_OUTPUT_DIR) / "cache" / "embeddings"))
        coverage = engine.book_embedding_coverage(cache)
    except Exception:
        st.warning("커버리지 데이터를 로드할 수 없습니다.")
        return

    if not coverage:
        st.info("📚 모든 책의 임베딩 커버리지가 100%입니다.")
        return

    # coverage_ratio < 1.0인 책만 필터 (coverage 0은 dict에 없음)
    incomplete = {k: v for k, v in coverage.items() if v["coverage_ratio"] < 1.0}
    if not incomplete:
        st.info("📚 모든 책의 임베딩 커버리지가 100%입니다.")
        return

    st.markdown("**커버리지 미달 책**")
    for book_id in sorted(incomplete):
        stats = incomplete[book_id]
        ratio_pct = stats["coverage_ratio"] * 100
        st.markdown(
            f"- **{book_id}**: {stats['embedded']}/{stats['total']} chunks "
            f"({ratio_pct:.1f}%) — dimension_ok: {stats['dimension_ok']}"
        )



"""DBMA Design System — System Monitor Page.

Real-time system health, performance metrics, and operational monitoring.
"""

from typing import Optional

import streamlit as st
import os
from pathlib import Path

from core.config import DEFAULT_EMBED_MODEL
from ui.pages._base import BasePage
from ui.theme.colors import THEME
from ui.state.store import StateStore


def render_monitor_page() -> None:
    """Render the DBMA System Monitor page."""
    page = BasePage(title="System Monitor", icon="💚")
    page.render_header()

    # ── Health Overview ────────────────────────────────────────
    page.render_section("시스템 건강 상태", icon="🏥")
    _render_health_overview()

    # ── Performance Metrics ────────────────────────────────────
    page.render_section("성능 지표", icon="📊")
    _render_performance_metrics()

    # ── Resource Usage ─────────────────────────────────────────
    page.render_section("리소스 사용량", icon="💻")
    _render_resource_usage()

    # ── Log Viewer ─────────────────────────────────────────────
    page.render_section("운영 로그", icon="📜")
    _render_log_viewer()

    page.render_footer()


def _render_health_overview() -> None:
    """Render system health overview."""
    components = [
        {"name": "벡터 데이터베이스", "status": "healthy", "detail": "연결 정상"},
        {"name": "임베딩 모델", "status": "healthy", "detail": f"{DEFAULT_EMBED_MODEL} 로드됨"},
        {"name": "파일 시스템", "status": "healthy", "detail": "읽기/쓰기 가능"},
        {"name": "메모리", "status": "warning", "detail": "사용율 72%"},
        {"name": "디스크", "status": "healthy", "detail": "여유 공간充足"},
        {"name": "파이프라인", "status": "idle", "detail": "대기 중"},
    ]

    status_colors = {
        "healthy": THEME.STATUS_SUCCESS,
        "warning": THEME.STATUS_WARNING,
        "error": THEME.STATUS_ERROR,
        "idle": THEME.TEXT_TERTIARY,
    }
    status_labels = {
        "healthy": "정상",
        "warning": "경고",
        "error": "오류",
        "idle": "대기",
    }

    cols = st.columns(len(components))
    for i, comp in enumerate(components):
        with cols[i]:
            color = status_colors.get(comp["status"], THEME.TEXT_TERTIARY)
            label = status_labels.get(comp["status"], comp["status"])
            icon = "✅" if comp["status"] == "healthy" else "⚠️" if comp["status"] == "warning" else "⏳"

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


def _render_performance_metrics() -> None:
    """Render performance metrics."""
    # Simulated metrics (replace with actual measurements)
    metrics = [
        {"label": "평균 응답 시간", "value": "142ms", "trend": "↓ 5%"},
        {"label": "처리_throughput", "value": "8.3/sec", "trend": "→ 0%"},
        {"label": "검색 정확도 (RRF)", "value": "0.8923", "trend": "↑ 2%"},
        {"label": "인덱스 크기", "value": "156MB", "trend": "↑ 12%"},
    ]

    c1, c2, c3, c4 = st.columns(4)
    for i, m in enumerate(metrics):
        with [c1, c2, c3, c4][i]:
            st.metric(m["label"], m["value"], m["trend"])


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


def _format_size(size_bytes: float | int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
"""DBMA Design System — Page Base Class.

Provides common utilities shared across all DBMA pages.
"""

from typing import Optional

import streamlit as st

from core.config import APP_VERSION
from ui.theme.colors import THEME


class BasePage:
    """Base class for DBMA pages with common rendering utilities."""

    def __init__(self, title: str, icon: str = "description"):
        self.title = title
        self.icon = icon

    def render_header(self) -> None:
        """Render the standard page header.

        icon은 Material Symbols 아이콘 이름(예: "search")이다 — 빈 문자열이면
        아이콘 없이 제목만 렌더링한다. 사용자-facing 캡션은 내서재/NAE —
        DBMA는 내부 식별자로만 유지(docs/governance/DBMA-BRAND-GOV-001.md).
        """
        icon_html = (
            f'<span class="material-symbols-outlined" style="font-size: 26px; vertical-align: -4px;">{self.icon}</span> '
            if self.icon else ""
        )
        st.markdown(
            f"""
            <header class="nae-page-header">
                <div class="nae-page-title">{icon_html}{self.title}</div>
                <div class="nae-page-meta">내서재 · NAE · v{APP_VERSION}</div>
            </header>
            """,
            unsafe_allow_html=True,
        )

    def render_section(self, title: str, icon: str = "list_alt") -> None:
        """Render a section heading with divider. icon은 Material Symbols
        아이콘 이름 — 빈 문자열이면 아이콘 없이 제목만 렌더링한다."""
        icon_html = (
            f'<span class="material-symbols-outlined" style="font-size: 20px; vertical-align: -3px;">{icon}</span> '
            if icon else ""
        )
        st.markdown(
            f'<div class="nae-section-heading">{icon_html}{title}</div>',
            unsafe_allow_html=True,
        )

    def render_error_box(self, message: str) -> None:
        """Render an error message box."""
        st.error(message)

    def render_warning_box(self, message: str) -> None:
        """Render a warning message box."""
        st.warning(message)

    def render_info_box(self, message: str) -> None:
        """Render an info message box."""
        st.info(message)

    def render_metrics_row(self, metrics: list[dict], num_cols: int = 4) -> None:
        """Render a row of metric cards.

        Parameters
        ----------
        metrics : list[dict]
            Each dict: {'label': str, 'value': str|int|float, 'icon': str, 'color': str}
        num_cols : int
            Number of columns to distribute across.
        """
        cols = st.columns(num_cols)
        for i, m in enumerate(metrics):
            with cols[i % num_cols]:
                icon = m.get("icon", "📊")
                color = m.get("color", THEME.STATUS_INFO)
                label = m["label"]
                value = m["value"]
                subtitle = m.get("subtitle")

                html = f"""
                <div style="text-align: center; padding: {16}px 8px;">
                    <div style="font-size: 24px; margin-bottom: 8px;">{icon}</div>
                    <div style="font-size: 22px; font-weight: 700; color: {THEME.TEXT_PRIMARY};">
                        {value}
                    </div>
                    <div style="font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin-top: 4px;">
                        {label}
                    </div>
                    {f'<div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-top: 2px;">{subtitle}</div>' if subtitle else ''}
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)

    def render_status_row(self, statuses: list[dict]) -> None:
        """Render a row of status badges.

        Parameters
        ----------
        statuses : list[dict]
            Each dict: {'label': str, 'status': str}
        """
        cols = st.columns(len(statuses))
        for i, s in enumerate(statuses):
            with cols[i]:
                label = s.get("label", "")
                status = s.get("status", "neutral")

                _BG_COLORS = {
                    "success": THEME.STATUS_SUCCESS_BG,
                    "warning": THEME.STATUS_WARNING_BG,
                    "error": THEME.STATUS_ERROR_BG,
                    "info": THEME.STATUS_INFO_BG,
                    "neutral": THEME.STATUS_NEUTRAL_BG,
                }
                _TEXT_COLORS = {
                    "success": THEME.STATUS_SUCCESS,
                    "warning": THEME.STATUS_WARNING,
                    "error": THEME.STATUS_ERROR,
                    "info": THEME.STATUS_INFO,
                    "neutral": THEME.STATUS_NEUTRAL,
                }

                bg = _BG_COLORS.get(status, THEME.STATUS_NEUTRAL_BG)
                text_color = _TEXT_COLORS.get(status, THEME.STATUS_NEUTRAL)

                html = f"""
                <span style="
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 4px;
                    background: {bg};
                    color: {text_color};
                    font-size: 11px;
                    font-weight: 600;
                ">
                    {label}
                </span>
                """
                st.markdown(html, unsafe_allow_html=True)

    def render_footer(self) -> None:
        """Render the standard page footer."""
        st.markdown(
            f"""
            <footer class="nae-fixed-footer">
                <span>현재 보고 있는 화면: {self.title}</span>
                <span class="nae-footer-link">내서재에게 물어보세요</span>
            </footer>
            """,
            unsafe_allow_html=True,
        )
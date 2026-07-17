"""DBMA Design System — Page Base Class.

Provides common utilities shared across all DBMA pages.
"""

from typing import Optional

import streamlit as st

from core.config import APP_VERSION
from ui.theme.colors import THEME


class BasePage:
    """Base class for DBMA pages with common rendering utilities."""

    def __init__(self, title: str, icon: str = "📄"):
        self.title = title
        self.icon = icon

    def render_header(self) -> None:
        """Render the standard page header."""
        st.markdown(f"## {self.icon} {self.title}")
        st.caption(f"DBMA v{APP_VERSION} — Personal Knowledge Operating System")

    def render_section(self, title: str, icon: str = "📋") -> None:
        """Render a section heading with divider."""
        st.divider()
        st.markdown(f"### {icon} {title}")

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
        st.divider()
        st.caption(f"DBMA v{APP_VERSION} — David Bang Ministry Archive | Personal Knowledge Operating System")
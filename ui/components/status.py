"""DBMA Design System — Status Components.

Progress indicators and status badges for workflow feedback.
"""

from typing import Optional

import streamlit as st
from ui.theme.colors import THEME


def progress_indicator(percentage: float,
                      label: Optional[str] = None,
                      show_value: bool = True) -> None:
    """Render a styled progress indicator.

    Parameters
    ----------
    percentage : float
        Progress from 0.0 to 100.0.
    label : str, optional
        Label displayed above the bar.
    show_value : bool
        Whether to show the percentage value in parentheses.
    """
    norm_pct = min(max(percentage, 0.0), 100.0)

    if label:
        st.caption(f"{label}: {norm_pct:.0f}%")

    st.progress(norm_pct / 100.0)


def status_badge(label: str,
                 status: str = "neutral",
                 size: str = "md") -> None:
    """Render a status badge inline.

    Parameters
    ----------
    label : str
        Badge text label.
    status : str
        One of 'success', 'warning', 'error', 'info', 'neutral'.
    size : str
        Size: 'sm' (small) or 'md' (medium).
    """
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

    if size == "sm":
        padding = "2px 6px"
        font_size = "10px"
    else:
        padding = "3px 10px"
        font_size = "11px"

    html = f"""
    <span style="
        display: inline-block;
        padding: {padding};
        border-radius: 4px;
        background: {bg};
        color: {text_color};
        font-size: {font_size};
        font-weight: 600;
        line-height: 1.4;
    ">
        {label}
    </span>
    """
    st.markdown(html, unsafe_allow_html=True)


def workflow_status(stages: list[dict]) -> None:
    """Render a multi-stage workflow progress indicator.

    Parameters
    ----------
    stages : list[dict]
        Each dict: {'label': str, 'status': str, 'progress': float}
        Status: 'complete', 'active', 'pending'.
    """
    _STAGE_STYLES = {
        "complete": ("✅", THEME.STATUS_SUCCESS),
        "active": ("🔄", THEME.BRAND_SECONDARY),
        "pending": ("⏳", THEME.TEXT_TERTIARY),
    }

    n = len(stages)
    if n == 0:
        return

    cols = st.columns(n + (n - 1))
    for i, stage in enumerate(stages):
        # Render stage node
        with cols[i * 2]:
            icon, color = _STAGE_STYLES.get(stage.get("status", "pending"), _STAGE_STYLES["pending"])
            label = stage.get("label", "")
            html = f"""
            <div style="text-align: center; padding: {8}px 4px;">
                <div style="font-size: 16px; margin-bottom: 2px;">{icon}</div>
                <div style="font-size: 10px; color: {color}; font-weight: 500; max-width: 80px; margin: 0 auto; word-wrap: break-word;">
                    {label}
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        # Render connector (except after last)
        if i < n - 1:
            with cols[i * 2 + 1]:
                current_status = stage.get("status", "pending")
                next_status = stages[i + 1].get("status", "pending")
                connector_color = THEME.BORDER_LIGHT
                if current_status == "complete":
                    connector_color = THEME.STATUS_SUCCESS
                elif current_status == "active":
                    connector_color = THEME.BRAND_SECONDARY

                progress = stage.get("progress", 0) / 100.0
                st.progress(max(min(progress, 1.0), 0.0))
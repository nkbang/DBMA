"""DBMA Design System — Metric Display Components.

Components for displaying numerical metrics and comparative data
in a professional academic workspace style.
"""

from typing import Optional

import streamlit as st
from ui.theme.colors import THEME


def stat_metric(label: str, value: str | int | float, delta: Optional[str | float] = None,
               delta_color: str = "normal", prefix: str = "", suffix: str = "") -> None:
    """Render a styled metric display.

    Parameters
    ----------
    label : str
        Metric label text.
    value : str | int | float
        Current metric value.
    delta : str | float, optional
        Change from previous value.
    delta_color : str
        "normal", "inverse", or "off".
    prefix : str
        Value prefix (e.g., "$", "%").
    suffix : str
        Value suffix (e.g., "%", " MB").
    """
    display_value = f"{prefix}{value}{suffix}"

    html = f"""
    <div style="padding: {12}px 0;">
        <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY}; font-weight: 500; margin-bottom: 4px;">
            {label}
        </div>
        <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-size: 24px; font-weight: 700; color: {THEME.TEXT_PRIMARY};">
                {display_value}
            </span>
            {f'<span style="font-size: 13px; color: {"#2D7D5B" if delta_color == "normal" else "#C62828" if delta_color == "inverse" else THEME.TEXT_TERTIARY}; font-weight: 500;">'
             f'({delta})</span>' if delta is not None else ''}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def stat_comparison(labels_values: list[tuple[str, str | int | float]],
                  comparison_delta: Optional[str] = None) -> None:
    """Render a side-by-side metric comparison.

    Parameters
    ----------
    labels_values : list[tuple[str, str | int | float]]
        List of (label, value) pairs for comparison metrics.
    comparison_delta : str, optional
        Overall delta annotation text.
    """
    n = len(labels_values)
    cols = st.columns(n)

    for i, (label, value) in enumerate(labels_values):
        with cols[i]:
            stat_metric(label=label, value=value)

    if comparison_delta:
        st.caption(comparison_delta)


def progress_bar_styled(percentage: float, label: Optional[str] = None,
                        color: Optional[str] = None) -> None:
    """Render a styled progress bar.

    Parameters
    ----------
    percentage : float
        Progress from 0.0 to 100.0.
    label : str, optional
        Label displayed above the bar.
    color : str, optional
        Custom progress bar color. Defaults to brand secondary.
    """
    if label:
        st.caption(f"{label}: {percentage:.0f}%")

    c = color or THEME.BRAND_SECONDARY
    st.progress(min(max(percentage, 0.0), 100.0) / 100.0)


def kpi_row(metrcs: list[dict], num_cols: int = 4) -> None:
    """Render a row of KPI (Key Performance Indicator) cards.

    Parameters
    ----------
    metrics : list[dict]
        Each dict must have: label, value, and optionally icon, subtitle, color.
    num_cols : int
        Number of columns to distribute metrics across.
    """
    cols = st.columns(num_cols)
    for i, m in enumerate(metrcs):
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
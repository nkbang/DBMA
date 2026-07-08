"""DBMA Design System — Card Components.

Reusable card components for displaying metrics, status information,
and document summaries in a consistent visual language.
"""

from dataclasses import dataclass
from typing import Optional

import streamlit as st

# Import theme tokens
from ui.theme.colors import THEME


@dataclass
class MetricCardConfig:
    """Configuration for MetricCard component."""
    title: str
    value: str | int | float
    subtitle: Optional[str] = None
    icon: str = "📊"
    color: Optional[str] = None
    border_color: Optional[str] = None


def metric_card(cfg: MetricCardConfig) -> None:
    """Render a metric value card.

    Parameters
    ----------
    cfg : MetricCardConfig
        Card configuration with title, value, subtitle, icon, and colors.
    """
    color = cfg.color or THEME.STATUS_INFO
    border_color = cfg.border_color or THEME.BORDER_LIGHT

    html = f"""
    <div style="
        background: {THEME.BG_SURFACE};
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: {16}px {20}px;
        margin-bottom: {12}px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <span style="font-size: 20px;">{cfg.icon}</span>
            <span style="
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px;
                color: {THEME.TEXT_SECONDARY};
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            ">
                {cfg.title}
            </span>
        </div>
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: {THEME.TEXT_PRIMARY};
            line-height: 1.1;
            margin-bottom: {cfg.subtitle and 4 or 0}px;
        ">
            {cfg.value}
        </div>
        {f'<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: {THEME.TEXT_TERTIARY};">' + cfg.subtitle + '</div>' if cfg.subtitle else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


@dataclass
class StatusCardConfig:
    """Configuration for StatusCard component."""
    label: str
    status: str  # success, warning, error, info, neutral
    detail: Optional[str] = None
    icon: Optional[str] = None


_STATUS_ICONS = {
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️",
    "neutral": "🔘",
}

_STATUS_COLORS = {
    "success": THEME.STATUS_SUCCESS,
    "warning": THEME.STATUS_WARNING,
    "error": THEME.STATUS_ERROR,
    "info": THEME.STATUS_INFO,
    "neutral": THEME.STATUS_NEUTRAL,
}


def status_card(cfg: StatusCardConfig) -> None:
    """Render a status indicator card.

    Parameters
    ----------
    cfg : StatusCardConfig
        Status card configuration.
    """
    icon = cfg.icon or _STATUS_ICONS.get(cfg.status, "🔘")
    color = _STATUS_COLORS.get(cfg.status, THEME.STATUS_NEUTRAL)
    bg_color = getattr(THEME, f"STATUS_{cfg.status.upper()}_BG", THEME.STATUS_NEUTRAL_BG)

    html = f"""
    <div style="
        background: {bg_color};
        border: 1px solid {color}44;
        border-radius: 8px;
        padding: {12}px {16}px;
        margin-bottom: {8}px;
        display: flex;
        align-items: center;
        gap: 12px;
    ">
        <span style="font-size: 18px;">{icon}</span>
        <div>
            <span style="
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px;
                font-weight: 600;
                color: {color};
            ">
                {cfg.label}
            </span>
            {f'<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 12px; color: {THEME.TEXT_SECONDARY}; margin-top: 2px;">{cfg.detail}</div>' if cfg.detail else ''}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


@dataclass
class DocCardConfig:
    """Configuration for document card component."""
    title: str
    doc_type: str = "document"
    size: Optional[str] = None
    modified: Optional[str] = None
    tags: Optional[list[str]] = None
    status: str = "neutral"


def doc_card(cfg: DocCardConfig) -> None:
    """Render a document summary card for library/grid views.

    Parameters
    ----------
    cfg : DocCardConfig
        Document card configuration.
    """
    status_color = _STATUS_COLORS.get(cfg.status, THEME.STATUS_NEUTRAL)
    tags_html = ""
    if cfg.tags:
        tag_items = " ".join(
            f'<span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; '
            f'background: {THEME.BRAND_PRIMARY}22; color: {THEME.BRAND_PRIMARY}; '
            f'font-weight: 500;">{tag}</span>'
            for tag in cfg.tags
        )
        tags_html = f'<div style="margin-top: 8px;">{tag_items}</div>'

    html = f"""
    <div style="
        background: {THEME.BG_SURFACE};
        border: 1px solid {THEME.BORDER_LIGHT};
        border-radius: 8px;
        padding: {16}px;
        margin-bottom: {12}px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        cursor: pointer;
        transition: box-shadow 0.15s ease;
    " onmouseover="this.style.boxShadow='0 3px 8px rgba(0,0,0,0.1)'"
       onmouseout="this.style.boxShadow='0 1px 3px rgba(0,0,0,0.04)'">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
            <span style="font-size: 14px; font-weight: 600; color: {THEME.TEXT_PRIMARY}; line-height: 1.3;">
                {cfg.title}
            </span>
            <span style="
                width: 8px; height: 8px; border-radius: 50%;
                background: {status_color};
                flex-shrink: 0; margin-left: 8px;
            "></span>
        </div>
        <div style="font-size: 11px; color: {THEME.TEXT_TERTIARY}; margin-bottom: 4px;">
            {cfg.doc_type.upper()}
            {f' • {cfg.size}' if cfg.size else ''}
            {f' • 수정: {cfg.modified}' if cfg.modified else ''}
        </div>
        {tags_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
"""DBMA Design System — Dialog Components.

Confirmation dialogs and informational overlays for user interaction.
"""

from typing import Optional

import streamlit as st
from ui.theme.colors import THEME


def confirm_action(message: str,
                   confirm_text: str = "확인",
                   cancel_text: str = "취소",
                   key: Optional[str] = None) -> bool:
    """Render a confirmation dialog and return user choice.

    Parameters
    ----------
    message : str
        Confirmation message to display.
    confirm_text : str
        Text for the confirmation button.
    cancel_text : str
        Text for the cancel button.
    key : str, optional
        Unique key for the dialog widget.

    Returns
    -------
    bool
        True if confirmed, False if cancelled.
    """
    col1, col2 = st.columns([1, 4])

    with col1:
        confirmed = st.button(
            confirm_text,
            key=key or "confirm_btn",
            use_container_width=True,
            type="primary",
        )
    with col2:
        st.caption(message)

    return confirmed


def show_info_dialog(title: str,
                     message: str,
                     icon: str = "ℹ️",
                     severity: str = "info") -> None:
    """Render an informational dialog box.

    Parameters
    ----------
    title : str
        Dialog title.
    message : str
        Dialog body message.
    icon : str
        Emoji icon for the dialog.
    severity : str
        One of 'info', 'success', 'warning', 'error'.
    """
    _BORDER_COLORS = {
        "info": THEME.STATUS_INFO,
        "success": THEME.STATUS_SUCCESS,
        "warning": THEME.STATUS_WARNING,
        "error": THEME.STATUS_ERROR,
    }
    bg_colors = {
        "info": THEME.STATUS_INFO_BG,
        "success": THEME.STATUS_SUCCESS_BG,
        "warning": THEME.STATUS_WARNING_BG,
        "error": THEME.STATUS_ERROR_BG,
    }
    border_color = _BORDER_COLORS.get(severity, THEME.STATUS_INFO)
    bg_color = bg_colors.get(severity, THEME.STATUS_INFO_BG)

    html = f"""
    <div style="
        background: {bg_color};
        border-left: 4px solid {border_color};
        border-radius: 6px;
        padding: {12}px {16}px;
        margin-bottom: {12}px;
    ">
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <span style="font-size: 18px;">{icon}</span>
            <div>
                <div style="font-size: 14px; font-weight: 600; color: {border_color}; margin-bottom: 4px;">
                    {title}
                </div>
                <div style="font-size: 13px; color: {THEME.TEXT_SECONDARY}; line-height: 1.5;">
                    {message}
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def show_warning_dialog(title: str, message: str) -> None:
    """Render a warning dialog."""
    show_info_dialog(
        title=title,
        message=message,
        icon="⚠️",
        severity="warning",
    )


def show_error_dialog(title: str, message: str) -> None:
    """Render an error dialog."""
    show_info_dialog(
        title=title,
        message=message,
        icon="❌",
        severity="error",
    )


def show_success_dialog(title: str, message: str) -> None:
    """Render a success dialog."""
    show_info_dialog(
        title=title,
        message=message,
        icon="✅",
        severity="success",
    )
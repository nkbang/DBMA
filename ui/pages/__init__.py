"""DBMA Design System — Pages package."""

from ui.pages._base import BasePage
from ui.pages.dashboard import render_dashboard_page
from ui.pages.library import render_library_page
from ui.pages.processing import render_processing_page
from ui.pages.research import render_research_page
from ui.pages.chat import render_chat_page
from ui.pages.sermon_draft import render_sermon_draft_page
from ui.pages.monitor import render_monitor_page

__all__ = [
    "BasePage",
    "render_dashboard_page",
    "render_library_page",
    "render_processing_page",
    "render_research_page",
    "render_chat_page",
    "render_sermon_draft_page",
    "render_monitor_page",
]
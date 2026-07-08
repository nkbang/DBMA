"""DBMA Design System — Components package.

Reusable presentational components built on Streamlit primitives.
All components accept theme tokens for consistent styling.
"""

from ui.components.cards import metric_card, status_card, doc_card
from ui.components.metrics import stat_metric, stat_comparison
from ui.components.tables import document_table, search_results_table
from ui.components.dialogs import confirm_action, show_info_dialog
from ui.components.status import progress_indicator, status_badge

__all__ = [
    "metric_card",
    "status_card",
    "doc_card",
    "stat_metric",
    "stat_comparison",
    "document_table",
    "search_results_table",
    "confirm_action",
    "show_info_dialog",
    "progress_indicator",
    "status_badge",
]

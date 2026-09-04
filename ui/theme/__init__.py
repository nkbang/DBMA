"""DBMA Design System — Theme package.

Provides the centralized color tokens used across all UI pages and
components.

[2026-08-25] typography.py/spacing.py were archived to
archive/legacy/ui/theme/ — their constants (FONT_*, SPACING_*) had zero
importers project-wide (only mentioned inside prose comments in
ui/pages/research.py), and this aggregate re-export had zero importers of
its own: every page imports `ui.theme.colors` directly. See
docs/UI-REALIGNMENT-PROPOSAL-v1.md §P2.
"""

from ui.theme.colors import DBMADesignSystemColors

__all__ = ["DBMADesignSystemColors"]

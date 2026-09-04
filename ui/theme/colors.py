"""DBMA Design System — Color Palette.

Semantic color tokens designed for a professional academic research workspace.
Colors are organized by function, not just hue, to ensure consistent visual
language across all pages and components.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DBMADesignSystemColors:
    """DBMA Design System color tokens.

    All colors use a semantic naming convention (role-based) with hex values.
    Primary/Secondary pairs are used for navigation emphasis.
    Status colors are used for document state indicators.
    """

    # ── Brand Colors ───────────────────────────────────────────
    # Primary brand — deep charcoal (Stitch "Scholar" system, see
    # docs/design/stitch/pastoral_research_desk/DESIGN.md)
    BRAND_PRIMARY: str = "#171E1E"
    # Secondary brand — muted wood accent
    BRAND_SECONDARY: str = "#6A5C4C"

    # ── Surface Colors ─────────────────────────────────────────
    # Main page background — soft cream (paper-like)
    BG_PAGE: str = "#F5F3EE"
    # Card / panel background
    BG_SURFACE: str = "#FBF9F4"
    # Sidebar background
    BG_SIDEBAR: str = "#FBF9F4"
    # Elevated surface (dialogs, overlays)
    BG_ELEVATED: str = "#FFFFFF"

    # ── Text Colors ────────────────────────────────────────────
    TEXT_PRIMARY: str = "#1B1C19"
    TEXT_SECONDARY: str = "#434848"
    TEXT_TERTIARY: str = "#737878"
    TEXT_INVERSE: str = "#FFFFFF"
    # Link color — conservative "Scholar Blue", reserved for primary actions
    TEXT_LINK: str = "#264B5D"

    # ── Border / Divider Colors ────────────────────────────────
    BORDER_LIGHT: str = "#E5E1D8"  # DESIGN.md §Elevation: "1px solid border (#E5E1D8)"
    BORDER_MEDIUM: str = "#C3C7C7"
    BORDER_FOCUS: str = "#264B5D"

    # ── Status Colors ──────────────────────────────────────────
    STATUS_SUCCESS: str = "#2D7D5B"
    STATUS_SUCCESS_BG: str = "#E6F4EE"
    STATUS_WARNING: str = "#B8860B"
    STATUS_WARNING_BG: str = "#FFF8E1"
    STATUS_ERROR: str = "#C62828"
    STATUS_ERROR_BG: str = "#FFEBEE"
    STATUS_INFO: str = "#1565C0"
    STATUS_INFO_BG: str = "#E3F2FD"
    STATUS_NEUTRAL: str = "#757575"
    STATUS_NEUTRAL_BG: str = "#F5F5F5"

    # ── Priority / Badge Colors ────────────────────────────────
    PRIORITY_HIGH: str = "#C62828"
    PRIORITY_MEDIUM: str = "#E65100"
    PRIORITY_LOW: str = "#2D7D5B"

    # ── Citation / Star Colors ─────────────────────────────────
    CITE_STAR_FILLED: str = "#C8943E"
    CITE_STAR_EMPTY: str = "#C0B8A8"
    CITE_BG: str = "#FDF8EE"
    CITE_BORDER: str = "#EDE5D6"

    # ── Chart / Data Visualization Colors ──────────────────────
    CHART_SEQUENCE: tuple[str, ...] = (
        "#1B365D",  # primary navy
        "#C8943E",  # gold accent
        "#2D7D5B",  # green
        "#C62828",  # red
        "#5C5C5C",  # gray
        "#1565C0",  # blue
        "#6A1B9A",  # purple
        "#AD1457",  # pink
    )

    @property
    def primary_palette(self) -> dict[str, str]:
        """Return primary brand colors as a dict."""
        return {
            "primary": self.BRAND_PRIMARY,
            "secondary": self.BRAND_SECONDARY,
        }

    @property
    def status_palette(self) -> dict[str, str]:
        """Return status colors as a dict."""
        return {
            "success": self.STATUS_SUCCESS,
            "warning": self.STATUS_WARNING,
            "error": self.STATUS_ERROR,
            "info": self.STATUS_INFO,
            "neutral": self.STATUS_NEUTRAL,
        }

    @property
    def css_colors_map(self) -> str:
        """Return CSS custom properties string for Streamlit injection."""
        return f"""
        :root {{
            --dbma-brand-primary: {self.BRAND_PRIMARY};
            --dbma-brand-secondary: {self.BRAND_SECONDARY};
            --dbma-bg-page: {self.BG_PAGE};
            --dbma-bg-surface: {self.BG_SURFACE};
            --dbma-bg-sidebar: {self.BG_SIDEBAR};
            --dbma-text-primary: {self.TEXT_PRIMARY};
            --dbma-text-secondary: {self.TEXT_SECONDARY};
            --dbma-text-tertiary: {self.TEXT_TERTIARY};
            --dbma-border-light: {self.BORDER_LIGHT};
            --dbma-border-medium: {self.BORDER_MEDIUM};
            --dbma-status-success: {self.STATUS_SUCCESS};
            --dbma-status-warning: {self.STATUS_WARNING};
            --dbma-status-error: {self.STATUS_ERROR};
            --dbma-status-info: {self.STATUS_INFO};
            --dbma-status-neutral: {self.STATUS_NEUTRAL};
        }}
        """


# Singleton instance for convenient access
THEME = DBMADesignSystemColors()
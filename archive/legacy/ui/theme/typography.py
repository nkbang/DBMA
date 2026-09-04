"""DBMA Design System — Typography Tokens.

Font families, sizes, weights, and line-heights designed for an academic
research workspace. Prioritizes readability for dense textual content.
"""


# ── Font Families ────────────────────────────────────────────────
# Primary: serif for a scholarly feel
FONT_FAMILY_PRIMARY: str = "'Georgia', 'Noto Serif KR', 'Times New Roman', serif"
# Secondary / UI: system sans-serif for readability at small sizes
FONT_FAMILY_SECONDARY: str = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "'Helvetica Neue', Arial, 'Noto Sans KR', sans-serif"
)

# ── Heading Sizes ────────────────────────────────────────────────
FONT_SIZE_HEADING_L1: int = 32       # Page title / main heading
FONT_SIZE_HEADING_L2: int = 24       # Section heading
FONT_SIZE_HEADING_L3: int = 18       # Subsection heading

# ── Body Sizes ───────────────────────────────────────────────────
FONT_SIZE_BODY: int = 14             # Default body text
FONT_SIZE_CAPTION: int = 12          # Secondary / tertiary info
FONT_SIZE_SMALL: int = 11            # Tertiary / footnote

# ── Weights ──────────────────────────────────────────────────────
FONT_WEIGHT_REGULAR: int = 400
FONT_WEIGHT_MEDIUM: int = 500
FONT_WEIGHT_SEMIBOLD: int = 600
FONT_WEIGHT_BOLD: int = 700

# ── Line Heights (ratio-based) ───────────────────────────────────
LINE_HEIGHT_HEADING: float = 1.25    # Tight for headings
LINE_HEIGHT_BODY: float = 1.6        # Comfortable for reading
LINE_HEIGHT_COMPACT: float = 1.35    # Dense data / tables


def heading_css(size_token: str) -> dict[str, str]:
    """Return CSS dict for a heading size token.

    Parameters
    ----------
    size_token : str
        One of 'L1', 'L2', 'L3'.

    Returns
    -------
    dict[str, str]
        CSS properties as key-value pairs.
    """
    sizes = {"L1": FONT_SIZE_HEADING_L1, "L2": FONT_SIZE_HEADING_L2, "L3": FONT_SIZE_HEADING_L3}
    size_px = sizes.get(size_token, FONT_SIZE_HEADING_L3)
    return {
        "font-family": FONT_FAMILY_SECONDARY,
        "font-size": f"{size_px}px",
        "font-weight": str(FONT_WEIGHT_BOLD),
        "line-height": str(LINE_HEIGHT_HEADING),
        "color": "#1A1A1A",
    }


def body_css(size_token: str = "body") -> dict[str, str]:
    """Return CSS dict for a body text size.

    Parameters
    ----------
    size_token : str
        One of 'body', 'caption', 'small'. Defaults to 'body'.

    Returns
    -------
    dict[str, str]
        CSS properties as key-value pairs.
    """
    sizes = {"body": FONT_SIZE_BODY, "caption": FONT_SIZE_CAPTION, "small": FONT_SIZE_SMALL}
    size_px = sizes.get(size_token, FONT_SIZE_BODY)
    return {
        "font-family": FONT_FAMILY_SECONDARY,
        "font-size": f"{size_px}px",
        "font-weight": str(FONT_WEIGHT_REGULAR),
        "line-height": str(LINE_HEIGHT_BODY),
        "color": "#1A1A1A",
    }


def heading_css_map() -> dict[str, dict[str, str]]:
    """Return a map of all heading CSS configurations."""
    return {f"H{level}": heading_css(str(level)) for level in [1, 2, 3]}


def body_css_map() -> dict[str, dict[str, str]]:
    """Return a map of all body text CSS configurations."""
    return {k: body_css(k) for k in ["body", "caption", "small"]}
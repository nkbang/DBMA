"""DBMA Design System — Spacing Tokens.

4px-based grid system for consistent vertical and horizontal rhythm.
All values are multiples of 4px for design consistency.
"""

# ── Spacing Scale (px) ───────────────────────────────────────────
SPACING_XS: int = 4     # Tightest spacing — inline elements
SPACING_SM: int = 8     # Small gaps — between related items
SPACING_MD: int = 12    # Medium spacing — default unit gap
SPACING_LG: int = 16    # Large spacing — section separation
SPACING_XL: int = 24    # Extra large — page layout blocks
SPACING_2XL: int = 32   # Between major sections
SPACING_3XL: int = 48   # Page margins, card gaps


# ── Spacing Map ────────────────────────────────────────────────────
SPACING_MAP: dict[str, int] = {
    "xs": SPACING_XS,
    "sm": SPACING_SM,
    "md": SPACING_MD,
    "lg": SPACING_LG,
    "xl": SPACING_XL,
    "2xl": SPACING_2XL,
    "3xl": SPACING_3XL,
}


def px(value: int | str) -> str:
    """Convert a spacing token or pixel value to CSS px string.

    Parameters
    ----------
    value : int | str
        Either an integer pixel value or a spacing key from SPACING_MAP.

    Returns
    -------
    str
        CSS-compatible 'Npx' string.
    """
    if isinstance(value, str):
        return f"{SPACING_MAP.get(value, SPACING_MD)}px"
    return f"{value}px"


def padding(*values: int | str) -> str:
    """Return CSS padding shorthand string.

    Parameters
    ----------
    *values : int | str
        Up to 4 spacing values (top-right-bottom-left).

    Returns
    -------
    str
        CSS padding value, e.g., '16px 24px 16px 24px'.
    """
    converted = [px(v) for v in values[:4]]
    if len(converted) == 1:
        return f"{converted[0]} all"
    if len(converted) == 2:
        return f"{converted[0]} {converted[1]}"
    if len(converted) == 3:
        return f"{converted[0]} {converted[1]} {converted[2]}"
    return " ".join(converted)


def gap(*values: int | str) -> str:
    """Return CSS gap value for flex/grid layouts.

    Parameters
    ----------
    *values : int | str
        Spacing values.

    Returns
    -------
    str
        CSS gap value.
    """
    converted = [px(v) for v in values[:2]]
    return " ".join(converted) if len(converted) > 1 else converted[0]


def card_padding() -> str:
    """Return recommended card padding value."""
    return px("lg")


def section_gap() -> str:
    """Return recommended section gap value."""
    return px("xl")
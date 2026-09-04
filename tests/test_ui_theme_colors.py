"""UI Theme Colors — border token validation.

DESIGN.md §Elevation mandates 1px solid border (#E5E1D8) for all cards.
This test validates that the color token matches DESIGN.md before any change.
"""

import pytest


class TestBorderLightToken:
    """BORDER_LIGHT가 DESIGN.md와 일치하는지 검증."""

    def test_border_light_value(self):
        from ui.theme.colors import THEME
        # DESIGN.md §Elevation: "1px solid border (#E5E1D8)"
        assert THEME.BORDER_LIGHT == "#E5E1D8", (
            f"BORDER_LIGHT이 DESIGN.md와 다릅니다. "
            f"현재: {THEME.BORDER_LIGHT}, DESIGN.md 기준: #E5E1D8"
        )

    def test_border_medium_value(self):
        from ui.theme.colors import THEME
        assert THEME.BORDER_MEDIUM == "#C3C7C7"

    def test_css_colors_map_includes_borders(self):
        from ui.theme.colors import THEME
        css = THEME.css_colors_map
        assert "--dbma-border-light" in css
        assert "--dbma-border-medium" in css
        assert "#E5E1D8" in css
        assert "#C3C7C7" in css


class TestAllColorTokens:
    """모든 색상 토큰이 유효한 hex 값인지 검증."""

    @pytest.fixture
    def color_instance(self):
        from ui.theme.colors import THEME
        return THEME

    def test_brand_primary(self, color_instance):
        assert color_instance.BRAND_PRIMARY == "#171E1E"

    def test_bg_page(self, color_instance):
        assert color_instance.BG_PAGE == "#F5F3EE"

    def test_bg_surface(self, color_instance):
        assert color_instance.BG_SURFACE == "#FBF9F4"

    def test_text_primary(self, color_instance):
        assert color_instance.TEXT_PRIMARY == "#1B1C19"

    def test_status_colors(self, color_instance):
        assert color_instance.STATUS_SUCCESS == "#2D7D5B"
        assert color_instance.STATUS_WARNING == "#B8860B"
        assert color_instance.STATUS_ERROR == "#C62828"
        assert color_instance.STATUS_INFO == "#1565C0"

    def test_status_bg_colors(self, color_instance):
        assert color_instance.STATUS_SUCCESS_BG == "#E6F4EE"
        assert color_instance.STATUS_WARNING_BG == "#FFF8E1"
        assert color_instance.STATUS_ERROR_BG == "#FFEBEE"
        assert color_instance.STATUS_INFO_BG == "#E3F2FD"

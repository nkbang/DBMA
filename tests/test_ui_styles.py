"""UI Global Styles — render_styles() validation.

Ensures the global CSS injection includes border styles for all cards.
"""

import pytest


class TestRenderStyles:
    """render_styles()가 전역 CSS를 올바르게 주입하는지 검증."""

    def test_render_styles_exists(self):
        from ui.styles import render_styles
        assert callable(render_styles)

    def test_render_styles_injects_css(self):
        """render_styles가 <style> 태그를 포함하는 HTML을 주입해야 함."""
        from ui.styles import render_styles
        import streamlit as st
        original_markdown = st.markdown

        captured_html = []

        def capture_markdown(html, **kwargs):
            captured_html.append(html)

        st.markdown = capture_markdown
        try:
            render_styles()
            assert len(captured_html) >= 1
            combined = "\n".join(captured_html)
            assert "<style>" in combined
        finally:
            st.markdown = original_markdown

    def test_render_styles_has_border_radius(self):
        """render_styles가 border-radius를 포함해야 함."""
        from ui.styles import render_styles
        import streamlit as st
        original_markdown = st.markdown

        captured_html = []

        def capture_markdown(html, **kwargs):
            captured_html.append(html)

        st.markdown = capture_markdown
        try:
            render_styles()
            combined = "\n".join(captured_html)
            assert "border-radius" in combined
        finally:
            st.markdown = original_markdown

"""UI Card Components — border style validation.

DESIGN.md §Elevation mandates 1px solid border (#E5E1D8) for all cards.
This test validates that card components render correct border styles.
"""

import pytest


class TestMetricCardBorder:
    """metric_card의 테두리 스타일 검증."""

    def test_metric_card_has_left_border(self):
        """metric_card는 왼쪽 4px accent border를 가져야 함."""
        from ui.components.cards import metric_card, MetricCardConfig
        cfg = MetricCardConfig(title="Test", value=42)
        # HTML 출력에 border-left가 포함되어야 함
        # (Streamlit 실행 없이 HTML 문자열 검증)
        import streamlit as st
        original_markdown = st.markdown

        captured_html = []

        def capture_markdown(html, **kwargs):
            captured_html.append(html)

        st.markdown = capture_markdown
        try:
            metric_card(cfg)
            assert len(captured_html) == 1
            html = captured_html[0]
            assert "border-left: 4px solid" in html
        finally:
            st.markdown = original_markdown


class TestStatusCardBorder:
    """status_card의 테두리 스타일 검증."""

    def test_status_card_has_solid_border(self):
        """status_card는 1px 실선 테두리를 가져야 함."""
        from ui.components.cards import status_card, StatusCardConfig
        cfg = StatusCardConfig(label="Test", status="success")
        import streamlit as st
        original_markdown = st.markdown

        captured_html = []

        def capture_markdown(html, **kwargs):
            captured_html.append(html)

        st.markdown = capture_markdown
        try:
            status_card(cfg)
            assert len(captured_html) == 1
            html = captured_html[0]
            # DESIGN.md 기준: 1px solid border
            assert "border:" in html
            assert "1px" in html
        finally:
            st.markdown = original_markdown


class TestDocCardBorder:
    """doc_card의 테두리 스타일 검증."""

    def test_doc_card_has_solid_border(self):
        """doc_card는 1px 실선 테두리를 가져야 함."""
        from ui.components.cards import doc_card, DocCardConfig
        cfg = DocCardConfig(title="Test Document", doc_type="book")
        import streamlit as st
        original_markdown = st.markdown

        captured_html = []

        def capture_markdown(html, **kwargs):
            captured_html.append(html)

        st.markdown = capture_markdown
        try:
            doc_card(cfg)
            assert len(captured_html) == 1
            html = captured_html[0]
            # DESIGN.md 기준: 1px solid border (#E5E1D8)
            assert "border:" in html
            assert "1px" in html
        finally:
            st.markdown = original_markdown

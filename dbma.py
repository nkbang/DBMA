from core import config  # noqa: F401
import streamlit as st
from ui.styles import inject_styles, render_header
from ui.sidebar import render_sidebar
from ui.tabs import render_processing_tab, render_analysis_tab


def main():
    inject_styles()
    render_header()
    target_dir, output_dir, chunk_size, chunk_overlap, use_ocr = render_sidebar()
    tab1, tab2 = st.tabs(["처리", "분석"])
    with tab1:
        render_processing_tab(target_dir, output_dir, chunk_size, chunk_overlap, use_ocr)
    with tab2:
        render_analysis_tab(output_dir)


if __name__ == "__main__":
    main()

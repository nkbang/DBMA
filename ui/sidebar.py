import streamlit as st
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR


def render_sidebar():
    st.sidebar.header("설정")

    target_dir = st.sidebar.text_input(
        "RAW 폴더",
        value=DEFAULT_RAW_DIR,
        help="처리할 원본 파일이 있는 폴더 경로",
    )

    output_dir = st.sidebar.text_input(
        "출력 폴더",
        value=DEFAULT_OUTPUT_DIR,
        help="Markdown, chunk, 이동된 원본 파일이 저장될 폴더 경로",
    )

    chunk_size = st.sidebar.number_input(
        "Chunk Size",
        min_value=200,
        max_value=5000,
        value=1200,
        step=100,
        help="문서를 나눌 기본 청크 크기",
    )

    chunk_overlap = st.sidebar.number_input(
        "Chunk Overlap",
        min_value=0,
        max_value=1000,
        value=200,
        step=50,
        help="청크 간 겹침 크기",
    )

    use_ocr = st.sidebar.checkbox(
        "PDF OCR 사용",
        value=False,
        help="스캔 PDF나 텍스트 추출이 어려운 PDF에 OCR을 사용합니다",
    )

    return target_dir, output_dir, chunk_size, chunk_overlap, use_ocr

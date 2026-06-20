import streamlit as st
from core.config import DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR


def render_sidebar():
    with st.sidebar:
        st.markdown("### 경로 설정")
        st.markdown("---")
        target_dir = st.text_input("RAW 폴더", value=DEFAULT_RAW_DIR)
        output_dir = st.text_input("출력 폴더", value=DEFAULT_OUTPUT_DIR)
        st.caption("지원 형식: PDF, TXT, MD, DOCX, EPUB, HTML, HTM, RTF")
        st.markdown("---")

        st.markdown("### 분절 설정")
        chunk_size = st.number_input("Chunk Size", value=1000, min_value=100, step=100)
        chunk_overlap = st.number_input("Chunk Overlap", value=200, min_value=0, step=50)
        st.markdown("---")

        st.markdown("### OCR")
        use_ocr = st.checkbox("OCR for PDF", value=False, help="스캔형 PDF나 이미지 기반 PDF에만 사용하세요.")
        if use_ocr:
            st.info("EasyOCR: ko, en, he, el")

        st.markdown("---")
        st.markdown(
            """
<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#3fb950;padding:8px 10px;background:#0d2b1a;border-radius:6px;border:1px solid #1a4a2a;">
다중 문서 형식 지원<br><br>
PDF / TXT / MD / DOCX / EPUB / HTML / RTF
</div>
""",
            unsafe_allow_html=True,
        )

    return target_dir, output_dir, int(chunk_size), int(chunk_overlap), use_ocr

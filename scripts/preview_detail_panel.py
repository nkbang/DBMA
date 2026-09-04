"""scripts/preview_detail_panel.py — detail_panel.py 컴포넌트 단독 미리보기.

C1-TASK-ORDER-030 §4 수동 검증용.
streamlit run scripts/preview_detail_panel.py 로 실행.
"""

import sys
from pathlib import Path

# Streamlit이 scripts/ 디렉터리에서 실행될 때 core 모듈을 찾을 수 있도록
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from core.document_detail import DocumentDetail, MatchLocation

st.set_page_config(page_title="NAE — 상세 패널 미리보기", layout="wide")
st.title("📖 내서재 — 상세 패널 컴포넌트 미리보기")

from ui.components.detail_panel import render_detail_panel

# --- 케이스 1: 정상 케이스 ---
st.header("케이스 1: 정상 문서")

detail_normal = DocumentDetail(
    document_id="doc-preview-001",
    title="믿음의 은혜",
    document_type="설교",
    source_path="/Volumes/DBMA-ExternalStorage/DBMA.org/_Ingest/2025/2025-03-16-믿음의-은혜.md",
    author="David Bang",
    created_at="2025-03-16T10:00:00Z",
    full_text="""믿음이란 것은 단순히 어떤 사실을 인정하는 것이 아닙니다.

히브리서 11장 1절은 믿음이란 것에 대해 이렇게 정의합니다. "믿음은 바라는 것들을 확신하며 보이지 않는 것들을 확신하는 것이라"

아브라함은 어떻게 이 믿음을 경험했을까요? 그는 하나님께서 주신 약속을 믿고, 자신의 고향을 떠날 수 있었습니다.

로마서 4장 20절에서 아브라함은 "믿음에 있어서 약하지도 아니하고"라고 기술되고 있습니다.

우리의 일상에서도 이 은혜를 경험할 수 있습니다. 매일의 삶 속에서 하나님의 인도하심을 볼 수 있기 때문입니다.""",
    match_locations=[
        MatchLocation(char_start=45, char_end=47),
        MatchLocation(char_start=120, char_end=122),
    ],
    tags=["믿음", "은혜", "아브라함"],
)

render_detail_panel(detail_normal, ["믿음"])

# --- 케이스 2: error 있는 케이스 ---
st.header("케이스 2: 오류 케이스 (존재하지 않는 파일)")

detail_error = DocumentDetail(
    document_id="doc-error-001",
    title=None,
    document_type=None,
    source_path="/nonexistent/path/to/file.md",
    author=None,
    created_at=None,
    full_text="",
    match_locations=[],
    tags=[],
    error="파일을 찾을 수 없습니다: /nonexistent/path/to/file.md",
)

render_detail_panel(detail_error, ["테스트"])

# --- 케이스 3: HTML 특수문자가 포함된 본문 ---
st.header("케이스 3: HTML 특수문자 포함")

detail_html = DocumentDetail(
    document_id="doc-html-001",
    title="코드 예제",
    document_type="기술 문서",
    source_path="/docs/code-example.md",
    author="Test Author",
    created_at="2025-01-01T00:00:00Z",
    full_text="""if x < 10 and y > 5:
    print("a & b")

# 결과: "hello"
""",
    match_locations=[
        MatchLocation(char_start=27, char_end=32),
    ],
    tags=["코드", "예제"],
)

render_detail_panel(detail_html, ["print"])

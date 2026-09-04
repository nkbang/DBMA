"""ui/components/detail_panel.py - 검색 결과 상세 패널 컴포넌트.

Phase 2: 우측 상세 패널 렌더링 전용 모듈.
Chat 페이지 연결은 Phase 3에서 한다.

핵심 함수:
    highlight_terms() - 순수 함수, HTML-escape 후 매치 단어에 <mark> 태그
    render_detail_panel() - Streamlit UI 렌더링 (st 의존성 있음)
"""

from __future__ import annotations

import html
import re

import streamlit as st
from core.document_detail import DocumentDetail


def _escape_for_html(text: str) -> str:
    """문본을 HTML-escape한다. chat.py에도 동일한 헬퍼가 있으나
    순환 임포트를 피하기 위해 의도적으로 중복한다(Phase 3에서
    chat.py가 이 모듈을 import하므로 반대 방향 import 금지)."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text


def highlight_terms(text: str, terms: list[str]) -> str:
    """text를 HTML-escape한 뒤 terms에 해당하는 부분을 <mark> 태그로
    감싼 HTML 문자열을 반환한다. 대소문자 구분은 원문 그대로(한국어라
    대소문자 이슈 없음). 빈 terms 리스트면 escape만 하고 그대로 반환.

    순서 중요: 먼저 전체 escape하고, 그 다음 <mark>로 감싸야
    escape된 &lt; 등이 <mark> 태그 내부에서 다시 이스케이프되지 않는다.
    """
    if not text:
        return ""

    escaped = _escape_for_html(text)

    if not terms:
        return escaped

    # terms 각각에 대해 <mark> 태그로 감싸기
    # re.escape로 특수문자 처리 (예: term이 "a.b"면 "a\.b"로 매칭)
    for term in terms:
        if not term:
            continue
        escaped = re.sub(
            re.escape(term),
            lambda m: f"<mark>{m.group(0)}</mark>",
            escaped,
        )

    return escaped


def render_detail_panel(detail: DocumentDetail, query_terms: list[str]) -> None:
    """
    2단 레이아웃의 오른쪽 컬럼 안에서 호출되는 것을 전제로 한다(호출자가
    st.columns()로 이미 컨텍스트를 잡아놓음 - 이 함수 자체는 컬럼을 만들지
    않는다).

    렌더링 순서:
    1. detail.error가 있으면: st.error(detail.error)로 표시하고, 그 아래에도
       가능한 메타데이터(title/author/source_path)는 계속 표시한다(본문만
       없는 것이지 메타데이터까지 숨길 이유는 없음). return.
    2. 제목(st.subheader), 문서유형/작성자/생성일/출처경로를 st.caption 또는
       st.markdown으로 표시.
    3. detail.tags가 있으면 뱃지 형태로 표시(st.markdown으로 간단히,
       복잡한 스타일링 불필요).
    4. detail.match_locations가 있으면 "검색어 N회 발견" 캡션 표시.
    5. 본문: highlight_terms(detail.full_text, query_terms)의 HTML을
       st.markdown(..., unsafe_allow_html=True)로 렌더링.
    6. "첫 매치 위치로 스크롤" 실험 (§2.2 참고).
    7. source_path는 텍스트로만 표시 + 복사 가능하게 st.code(detail.source_path)
       사용 (클릭 시 실행되는 링크/버튼 절대 아님 - 계획서 §5 결정사항).
    """
    # 1. 에러 표시
    if detail.error:
        st.error(detail.error)
        # 메타데이터는 계속 표시
        if detail.title:
            st.subheader(detail.title)
        meta_parts = []
        if detail.document_type:
            meta_parts.append(f"문서유형: {detail.document_type}")
        if detail.author:
            meta_parts.append(f"작성자: {detail.author}")
        if detail.created_at:
            meta_parts.append(f"생성일: {detail.created_at}")
        if meta_parts:
            st.caption(" | ".join(meta_parts))
        return

    # 2. 제목 및 메타데이터
    if detail.title:
        st.subheader(detail.title)

    meta_parts = []
    if detail.document_type:
        meta_parts.append(f"문서유형: {detail.document_type}")
    if detail.author:
        meta_parts.append(f"작성자: {detail.author}")
    if detail.created_at:
        meta_parts.append(f"생성일: {detail.created_at}")
    if meta_parts:
        st.caption(" | ".join(meta_parts))

    # 3. 태그 뱃지
    if detail.tags:
        tag_html = " ".join(
            f'<span style="display:inline-block;padding:2px 8px;margin:2px;background:#e8e8e8;border-radius:4px;font-size:0.85em;">{html.escape(t)}</span>'
            for t in detail.tags
        )
        st.markdown(tag_html, unsafe_allow_html=True)

    # 4. match_locations 캡션
    if detail.match_locations:
        st.caption(f"검색어 {len(detail.match_locations)}개 위치 발견")

    # 5. 원본 파일 경로는 실행 가능한 링크가 아닌 텍스트로만 표시
    if detail.source_path:
        st.caption("원본 파일 경로")
        st.code(detail.source_path, language=None)

    # 6. 본문 렌더링 (highlight_terms 적용)
    if detail.full_text:
        highlighted = highlight_terms(detail.full_text, query_terms)

        # "첫 매치로 스크롤" 실험
        # Streamlit은 네이티브 스크롤 제어 API가 없다.
        # 첫 매치 앞에 앵커를 심고 script로 scrollIntoView 시도.
        # 만약 Streamlit이 <script>를 실행 안 시켜줄 수 있으므로,
        # 실패 시 완화안(첫 매치 앞부분부터 잘라 표시)을 사용한다.

        first_match_offset = None
        if detail.match_locations:
            first_match_offset = detail.match_locations[0].char_start

        if first_match_offset is not None and first_match_offset > 0:
            # 완화안: 첫 매치 위치 기준으로 앞부분을 잘라서 표시
            # 첫 매치 앞 300자부터 본문 시작
            preview_start = max(0, first_match_offset - 300)
            preview_text = detail.full_text[preview_start:]

            # 다시 highlight_terms 적용 (잘라낸 텍스트에 대해)
            highlighted = highlight_terms(preview_text, query_terms)
            # 앞에 "..." 추가
            if preview_start > 0:
                highlighted = '<span style="color:#888;">...</span>\n\n' + highlighted

            st.markdown(highlighted, unsafe_allow_html=True)
            # "본문 처음부터 보기" 토글
            with st.expander("본문 처음부터 보기"):
                full_highlighted = highlight_terms(detail.full_text, query_terms)
                st.markdown(full_highlighted, unsafe_allow_html=True)
        else:
            # 첫 매치가 없거나 첫 부분이면 전체 표시
            st.markdown(highlighted, unsafe_allow_html=True)


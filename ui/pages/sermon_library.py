"""DBMA — 저장된 설교 보관함 (P1: 목록·조회, P2: 강단 전달 모드).

설계 근거: docs/DBMA_SERMON_ARTIFACT_PIPELINE_DESIGN_v1.md §5.3.
강단 전달 모드는 저장된 원고를 큰 글씨·고대비로 렌더링할 뿐이며 LLM을
호출하지 않는다 — 순수 렌더링이라 실패할 여지가 없다(설계 판단).
"""

import html

import streamlit as st

from ui.pages._base import BasePage
from ui.theme.colors import THEME
from core.sermon_artifact import list_sermon_artifacts, load_sermon_artifact


def render_sermon_library_page() -> None:
    page = BasePage(title="저장된 설교", icon="auto_stories")
    page.render_header()

    sermon_id = st.session_state.get("sermon_library_open_id")
    if sermon_id:
        _render_open_artifact(sermon_id)
    else:
        _render_artifact_list()

    page.render_footer()


def _render_artifact_list() -> None:
    summaries = list_sermon_artifacts()
    if not summaries:
        st.info("저장된 설교가 없습니다. '설교 준비' 탭에서 설교문을 완성한 뒤 저장할 수 있습니다.")
        return

    st.caption(f"저장된 설교 {len(summaries)}편")
    for s in summaries:
        with st.container(border=True):
            cols = st.columns([5, 2, 1])
            with cols[0]:
                st.markdown(f"**{s.get('title') or '(제목 없음)'}**")
                st.caption(s.get("scripture_and_theme", ""))
            with cols[1]:
                st.caption(f"{s.get('sermon_format', '')} · {s.get('created_at', '')[:10]}")
            with cols[2]:
                if st.button("열기", key=f"open_{s['sermon_id']}", use_container_width=True):
                    st.session_state["sermon_library_open_id"] = s["sermon_id"]
                    st.session_state["sermon_library_podium"] = False
                    st.rerun()


def _render_open_artifact(sermon_id: str) -> None:
    artifact = load_sermon_artifact(sermon_id)
    if artifact is None:
        st.error("저장된 설교를 찾을 수 없습니다 — 삭제되었을 수 있습니다.")
        if st.button("목록으로"):
            st.session_state.pop("sermon_library_open_id", None)
            st.rerun()
        return

    podium = st.session_state.get("sermon_library_podium", False)

    top_cols = st.columns([1, 1, 4])
    with top_cols[0]:
        if st.button("← 목록으로", key="sermon_lib_back"):
            st.session_state.pop("sermon_library_open_id", None)
            st.session_state["sermon_library_podium"] = False
            st.rerun()
    with top_cols[1]:
        label = "일반 보기" if podium else "강단 모드"
        icon = ":material/visibility:" if podium else ":material/podium:"
        if st.button(label, key="sermon_lib_toggle_podium", icon=icon):
            st.session_state["sermon_library_podium"] = not podium
            st.rerun()

    if podium:
        _render_podium(artifact)
    else:
        _render_normal_view(artifact)


def _render_normal_view(artifact) -> None:
    outline = artifact.outline
    st.markdown(f"## {outline.get('title', '')}")
    st.caption(f"{artifact.scripture_and_theme} · {artifact.sermon_format} · {artifact.created_at[:10]}")

    doctrine_report = artifact.doctrine_report
    if doctrine_report and not doctrine_report.get("passed", True):
        for w in doctrine_report.get("warnings", []):
            st.warning(w)

    with st.container(border=True):
        st.markdown("### 서론")
        st.markdown(outline.get("introduction", ""))
        for i, point in enumerate(outline.get("points", [])):
            st.markdown(f"### 대지 {i + 1}: {point}")
            st.markdown(artifact.expanded.get(str(i), "_(확장되지 않음)_"))
        st.markdown("### 결론")
        st.markdown(outline.get("conclusion", ""))

    st.caption(f"근거 자료 {len(artifact.evidence.get('candidate_tsu_ids', []))}건 사용")


def _render_podium(artifact) -> None:
    """[P2, 강단 전달 모드] 큰 글씨·고대비. LLM 호출 없음 — 저장된
    원고를 그대로 렌더링만 한다."""
    outline = artifact.outline
    st.markdown(
        f"""
        <style>
        .nae-podium {{
            font-family: 'Source Serif 4', serif;
            font-size: 28px;
            line-height: 2.0;
            color: {THEME.TEXT_PRIMARY};
            background: {THEME.BG_SURFACE};
            padding: 2rem;
            border-radius: 12px;
        }}
        .nae-podium h2 {{ font-size: 34px; margin-bottom: 0.5em; }}
        .nae-podium h3 {{ font-size: 24px; color: {THEME.BRAND_PRIMARY}; margin-top: 1.2em; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _p(text: str) -> str:
        return html.escape(text).replace("\n", "<br>")

    parts = [
        f"<h2>{html.escape(outline.get('title', ''))}</h2>",
        f"<h3>서론</h3><p>{_p(outline.get('introduction', ''))}</p>",
    ]
    for i, point in enumerate(outline.get("points", [])):
        parts.append(f"<h3>대지 {i + 1}: {html.escape(point)}</h3>")
        parts.append(f"<p>{_p(artifact.expanded.get(str(i), ''))}</p>")
    parts.append(f"<h3>결론</h3><p>{_p(outline.get('conclusion', ''))}</p>")

    st.markdown(f'<div class="nae-podium">{"".join(parts)}</div>', unsafe_allow_html=True)

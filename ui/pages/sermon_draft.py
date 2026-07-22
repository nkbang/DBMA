"""DBMA — 설교문 작성 워크숍 페이지 (Phase 1).

본문/주제 입력 → 넓은 범위 검색 → 개요 생성 → 사용자 검토·수정 →
승인된 대지별 확장 생성 → 최종 초안 조립.

설계 근거: docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-Review.md
- 검색: QueryProcessor.process()를 k만 넓혀서 단일 호출 (ADR-001 준수,
  core/retrieval.py 변경 없음).
- 상태: st.session_state["sermon_draft_state"] 딕셔너리, status 필드로
  단계 전이 관리 (설계 문서 Q2).
- 생성: core/generation.py::SermonDraftService (GenerationService와
  별도, 조합 방식 — 설계 문서 Q4).
- 문체 참고: TSU 스키마 변경 없이 file_scope 다중 선택 UI를 그대로
  재사용 (설계 문서 Q3의 "sermon_type 메타데이터" 대안 — CUE가 §4 열린
  질문 답변 시 스키마 변경 없는 쪽으로 단순화함).
"""

import streamlit as st

from ui.pages._base import BasePage
from core.retrieval import QueryProcessor
from core.generation import SermonDraftService, SermonOutline, SERMON_FORMATS
from core.sermon.bible_books import BIBLE_BOOKS
from core.sermon.doctrine_filter import check as doctrine_check
from ui.state.query_processor import get_shared_query_processor

_CANDIDATE_K = 20  # 설교 개요용 넓은 후보군 — Chat(k=3~5)보다 크게

_STATUS_HAS_OUTLINE = {"outline_generated", "reviewing", "approved", "expanding", "draft_complete"}
_STATUS_HAS_EXPANSION = {"approved", "expanding", "draft_complete"}


def render_sermon_draft_page() -> None:
    """Render the DBMA Sermon Draft workshop page."""
    page = BasePage(title="설교문 작성", icon="📝")
    page.render_header()

    _init_state()
    state = st.session_state["sermon_draft_state"]

    page.render_section("1단계: 본문과 주제", icon="📖")
    _render_input_step()

    if state["status"] in _STATUS_HAS_OUTLINE and state["outline"] is not None:
        page.render_section("2단계: 개요 검토", icon="📋")
        _render_outline_step()

    if state["status"] in _STATUS_HAS_EXPANSION:
        page.render_section("3단계: 본문 확장", icon="✍️")
        _render_expansion_step()

    page.render_footer()


def _init_state() -> None:
    if "sermon_draft_state" not in st.session_state:
        st.session_state["sermon_draft_state"] = {
            "status": "input",
            "scripture_and_theme": "",
            "style_files": [],
            "sermon_format": SERMON_FORMATS[0],  # "주제설교"
            "outline": None,  # SermonOutline
            "candidates": [],  # list[RankedCandidate] — [자료N] 인용용 원본
            "expanded": {},  # point_index(int) -> str
        }


def _get_processor() -> QueryProcessor:
    # [일관성] Chat/Research와 동일한 세션 공유 QueryProcessor — 별도
    # RetrievalEngine 인스턴스를 만들지 않는다 (One Retrieval Engine).
    return get_shared_query_processor()


def _get_service() -> SermonDraftService:
    if "sermon_draft_service" not in st.session_state:
        st.session_state["sermon_draft_service"] = SermonDraftService()
    return st.session_state["sermon_draft_service"]


def _render_book_coverage_buttons() -> None:
    """[2026-07-21] 66권 성경 이름 버튼 — 코퍼스에 실제 임베딩된 서로 다른
    원본 문서(주석서 등) 개수를 각 버튼에 표시한다. 클릭하면 본문 입력란
    (아래 st.form의 scripture_and_theme)에 그 책 이름이 채워진다.

    core/sermon/bible_books.py(정규 66권 목록, query_enhancements.py의
    오탈자 있는 별칭 테이블과 별개) + RetrievalEngine.book_coverage()
    (TSU 코퍼스를 읽기 전용으로 집계, 새 검색 경로 없음 — ADR-001 준수)로
    구성했다. 문서가 늘어나면(재처리·신규 업로드) 숫자가 자동으로
    갱신된다 — 하드코딩된 값이 아니다.

    버튼은 st.form 밖에 있어야 한다(Streamlit 제약 — st.button은 form
    안에서 즉시 클릭 반응하지 않음, st.form_submit_button만 가능)."""
    coverage = _get_processor().engine.book_coverage()
    with st.expander("📖 전체 성경 이름 (책마다 임베딩된 자료 수)"):
        cols = st.columns(6)
        for i, (name, book_id) in enumerate(BIBLE_BOOKS):
            count = coverage.get(book_id, 0)
            with cols[i % 6]:
                if st.button(f"{name} {count}", key=f"book_btn_{book_id}", use_container_width=True):
                    st.session_state["sermon_draft_state"]["scripture_and_theme"] = name
                    # [버그 수정 2026-07-21] _render_input_step()의 text_area가
                    # value=와 key=를 동시에 쓴다 — Streamlit은 위젯이 이미
                    # 한 번 렌더링된 뒤에는 key로 저장된 session_state 값을
                    # value=보다 우선한다. 그래서 state["scripture_and_theme"]만
                    # 바꾸면 rerun 후에도 텍스트 영역이 비어있는 채로 남는다
                    # (실사용 재현 확인). 위젯의 실제 키에도 같이 써야 한다.
                    st.session_state["sermon_input_text"] = name
                    st.rerun()


def _render_input_step() -> None:
    """[버그 수정] 이 3개 위젯을 st.form 없이 개별 렌더링했을 때, 텍스트를
    입력한 뒤 blur(포커스 이탈)하기 전에 라디오/멀티셀렉트를 건드리면
    Streamlit이 textarea의 커밋 안 된 이전 값(빈 문자열)으로 스크립트를
    재실행해 "개요 생성" 버튼이 계속 비활성 상태로 보이는 문제가 있었다
    (실사용 재현 확인). st.form은 제출(submit) 시점에만 재실행하고 그때
    모든 위젯 값을 한 번에 확정해서 가져오므로, 위젯 간 상호작용 순서와
    무관하게 항상 최신 텍스트를 읽는다."""
    state = st.session_state["sermon_draft_state"]
    files = _get_processor().engine.list_source_files()

    _render_book_coverage_buttons()

    with st.form("sermon_input_form"):
        scripture_and_theme = st.text_area(
            "본문 성경 구절과 설교 주제",
            value=state["scripture_and_theme"],
            placeholder="예: 로마서 5:1-5, 고난 중의 소망",
            height=80,
            key="sermon_input_text",
        )

        sermon_format = st.radio(
            "설교 형식",
            options=SERMON_FORMATS,
            horizontal=True,
            help="주제설교: 대지를 신학적 주제 단위로 재구성. 강해설교: 대지가 본문의 절 순서를 그대로 따라가며 주해.",
            key="sermon_format_radio",
        )

        style_files = st.multiselect(
            "문체 참고용 과거 설교문 (선택, 최대 3개)",
            options=files,
            default=[f for f in state["style_files"] if f in files],
            help="선택한 파일의 어투만 확장 단계에서 참고합니다 — 내용 근거로는 쓰이지 않습니다.",
            max_selections=3,
        )

        submitted = st.form_submit_button("📝 개요 생성", type="primary", use_container_width=True)

    if submitted:
        if not scripture_and_theme.strip():
            st.warning("본문 성경 구절과 설교 주제를 입력하세요.")
        else:
            _generate_outline(scripture_and_theme.strip(), style_files, sermon_format)


def _generate_outline(scripture_and_theme: str, style_files: list[str], sermon_format: str) -> None:
    state = st.session_state["sermon_draft_state"]
    processor = _get_processor()
    service = _get_service()

    with st.spinner("자료를 검색하고 개요를 작성하는 중..."):
        try:
            response = processor.process(scripture_and_theme, query_id="sermon-draft", k=_CANDIDATE_K)
        except Exception as e:
            st.error(f"검색 실패: {e}")
            return
        outline, error = service.generate_outline(
            scripture_and_theme, response.top_k_results, sermon_format=sermon_format
        )

    if error:
        st.error(f"개요 생성 실패: {error}")
        return

    # [ADR-009 §Decision-4] Doctrine Filter — 사후·경고 전용, 생성 자체를
    # 막지 않는다. 실패해도(doctrine_check는 raise하지 않음) 개요 검토
    # 흐름은 그대로 진행된다.
    context_preview = "\n\n".join(c.content[:500] for c in response.top_k_results[:5])
    state["doctrine_report"] = doctrine_check(outline, context_preview)

    state["scripture_and_theme"] = scripture_and_theme
    state["style_files"] = style_files
    state["sermon_format"] = sermon_format
    state["outline"] = outline
    state["candidates"] = response.top_k_results
    state["expanded"] = {}
    state["status"] = "outline_generated"
    st.rerun()


def _render_doctrine_warning() -> None:
    """[ADR-009 §Decision-4] 경고 배너만 — 점수화 없음, 생성 차단 없음.
    report가 없거나(구버전 세션 상태) 통과했으면 아무것도 표시하지 않는다
    (과잉 경고 방지, doctrine_filter.py의 "명백하지 않으면 침묵" 원칙과
    같은 톤)."""
    report = st.session_state["sermon_draft_state"].get("doctrine_report")
    if report is None or report.passed:
        return
    for w in report.warnings:
        st.warning(w)
    if report.flagged_categories:
        st.caption(f"관련 범주: {', '.join(report.flagged_categories)} · 신뢰도: {report.confidence}")


def _render_outline_step() -> None:
    state = st.session_state["sermon_draft_state"]
    outline: SermonOutline = state["outline"]

    _render_doctrine_warning()
    st.caption(f"설교 형식: {state['sermon_format']}")
    title = st.text_input("제목", value=outline.title, key="sermon_outline_title")
    introduction = st.text_area("서론", value=outline.introduction, height=80, key="sermon_outline_intro")

    edited_points = []
    for i, point in enumerate(outline.points):
        edited_points.append(
            st.text_area(f"대지 {i + 1}", value=point, height=60, key=f"sermon_outline_point_{i}")
        )

    conclusion = st.text_area("결론", value=outline.conclusion, height=80, key="sermon_outline_conclusion")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 수정 반영", use_container_width=True):
            state["outline"] = SermonOutline(
                title=title, introduction=introduction, points=edited_points, conclusion=conclusion
            )
            state["status"] = "reviewing"
            st.success("반영되었습니다.")
    with col2:
        if st.button("✅ 개요 승인 — 확장 단계로", type="primary", use_container_width=True):
            state["outline"] = SermonOutline(
                title=title, introduction=introduction, points=edited_points, conclusion=conclusion
            )
            state["status"] = "approved"
            st.rerun()


def _render_expansion_step() -> None:
    state = st.session_state["sermon_draft_state"]
    outline: SermonOutline = state["outline"]
    service = _get_service()

    if not outline.points:
        st.warning("승인된 대지가 없습니다 — 2단계에서 대지를 추가한 뒤 다시 승인하세요.")
        return

    style_examples = _build_style_examples(state["style_files"])

    for i, point in enumerate(outline.points):
        already_done = i in state["expanded"]
        with st.expander(f"대지 {i + 1}: {point[:40]}", expanded=not already_done):
            if already_done:
                st.markdown(state["expanded"][i])
                if st.button("🔄 다시 생성", key=f"sermon_regen_{i}"):
                    del state["expanded"][i]
                    st.rerun()
            else:
                if st.button("✍️ 이 대지 확장하기", key=f"sermon_expand_{i}"):
                    with st.spinner("작성 중..."):
                        text, error = service.expand_point(
                            point,
                            state["scripture_and_theme"],
                            state["candidates"],
                            style_examples,
                            sermon_format=state["sermon_format"],
                        )
                    if error:
                        st.error(f"생성 실패: {error}")
                    else:
                        state["expanded"][i] = text
                        state["status"] = "expanding"
                        st.rerun()

    if outline.points and len(state["expanded"]) == len(outline.points):
        state["status"] = "draft_complete"
        st.divider()
        st.subheader("📄 완성된 설교문 초안")
        full_draft = _assemble_draft(outline, state["expanded"])
        st.markdown(full_draft)
        st.download_button(
            "⬇️ 다운로드 (.md)",
            data=full_draft,
            file_name="sermon_draft.md",
            mime="text/markdown",
            use_container_width=True,
        )


def _build_style_examples(style_files: list[str]) -> str:
    """선택된 파일들의 본문 발췌를 합쳐 어투 참고용 문자열을 만든다.
    최대 3개, 각 400자 — 열린 질문 Q-A2 답변(내용이 아닌 어투 힌트라
    많을수록 좋은 게 아님)."""
    if not style_files:
        return ""
    engine = _get_processor().engine
    excerpts: list[str] = []
    for f in style_files[:3]:
        for tsu in engine.tsus:
            if tsu.get("source_file") == f:
                excerpts.append(tsu.get("content", "")[:400])
                break
    return "\n---\n".join(excerpts)


def _assemble_draft(outline: SermonOutline, expanded: dict) -> str:
    parts = [f"# {outline.title}", "", "## 서론", outline.introduction, ""]
    for i, point in enumerate(outline.points):
        parts.append(f"## 대지 {i + 1}: {point}")
        parts.append(expanded.get(i, ""))
        parts.append("")
    parts.append("## 결론")
    parts.append(outline.conclusion)
    return "\n".join(parts)

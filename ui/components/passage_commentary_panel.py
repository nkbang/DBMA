"""ui/components/passage_commentary_panel.py — 본문 해설 참고 패널 (ADR-031 §9 연동).

free-text(설교 "본문 성경 구절과 설교 주제" 등)에서 성경 구절을 추출해, 그 본문에
대한 **내서재 근거 해설**을 접이식 참고 패널로 보여준다.

"연구하기 > 본문 해설" 탭(`ui/pages/_passage_commentary_tab.py`, 성경뷰어 기반)과
달리 이 패널은:
  - 성경 본문 텍스트 표시 없음 (구절은 free-text 에서 파싱)
  - "원문 보기" 상세 패널 없음 (세로 단일 흐름 화면용 경량 버전)
  - 자동 생성 없음 — 명시적 «해설 생성» 버튼으로만 Ollama 호출

생성/검색/각주 로직은 전부 `core/passage_commentary.py` 재사용. `core/retrieval.py`·
`core/generation.py` 시그니처 무변경(ADR-031 §4).
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from core.generation import GenerationService
from core.passage_commentary import (
    circled_marker,
    make_response_package,
    reference_label,
    render_answer_with_badges,
    retrieve_passage_commentary,
)
from core.retrieval import QueryParser, ScriptureReference
from ui.state.query_processor import get_shared_query_processor

logger = logging.getLogger(__name__)


def _extract_first_ref(text: str) -> Optional[ScriptureReference]:
    """free-text 에서 첫 성경 구절 참조를 뽑는다. 기존 QueryParser 재사용 —
    새 파서를 만들지 않는다. 구절 표기가 없으면 None."""
    if not text or not text.strip():
        return None
    try:
        refs = QueryParser().parse(text).scripture_refs
    except Exception as e:  # noqa: BLE001 — 파싱 실패가 화면을 막지 않게
        logger.warning("[passage_commentary_panel] ref 파싱 실패: %s", e)
        return None
    return refs[0] if refs else None


def render_passage_commentary_panel(free_text: str, *, key_prefix: str) -> None:
    """free_text 에 성경 구절이 있으면 «본문 해설» 익스팬더를 렌더한다.
    구절이 없으면 아무것도 그리지 않는다(호출부는 무조건 호출해도 안전)."""
    ref = _extract_first_ref(free_text)
    if ref is None:
        return

    label = reference_label(ref)
    result_key = f"{key_prefix}_pcp_result"
    cached = st.session_state.get(result_key)
    fresh = bool(cached) and cached.get("label") == label

    with st.expander(f"📖 «{label}» 본문 해설 (내서재 근거)", expanded=fresh):
        if st.button(f"«{label}» 해설 생성", key=f"{key_prefix}_pcp_go"):
            cached = _run(ref, label)
            st.session_state[result_key] = cached
            fresh = True

        if fresh:
            _render_result(cached)
        else:
            st.caption(
                "설교 개요·확장과는 **별개**인 참고 자료입니다. 버튼을 누르면 내서재에서 "
                "이 본문 관련 주석을 찾아 근거 각주와 함께 해설을 만듭니다."
            )


def _run(ref: ScriptureReference, label: str) -> dict:
    """검색 → 정합 필터 → (자료 있으면) 스트리밍 생성. 세션에 담을 dict 반환."""
    processor = get_shared_query_processor()
    outcome = retrieve_passage_commentary(ref, processor)

    if outcome.status == "retrieval_failed":
        return {"label": label, "status": "gen_failed", "error": outcome.error,
                "answer_badged": "", "footnotes": []}
    if outcome.status == "no_material":
        return {"label": label, "status": "no_material", "answer_badged": "", "footnotes": []}

    pkg, _citations, footnotes = make_response_package(outcome, ref, registry=_load_registry())
    generator = GenerationService()

    placeholder = st.empty()
    parts: list[str] = []
    try:
        stream = generator.generate_stream(pkg, **_gen_overrides())
        for piece in stream:
            parts.append(piece)
            placeholder.markdown("".join(parts))
        result = stream.to_result() if hasattr(stream, "to_result") else None
        answer = (getattr(result, "answer", "") if result else "") or "".join(parts)
        gen_error = getattr(result, "error", None) if result else None
    except Exception as e:  # noqa: BLE001 — 생성 실패가 설교 작성 흐름을 막지 않게
        logger.warning("[passage_commentary_panel] 생성 실패: %s", e)
        placeholder.empty()
        return {"label": label, "status": "gen_failed", "error": str(e),
                "answer_badged": "", "footnotes": footnotes}

    placeholder.empty()
    if gen_error:
        return {"label": label, "status": "gen_failed", "error": gen_error,
                "answer_badged": "", "footnotes": footnotes}
    return {
        "label": label,
        "status": "ok",
        "answer_badged": render_answer_with_badges(answer, len(footnotes)),
        "footnotes": footnotes,
    }


def _render_result(result: dict) -> None:
    status = result["status"]
    if status == "no_material":
        st.info(
            f"내서재에 «{result['label']}» 본문과 직접 관련된 주석 자료가 없습니다. "
            "«자료 등록» 에서 관련 주석서를 추가하면 해설을 만들 수 있습니다."
        )
        return
    if status == "gen_failed":
        msg = "해설 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        if result.get("error"):
            msg += f"\n\n({result['error']})"
        st.warning(msg)
        return

    st.markdown(result["answer_badged"] or "_생성된 해설이 없습니다._")
    footnotes = result.get("footnotes") or []
    if footnotes:
        st.markdown("**참고 자료 (내서재)**")
        for fn in footnotes:
            st.markdown(f"{circled_marker(fn.marker)} {fn.formatted()}")
            if fn.excerpt:
                st.caption(f"{fn.excerpt}…")


def _gen_overrides() -> dict:
    """사이드바(ui/app.py::_render_settings_expander)에서 고른 생성 모델/창의성만
    generate_stream 에 넘긴다 — 고른 적 없으면 빈 dict 이라 core 기본값 사용.
    `ui.pages.chat._settings_overrides()` 와 동일 로직을 인라인한다(순환 import
    회피: chat → ui.pages 패키지 초기화 → sermon_draft → 이 모듈)."""
    overrides: dict = {}
    gen_model = st.session_state.get("settings_gen_model")
    if gen_model:
        overrides["gen_model"] = gen_model
    temperature = st.session_state.get("settings_temperature")
    if temperature is not None:
        overrides["temperature"] = float(temperature)
    return overrides


def _load_registry() -> Optional[dict]:
    """각주 서지를 실제 레코드에서 채우기 위한 identity registry. 실패해도
    각주는 후보 메타데이터로 폴백하므로 None 허용."""
    try:
        from core.config import DEFAULT_REGISTRY_PATH
        from core.identity_registry import load_identity_registry

        return load_identity_registry(DEFAULT_REGISTRY_PATH)
    except Exception as e:  # noqa: BLE001
        logger.warning("[passage_commentary_panel] registry 로드 실패 (각주 폴백): %s", e)
        return None

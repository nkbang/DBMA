"""tests/test_contamination_marker_disclosure.py — 오염 문자 표식·고지 회귀 방지.

근거: `docs/DBMA_P0_5_RERUN_20260926_SIGNALS_001.md` §3. 종전에는 재시도를 소진하면
오염 문자를 **조용히 삭제**했고, 그 결과 남은 문장이 정상처럼 보이면서 단어가
망가졌다:

    B2: "이미 하나님 앞에서 완전히로워졌기 때문에"   ← 義 삭제 → "의로워졌기" 깨짐
    H1: "그 속에서 정와 사랑을 실현시키고자"          ← 義 삭제 → "정의"가 "정"으로

"의"(righteousness)처럼 핵심 신학 용어가 한 글자 삭제로 사라지는데 독자는 오탈자로
읽고 넘어간다. 삭제 자체보다 **삭제를 감추는 것**이 문제다. 그래서 표식을 남기고
답변 경로에는 고지까지 붙인다.

전량 유보 전환은 기각했다 — 실측 소진 7건 중 못 읽을 수준은 1건(E2)뿐이고
B2·H1·C2는 내용이 온전해 과잉이며, 손상 정도로 분기하는 안은 검증되지 않은
임계값 위에 차단 로직을 얹는 형태다(feedback_avoid_risky_uncertain_design).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.generation as gen  # noqa: E402
from core.generation import (  # noqa: E402
    _CONTAMINATION_MARKER,
    _contamination_notice,
    _detect_script_contamination,
    _sanitize_script_contamination,
)


# ── 표식 의미 ────────────────────────────────────────────────


def test_marker_replaces_one_for_one_not_deletes():
    """글자 수가 유지되어야 "여기에 글자가 있었다"가 보인다."""
    out = _sanitize_script_contamination("정義와 사랑")

    assert out == f"정{_CONTAMINATION_MARKER}와 사랑"
    assert _detect_script_contamination(out) == []


def test_marker_preserves_the_real_failure_case():
    """실측된 B2/H1 손상이 이제 눈에 보인다."""
    assert _sanitize_script_contamination("완전히 義로워졌기") == (
        f"완전히 {_CONTAMINATION_MARKER}로워졌기"
    )


def test_clean_korean_untouched():
    text = "태초에 말씀이 계시니라 (요 1:1)"
    assert _sanitize_script_contamination(text) == text
    assert _contamination_notice(text) == ""


# ── 고지 ─────────────────────────────────────────────────────


def test_notice_counts_markers():
    out = _sanitize_script_contamination("義와 法則과 論")  # 義·法·則·論 = 4자
    notice = _contamination_notice(out)

    assert "4자" in notice
    assert _CONTAMINATION_MARKER in notice


def test_notice_empty_when_nothing_removed():
    assert _contamination_notice("정상 문장") == ""


# ── 경로별 적용 ──────────────────────────────────────────────


class _Resp:
    """GenerationService.generate()가 요구하는 최소 ResponsePackage 대역."""

    def __init__(self):
        self.question = "칭의란 무엇입니까?"
        self.top_k_results = []
        self.llm_context_block = "context"
        self.context_used = True
        self.citations = []
        self.scripture_contexts = []


def _always_contaminated(**_kw):
    return {"response": "칭의는 義롭다 하심이다."}


def test_answer_path_appends_notice(monkeypatch):
    """질의응답 경로 — 표식만으로는 원인을 모르므로 고지까지 붙는다."""
    monkeypatch.setattr(gen.ollama, "generate", _always_contaminated)

    result = gen.GenerationService().generate(_Resp())

    assert _CONTAMINATION_MARKER in result.answer
    assert "제거했습니다" in result.answer
    assert _detect_script_contamination(result.answer) == []


def test_sermon_expansion_gets_marker_but_no_notice(monkeypatch):
    """설교 대지 확장 — 결과가 최종 원고에 그대로 조립되므로 안내 문구가
    섞이면 산출물이 오염된다. 표식만 남기고 고지는 붙이지 않는다."""
    monkeypatch.setattr(gen.ollama, "generate", _always_contaminated)

    text, error, _cg = gen.SermonDraftService().expand_point(
        "첫째 대지", "로마서 5:1-5", []
    )

    assert error is None
    assert _CONTAMINATION_MARKER in text
    assert "제거했습니다" not in text, "원고에 안내 문구가 섞이면 안 된다"

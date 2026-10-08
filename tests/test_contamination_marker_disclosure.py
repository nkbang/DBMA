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


# ── 라틴 문자 오염 (2026-09-26) ───────────────────────────────
#
# _SCRIPT_CONTAMINATION_RE는 문자 체계로 판정해 라틴 알파벳을 전부 면제한다 —
# 정상 출력에 "Charles Haddon Spurgeon"·영문 원문 인용이 들어가기 때문이다.
# 그래서 순수 라틴 외국어 혼입(독일어 persönlich, 인도네시아어 bahwa)은 원리상
# 탐지되지 않았다. 판별 기준은 사전이 아니라 **근거 문맥**이다.
#
# 실측 검증(P0-5 24건 × 2회분): 재현율 2/2, 오탐 0/107 라틴 토큰.
# 사전을 주 신호로 쓴 초안은 has·soldiers·Churches(굴절형)와 Hiscox·Dagg·Dei
# (고유명사)를 오탐했다 — 문맥 신호로 바꾸자 사라졌다.

_CTX = (
    "Charles Haddon Spurgeon preached on justification and the deacon's "
    "qualifications in the Metropolitan Tabernacle Pulpit."
)


def test_latin_quoted_from_context_is_not_flagged():
    answer = "스퍼전은 justification 을 다룹니다(출처: Metropolitan Tabernacle Pulpit)."
    assert gen._detect_latin_contamination(answer, _CTX) == []


def test_foreign_latin_words_are_flagged():
    """09-23 실측 사례 2건을 그대로 고정한다."""
    answer = "이것은 bahwa 그리고 persönlich 한 문제입니다."
    assert gen._detect_latin_contamination(answer, _CTX) == ["bahwa", "persönlich"]


def test_capitalized_tokens_exempt_as_proper_nouns():
    """Hiscox·Dagg·Dei 류 고유명사가 오탐되던 문제."""
    answer = "Hiscox와 Dagg는 Imago Dei를 다루지 않습니다."
    assert gen._detect_latin_contamination(answer, _CTX) == []


def test_no_context_means_no_judgment():
    """근거가 없으면 판정 근거도 없다 — 추측으로 표시하지 않는다."""
    assert gen._detect_latin_contamination("bahwa persönlich", "") == []


def test_latin_notice_lists_words():
    notice = gen._latin_notice(["bahwa", "persönlich"])
    assert "bahwa" in notice and "persönlich" in notice
    assert gen._latin_notice([]) == ""


class _RespWithContext(_Resp):
    def __init__(self):
        super().__init__()
        self.llm_context_block = _CTX


def test_latin_contamination_discloses_without_deleting(monkeypatch):
    """계약 — 라틴 오염은 지우지 않고 고지만 붙인다.

    단어 삭제는 글자 삭제보다 파괴적이고, 판정 표본이 작아(양성 2건) 검증되지
    않은 판정 위에 제거 로직을 얹지 않는다(feedback_avoid_risky_uncertain_design).
    """
    monkeypatch.setattr(
        gen.ollama, "generate",
        lambda **_k: {"response": "칭의는 bahwa 중요한 교리입니다."},
    )

    result = gen.GenerationService().generate(_RespWithContext())

    assert "bahwa" in result.answer, "라틴 오염 단어를 삭제하면 안 된다"
    assert "외국어로 보이는 단어" in result.answer


def test_streaming_path_also_discloses_latin(monkeypatch):
    """채팅이 실제로 쓰는 경로(generate_stream)에도 적용돼야 한다 —
    블로킹 generate()에만 붙이면 사용자에게는 아무 효과가 없다."""
    def fake(**_k):
        for piece in ["칭의는 ", "bahwa ", "중요합니다."]:
            yield {"response": piece}

    monkeypatch.setattr(gen.ollama, "generate", fake)

    stream = gen.GenerationService().generate_stream(_RespWithContext())
    list(stream)
    answer = stream.to_result().answer

    assert "bahwa" in answer, "삭제하지 않는다"
    assert "외국어로 보이는 단어" in answer

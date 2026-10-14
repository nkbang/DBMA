"""tests/test_author_name_normalization.py — 인명 표기 통일 + 라틴 고지 문구 + 화면 교체.

근거: P0-5 24건 재실행 3회분(2026-09-23/26/27)에서 Spurgeon 하나가 다섯 가지로
적혔다 — 스퍼전 · 스페전 · 스페어전 · 스펀지언 · 스페urgeon(한글+라틴 반쪽 음역).
같은 인물이 답변마다 다른 사람처럼 보이고, 마지막 형태는 라틴 오염 탐지까지
유발했다(docs/DBMA_P0_5_RERUN_20260927_SIGNALS_002.md §3).

세 가지를 함께 지킨다:
  1. 알려진 오표기를 표준형(스펄전)으로 바로잡는다.
  2. 그 치환은 라틴 오염 탐지보다 먼저 일어난다(불필요한 재시도·고지 방지).
  3. 완성된 답변에서만 가능한 처리는 그 턴의 화면에도 보여야 한다.
"""

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.generation as gen  # noqa: E402
from core.generation import _normalize_author_names  # noqa: E402

_CTX = "Charles Haddon Spurgeon preached on justification."
VARIANTS = ["스퍼전", "스페전", "스페어전", "스펀지언", "스페urgeon"]


# ── 1. 치환 ──────────────────────────────────────────────────


@pytest.mark.parametrize("variant", VARIANTS)
def test_each_observed_variant_becomes_canonical(variant):
    out = _normalize_author_names(f"C.H. {variant}의 설교에 따르면")
    assert out == "C.H. 스펄전의 설교에 따르면"


def test_particles_after_the_name_are_preserved():
    assert _normalize_author_names("스펀지언은 말했고 스펀지언을 인용합니다") == (
        "스펄전은 말했고 스펄전을 인용합니다"
    )


def test_canonical_form_and_english_name_untouched():
    text = "찰스 스펄전(Charles Haddon Spurgeon)은 침례교 목사였습니다."
    assert _normalize_author_names(text) == text


def test_unrelated_text_and_empty_inputs_unchanged():
    assert _normalize_author_names("칭의는 믿음으로 말미암습니다.") == "칭의는 믿음으로 말미암습니다."
    assert _normalize_author_names("") == ""


def test_unlisted_variant_is_not_guessed():
    """목록에 없는 새 변형은 건드리지 않는다 — 추측으로 패턴을 넓히면 다른 단어를
    바꿀 수 있다. 새 변형은 재실행에서 수집해 표에 추가한다."""
    assert _normalize_author_names("스펄젼의 설교") == "스펄젼의 설교"


# ── 2. 경로별 적용, 그리고 탐지보다 먼저 ─────────────────────


class _Resp:
    def __init__(self):
        self.question = "스펄전은 누구입니까?"
        self.top_k_results = []
        self.llm_context_block = _CTX
        self.context_used = True
        self.citations = []
        self.scripture_contexts = []


def test_generate_normalizes_and_does_not_trigger_latin_retry(monkeypatch):
    """'스페urgeon'의 urgeon이 라틴 탐지에 걸리면 재시도와 고지가 불필요하게
    일어난다 — 치환이 탐지보다 먼저여야 한다."""
    calls = []

    def fake(**_k):
        calls.append(1)
        return {"response": "C.H. 스페urgeon은 침례교 목사였습니다."}

    monkeypatch.setattr(gen.ollama, "generate", fake)

    result = gen.GenerationService().generate(_Resp())

    assert result.answer == "C.H. 스펄전은 침례교 목사였습니다."
    assert len(calls) == 1, "치환 후에는 오염이 없으므로 재시도하면 안 된다"
    assert "로마자 표기가 섞여 있습니다" not in result.answer


def test_stream_final_result_is_normalized(monkeypatch):
    def fake(**_k):
        for piece in ["C.H. 스페", "urgeon", "은 침례교 목사였습니다."]:
            yield {"response": piece}

    monkeypatch.setattr(gen.ollama, "generate", fake)

    stream = gen.GenerationService().generate_stream(_Resp())
    list(stream)
    answer = stream.to_result().answer

    # 이름이 조각 경계에서 갈려도 완성본에서 한 번에 바로잡는다.
    assert answer == "C.H. 스펄전은 침례교 목사였습니다."


# ── 3. 라틴 고지 문구 ────────────────────────────────────────


def test_latin_notice_describes_the_actual_condition():
    """탐지 조건은 '근거에 없는 로마자 표기'다. 실전 첫 탐지가 외국어가 아니라 깨진
    인명 음역이었으므로 '외국어'라고만 말하면 부정확하다."""
    notice = gen._latin_notice(["bahwa"])

    assert "로마자 표기" in notice
    assert "인명 표기가 깨진" in notice
    assert "외국어로 보이는 단어" not in notice


# ── 4. 화면 교체 ─────────────────────────────────────────────


class _FakePlaceholder:
    def __init__(self):
        self.replaced_with = None

    @contextmanager
    def container(self):
        yield

    def markdown(self, text):
        self.replaced_with = text


class _FakeSt:
    def __init__(self):
        self.placeholder = _FakePlaceholder()

    def empty(self):
        return self.placeholder

    def write_stream(self, stream):
        return "".join(stream)  # 실제 st.write_stream처럼 이어 붙인 문자열을 돌려준다


class _FakeStream:
    def __init__(self, pieces, final):
        self._pieces, self._final = pieces, final

    def __iter__(self):
        return iter(self._pieces)

    def to_result(self):
        class _R:
            answer = self._final
        return _R()


def test_screen_replaced_when_final_answer_differs(monkeypatch):
    """인명 통일·고지는 to_result()에서만 가능하다. 화면을 교체하지 않으면 그 턴에는
    보이지 않고 다음 화면 갱신 때에야 나타난다."""
    from ui.pages import chat

    fake = _FakeSt()
    monkeypatch.setattr(chat, "st", fake)

    stream = _FakeStream(["C.H. 스페전", "의 설교"], "C.H. 스펄전의 설교\n\n⚠️ 고지")
    result = chat._stream_and_finalize(stream)

    assert result.answer.endswith("⚠️ 고지")
    assert fake.placeholder.replaced_with == "C.H. 스펄전의 설교\n\n⚠️ 고지"


def test_screen_not_redrawn_when_nothing_changed(monkeypatch):
    """대부분의 답변은 완성본이 스트리밍 텍스트와 같다 — 다시 그리면 깜박인다."""
    from ui.pages import chat

    fake = _FakeSt()
    monkeypatch.setattr(chat, "st", fake)

    stream = _FakeStream(["정상 ", "답변"], "정상 답변")
    chat._stream_and_finalize(stream)

    assert fake.placeholder.replaced_with is None

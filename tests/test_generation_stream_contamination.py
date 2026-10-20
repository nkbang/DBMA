"""GenerationStream 의 CJK 오염 문자 제거 (2026-09-04).

블로킹 경로 generate() 에만 있던 한국어 출력 순도 방어(재시도+sanitize)를
스트리밍 경로에도 넣었다. 스트리밍은 mid-stream 재시도가 불가능하므로
"재시도 소진 → 강제 제거"에 해당하는 sanitize만 적용한다 — 청크가 도착할
때마다 비한글 오염 문자(히라가나/가타카나/CJK 한자/태국어)를 제거한다.
"""

import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import ollama  # noqa: F401
except ImportError:
    if "ollama" not in sys.modules:
        _stub = types.ModuleType("ollama")
        _stub.generate = lambda *a, **k: {"response": ""}
        _stub.embeddings = lambda *a, **k: {"embedding": []}
        sys.modules["ollama"] = _stub

from core import generation
from core.generation import GenerationService, _detect_script_contamination
from core.retrieval import ParsedQuery, PerformanceMetrics, ResponsePackage


def _make_response() -> ResponsePackage:
    return ResponsePackage(
        query_id="q1",
        question="요한복음 1:1 해설",
        candidates=[],
        top_k_results=[],
        performance_metrics=PerformanceMetrics(),
        parsed_query=ParsedQuery(original_query="요한복음 1:1 해설", intent="unknown"),
        llm_context_block="context",
        citations=[],
    )


def _fake_generate(pieces):
    """ollama.generate 대역 — stream=True 면 청크 이터레이터, 아니면 단일 dict."""
    def _gen(*args, stream=False, **kwargs):
        if stream:
            return iter([{"response": p} for p in pieces])
        return {"response": "".join(pieces)}
    return _gen


def test_strips_cjk_from_each_streamed_piece(monkeypatch):
    monkeypatch.setattr(
        "core.generation.ollama.generate",
        _fake_generate(["요한복음 ", "1:1은 ", "私의 ", "말씀 ", "世상"]),
    )
    stream = GenerationService().generate_stream(_make_response())
    yielded = list(stream)

    for piece in yielded:
        assert _detect_script_contamination(piece) == []
    joined = "".join(yielded)
    assert "私" not in joined and "世" not in joined
    # [2026-09-26] 삭제 → 표식. 조용히 지우면 "의"가 사라진 "로워졌기"처럼
    # 망가진 단어가 정상처럼 보인다(P0-5 실측 B2/H1).
    assert joined == "요한복음 1:1은 □의 말씀 □상"

    result = stream.to_result()
    assert _detect_script_contamination(result.answer) == []
    # 답변 경로에는 고지가 덧붙는다 — 본문은 그대로 앞에 온다.
    assert result.answer.startswith("요한복음 1:1은 □의 말씀 □상")
    assert "□" in result.answer and "제거했습니다" in result.answer


def test_skips_piece_that_is_only_contamination(monkeypatch):
    monkeypatch.setattr(
        "core.generation.ollama.generate",
        _fake_generate(["좋은 답", "の", "니다"]),
    )
    stream = GenerationService().generate_stream(_make_response())
    yielded = list(stream)

    # [2026-09-26] 오염만 있던 청크도 이제 표식으로 남는다 — 글자가 있었다는
    # 사실을 감추지 않는 것이 이 변경의 요점이다.
    assert yielded == ["좋은 답", "□", "니다"]
    assert stream.to_result().answer.startswith("좋은 답□니다")


def test_clean_korean_passes_through_unchanged(monkeypatch):
    pieces = ["태초에 ", "말씀이 ", "계시니라 (요 1:1)"]
    monkeypatch.setattr("core.generation.ollama.generate", _fake_generate(pieces))
    stream = GenerationService().generate_stream(_make_response())
    yielded = list(stream)

    assert yielded == pieces
    assert stream.to_result().answer == "태초에 말씀이 계시니라 (요 1:1)"


def test_thai_and_kana_also_marked(monkeypatch):
    monkeypatch.setattr(
        "core.generation.ollama.generate",
        _fake_generate(["은혜 ", "ก", "가 ", "ナ", "충만"]),
    )
    stream = GenerationService().generate_stream(_make_response())
    list(stream)  # to_result()는 완전 순회 후에만 유효
    result = stream.to_result()
    assert _detect_script_contamination(result.answer) == []
    assert result.answer.startswith("은혜 □가 □충만")


class TestThinkPassthrough:
    """[J6, 2026-10-18] thinking 모델 대응 — think 인자는 넘길 때만 전달한다.

    생성 모델 후보로 올린 qwen3 계열은 thinking 모델이고, num_predict(1024)가
    사고 과정에 전량 소진되면 `response`가 빈 문자열로 돌아온다(실측:
    thinking 3,850자 / response 0자 / done_reason="length"). 이 경로는
    `result["response"]`만 읽으므로 답변이 통째로 사라진다 — A/B 측정이
    성립하지 않아 think 패스스루를 넣었다.

    가장 중요한 불변식은 **생략 시 종전과 동일한 호출**이다. 현행 모델의
    동작·측정값이 이 변경으로 흔들리면 안 된다.
    """

    def _response(self):
        from core.retrieval import ParsedQuery, PerformanceMetrics, ResponsePackage

        return ResponsePackage(
            query_id="q", question="질문", candidates=[], top_k_results=[],
            performance_metrics=PerformanceMetrics(),
            parsed_query=ParsedQuery(original_query="질문", intent="theological"),
            llm_context_block="자료 본문", citations=[],
        )

    def test_omitted_think_sends_no_think_kwarg(self, monkeypatch):
        """설정이 꺼져 있으면 호출이 종전과 바이트 단위로 같아야 한다.

        [2026-10-20] 프로덕션 기본값은 이제 disable_thinking: true다(v4가
        thinking 모델). 이 테스트가 지키는 불변식은 "설정이 꺼진 상태에서는
        아무것도 넘기지 않는다"이므로 설정을 명시적으로 꺼고 확인한다 —
        llama 계열로 롤백했을 때 동작이 종전과 같아야 하기 때문이다.
        """
        seen = {}

        def fake_generate(**kwargs):
            seen.update(kwargs)
            return {"response": "답변입니다."}

        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", False)
        monkeypatch.setattr(generation.ollama, "generate", fake_generate)
        generation.GenerationService().generate(self._response())
        assert "think" not in seen

    def test_explicit_think_false_is_forwarded(self, monkeypatch):
        seen = {}

        def fake_generate(**kwargs):
            seen.update(kwargs)
            return {"response": "답변입니다."}

        monkeypatch.setattr(generation.ollama, "generate", fake_generate)
        generation.GenerationService().generate(self._response(), think=False)
        assert seen.get("think") is False

    def test_explicit_think_true_is_forwarded(self, monkeypatch):
        seen = {}

        def fake_generate(**kwargs):
            seen.update(kwargs)
            return {"response": "답변입니다."}

        monkeypatch.setattr(generation.ollama, "generate", fake_generate)
        generation.GenerationService().generate(self._response(), think=True)
        assert seen.get("think") is True


class TestThinkSwitchReachesEveryPath:
    """[J6 전환, 2026-10-20] thinking 스위치가 생성 경로 **전부**에 닿는가.

    프로덕션 생성 모델이 qwen3 계열(my-theology-bot-v4)로 바뀌었다. 이 계열은
    `num_predict`가 사고 과정에 전량 소진되면 `response`가 빈 문자열로
    돌아오므로, 한 경로라도 빠뜨리면 그 화면만 빈 답변이 된다. 특히
    **스트리밍 경로가 UI의 주 경로**다 — generate()만 고치고 끝내면 앱에서는
    아무것도 안 보인다.

    경로는 넷이다: 스트리밍 · 단발 생성 · 설교 개요 · 대지 확장.
    """

    def _response(self):
        from core.retrieval import ParsedQuery, PerformanceMetrics, ResponsePackage

        return ResponsePackage(
            query_id="q", question="질문", candidates=[], top_k_results=[],
            performance_metrics=PerformanceMetrics(),
            parsed_query=ParsedQuery(original_query="질문", intent="theological"),
            llm_context_block="자료 본문", citations=[],
        )

    def test_helper_follows_config(self, monkeypatch):
        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", True)
        assert generation._think_kwargs() == {"think": False}
        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", False)
        assert generation._think_kwargs() == {}

    def test_explicit_override_beats_config(self, monkeypatch):
        """A/B 측정 하네스는 모델별로 직접 지정한다 — 설정보다 우선한다."""
        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", True)
        assert generation._think_kwargs(True) == {"think": True}
        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", False)
        assert generation._think_kwargs(False) == {"think": False}

    def test_streaming_path_sends_think(self, monkeypatch):
        """UI 주 경로 — 빠뜨리면 화면이 빈 채로 남는다."""
        seen = {}

        def fake_generate(**kwargs):
            seen.update(kwargs)
            return iter([{"response": "답변"}])

        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", True)
        monkeypatch.setattr(generation.ollama, "generate", fake_generate)
        stream = generation.GenerationService().generate_stream(self._response())
        list(stream)
        assert seen.get("think") is False
        assert seen.get("stream") is True

    def test_generate_path_sends_think(self, monkeypatch):
        seen = {}

        def fake_generate(**kwargs):
            seen.update(kwargs)
            return {"response": "답변입니다."}

        monkeypatch.setattr(generation, "GEN_DISABLE_THINKING", True)
        monkeypatch.setattr(generation.ollama, "generate", fake_generate)
        generation.GenerationService().generate(self._response())
        assert seen.get("think") is False

    def test_every_ollama_generate_call_passes_think_kwargs(self):
        """설교 경로 2곳을 포함해 네 호출부가 모두 헬퍼를 쓰는지 소스로 고정.

        설교 경로는 ResponsePackage가 아니라 후보 목록을 받아 모킹이 번거롭고,
        무엇보다 '호출부를 빠뜨리지 않았는가'가 이 테스트의 관심사다.
        """
        import inspect
        import re

        src = inspect.getsource(generation)
        # 주석·독스트링의 언급("ollama.generate()는 …")을 세지 않도록
        # 실제 호출 형태(`= ollama.generate(` / `in ollama.generate(`)만 센다.
        calls = [m.start() for m in re.finditer(r"(?:=|\bin)\s*ollama\.generate\(", src)]
        assert len(calls) == 4, f"생성 호출부가 {len(calls)}곳 — 4곳이어야 한다"
        for pos in calls:
            tail = src[pos:pos + 400]
            assert "_think_kwargs(" in tail or "think_kwargs" in tail, (
                "thinking 인자를 넘기지 않는 ollama.generate 호출부가 있다:\n"
                + tail[:200]
            )

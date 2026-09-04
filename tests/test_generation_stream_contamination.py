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
    assert joined == "요한복음 1:1은 의 말씀 상"

    result = stream.to_result()
    assert _detect_script_contamination(result.answer) == []
    assert result.answer == "요한복음 1:1은 의 말씀 상"


def test_skips_piece_that_is_only_contamination(monkeypatch):
    monkeypatch.setattr(
        "core.generation.ollama.generate",
        _fake_generate(["좋은 답", "の", "니다"]),
    )
    stream = GenerationService().generate_stream(_make_response())
    yielded = list(stream)

    assert yielded == ["좋은 답", "니다"]  # 오염만 있던 청크는 yield 안 됨
    assert stream.to_result().answer == "좋은 답니다"


def test_clean_korean_passes_through_unchanged(monkeypatch):
    pieces = ["태초에 ", "말씀이 ", "계시니라 (요 1:1)"]
    monkeypatch.setattr("core.generation.ollama.generate", _fake_generate(pieces))
    stream = GenerationService().generate_stream(_make_response())
    yielded = list(stream)

    assert yielded == pieces
    assert stream.to_result().answer == "태초에 말씀이 계시니라 (요 1:1)"


def test_thai_and_kana_also_removed(monkeypatch):
    monkeypatch.setattr(
        "core.generation.ollama.generate",
        _fake_generate(["은혜 ", "ก", "가 ", "ナ", "충만"]),
    )
    stream = GenerationService().generate_stream(_make_response())
    list(stream)  # to_result()는 완전 순회 후에만 유효
    result = stream.to_result()
    assert _detect_script_contamination(result.answer) == []
    assert result.answer == "은혜 가 충만"

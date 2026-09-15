"""core/passage_commentary.py — 지정 본문 → 내서재 근거 해설 (ADR-031).

`QueryProcessor` / `GenerationService` 는 fake 로 주입한다 — Ollama·코퍼스 없이
정합 필터, no_material 게이트, 프롬프트 가드, 각주/배지 렌더를 검증한다.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.passage_commentary import (
    circled_marker,
    generate_passage_commentary,
    make_response_package,
    reference_label,
    render_answer_with_badges,
    retrieve_passage_commentary,
)
from core.retrieval import ScriptureReference


# ── fakes ────────────────────────────────────────────────
class _Cand:
    def __init__(self, tsu_id, content, verse_mapping=None, final_score=0.5, **md):
        self.tsu_id = tsu_id
        self.content = content
        self.final_score = final_score
        self.metadata = {"verse_mapping": verse_mapping or {}, **md}


class _Resp:
    def __init__(self, cands):
        self.top_k_results = list(cands)
        self.question = ""
        self.llm_context_block = ""
        self.citations = []
        self.candidates = list(cands)


class _Processor:
    def __init__(self, cands):
        self._cands = cands
        self.calls = []

    def process(self, query, query_id="", k=10):
        self.calls.append((query, k))
        return _Resp(self._cands)


class _Gen:
    def __init__(self, answer="지혜는 은보다 낫다 [1]. 정금보다 지식이다 [2].", error=None):
        self.answer = answer
        self.error = error
        self.calls = 0

    def generate(self, pkg):
        self.calls += 1
        return SimpleNamespace(answer=self.answer, error=self.error)


class _BoomGen:
    def generate(self, pkg):  # pragma: no cover - 호출되면 실패
        raise AssertionError("no_material 이면 생성하면 안 된다")


_REF = ScriptureReference(book_id="PRO", chapter=8, verse_start=10)
_ALIGNED_VM = {"book_id": "PRO", "chapter": 8, "verse_start": 1, "verse_end": 36}
_OFF_BOOK_VM = {"book_id": "ROM", "chapter": 8, "verse_start": 1}


# ── reference_label / circled_marker ─────────────────────
def test_reference_label_single_and_range():
    assert reference_label(_REF) == "잠언 8:10"
    assert reference_label(ScriptureReference("PRO", 8, 10, 12)) == "잠언 8:10-12"


def test_circled_marker():
    assert circled_marker(1) == "①"
    assert circled_marker(3) == "③"
    assert circled_marker(21) == "[21]"


# ── retrieve_passage_commentary: 정합 필터 ───────────────
def test_keeps_only_verse_aligned_candidates():
    proc = _Processor([
        _Cand("A", "잠언 8장 주해", _ALIGNED_VM),
        _Cand("B", "로마서 8장 주해", _OFF_BOOK_VM),
        _Cand("C", "verse_mapping 없음", {}),
    ])
    outcome = retrieve_passage_commentary(_REF, proc)
    assert outcome.status == "ok"
    assert [c.tsu_id for c in outcome.aligned] == ["A"]
    assert proc.calls and "잠언 8:10" in proc.calls[0][0]


def test_no_material_when_nothing_aligns():
    proc = _Processor([_Cand("B", "x", _OFF_BOOK_VM), _Cand("C", "y", {})])
    outcome = retrieve_passage_commentary(_REF, proc)
    assert outcome.status == "no_material"
    assert outcome.aligned == []
    assert outcome.response is not None


def test_retrieval_failure_isolated():
    class _Boom:
        def process(self, *a, **k):
            raise RuntimeError("engine down")

    outcome = retrieve_passage_commentary(_REF, _Boom())
    assert outcome.status == "retrieval_failed"
    assert outcome.error


# ── make_response_package: 프롬프트 가드 + 각주 ──────────
def test_response_package_prompt_and_footnotes():
    proc = _Processor([_Cand("A", "잠언 8장 주해 본문", _ALIGNED_VM,
                             author="박윤선", title="잠언 주석", source_type="주석")])
    outcome = retrieve_passage_commentary(_REF, proc)
    pkg, citations, footnotes = make_response_package(outcome, _REF)

    assert "잠언 8:10" in pkg.llm_context_block
    assert "<자료>" in pkg.llm_context_block
    assert "[1]" in pkg.llm_context_block  # 번호형 컨텍스트
    assert "추측" in pkg.llm_context_block  # 가드 문구
    assert "[1]" in pkg.question           # 지시문에 마커 형식 명시
    assert len(footnotes) == 1 == len(citations)
    assert footnotes[0].marker == 1
    assert footnotes[0].author == "박윤선"
    assert "잠언 주석" in footnotes[0].formatted()


def test_registry_enrichment_overrides_metadata_fallback():
    proc = _Processor([
        _Cand("A", "잠언 8장 주해 본문", _ALIGNED_VM,
              document_id="doc-1", source_file="9. 로마서1.pdf", source_type="pdf")
    ])
    registry = {
        "documents": {
            "doc-1": {
                "author": "박윤선",
                "title": "잠언 주석",
                "doc_type": "주석",
                "created_at": "1998-05-01",
                "source_file": "9. 로마서1.pdf",
                "superseded_by": None,
            }
        }
    }
    outcome = retrieve_passage_commentary(_REF, proc)
    _pkg, _c, footnotes = make_response_package(outcome, _REF, registry=registry)
    fn = footnotes[0]
    assert fn.author == "박윤선"
    assert fn.title == "잠언 주석"      # 파일명 폴백이 아니라 레지스트리 title
    assert fn.doc_type == "주석"        # source_type "pdf" 가 아니라 doc_type
    assert fn.year == "1998"
    assert fn.formatted() == "박윤선, *잠언 주석* (주석, 1998), 잠언 8:1-36."


# ── render_answer_with_badges ───────────────────────────
def test_render_badges_only_in_range():
    out = render_answer_with_badges("a [1] b [2] c [5] d", max_marker=2)
    assert out == "a ① b ② c [5] d"


# ── generate_passage_commentary: end-to-end (fake) ──────
def test_generate_happy_path():
    proc = _Processor([_Cand("A", "주해", _ALIGNED_VM, author="저자", title="제목")])
    res = generate_passage_commentary(_REF, proc, _Gen(answer="지혜는 은보다 낫다 [1]."))
    assert res.status == "ok"
    assert res.answer_badged == "지혜는 은보다 낫다 ①."
    assert res.reference_label == "잠언 8:10"
    assert len(res.footnotes) == 1


def test_generate_no_material_does_not_call_generator():
    proc = _Processor([_Cand("B", "x", _OFF_BOOK_VM)])
    res = generate_passage_commentary(_REF, proc, _BoomGen())
    assert res.status == "no_material"
    assert res.answer == ""


def test_generate_marks_gen_failed_on_error():
    proc = _Processor([_Cand("A", "주해", _ALIGNED_VM)])
    res = generate_passage_commentary(_REF, proc, _Gen(error="ollama timeout"))
    assert res.status == "gen_failed"
    assert res.error == "ollama timeout"

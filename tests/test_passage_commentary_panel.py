"""ui/components/passage_commentary_panel.py — 설교 준비 화면 본문 해설 참고 패널
(ADR-031 §9 연동).

free-text 에서 성경 구절을 뽑아내는 로직과, 패널 렌더(익스팬더 노출 / no_material /
배지·각주)를 fake generator 로 검증한다. Ollama·코퍼스 없이 돌아간다.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import ScriptureReference
from ui.components.passage_commentary_panel import _extract_first_ref


class TestExtractFirstRef:
    def test_korean_book_with_range(self):
        ref = _extract_first_ref("로마서 5:1-5, 고난 중의 소망")
        assert isinstance(ref, ScriptureReference)
        assert (ref.book_id, ref.chapter, ref.verse_start, ref.verse_end) == ("ROM", 5, 1, 5)

    def test_korean_short_alias_no_space(self):
        ref = _extract_first_ref("요3:16 하나님의 사랑")
        assert ref is not None
        assert (ref.book_id, ref.chapter, ref.verse_start) == ("JHN", 3, 16)

    def test_english_reference(self):
        ref = _extract_first_ref("Explain Proverbs 8:10 in context")
        assert ref is not None
        assert (ref.book_id, ref.chapter, ref.verse_start) == ("PRO", 8, 10)

    def test_theme_only_no_ref(self):
        assert _extract_first_ref("고난 중의 소망") is None

    def test_empty(self):
        assert _extract_first_ref("") is None
        assert _extract_first_ref("   ") is None

    def test_first_ref_wins_when_multiple(self):
        ref = _extract_first_ref("로마서 5:1 와 요한복음 3:16 비교")
        assert ref is not None
        assert ref.book_id == "ROM"


# ── AppTest 스모크 (fake generator) ─────────────────────
_SMOKE = os.path.join(os.path.dirname(__file__), "_pcp_smoke_app.py")


_SMOKE_TMPL = '''\
import sys; sys.path.insert(0, {root!r})
from types import SimpleNamespace
import core.generation as gen
import ui.components.passage_commentary_panel as pcp

class _Stream:
    A = "지혜는 은보다 낫다 [1]. 재물보다 순종이다 [2]."
    def __iter__(self):
        yield self.A
    def to_result(self):
        return SimpleNamespace(answer=self.A, error=None, claim_guard_result=None)

gen.GenerationService.generate_stream = lambda self, resp, *a, **k: _Stream()

# 실제 코퍼스 대신 정합 후보를 주는 fake processor (JHN 3:16 정합)
class _Cand:
    def __init__(self, tid, title):
        self.tsu_id = tid; self.content = "요한복음 3장 주해 본문 " + tid; self.final_score = 0.9
        self.metadata = {{"verse_mapping": {{"book_id": "JHN", "chapter": 3,
                          "verse_start": 1, "verse_end": 36}},
                          "title": title, "author": "저자"}}
class _Resp:
    def __init__(self):
        self.top_k_results = [_Cand("t1", "요한복음 주석"), _Cand("t2", "요한복음 강해")]
        self.candidates = list(self.top_k_results)
        self.question = ""; self.llm_context_block = ""; self.citations = []
class _Proc:
    def process(self, q, query_id="", k=10):
        return _Resp()

pcp.get_shared_query_processor = lambda: _Proc()
pcp._load_registry = lambda: None

import streamlit as st
from ui.components.passage_commentary_panel import render_passage_commentary_panel
render_passage_commentary_panel({text!r}, key_prefix="t")
'''


def _write_smoke_app(text: str, *, with_material: bool = True) -> None:
    root = os.path.join(os.path.dirname(__file__), "..")
    src = _SMOKE_TMPL.format(root=root, text=text)
    if not with_material:
        # 정합 후보를 비워 no_material 경로를 태운다
        src = src.replace(
            'self.top_k_results = [_Cand("t1", "요한복음 주석"), _Cand("t2", "요한복음 강해")]',
            "self.top_k_results = []",
        )
    with open(_SMOKE, "w", encoding="utf-8") as f:
        f.write(src)


def _cleanup() -> None:
    try:
        os.remove(_SMOKE)
    except OSError:
        pass


def test_panel_hidden_without_ref():
    from streamlit.testing.v1 import AppTest

    _write_smoke_app("고난 중의 소망")
    try:
        at = AppTest.from_file(_SMOKE, default_timeout=60).run()
        assert at.exception in (None, []) or not list(at.exception)
        assert not at.expander  # 구절 없으면 패널 자체가 없어야 한다
    finally:
        _cleanup()


def test_panel_shows_expander_with_ref():
    from streamlit.testing.v1 import AppTest

    _write_smoke_app("로마서 5:1-5, 고난 중의 소망")
    try:
        at = AppTest.from_file(_SMOKE, default_timeout=60).run()
        assert at.exception in (None, []) or not list(at.exception)
        labels = [e.label for e in at.expander]
        assert any("로마서 5:1-5" in lbl and "본문 해설" in lbl for lbl in labels)
        # 버튼만 있고 아직 생성 안 함 → 안내 캡션
        assert any("별개" in c.value for c in at.caption)
    finally:
        _cleanup()


def test_panel_generates_badges_and_footnotes_on_click():
    from streamlit.testing.v1 import AppTest

    _write_smoke_app("요한복음 3:16 하나님의 사랑", with_material=True)
    try:
        at = AppTest.from_file(_SMOKE, default_timeout=90).run()
        btns = [b for b in at.button if "해설 생성" in b.label]
        assert btns, "해설 생성 버튼이 있어야 한다"
        btns[0].click().run()
        assert at.exception in (None, []) or not list(at.exception)
        md = " ".join(m.value for m in at.markdown)
        assert "①" in md and "②" in md          # [1][2] → 배지 치환
        assert "참고 자료 (내서재)" in md
        assert "요한복음 주석" in md              # 각주 서지
    finally:
        _cleanup()


def test_panel_no_material_shows_notice_only():
    from streamlit.testing.v1 import AppTest

    _write_smoke_app("스바냐 1:1 심판", with_material=False)
    try:
        at = AppTest.from_file(_SMOKE, default_timeout=60).run()
        btns = [b for b in at.button if "해설 생성" in b.label]
        assert btns
        btns[0].click().run()
        assert at.exception in (None, []) or not list(at.exception)
        infos = " ".join(i.value for i in at.info)
        assert "관련된 주석 자료가 없습니다" in infos
        md = " ".join(m.value for m in at.markdown)
        assert "참고 자료 (내서재)" not in md   # 생성/각주 없음
    finally:
        _cleanup()

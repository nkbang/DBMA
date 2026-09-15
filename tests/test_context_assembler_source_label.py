"""Regression test — core/retrieval.py::ContextAssembler.assemble() 서지 정보 주입.

[PM 정렬 감사 R3 / 선결 #3] 이전에는 LLM 문맥 블록이
`<context id="TSU-..." score="...">`뿐이라 저자·문헌·위치가 모델에 전혀
가지 않았다. 이제 각 블록 첫 줄에 "출처: ..." 를 넣는다. 정보가 하나도
없으면 그 줄을 넣지 않는다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import (
    ContextAssembler,
    ParsedQuery,
    RankedCandidate,
    _format_context_source_label,
)


def _cand(metadata, content="본문 내용입니다.", tsu_id="TSU-X-1", score=0.5):
    return RankedCandidate(tsu_id=tsu_id, content=content, metadata=metadata, final_score=score)


def _assemble(cands):
    block, _ = ContextAssembler().assemble(cands, ParsedQuery(original_query="q", intent="unknown"))
    return block


# ── _format_context_source_label ────────────────────────────────

def test_label_title_and_author():
    label = _format_context_source_label({"title": "로마서 주석", "author": "홍길동"})
    assert label == "로마서 주석 — 홍길동"


def test_label_does_not_duplicate_author_already_in_title():
    # NAE 경로: title이 "{book} by {author}"로 합성됨
    label = _format_context_source_label(
        {"title": "Complete Works by Andrew Fuller", "author": "Andrew Fuller"}
    )
    assert label == "Complete Works by Andrew Fuller"


def test_label_appends_page_and_paragraph():
    label = _format_context_source_label(
        {"title": "조직신학", "author": "김목사", "page": 42, "paragraph": 3}
    )
    assert label == "조직신학 — 김목사, p.42, 문단 3"


def test_label_includes_scripture_ref():
    label = _format_context_source_label({"author": "칼뱅"}, scripture_ref="ROM 8:1")
    assert "ROM 8:1" in label
    assert "칼뱅" in label


def test_label_ignores_placeholder_refs():
    assert _format_context_source_label({"title": "T"}, "Unknown reference") == "T"
    assert _format_context_source_label({"title": "T"}, "Unmapped passage") == "T"


def test_label_falls_back_to_source_file():
    assert _format_context_source_label({"source_file": "9. 로마서1.pdf"}) == "9. 로마서1.pdf"


def test_label_empty_when_no_metadata():
    assert _format_context_source_label({}) == ""
    assert _format_context_source_label({"author": "", "title": None}) == ""


def test_label_logos_location_from_provenance():
    label = _format_context_source_label(
        {"title": "W", "source_provenance": {"logos_location": "Rom 12:1"}}
    )
    assert label.endswith("Rom 12:1")


# ── assemble() 통합 ─────────────────────────────────────────────

def test_assemble_injects_source_line():
    block = _assemble([_cand({"title": "로마서 주석", "author": "홍길동", "page": 12})])
    assert "출처: 로마서 주석 — 홍길동, p.12" in block
    assert "본문 내용입니다." in block
    assert '<context id="TSU-X-1"' in block  # 래퍼 유지


def test_assemble_omits_source_line_when_no_biblio():
    block = _assemble([_cand({})])
    assert "출처:" not in block
    assert "본문 내용입니다." in block


def test_assemble_uses_verse_mapping_ref():
    md = {"author": "칼뱅", "verse_mapping": {"book_id": "ROM", "chapter": 8, "verse_start": 1}}
    block = _assemble([_cand(md)])
    assert "출처: 칼뱅, ROM 8:1" in block

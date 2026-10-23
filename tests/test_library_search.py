"""core/library_search.py — 메타데이터 + 본문 검색."""
import unicodedata

from core.library_search import parse_query, search_documents


def _doc(tmp_path, title, body):
    from core.utils import make_safe_stem
    (tmp_path / f"{make_safe_stem(title)}.md").write_text(body, encoding="utf-8")
    return {"title": title, "type": "pdf", "path": f"/raw/{title}", "modified": "2026-08-01"}


def test_parse_query():
    assert parse_query('은혜 "십자가의 도" -요한') == (["은혜", "십자가의 도"], ["요한"])


def test_content_and_metadata_search(tmp_path):
    a = _doc(tmp_path, "로마서.pdf", "하나님의 은혜는\n충분하다")
    b = _doc(tmp_path, "요한복음.pdf", "사랑 사랑 사랑")
    out = str(tmp_path)
    assert [h.doc["title"] for h in search_documents([a, b], "은혜", output_dir=out)] == ["로마서.pdf"]
    assert [h.doc["title"] for h in search_documents([a, b], "요한", output_dir=out)] == ["요한복음.pdf"]
    assert search_documents([a, b], "은혜 사랑", output_dir=out) == []
    assert [h.doc["title"] for h in search_documents([a, b], "-은혜", output_dir=out)] == ["요한복음.pdf"]


def test_phrase_spans_newline_and_snippet(tmp_path):
    a = _doc(tmp_path, "a.pdf", "그의\n은혜는 충분하다")
    hits = search_documents([a], '"그의 은혜"', output_dir=str(tmp_path))
    assert hits and "**그의 은혜**" in hits[0].snippets[0]


def test_nfd_query_and_title_ranks_first(tmp_path):
    a = _doc(tmp_path, "은혜론.pdf", "본문")
    b = _doc(tmp_path, "기타.pdf", "은혜 " * 3)
    q = unicodedata.normalize("NFD", "은혜")
    hits = search_documents([b, a], q, output_dir=str(tmp_path))
    assert [h.doc["title"] for h in hits] == ["은혜론.pdf", "기타.pdf"]

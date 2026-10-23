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


# ── 확장 기능: 저자·분류·성경 구절·번역·필터·이력 ─────────────────────────

import pytest

from core.library_authors import canonical_author, categorize
from core.library_search import (
    enrich_documents, excerpt, facet_counts, passes_filters, recent_searches,
    record_search, saved_searches, toggle_saved_search,
)


def _reg(**rows):
    """{source_file: record} — registry 직접 주입."""
    return {k: v for k, v in rows.items()}


def test_author_variants_collapse():
    keys = {canonical_author(a).key for a in [
        "Charles Haddon Spurgeon", "C. H. Spurgeon", "C.H. SURGEON",
        "Spurgeon, C. H. (Charles Haddon), 1834-1892", "C.H.Spurgeon"]}
    assert keys == {"spurgeon"}
    assert canonical_author("톰 라이트").key == "wright"
    assert canonical_author("").key == "unknown"
    assert canonical_author("Some Person, 1800-1850").display == "Some Person"


def test_categorize_refines_other():
    assert categorize("The Metropolitan Tabernacle Pulpit", "x.txt", "기타") == "설교집"
    assert categorize("Expositions of holy scripture /", "x.txt", "기타") == "강해·주석"
    assert categorize("Zzz", "zzz.txt", "기타") == "기타"
    assert categorize("Zzz", "zzz.txt", "주석") == "주석"


def test_registry_fields_searchable_and_filters(tmp_path):
    a = _doc(tmp_path, "Spurgeon_A.txt", "plain body")
    b = _doc(tmp_path, "Other_B.txt", "plain body")
    reg = {
        "Spurgeon_A.txt": {"title": "Sermons A", "author": "C.H. SURGEON", "language": "en",
                           "doc_type": "기타", "chunk_count": 5, "noise_score": 40},
        "Other_B.txt": {"title": "Book B", "author": "Jane Roe", "language": "ko"},
    }
    out = str(tmp_path)
    r = search_documents([a, b], "스펄전", output_dir=out, registry=reg)
    assert [h.info.title for h in r] == ["Sermons A"] and r[0].info.low_quality
    assert [h.info.title for h in search_documents([a, b], "author:jane", output_dir=out, registry=reg)] == ["Book B"]
    assert [h.info.title for h in search_documents([a, b], "lang:ko body", output_dir=out, registry=reg)] == ["Book B"]
    infos = enrich_documents([a, b], reg)
    assert [i.title for i in infos if passes_filters(i, authors=["spurgeon"])] == ["Sermons A"]
    assert {k for k, _, _ in facet_counts(infos)["language"]} == {"en", "ko"}


@pytest.mark.parametrize("query", ["롬 8:28", "Romans viii. 28", "로마서 8장 28절", "Rom 8:28"])
def test_scripture_reference_notations(tmp_path, query):
    a = _doc(tmp_path, "en.txt", "We know that all things work together. — Romans viii.\n28. Good.")
    b = _doc(tmp_path, "ko.txt", "모든 것이 합력하여 (롬 8:28) 선을 이룬다")
    c = _doc(tmp_path, "no.txt", "Romans viii. 29 and 1 John viii. 28 and Romans 18:28 here")
    got = {h.info.title for h in search_documents([a, b, c], query, output_dir=str(tmp_path), registry={})}
    assert "no.txt" not in got
    assert got and got <= {"en.txt", "ko.txt"}
    hit = search_documents([a], "롬 8:28", output_dir=str(tmp_path), registry={})[0]
    assert hit.passages[0].kind == "scripture" and "**" in hit.passages[0].snippet


def test_korean_query_finds_english_text(tmp_path):
    a = _doc(tmp_path, "en.txt", "The grace of God is free.")
    hits = search_documents([a], "은혜", output_dir=str(tmp_path), registry={})
    assert len(hits) == 1 and hits[0].via and "grace" in hits[0].via[0]
    assert "**grace**" in hits[0].snippets[0]


def test_location_label_and_excerpt(tmp_path):
    body = "SERMON XII.\n" + "filler " * 200 + "the needle here " + "filler " * 200
    a = _doc(tmp_path, "s.txt", body)
    hit = search_documents([a], "needle", output_dir=str(tmp_path), registry={})[0]
    assert "SERMON XII." in hit.passages[0].location and "%" in hit.passages[0].location
    text, start, end = excerpt(a, hit.passages[0].offset, radius=300, output_dir=str(tmp_path), terms=hit.terms)
    assert "**needle**" in text and start < hit.passages[0].offset < end


def test_history_and_saved(tmp_path):
    p = tmp_path / "prefs.json"
    for q in ["a", "b", "a"]:
        record_search(q, p)
    assert recent_searches(p) == ["a", "b"]
    assert toggle_saved_search("x y", p) is True and saved_searches(p) == ["x y"]
    assert toggle_saved_search("x y", p) is False and saved_searches(p) == []

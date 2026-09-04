"""tests/test_footnote_citation.py - 풋노트 인용(Zotero 벤치마킹) 단위 테스트.

_build_footnote_citation() 검증:
    - 최초 인용: 번호 1, 전체 서지
    - 연속 재인용(같은 문서 바로 다음): "Ibid."
    - 비연속 재인용: 약식 서지
    - 저자/연도 없는 경우의 폴백
"""

from core.document_detail import DocumentDetail
from ui.pages.research import _build_footnote_citation, _extract_citation_year


def _detail(**overrides) -> DocumentDetail:
    base = dict(
        document_id="doc-1",
        title="조직신학 개론",
        document_type="단행본",
        source_path="/data/output/doc1.md",
        author="루이스 벌코프",
        created_at="2026-07-30T10:00:00",
    )
    base.update(overrides)
    return DocumentDetail(**base)


class TestExtractCitationYear:
    def test_valid_iso_date(self):
        assert _extract_citation_year("2026-07-30T10:00:00") == "2026"

    def test_none(self):
        assert _extract_citation_year(None) is None

    def test_non_digit_prefix(self):
        assert _extract_citation_year("알수없음") is None

    def test_too_short(self):
        assert _extract_citation_year("20") is None


class TestBuildFootnoteCitation:
    def test_first_citation_full_form(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail = _detail()
        result = _build_footnote_citation(detail, "doc1.md", "doc-1")
        assert result == "1. 루이스 벌코프, *조직신학 개론* (단행본, 2026)."
        assert session_state["research_footnotes"] == ["doc-1"]

    def test_consecutive_recitation_uses_ibid(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail = _detail()
        _build_footnote_citation(detail, "doc1.md", "doc-1")
        result = _build_footnote_citation(detail, "doc1.md", "doc-1")
        assert result == "2. Ibid."

    def test_non_consecutive_recitation_uses_short_form(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail_a = _detail(document_id="doc-1")
        detail_b = _detail(document_id="doc-2", title="구약신학", author="게할더스 보스")
        _build_footnote_citation(detail_a, "doc1.md", "doc-1")
        _build_footnote_citation(detail_b, "doc2.md", "doc-2")
        result = _build_footnote_citation(detail_a, "doc1.md", "doc-1")
        assert result == "3. 루이스 벌코프, *조직신학 개론*."

    def test_footnote_numbers_increment_across_session(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail = _detail()
        first = _build_footnote_citation(detail, "doc1.md", "doc-1")
        second = _build_footnote_citation(detail, "doc1.md", "doc-1")
        assert first.startswith("1.")
        assert second.startswith("2.")

    def test_missing_author_falls_back_to_title_only(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail = _detail(author=None)
        result = _build_footnote_citation(detail, "doc1.md", "doc-1")
        assert result == "1. *조직신학 개론* (단행본, 2026)."

    def test_missing_title_falls_back_to_source_file(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        detail = _detail(title=None, author=None, document_type=None, created_at=None)
        result = _build_footnote_citation(detail, "raw_doc.md", "doc-1")
        assert result == "1. *raw_doc.md*."

    def test_long_title_truncated_in_short_form(self, monkeypatch):
        session_state = {}
        monkeypatch.setattr("ui.pages.research.st.session_state", session_state)
        long_title = "매우 길게 작성된 신학 서적의 전체 제목 예시입니다 계속"
        detail_a = _detail(document_id="doc-1", title=long_title)
        detail_b = _detail(document_id="doc-2", title="다른 책")
        _build_footnote_citation(detail_a, "doc1.md", "doc-1")
        _build_footnote_citation(detail_b, "doc2.md", "doc-2")
        result = _build_footnote_citation(detail_a, "doc1.md", "doc-1")
        assert result.endswith("*.")
        assert "…" in result

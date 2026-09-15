"""tests/test_extractors_epub_html_metadata.py — EPUB/HTML 내장 메타데이터 추출 회귀 방지.

실측 근거(2026-09-15): core.extractors.extract_text_from_file()이 PDF(docinfo)와
DOCX(core_properties)에서만 title/author를 읽고 EPUB·HTML 경로에는 그 호출이
없었다. 그 결과 dc:title/dc:creator를 실제로 담고 있는 EPUB도 registry·TSU에
title=None, author=None으로 등록됐다 — 인용 표기가 비는 원인
(docs/DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md §5.1).

재현 사례: "매튜 풀 청교도 성경주석 14 마태복음.epub"은
dc:title="매튜 풀 청교도 성경주석 14 : 마태복음", dc:creator="매튜 풀"을
담고 있으나 파이프라인이 둘 다 버렸다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.extractors import (  # noqa: E402
    _extract_epub_title_author,
    _extract_html_title_author,
    extract_text_from_file,
)


def _write_epub(path: Path, title: str | None, author: str | None) -> Path:
    """최소 구성 EPUB을 만든다(본문 1장 + 선택적 DC 메타데이터)."""
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("test-id")
    if title is not None:
        book.set_title(title)
    if author is not None:
        book.add_author(author)
    chapter = epub.EpubHtml(title="c1", file_name="c1.xhtml", lang="ko")
    chapter.content = "<html><body><p>본문입니다.</p></body></html>"
    book.add_item(chapter)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)
    return path


def test_epub_embedded_title_and_author_are_extracted(tmp_path):
    src = _write_epub(tmp_path / "book.epub", "청교도 성경주석 : 마태복음", "매튜 풀")

    title, author = _extract_epub_title_author(str(src))

    assert title == "청교도 성경주석 : 마태복음"
    assert author == "매튜 풀"


def test_epub_metadata_reaches_extract_text_from_file(tmp_path):
    """단위 함수만이 아니라 dispatch를 통과해야 한다 — 누락됐던 지점이 여기다."""
    src = _write_epub(tmp_path / "book.epub", "Lectures to My Students", "C. H. Spurgeon")

    result = extract_text_from_file(str(src))

    assert result["title"] == "Lectures to My Students"
    assert result["author"] == "C. H. Spurgeon"
    assert result["source_type"] == "epub"


def test_epub_without_metadata_returns_none_not_guess(tmp_path):
    """메타데이터가 없으면 파일명에서 추론하지 않는다 (SPRINT17-Phase5-C2 M2-a)."""
    src = _write_epub(tmp_path / "추론하면_안되는_제목.epub", None, None)

    title, author = _extract_epub_title_author(str(src))

    assert title is None
    assert author is None


def test_epub_unreadable_file_degrades_to_none(tmp_path):
    """깨진 파일이 예외를 올려 처리 전체를 중단시키면 안 된다."""
    src = tmp_path / "broken.epub"
    src.write_bytes(b"not a real epub")

    assert _extract_epub_title_author(str(src)) == (None, None)


def test_html_title_and_author_meta_are_extracted(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(
        '<html><head><title>설교자의 기도</title>'
        '<meta name="Author" content="스펄전"></head>'
        "<body><h1>다른 제목</h1><p>본문</p></body></html>",
        encoding="utf-8",
    )

    title, author = _extract_html_title_author(str(src))

    # <h1>이 아니라 <title>을 신뢰한다 — 문서가 선언한 메타데이터만 읽는다.
    assert title == "설교자의 기도"
    assert author == "스펄전"


def test_html_metadata_reaches_extract_text_from_file(tmp_path):
    src = tmp_path / "page.html"
    src.write_text(
        "<html><head><title>Till He Come</title></head><body><p>x</p></body></html>",
        encoding="utf-8",
    )

    result = extract_text_from_file(str(src))

    assert result["title"] == "Till He Come"
    assert result["author"] is None


@pytest.mark.parametrize("ext,content", [("txt", "본문"), ("md", "# 제목\n본문")])
def test_plaintext_formats_still_have_no_metadata(tmp_path, ext, content):
    """txt/md는 내장 메타데이터가 없다 — None이 정상이며 파일명 추론은 금지."""
    src = tmp_path / f"스펄전_설교집.{ext}"
    src.write_text(content, encoding="utf-8")

    result = extract_text_from_file(str(src))

    assert result["title"] is None
    assert result["author"] is None

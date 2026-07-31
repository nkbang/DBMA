from unittest.mock import MagicMock, patch

from NAE.collectors.archive_org import filters, metadata as meta_mod
from NAE.collectors.archive_org.search import SearchResult


def _mock_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.side_effect = None
    return resp


def test_fetch_item_metadata_parses_fields():
    payload = {
        "metadata": {
            "title": "Body of Divinity",
            "creator": "John Gill",
            "publisher": "Some Press",
            "year": "1770",
            "language": "English",
            "subject": ["Baptist", "Theology"],
            "collection": ["americana"],
            "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        },
        "item": {"downloads": 100},
        "files": [
            {"name": "book.pdf", "format": "Text PDF", "size": "1000"},
            {"name": "book_djvu.txt", "format": "DjVuTXT", "size": "200"},
        ],
    }
    with patch("NAE.collectors.archive_org.metadata.requests.get", return_value=_mock_response(payload)):
        item = meta_mod.fetch_item_metadata("john_gill_body_divinity")

    assert item.title == "Body of Divinity"
    assert item.subjects == ["Baptist", "Theology"]
    assert len(item.files) == 2


def test_select_download_files_prefers_pdf():
    item = meta_mod.ItemMetadata(
        identifier="id1",
        files=[
            meta_mod.FileEntry(name="book.pdf", format="text pdf"),
            meta_mod.FileEntry(name="book.epub", format="epub"),
            meta_mod.FileEntry(name="book_djvu.txt", format="djvutxt"),
        ],
    )
    chosen = meta_mod.select_download_files(item)
    assert chosen["primary"].name == "book.pdf"
    assert chosen["ocr_txt"].name == "book_djvu.txt"


def test_build_metadata_dict_contains_required_fields():
    item = meta_mod.ItemMetadata(identifier="id1", title="T", creator="C", year="1900")
    entry = meta_mod.build_metadata_dict(
        item, license_ok="public_domain", download_url="https://x", checksum="abc", downloaded=True,
    )
    for key in ["identifier", "title", "creator", "publisher", "year", "language",
                "subjects", "downloads", "collection", "license", "source_url",
                "download_url", "checksum", "downloaded"]:
        assert key in entry


def test_filters_reject_in_copyright():
    r = SearchResult(identifier="x", mediatype="texts", language="eng",
                      licenseurl="https://archive.org/details/in-copyright")
    ok, reason = filters.passes_all_filters(r)
    assert ok is False
    assert "license" in reason


def test_filters_accept_public_domain():
    r = SearchResult(identifier="x", mediatype="texts", language="eng",
                      licenseurl="https://creativecommons.org/publicdomain/mark/1.0/")
    ok, reason = filters.passes_all_filters(r)
    assert ok is True


def test_filters_reject_video_mediatype():
    r = SearchResult(identifier="x", mediatype="movies", language="eng",
                      licenseurl="https://creativecommons.org/publicdomain/mark/1.0/")
    ok, reason = filters.passes_all_filters(r)
    assert ok is False
    assert "mediatype" in reason


def test_is_public_domain_missing_licenseurl_but_pre_cutoff_year():
    ok, reason = filters.is_public_domain(licenseurl="", rights="", year="1770")
    assert ok is True
    assert reason.startswith("year_cutoff")


def test_is_public_domain_missing_licenseurl_and_recent_year_is_unknown():
    ok, reason = filters.is_public_domain(licenseurl="", rights="", year="1990")
    assert ok is False
    assert reason == "unknown"


def test_is_public_domain_rights_text_overrides_missing_license():
    ok, reason = filters.is_public_domain(licenseurl="", rights="Public domain in the United States.", year="")
    assert ok is True
    assert reason.startswith("rights_public_domain")


def test_is_public_domain_disallowed_license_wins_over_year():
    ok, reason = filters.is_public_domain(
        licenseurl="https://archive.org/details/in-copyright", year="1800",
    )
    assert ok is False
    assert reason.startswith("licenseurl_disallowed")

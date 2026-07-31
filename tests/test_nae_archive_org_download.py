import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from NAE.collectors.archive_org import downloader


def test_sha256_of_file(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert downloader.sha256_of_file(f) == expected


def test_download_file_success(tmp_path: Path):
    content = b"pdf-bytes"
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.side_effect = None
    resp.iter_content.return_value = [content]
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    dest = tmp_path / "books" / "id1" / "original.pdf"
    with patch("NAE.collectors.archive_org.downloader.requests.get", return_value=resp):
        ok, checksum = downloader.download_file("https://archive.org/download/id1/f.pdf", dest)

    assert ok is True
    assert dest.exists()
    assert checksum == hashlib.sha256(content).hexdigest()


def test_download_file_404_fails_after_retries(tmp_path: Path):
    resp = MagicMock()
    resp.status_code = 404
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False

    dest = tmp_path / "books" / "id2" / "original.pdf"
    with patch("NAE.collectors.archive_org.downloader.requests.get", return_value=resp), \
         patch("NAE.collectors.archive_org.downloader.time.sleep"):
        ok, err = downloader.download_file("https://archive.org/download/id2/f.pdf", dest, retry=2)

    assert ok is False
    assert "404" in err
    assert not dest.exists()


def test_verify_checksum(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"data")
    expected = hashlib.sha256(b"data").hexdigest()
    assert downloader.verify_checksum(f, expected) is True
    assert downloader.verify_checksum(f, "wrong") is False
    assert downloader.verify_checksum(tmp_path / "missing.txt", expected) is False

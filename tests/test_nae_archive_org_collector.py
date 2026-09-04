import json
from pathlib import Path

from NAE.collectors.archive_org import collector, config, downloader


def test_is_locally_intact_true_when_files_and_checksum_match(tmp_path: Path, monkeypatch):
    download_root = tmp_path / "raw"
    item_dir = download_root / "books" / "id1"
    item_dir.mkdir(parents=True)
    (item_dir / "metadata.json").write_text("{}", encoding="utf-8")
    original = item_dir / "original.pdf"
    original.write_bytes(b"content")
    checksum = downloader.sha256_of_file(original)

    entry = {"checksum": checksum}
    assert collector.is_locally_intact("id1", entry, download_root) is True


def test_is_locally_intact_false_when_checksum_mismatch(tmp_path: Path):
    download_root = tmp_path / "raw"
    item_dir = download_root / "books" / "id1"
    item_dir.mkdir(parents=True)
    (item_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (item_dir / "original.pdf").write_bytes(b"content")

    entry = {"checksum": "deadbeef"}
    assert collector.is_locally_intact("id1", entry, download_root) is False


def test_is_locally_intact_false_when_files_missing(tmp_path: Path):
    download_root = tmp_path / "raw"
    entry = {"checksum": "deadbeef"}
    assert collector.is_locally_intact("missing_id", entry, download_root) is False


def test_write_manifest_creates_item_and_central_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "MANIFESTS_ROOT", tmp_path / "manifests")
    item_dir = tmp_path / "raw" / "books" / "id1"
    item_dir.mkdir(parents=True)
    (item_dir / "original.pdf").write_bytes(b"x")
    entry = {"checksum": "abc123"}

    collector.write_manifest(item_dir, identifier="id1", entry=entry)

    item_manifest = json.loads((item_dir / "manifest.json").read_text(encoding="utf-8"))
    central_manifest = json.loads((tmp_path / "manifests" / "id1.json").read_text(encoding="utf-8"))
    assert item_manifest["identifier"] == "id1"
    assert item_manifest["sha256"] == "abc123"
    assert item_manifest["collector_version"] == config.COLLECTOR_VERSION
    assert central_manifest == item_manifest


def test_write_report_creates_latest_and_timestamped(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_ROOT", tmp_path / "reports")
    summary = {"search_results": 5, "downloaded": 2, "skipped_duplicate": 0,
               "skipped_license": 3, "failed": 0, "failures": [],
               "elapsed_seconds": 1.0, "average_per_sec": 2.0}
    path = collector.write_report(summary, ["Baptist"])
    assert path.exists()
    latest = json.loads((tmp_path / "reports" / "latest.json").read_text(encoding="utf-8"))
    assert latest["downloaded"] == 2
    assert latest["collector_version"] == config.COLLECTOR_VERSION

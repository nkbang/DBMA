import json
from pathlib import Path

from NAE.pipeline.canonical import pipeline


def _write_ocr_item(tmp_path: Path, identifier: str, ocr_text: str) -> Path:
    item_dir = tmp_path / "raw" / "books" / identifier
    item_dir.mkdir(parents=True)
    (item_dir / "ocr.txt").write_text(ocr_text, encoding="utf-8")
    return item_dir


CLASSIC_TYPEFACE_OCR = (
    "THE WORKS OF JOHN GILL\n"
    "11\n"
    "\x0c"
    "THE WORKS OF JOHN GILL\n"
    "12\n"
    "\x0c"
    "THE WORKS OF JOHN GILL\n"
    "\n"
    "CHAPTER ONE\n"
    "\n"
    "The doc-\ntrine of grace is central to the whole\n"
    "of Scripture, as it is written in Rom. 3:24,\n"
    "for we are justified freely by his grace.\n"
    "\n"
    "~~~~~~~~~~\n"
    "\n"
    "1. See Calvin, Institutes, Book III, chap. 21.\n"
    "13\n"
)


def test_normalize_item_produces_canonical_output(tmp_path: Path):
    item_dir = _write_ocr_item(tmp_path, "john_gill_works", CLASSIC_TYPEFACE_OCR)
    result = pipeline.normalize_item(item_dir, identifier="john_gill_works")

    assert result["status"] == "ok"
    assert "doctrine of grace" in result["canonical_text"]
    assert "~~~~~~~~~~" not in result["canonical_text"]
    assert "THE WORKS OF JOHN GILL" not in result["canonical_text"]

    cj = result["canonical_json"]
    assert cj["identifier"] == "john_gill_works"
    assert cj["source"] == "ocr"
    assert len(cj["footnotes"]) == 1
    assert "Calvin" in cj["footnotes"][0]["text"]
    assert any("Rom. 3:24" in ref or "3:24" in ref for ref in cj["scripture_references"])

    report = result["report"]
    assert report["status"] == "ok"
    assert report["page_count"] == 3
    assert report["headers_footers_removed"] >= 3
    assert report["page_numbers_removed"] == 3
    assert report["footnotes_extracted"] == 1


def test_normalize_item_falls_back_when_ocr_txt_is_binary_garbage(tmp_path: Path):
    item_dir = tmp_path / "raw" / "books" / "corrupt_ocr_item"
    item_dir.mkdir(parents=True)
    (item_dir / "ocr.txt").write_bytes(bytes(range(256)) * 20)  # looks like compressed/binary junk
    result = pipeline.normalize_item(item_dir, identifier="corrupt_ocr_item")
    assert result["status"] == "failed"
    assert result["report"]["reason"] == "no_extractable_source"


def test_normalize_item_fails_gracefully_without_source(tmp_path: Path):
    item_dir = tmp_path / "raw" / "books" / "empty_item"
    item_dir.mkdir(parents=True)
    result = pipeline.normalize_item(item_dir, identifier="empty_item")
    assert result["status"] == "failed"
    assert result["report"]["reason"] == "no_extractable_source"


def test_write_canonical_output_creates_all_three_files(tmp_path: Path):
    item_dir = _write_ocr_item(tmp_path, "sample_item", CLASSIC_TYPEFACE_OCR)
    result = pipeline.normalize_item(item_dir, identifier="sample_item")

    out_dir = tmp_path / "canonical" / "sample_item"
    pipeline.write_canonical_output(result, out_dir)

    assert (out_dir / "canonical.txt").exists()
    assert (out_dir / "canonical.json").exists()
    assert (out_dir / "normalize_report.json").exists()

    canonical_json = json.loads((out_dir / "canonical.json").read_text(encoding="utf-8"))
    assert canonical_json["paragraphs"]
    assert all("page_start" in p and "page_end" in p for p in canonical_json["paragraphs"])


def test_process_identifier_finds_item_across_categories(tmp_path: Path):
    raw_root = tmp_path / "raw"
    _write_ocr_item(tmp_path, "tract_item", CLASSIC_TYPEFACE_OCR)
    (raw_root / "tracts").mkdir(parents=True, exist_ok=True)
    (raw_root / "tracts" / "tract_item2").mkdir(parents=True, exist_ok=True)
    (raw_root / "tracts" / "tract_item2" / "ocr.txt").write_text(CLASSIC_TYPEFACE_OCR, encoding="utf-8")

    canonical_root = tmp_path / "canonical"
    result = pipeline.process_identifier("tract_item2", raw_root=raw_root, canonical_root=canonical_root)

    assert result["status"] == "ok"
    assert (canonical_root / "tract_item2" / "canonical.txt").exists()


def test_process_identifier_reports_missing_item(tmp_path: Path):
    raw_root = tmp_path / "raw"
    raw_root.mkdir(parents=True)
    result = pipeline.process_identifier("does_not_exist", raw_root=raw_root, canonical_root=tmp_path / "canonical")
    assert result["status"] == "failed"
    assert result["report"]["reason"] == "raw_item_not_found"

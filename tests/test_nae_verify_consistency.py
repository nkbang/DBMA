import json
from pathlib import Path

from NAE.pipeline.verify import consistency


def _setup_canonical(tmp_path: Path, identifier: str) -> Path:
    canonical_root = tmp_path / "canonical"
    item_dir = canonical_root / identifier
    item_dir.mkdir(parents=True)
    canonical_json = {
        "paragraphs": [
            {"index": 3, "text": "As John Gill argued in his commentary.", "page_start": 5},
        ],
        "footnotes": [{"page": 5, "text": "See Calvin, Institutes III."}],
    }
    with open(item_dir / "canonical.json", "w", encoding="utf-8") as fh:
        json.dump(canonical_json, fh)
    return canonical_root


def test_verify_citations_matches_footnote(tmp_path: Path):
    canonical_root = _setup_canonical(tmp_path, "gill_item")
    record = {"identifier": "gill_item", "page": 5, "paragraph": 3,
              "citations": ["See Calvin, Institutes III."]}
    result = consistency.verify_citations(record, canonical_root=canonical_root)
    assert result["See Calvin, Institutes III."] is True


def test_verify_citations_matches_author_mention(tmp_path: Path):
    canonical_root = _setup_canonical(tmp_path, "gill_item")
    record = {"identifier": "gill_item", "page": 5, "paragraph": 3, "citations": ["John Gill"]}
    result = consistency.verify_citations(record, canonical_root=canonical_root)
    assert result["John Gill"] is True


def test_verify_citations_unverified_citation(tmp_path: Path):
    canonical_root = _setup_canonical(tmp_path, "gill_item")
    record = {"identifier": "gill_item", "page": 5, "paragraph": 3, "citations": ["Made up citation"]}
    result = consistency.verify_citations(record, canonical_root=canonical_root)
    assert result["Made up citation"] is False


def test_verify_citations_no_canonical_file_returns_false(tmp_path: Path):
    canonical_root = tmp_path / "canonical"
    canonical_root.mkdir()
    record = {"identifier": "missing_item", "page": 5, "paragraph": 3, "citations": ["X"]}
    result = consistency.verify_citations(record, canonical_root=canonical_root)
    assert result["X"] is False


def test_verify_citations_empty_returns_empty_dict(tmp_path: Path):
    canonical_root = tmp_path / "canonical"
    canonical_root.mkdir()
    record = {"identifier": "x", "citations": []}
    assert consistency.verify_citations(record, canonical_root=canonical_root) == {}

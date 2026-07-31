import json
from pathlib import Path

from NAE.pipeline.tsu import parser


def _setup_item(tmp_path: Path, identifier: str) -> tuple[Path, Path]:
    canonical_root = tmp_path / "canonical"
    raw_root = tmp_path / "raw"

    canonical_dir = canonical_root / identifier
    canonical_dir.mkdir(parents=True)
    canonical_json = {
        "identifier": identifier,
        "pipeline_version": "2.0.0",
        "paragraphs": [
            {
                "index": 0,
                "type": "heading",
                "text": "OF BAPTISM",
                "page_start": 1,
                "page_end": 1,
                "sentences": [],
                "scripture_references": [],
            },
            {
                "index": 1,
                "type": "prose",
                "text": "Believer's baptism follows a profession of faith. This is clearly seen in Acts 2:41.",
                "page_start": 1,
                "page_end": 1,
                "sentences": [
                    {"sentence_index": 0, "text": "Believer's baptism follows a profession of faith."},
                    {"sentence_index": 1, "text": "This is clearly seen in Acts 2:41."},
                ],
                "scripture_references": [{"original": "Acts 2:41", "canonical": "Acts 2:41"}],
            },
            {
                "index": 2,
                "type": "prose",
                "text": "See.",
                "page_start": 1,
                "page_end": 1,
                "sentences": [{"sentence_index": 0, "text": "See."}],
                "scripture_references": [],
            },
        ],
        "footnotes": [{"page": 1, "text": "See Calvin, Institutes III."}],
        "scripture_references": ["Acts 2:41"],
    }
    with open(canonical_dir / "canonical.json", "w", encoding="utf-8") as fh:
        json.dump(canonical_json, fh)

    raw_dir = raw_root / "books" / identifier
    raw_dir.mkdir(parents=True)
    with open(raw_dir / "metadata.json", "w", encoding="utf-8") as fh:
        json.dump({"title": "Body of Divinity", "creator": "John Gill", "collector_version": "1.1.0"}, fh)

    return canonical_root, raw_root


def test_build_candidates_skips_non_prose_and_short_sentences(tmp_path: Path):
    canonical_root, raw_root = _setup_item(tmp_path, "gill_body_of_divinity")
    candidates = parser.build_candidates("gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root)

    texts = [c.text for c in candidates]
    assert "OF BAPTISM" not in texts  # heading paragraph excluded
    assert "See." not in texts  # too short
    assert "Believer's baptism follows a profession of faith." in texts


def test_build_candidates_attaches_book_author_and_context(tmp_path: Path):
    canonical_root, raw_root = _setup_item(tmp_path, "gill_body_of_divinity")
    candidates = parser.build_candidates("gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root)

    first = candidates[0]
    assert first.book == "Body of Divinity"
    assert first.author == "John Gill"
    assert first.context_after == "This is clearly seen in Acts 2:41."
    assert first.collector_version == "1.1.0"
    assert first.canonical_version == "2.0.0"

    second = candidates[1]
    assert second.context_before == "Believer's baptism follows a profession of faith."
    assert "Acts 2:41" in second.candidate_scriptures


def test_build_candidates_includes_footnote_and_author_citations(tmp_path: Path):
    canonical_root, raw_root = _setup_item(tmp_path, "gill_body_of_divinity")
    candidates = parser.build_candidates("gill_body_of_divinity", canonical_root=canonical_root, raw_root=raw_root)
    assert any("See Calvin, Institutes III." in c.candidate_citations for c in candidates)


def test_build_candidates_missing_canonical_returns_empty(tmp_path: Path):
    canonical_root = tmp_path / "canonical"
    raw_root = tmp_path / "raw"
    canonical_root.mkdir()
    raw_root.mkdir()
    candidates = parser.build_candidates("does_not_exist", canonical_root=canonical_root, raw_root=raw_root)
    assert candidates == []

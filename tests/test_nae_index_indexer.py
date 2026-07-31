import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from NAE.pipeline.index import indexer


def _write_records(tmp_path: Path, identifier: str, records: list[dict], filename: str = "tsu.json") -> Path:
    tsu_root = tmp_path / "tsu"
    out_dir = tsu_root / identifier
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / filename, "w", encoding="utf-8") as fh:
        json.dump(records, fh)
    return tsu_root


@patch("NAE.pipeline.index.indexer.qdrant_store.upsert_points")
@patch("NAE.pipeline.index.indexer.qdrant_store.ensure_collection")
@patch("NAE.pipeline.index.indexer.qdrant_store.get_client")
@patch("NAE.pipeline.index.indexer.embed_client.embed_text")
def test_index_identifier_indexes_claim_records(mock_embed, mock_get_client, mock_ensure, mock_upsert, tmp_path: Path):
    mock_embed.return_value = [0.1] * 1024
    mock_get_client.return_value = MagicMock()

    records = [
        {"id": "TSU-0000001", "claim": "A claim.", "book": "B", "page": 1, "scriptures": [], "duplicate_of": None},
    ]
    tsu_root = _write_records(tmp_path, "item1", records)

    report = indexer.index_identifier("item1", tsu_root=tsu_root)

    assert report["indexed"] == 1
    assert report["skipped_duplicate"] == 0
    assert report["embedding_errors"] == 0
    mock_upsert.assert_called_once()
    assert (tsu_root / "item1" / "index_report.json").exists()


@patch("NAE.pipeline.index.indexer.qdrant_store.upsert_points")
@patch("NAE.pipeline.index.indexer.qdrant_store.ensure_collection")
@patch("NAE.pipeline.index.indexer.qdrant_store.get_client")
@patch("NAE.pipeline.index.indexer.embed_client.embed_text")
def test_index_identifier_skips_duplicates(mock_embed, mock_get_client, mock_ensure, mock_upsert, tmp_path: Path):
    mock_embed.return_value = [0.1] * 1024
    mock_get_client.return_value = MagicMock()

    records = [
        {"id": "TSU-0000001", "claim": "A claim.", "book": "B", "page": 1, "scriptures": [], "duplicate_of": None},
        {"id": "TSU-0000002", "claim": "A duplicate claim.", "book": "B", "page": 2, "scriptures": [],
         "duplicate_of": "TSU-0000001"},
    ]
    tsu_root = _write_records(tmp_path, "item1", records)

    report = indexer.index_identifier("item1", tsu_root=tsu_root)

    assert report["indexed"] == 1
    assert report["skipped_duplicate"] == 1


@patch("NAE.pipeline.index.indexer.qdrant_store.upsert_points")
@patch("NAE.pipeline.index.indexer.qdrant_store.ensure_collection")
@patch("NAE.pipeline.index.indexer.qdrant_store.get_client")
@patch("NAE.pipeline.index.indexer.embed_client.embed_text")
def test_index_identifier_counts_embedding_errors(mock_embed, mock_get_client, mock_ensure, mock_upsert, tmp_path: Path):
    mock_embed.return_value = None
    mock_get_client.return_value = MagicMock()

    records = [
        {"id": "TSU-0000001", "claim": "A claim.", "book": "B", "page": 1, "scriptures": [], "duplicate_of": None},
    ]
    tsu_root = _write_records(tmp_path, "item1", records)

    report = indexer.index_identifier("item1", tsu_root=tsu_root)

    assert report["indexed"] == 0
    assert report["embedding_errors"] == 1


@patch("NAE.pipeline.index.indexer.qdrant_store.upsert_points")
@patch("NAE.pipeline.index.indexer.qdrant_store.ensure_collection")
@patch("NAE.pipeline.index.indexer.qdrant_store.get_client")
def test_index_identifier_prefers_verified_over_plain(mock_get_client, mock_ensure, mock_upsert, tmp_path: Path):
    mock_get_client.return_value = MagicMock()
    plain = [{"id": "TSU-0000001", "claim": "Plain.", "book": "B", "page": 1, "scriptures": []}]
    verified = [{"id": "TSU-0000001", "claim": "Verified.", "book": "B", "page": 1, "scriptures": [],
                 "overall_score": 0.9, "duplicate_of": None}]

    tsu_root = _write_records(tmp_path, "item1", plain, filename="tsu.json")
    _write_records(tmp_path, "item1", verified, filename="tsu_verified.json")

    records = indexer.load_records("item1", tsu_root=tsu_root)
    assert records[0]["claim"] == "Verified."

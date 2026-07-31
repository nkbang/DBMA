"""Phase 4 - TSU -> Embedding -> Qdrant orchestrator.

Prefers tsu_verified.json (Phase 3.5 output, carries score/duplicate_of) and
falls back to tsu.json if verification hasn't been run yet for an item.
Records flagged as duplicate_of another record are skipped at index time
(the canonical record is indexed instead) so retrieval results aren't
polluted with near-identical claims.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import hashing
from NAE.pipeline.tsu import config as tsu_config
from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION

from . import config, qdrant_store

logger = logging.getLogger("nae.index.indexer")


def load_records(identifier: str, tsu_root: Path = tsu_config.TSU_ROOT) -> list[dict]:
    verified_path = tsu_root / identifier / "tsu_verified.json"
    plain_path = tsu_root / identifier / "tsu.json"
    path = verified_path if verified_path.exists() else plain_path
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def index_identifier(identifier: str, *, tsu_root: Path = tsu_config.TSU_ROOT,
                      qdrant_url: str = config.QDRANT_URL) -> dict[str, Any]:
    records = load_records(identifier, tsu_root)

    client = qdrant_store.get_client(qdrant_url)
    qdrant_store.ensure_collection(client)

    indexed = 0
    skipped_duplicate = 0
    embedding_errors = 0
    points = []

    for record in records:
        if record.get("duplicate_of"):
            skipped_duplicate += 1
            continue
        claim_text = record.get("claim")
        if not claim_text:
            continue

        content_hash = hashing.tsu_hash(
            schema_version=record.get("tsu_schema_version", TSU_SCHEMA_VERSION),
            claim=claim_text, book=record.get("book", ""),
            page=record.get("page", ""), scriptures=record.get("scriptures", []),
        )
        vector = embed_client.embed_text(claim_text, content_hash=content_hash)
        if vector is None:
            embedding_errors += 1
            continue

        points.append(qdrant_store.build_point(record, vector))
        indexed += 1

    qdrant_store.upsert_points(client, points)

    report = {
        "identifier": identifier,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collection": config.COLLECTION_NAME,
        "records_total": len(records),
        "indexed": indexed,
        "skipped_duplicate": skipped_duplicate,
        "embedding_errors": embedding_errors,
    }

    out_dir = tsu_root / identifier
    with open(out_dir / "index_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    return report


def index_all(*, tsu_root: Path = tsu_config.TSU_ROOT, qdrant_url: str = config.QDRANT_URL) -> dict[str, Any]:
    if not tsu_root.exists():
        return {"processed": 0, "indexed": 0, "identifiers": []}

    identifiers = [d.name for d in tsu_root.iterdir() if d.is_dir()]
    summary = {"processed": 0, "indexed": 0, "identifiers": []}
    for identifier in identifiers:
        report = index_identifier(identifier, tsu_root=tsu_root, qdrant_url=qdrant_url)
        summary["processed"] += 1
        summary["indexed"] += report["indexed"]
        summary["identifiers"].append({"identifier": identifier, "indexed": report["indexed"]})
    return summary

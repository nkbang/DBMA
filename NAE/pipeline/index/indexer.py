"""Phase 4 - TSU -> Review Gate -> Embedding -> Qdrant orchestrator.

Prefers tsu_verified.json (Phase 3.5 output, carries score/duplicate_of) and
falls back to tsu.json if verification hasn't been run yet for an item.
Records flagged as duplicate_of another record are skipped at index time
(the canonical record is indexed instead) so retrieval results aren't
polluted with near-identical claims.

NAE-TSU-REVIEW-GATE-WIRING-IMPLEMENTATION-001: `load_records()` now passes
every record (from either tsu_verified.json or tsu.json — the two are not
the same "verified", see NAE/pipeline/tsu/review_gate.py module docstring)
through the TSU Review Gate before it ever reaches this module's caller.
Only `review_status == "verified"` records are returned — a record can sit
in tsu_verified.json (duplicate-checked) and still be excluded here if a
human hasn't confirmed the claim itself yet.
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
from NAE.pipeline.tsu.review_gate import ReviewGateBatchSummary, filter_embedding_eligible

from . import config, qdrant_store

logger = logging.getLogger("nae.index.indexer")


def load_records_with_gate_summary(
    identifier: str, tsu_root: Path = tsu_config.TSU_ROOT
) -> tuple[list[dict], ReviewGateBatchSummary]:
    """`tsu_verified.json`(있으면) 또는 `tsu.json`을 읽고, TSU Review
    Gate(`review_status == "verified"`)를 통과한 레코드만 반환한다.

    JSON 파싱 실패(손상된 TSU 파일)는 예외를 던지지 않고 빈 결과로
    처리한다 — 배치 인덱싱 중 파일 하나가 깨졌다고 전체가 죽지 않도록
    (기존 TSU Builder의 "fail soft" 관례와 동일).
    """
    verified_path = tsu_root / identifier / "tsu_verified.json"
    plain_path = tsu_root / identifier / "tsu.json"
    path = verified_path if verified_path.exists() else plain_path
    if not path.exists():
        return [], ReviewGateBatchSummary(total=0)

    try:
        with open(path, encoding="utf-8") as fh:
            raw_records = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("TSU 파일 파싱 실패, 건너뜀: %s (%s)", path, exc)
        return [], ReviewGateBatchSummary(total=0)

    if not isinstance(raw_records, list):
        logger.warning("TSU 파일 형식 오류(list 아님), 건너뜀: %s", path)
        return [], ReviewGateBatchSummary(total=0)

    gate_summary = filter_embedding_eligible(raw_records)
    return gate_summary.pass_records, gate_summary


def load_records(identifier: str, tsu_root: Path = tsu_config.TSU_ROOT) -> list[dict]:
    """하위 호환 유지용 — Review Gate를 통과한 레코드 목록만 반환한다
    (기존 호출자가 있다면 이 함수만 써도 자동으로 Gate가 적용된다)."""
    records, _summary = load_records_with_gate_summary(identifier, tsu_root)
    return records


def index_identifier(identifier: str, *, tsu_root: Path = tsu_config.TSU_ROOT,
                      qdrant_url: str = config.QDRANT_URL, dry_run: bool = False) -> dict[str, Any]:
    records, gate_summary = load_records_with_gate_summary(identifier, tsu_root)

    if dry_run:
        # 읽기 전용 — embedding 호출도, Qdrant 접근도, 파일 쓰기도 하지 않는다.
        would_index = 0
        would_skip_duplicate = 0
        for record in records:
            if record.get("duplicate_of"):
                would_skip_duplicate += 1
                continue
            if not record.get("claim"):
                continue
            would_index += 1

        return {
            "identifier": identifier,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": True,
            "collection": config.COLLECTION_NAME,
            "records_total_raw": gate_summary.total,
            "gate_pass": gate_summary.pass_count,
            "gate_block": gate_summary.block_count,
            "gate_block_details": gate_summary.block_details,
            "would_index": would_index,
            "would_skip_duplicate": would_skip_duplicate,
        }

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
        "records_total_raw": gate_summary.total,
        "gate_pass": gate_summary.pass_count,
        "gate_block": gate_summary.block_count,
        "indexed": indexed,
        "skipped_duplicate": skipped_duplicate,
        "embedding_errors": embedding_errors,
    }

    out_dir = tsu_root / identifier
    with open(out_dir / "index_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    return report


def index_all(*, tsu_root: Path = tsu_config.TSU_ROOT, qdrant_url: str = config.QDRANT_URL,
              dry_run: bool = False) -> dict[str, Any]:
    if not tsu_root.exists():
        return {"processed": 0, "indexed": 0, "identifiers": []}

    identifiers = [d.name for d in tsu_root.iterdir() if d.is_dir()]
    summary: dict[str, Any] = {"processed": 0, "indexed": 0, "identifiers": []}
    for identifier in identifiers:
        report = index_identifier(identifier, tsu_root=tsu_root, qdrant_url=qdrant_url, dry_run=dry_run)
        summary["processed"] += 1
        summary["indexed"] += report.get("would_index" if dry_run else "indexed", 0)
        summary["identifiers"].append(
            {"identifier": identifier, "indexed": report.get("would_index" if dry_run else "indexed", 0)}
        )
    return summary

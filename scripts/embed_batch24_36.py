"""BGE-M3 embedding — Batch 24-36 승인 후보 1,271건 전용 (READ scope 제한).

`indexer.index_all()`은 corpus 전체 verified TSU(3,319건, 이 중 과거 Batch
1-23의 2,038건 backlog 포함)를 대상으로 하므로 이번 요청 범위(1,271건만)에
맞지 않는다. 이 스크립트는 `output/final_human_review_candidate.json`의
정확히 1,271개 tsu_id만 골라 embedding + Qdrant upsert한다. 2,038건
backlog는 건드리지 않는다(별도 후속 작업).

Production TSU 파일, decisions, exception_queue는 쓰지 않는다 — 오직
embedding cache와 Qdrant `nae_tsu_v1` 컬렉션에만 쓴다.
"""
from __future__ import annotations

import json
from pathlib import Path

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import hashing
from NAE.pipeline.index import config, qdrant_store
from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_target_ids() -> set[str]:
    final = json.loads((REPO_ROOT / "output/final_human_review_candidate.json").read_text(encoding="utf-8"))
    return set(final["screening_clear"]["tsu_ids"]) | set(final["qa_flag_nonblocking"]["tsu_ids"])


def main() -> None:
    target_ids = load_target_ids()
    assert len(target_ids) == 1271, f"expected 1271 target TSUs, got {len(target_ids)}"

    dagg = json.loads((REPO_ROOT / "NAE/corpus/tsu/Dagg_Church_Order/tsu.json").read_text(encoding="utf-8"))
    dagg_by_id = {r["id"]: r for r in dagg}

    client = qdrant_store.get_client()
    qdrant_store.ensure_collection(client)

    existing_ids: set[str] = set()
    offset = None
    while True:
        pts, offset = client.scroll(collection_name=config.COLLECTION_NAME, limit=500, offset=offset, with_payload=True, with_vectors=False)
        existing_ids.update(p.payload["tsu_id"] for p in pts)
        if offset is None:
            break

    already_embedded = target_ids & existing_ids
    to_embed = sorted(target_ids - existing_ids)
    print(f"target: {len(target_ids)}, already_embedded(skip): {len(already_embedded)}, to_embed: {len(to_embed)}")

    indexed = 0
    embedding_errors = []
    points = []
    for tid in to_embed:
        record = dagg_by_id.get(tid)
        if record is None:
            embedding_errors.append((tid, "NOT_FOUND_IN_PRODUCTION"))
            continue
        if record.get("review_status") != "verified":
            embedding_errors.append((tid, f"review_status={record.get('review_status')}"))
            continue
        claim_text = record.get("claim")
        if not claim_text:
            embedding_errors.append((tid, "EMPTY_CLAIM"))
            continue

        content_hash = hashing.tsu_hash(
            schema_version=record.get("tsu_schema_version", TSU_SCHEMA_VERSION),
            claim=claim_text, book=record.get("book", ""),
            page=record.get("page", ""), scriptures=record.get("scriptures", []),
        )
        vector = embed_client.embed_text(claim_text, content_hash=content_hash)
        if vector is None:
            embedding_errors.append((tid, "EMBED_FAILED"))
            continue
        points.append(qdrant_store.build_point(record, vector))
        indexed += 1

        if len(points) >= 100:
            qdrant_store.upsert_points(client, points)
            points = []
            print(f"  ...{indexed}/{len(to_embed)} upserted", flush=True)

    if points:
        qdrant_store.upsert_points(client, points)

    report = {
        "scope": "Batch 24-36 (1,271 target)",
        "target_count": len(target_ids),
        "already_embedded_skipped": len(already_embedded),
        "newly_indexed": indexed,
        "errors": embedding_errors,
        "error_count": len(embedding_errors),
    }
    (REPO_ROOT / "output/embed_batch24_36_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Incremental ingestion 오케스트레이션 — dry-run과 실제 실행(apply)을
명확히 분리한다. dry-run은 어떤 파일도, Qdrant도, 캐시도 쓰지 않는다.
"""
from __future__ import annotations

from typing import Any, Callable

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import config as embed_config

from . import content_hash as ch
from . import embedding as emb
from . import indexing as idx
from .state import IncrementalStateStore, ProcessingState


def dry_run(
    records: list[dict[str, Any]],
    *,
    state_store: IncrementalStateStore,
    model: str = embed_config.DEFAULT_EMBED_MODEL,
    cache_root=embed_config.EMBEDDING_CACHE_ROOT,
) -> dict[str, Any]:
    """어떤 쓰기도 하지 않는다(파일/Qdrant/캐시 전부). NEW/CHANGED/
    UNCHANGED와, 그로부터 파생되는 SKIP/EMBED/INDEX 예상치만 계산한다."""
    known_hashes = state_store.known_hashes()
    change_status = ch.classify_batch(records, known_hashes)

    counts = {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0}
    for status in change_status.values():
        counts[status.value] += 1

    embed_plan = emb.plan_embedding(records, model=model, cache_root=cache_root)
    embed_count = sum(1 for v in embed_plan.values() if v == "EMBED")
    skip_count = sum(1 for v in embed_plan.values() if v == "SKIP")

    # NEW/CHANGED만 index 대상(embedding까지 성공해야 하지만 dry-run이므로 추정치)
    index_candidates = [tid for tid, status in change_status.items() if status != ch.ChangeStatus.UNCHANGED]

    return {
        "mode": "dry_run",
        "total_records": len(records),
        "NEW": counts["NEW"],
        "CHANGED": counts["CHANGED"],
        "UNCHANGED": counts["UNCHANGED"],
        "SKIP": skip_count,
        "EMBED": embed_count,
        "INDEX": len(index_candidates),
        "change_status": {tid: s.value for tid, s in change_status.items()},
        "embed_plan": embed_plan,
    }


def apply(
    records: list[dict[str, Any]],
    *,
    state_store: IncrementalStateStore,
    model: str = embed_config.DEFAULT_EMBED_MODEL,
    embed_fn: Callable[..., list[float] | None] = embed_client.embed_text,
    qdrant_client=None,
    cache_root=embed_config.EMBEDDING_CACHE_ROOT,
) -> dict[str, Any]:
    """실제로 embedding + Qdrant upsert + state 갱신을 수행한다. `--apply`
    없이는 호출되지 않아야 한다(CLI에서 강제)."""
    known_hashes = state_store.known_hashes()
    change_status = ch.classify_batch(records, known_hashes)

    to_process = [r for r in records if change_status[r["id"]] != ch.ChangeStatus.UNCHANGED]
    unchanged = [r["id"] for r in records if change_status[r["id"]] == ch.ChangeStatus.UNCHANGED]

    for tsu_id in unchanged:
        state_store.set_state(tsu_id, ProcessingState.INDEXED, known_hashes.get(tsu_id))

    embed_result = emb.execute_incremental_embed(to_process, model=model, embed_fn=embed_fn, cache_root=cache_root)

    for tsu_id in embed_result["skipped"]:
        rec = next(r for r in to_process if r["id"] == tsu_id)
        state_store.set_state(tsu_id, ProcessingState.EMBEDDED, ch.compute_content_hash(rec))
    for tsu_id, reason in embed_result["errors"]:
        state_store.set_state(tsu_id, ProcessingState.EMBEDDING_FAILED)

    records_by_id = {r["id"]: r for r in to_process if r["id"] in embed_result["vectors"]}
    index_result = idx.execute_incremental_index(records_by_id, embed_result["vectors"], client=qdrant_client)

    for tsu_id in embed_result["vectors"]:
        rec = records_by_id[tsu_id]
        state_store.set_state(tsu_id, ProcessingState.INDEXED, ch.compute_content_hash(rec))

    state_store.save()

    return {
        "mode": "apply",
        "total_records": len(records),
        "NEW": sum(1 for s in change_status.values() if s == ch.ChangeStatus.NEW),
        "CHANGED": sum(1 for s in change_status.values() if s == ch.ChangeStatus.CHANGED),
        "UNCHANGED": len(unchanged),
        "embedded": embed_result["embedded"],
        "embedding_errors": embed_result["errors"],
        "indexed_count": index_result["indexed_count"],
        "index_lifecycle": index_result["lifecycle"],
    }

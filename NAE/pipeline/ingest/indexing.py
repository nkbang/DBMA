"""Incremental Qdrant indexing — 새/변경 vector만 upsert, 기존 vector는
그대로 둔다. `index_all()`(corpus 전체 재스캔)을 정상 실행 경로로 쓰지
않는다 — 그 함수는 reconciliation/recovery/audit 용도로만 유지한다
(NAE/pipeline/index/indexer.py 참고, 이 모듈이 대체하는 것은 "정상 실행
경로"이지 그 함수 자체가 아니다).
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from NAE.pipeline.index import qdrant_store
from NAE.pipeline.index import config as index_config


class VectorLifecycle(str, Enum):
    ACTIVE = "ACTIVE"       # 현재 Qdrant에 존재, 최신 content_hash와 일치
    REPLACED = "REPLACED"   # CHANGED로 재분류되어 upsert로 교체됨(point id는 tsu_id 기반이라 자동 교체)
    DELETED = "DELETED"     # Production에서 사라진 tsu_id — stale vector 후보(자동 삭제하지 않음, §명시적 조치 필요)


def existing_point_ids(client, collection_name: str = index_config.COLLECTION_NAME) -> set[str]:
    """Qdrant 컬렉션에 이미 존재하는 tsu_id 집합을 READ-ONLY로 조회한다."""
    ids: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection_name, limit=500, offset=offset,
            with_payload=True, with_vectors=False,
        )
        ids.update(p.payload["tsu_id"] for p in points)
        if offset is None:
            break
    return ids


def plan_indexing(target_tsu_ids: set[str], existing_ids: set[str]) -> dict[str, list[str]]:
    """target(이번에 embedding까지 완료된 tsu_id 집합)과 Qdrant에 이미
    있는 것을 비교해 NEW/UNCHANGED로 나눈다. Production에는 있지만 이번
    target에 없는 기존 vector는 건드리지 않는다(다른 배치의 소관)."""
    new_ids = sorted(target_tsu_ids - existing_ids)
    unchanged_ids = sorted(target_tsu_ids & existing_ids)
    return {"NEW": new_ids, "UNCHANGED": unchanged_ids}


def execute_incremental_index(
    records_by_id: dict[str, dict[str, Any]],
    vectors_by_id: dict[str, list[float]],
    *,
    client=None,
    collection_name: str = index_config.COLLECTION_NAME,
) -> dict[str, Any]:
    """embedding까지 끝난 (record, vector) 쌍만 upsert한다. 기존 vector는
    건드리지 않는다 — Qdrant upsert는 point id(tsu_id 파생)가 겹칠 때만
    교체(REPLACED)하고, 겹치지 않으면 추가(NEW)한다."""
    if client is None:
        client = qdrant_store.get_client()
    qdrant_store.ensure_collection(client, collection_name=collection_name)

    existing_ids = existing_point_ids(client, collection_name)
    target_ids = set(vectors_by_id.keys())
    plan = plan_indexing(target_ids, existing_ids)

    points = []
    for tsu_id, vector in vectors_by_id.items():
        record = records_by_id[tsu_id]
        points.append(qdrant_store.build_point(record, vector))

    qdrant_store.upsert_points(client, points, collection_name=collection_name)

    lifecycle = {
        tsu_id: (VectorLifecycle.REPLACED if tsu_id in existing_ids else VectorLifecycle.ACTIVE).value
        for tsu_id in target_ids
    }

    return {
        "plan": plan,
        "indexed_count": len(points),
        "lifecycle": lifecycle,
    }

"""Content hash / idempotency — NEW / UNCHANGED / CHANGED 판정.

`NAE.pipeline.embed.hashing.tsu_hash()`(schema_version+claim+book+page+
scriptures)를 그대로 재사용한다 — 새 해시 알고리즘을 만들지 않는다. 이
모듈은 그 해시를 이전에 기록된 상태(state store)와 비교해 3가지 중 하나로
분류하는 책임만 진다.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from NAE.pipeline.embed import hashing
from NAE.pipeline.tsu.config import TSU_SCHEMA_VERSION


class ChangeStatus(str, Enum):
    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"


def compute_content_hash(record: dict[str, Any]) -> str:
    return hashing.tsu_hash(
        schema_version=record.get("tsu_schema_version", TSU_SCHEMA_VERSION),
        claim=record.get("claim", ""),
        book=record.get("book", ""),
        page=record.get("page", ""),
        scriptures=record.get("scriptures", []),
    )


def classify(tsu_id: str, current_hash: str, known_hashes: dict[str, str]) -> ChangeStatus:
    """`known_hashes`는 tsu_id -> 마지막으로 기록된 content_hash 맵(상태
    저장소에서 읽은 값). 이전에 본 적 없는 tsu_id면 NEW, 해시가 같으면
    UNCHANGED, 다르면 CHANGED."""
    previous = known_hashes.get(tsu_id)
    if previous is None:
        return ChangeStatus.NEW
    if previous == current_hash:
        return ChangeStatus.UNCHANGED
    return ChangeStatus.CHANGED


def classify_batch(records: list[dict[str, Any]], known_hashes: dict[str, str]) -> dict[str, ChangeStatus]:
    result: dict[str, ChangeStatus] = {}
    for record in records:
        tsu_id = record["id"]
        current_hash = compute_content_hash(record)
        result[tsu_id] = classify(tsu_id, current_hash, known_hashes)
    return result

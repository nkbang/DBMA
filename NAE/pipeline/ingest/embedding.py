"""Incremental embedding — content_hash + model + model_version + dimension이
전부 같으면 SKIP, 하나라도 다르면 EMBED.

`NAE.pipeline.embed.client.embed_text()`는 이미 content_hash 파일명으로
캐시하지만, 캐시 파일 자체에 기록된 `model`을 요청한 `model`과 대조하지는
않는다. 이 모듈은 그 위에 model/dimension 일치 여부까지 명시적으로
확인하는 계층을 얹는다 — 캐시 파일이 있어도 model이 다르면 CHANGED로
재분류해 재임베딩을 유도한다.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from NAE.pipeline.embed import client as embed_client
from NAE.pipeline.embed import config as embed_config

from .content_hash import ChangeStatus, compute_content_hash


def _cached_model(content_hash: str, cache_root=embed_config.EMBEDDING_CACHE_ROOT) -> str | None:
    path = cache_root / f"{content_hash}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("model")
    except (json.JSONDecodeError, OSError):
        return None


def plan_embedding(
    records: list[dict[str, Any]],
    *,
    model: str = embed_config.DEFAULT_EMBED_MODEL,
    dimension: int = embed_config.EMBED_DIMENSION,
    cache_root=embed_config.EMBEDDING_CACHE_ROOT,
) -> dict[str, str]:
    """tsu_id -> "SKIP" | "EMBED" 계획을 반환한다(READ-ONLY, 아무것도
    쓰지 않음). SKIP 조건: content_hash 캐시가 존재하고, 그 캐시의 model이
    요청 model과 동일할 때만(dimension은 model이 고정되어 있으면 함께
    고정되므로 model 일치로 대표한다)."""
    plan: dict[str, str] = {}
    for record in records:
        tsu_id = record["id"]
        content_hash = compute_content_hash(record)
        cached_model = _cached_model(content_hash, cache_root)
        if cached_model is not None and cached_model == model:
            plan[tsu_id] = "SKIP"
        else:
            plan[tsu_id] = "EMBED"
    return plan


def execute_incremental_embed(
    records: list[dict[str, Any]],
    *,
    model: str = embed_config.DEFAULT_EMBED_MODEL,
    dimension: int = embed_config.EMBED_DIMENSION,
    cache_root=embed_config.EMBEDDING_CACHE_ROOT,
    embed_fn: Callable[..., list[float] | None] = embed_client.embed_text,
) -> dict[str, Any]:
    """계획에서 EMBED로 분류된 레코드만 실제로 embedding한다. `embed_fn`은
    테스트에서 실제 Ollama 호출 없이 결정적 fake 함수로 주입할 수 있다."""
    plan = plan_embedding(records, model=model, dimension=dimension, cache_root=cache_root)
    embedded: list[str] = []
    skipped: list[str] = []
    errors: list[tuple[str, str]] = []
    vectors: dict[str, list[float]] = {}

    by_id = {r["id"]: r for r in records}
    for tsu_id, action in plan.items():
        if action == "SKIP":
            skipped.append(tsu_id)
            continue
        record = by_id[tsu_id]
        claim = record.get("claim")
        if not claim:
            errors.append((tsu_id, "EMPTY_CLAIM"))
            continue
        content_hash = compute_content_hash(record)
        vector = embed_fn(claim, content_hash=content_hash, model=model, cache_root=cache_root)
        if vector is None:
            errors.append((tsu_id, "EMBED_FAILED"))
            continue
        vectors[tsu_id] = vector
        embedded.append(tsu_id)

    return {
        "plan": plan,
        "embedded": embedded,
        "skipped": skipped,
        "errors": errors,
        "vectors": vectors,
    }

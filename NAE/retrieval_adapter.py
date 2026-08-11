"""NAE optional retrieval adapter (NAE-OPTIONAL-MODULE-PACKAGING-001).

`core/retrieval.py::RetrievalEngine`(ADR-001 유일 정본, "One Pipeline,
One Config, One Retrieval Engine, One Execution State")을 수정하지 않는다
— `RetrievalEngine`은 이 모듈을 import하지 않고, 이 모듈도 `RetrievalEngine`
을 import하지 않는다. 이 파일은 `nae_pd` module이 enabled일 때만 **호출하는
쪽**(예: 향후 UI 탭, 별도 스크립트)이 명시적으로 불러 쓰는 독립 adapter다.

DBMA Core retrieval 경로에 자동으로 끼워 넣지 않는다 — "명시적 module
boundary를 통해서만 접근"(지시서 §6) 원칙.
"""
from __future__ import annotations

from typing import Any

from core import module_registry


class NaePdModuleDisabledError(RuntimeError):
    pass


def search(query_vector: list[float], *, top_k: int = 10, limit_check: bool = True) -> list[dict[str, Any]]:
    """`nae_pd` module이 비활성화 상태면 예외를 던진다 — DBMA Core
    retrieval 경로가 실수로 이 함수를 호출해도 NAE corpus/index에
    접근하지 않는다."""
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError("nae_pd module is disabled — enable via `scripts/dbma_module.py enable nae_pd` first")

    from NAE.pipeline.index import qdrant_store, config as index_config

    client = qdrant_store.get_client()
    hits = client.search(collection_name=index_config.COLLECTION_NAME, query_vector=query_vector, limit=top_k)
    return [{"tsu_id": h.payload.get("tsu_id"), "score": h.score, "payload": h.payload} for h in hits]

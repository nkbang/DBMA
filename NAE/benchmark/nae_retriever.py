"""NAE/benchmark/nae_retriever.py — Real NAE Qdrant-backed Retriever
(NAE-PILOT-001-RETRIEVAL-BENCHMARK-001).

Implements `runner.Retriever` protocol against the real `nae_qdrant`
instance (`nae_tsu_v1` collection) using `bge-m3:latest` for query
embedding. Read-only — never writes to Qdrant, never touches Production
TSU files. Completely separate from `core/retrieval.py::RetrievalEngine`
(DBMA legacy path) — this module only talks to the NAE-dedicated Qdrant
instance (port 7333), per ADR-013.
"""
from __future__ import annotations

from NAE.pipeline.embed import config as embed_config
from NAE.pipeline.index import config as index_config
from NAE.pipeline.index import qdrant_store


class NaeQdrantRetriever:
    """`runner.Retriever` 프로토콜 구현체 — `nae_tsu_v1`에 대해서만
    질의한다(읽기 전용, upsert/delete 없음)."""

    def __init__(self, collection_name: str = index_config.COLLECTION_NAME,
                 model: str = embed_config.DEFAULT_EMBED_MODEL) -> None:
        self.collection_name = collection_name
        self.model = model
        self._client = qdrant_store.get_client()

    def _embed_query(self, query: str) -> list[float]:
        import ollama

        result = ollama.embeddings(model=self.model, prompt=query)
        return result["embedding"]

    def retrieve(self, query: str, k: int) -> list[str]:
        vector = self._embed_query(query)
        response = self._client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=k,
            with_payload=["tsu_id"],
        )
        return [point.payload["tsu_id"] for point in response.points]

"""
core/ingest.py — Qdrant 문서 삽입 스크립트 (안전한 import)

이 모듈은 import 시점에 외부 서비스 연결을 시도하지 않습니다.
insert() 함수를 명시적으로 호출해야 합니다.
"""

import logging

# [SPRINT17-RG-3] Runtime usage verification — additive logging only, no logic change.
logger = logging.getLogger(__name__)


def _ensure_qdrant():
    """qdrant_client를 선택적으로 임포트합니다."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct
        return QdrantClient, PointStruct
    except ImportError:
        raise ImportError("qdrant_client가 설치되지 않았습니다. pip install qdrant-client")


DEFAULT_QDRANT_URL = "http://localhost:6333"
COLLECTION = "dbma_sermon"


def insert(doc_id: str, text: str, url: str = DEFAULT_QDRANT_URL) -> dict:
    """문서를 Qdrant에 삽입합니다."""
    logger.debug("[SPRINT17-RG-3] core.ingest.insert entry point hit | doc_id=%s", doc_id)
    from core.embedder import embed
    QdrantClient, PointStruct = _ensure_qdrant()
    client = QdrantClient(url=url)
    vector = embed(text)

    client.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=doc_id,
                vector=vector,
                payload={"text": text}
            )
        ]
    )
    return {"status": "ok", "doc_id": doc_id}


if __name__ == "__main__":
    result = insert("test-1", "In the beginning God created the heavens and the earth.")
    print(f"INGEST OK: {result}")

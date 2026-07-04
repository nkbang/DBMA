"""
search.py — Qdrant 벡터 검색 + 메타데이터 반환 (안전한 import)

이 모듈은 import 시점에 외부 서비스 연결을 시도하지 않습니다.
search() 함수 호출 시에만 연결합니다.
"""

from core.embedder import embed

COLLECTION_NAME = "dbma_sermon"
DEFAULT_QDRANT_URL = "http://localhost:6333"


def search(query: str, limit: int = 5, url: str = DEFAULT_QDRANT_URL) -> list:
    """
    쿼리를 임베딩하여 Qdrant에서 유사 노드를 검색한다.

    Args:
        query: 검색 쿼리 텍스트
        limit: 반환할 결과 수
        url: Qdrant 서버 URL

    Returns:
        [{"score": float, "text": str, "source": str,
          "section": str, "header_level": int, "filepath": str}, ...]
    """
    from qdrant_client import QdrantClient

    v = embed(query)
    client = QdrantClient(url=url)

    try:
        res = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=v,
            limit=limit,
            with_payload=True,
        )
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for r in res:
        payload = r.payload or {}
        results.append({
            "score": round(r.score, 4),
            "text": payload.get("text", ""),
            "source": payload.get("source", ""),
            "section": payload.get("section", ""),
            "header_level": payload.get("header_level", 0),
            "filepath": payload.get("filepath", ""),
        })

    return results


def search_pretty(query: str, limit: int = 5) -> None:
    """터미널 출력용 검색 함수."""
    results = search(query, limit=limit)
    for i, r in enumerate(results, 1):
        if "error" in r:
            print(f"[오류] {r['error']}")
            break
        print(f"\n[{i}] score={r['score']} | {r['source']} > {r['section']}")
        print(r["text"][:300])


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "하나님의 창조"
    search_pretty(q)

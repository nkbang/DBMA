"""
core/qdrant_init.py — Qdrant 컬렉션 초기화 스크립트

이 모듈은 import 시점에 외부 서비스 연결을 시도하지 않습니다.
사용하려면 반드시 __main__으로 실행하거나 init_collection()을 명시적으로 호출하세요.

사용 예:
    python -m core.qdrant_init        # CLI 실행
    from core.qdrant_init import init_collection; init_collection()  # 프로그램틱
"""

COLLECTION = "dbma_sermon"
DEFAULT_QDRANT_URL = "http://localhost:6333"


def init_collection(url: str = DEFAULT_QDRANT_URL) -> None:
    """Qdrant 컬렉션을 초기화합니다 (안전한 함수형 API)."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import VectorParams, Distance
    except ImportError as e:
        print(f"ERROR: qdrant_client가 설치되지 않았습니다. pip install qdrant-client")
        raise

    client = QdrantClient(url=url)
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    )
    print(f"OK: collection '{COLLECTION}' created at {url}")


if __name__ == "__main__":
    init_collection()

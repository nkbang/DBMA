from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(url="http://localhost:6333")

COLLECTION = "dbma_sermon"

client.recreate_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(
        size=768,
        distance=Distance.COSINE
    )
)

print("OK: collection created")

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from embedder import embed

client = QdrantClient(url="http://localhost:6333")

COLLECTION = "dbma_sermon"

def ingest(doc_id: str, text: str):
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

if __name__ == "__main__":
    ingest("test-1", "In the beginning God created the heavens and the earth.")
    print("INGEST OK")

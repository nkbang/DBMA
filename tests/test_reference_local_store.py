"""NAE/reference_local_store.py + search_reference() 로컬 우선 경로 (Docker 불필요)."""
import pytest
from qdrant_client import QdrantClient, models

from NAE import reference_local_store as store
from NAE import reference_retrieval_adapter as adapter
from NAE.pipeline.reference import config as ref_config
from ui.state import reference_store


@pytest.fixture
def local_dir(tmp_path, monkeypatch):
    d = tmp_path / "ref_local"
    monkeypatch.setenv("NAE_REFERENCE_LOCAL_PATH", str(d))
    store.close_local_client()
    yield d
    store.close_local_client()


def _build(d, collection="nae_ref_v1", ready=True):
    c = QdrantClient(path=str(d))
    c.create_collection(collection, vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE))
    c.upsert(collection, [
        models.PointStruct(id=1, vector=[1, 0, 0], payload={"text": "[DRAGON] a great serpent", "source_id": "smith"}),
        models.PointStruct(id=2, vector=[0, 1, 0], payload={"text": "[GRACE] unmerited favour", "source_id": "smith"}),
    ])
    c.close()
    if ready:
        (d / store.READY_MARKER).write_text("ok")


def _no_server(monkeypatch, vector):
    monkeypatch.setattr(adapter, "_get_cached_embedding", lambda h: vector)
    monkeypatch.setattr(ref_config, "QDRANT_URL", "http://127.0.0.1:1")  # 닿지 않는 서버


def test_not_ready_without_marker(local_dir):
    assert not store.is_ready() and store.get_local_client() is None
    _build(local_dir, ready=False)
    assert not store.is_ready() and store.get_local_client() is None


def test_search_uses_local_store_without_server(local_dir, monkeypatch):
    _build(local_dir)
    _no_server(monkeypatch, [1.0, 0.0, 0.0])
    out = adapter.search_reference("dragon", top_k=1)
    assert [r["text"] for r in out] == ["[DRAGON] a great serpent"]
    assert reference_store.local_store_ready() and reference_store.is_reachable()


def test_missing_collection_falls_back_and_never_raises(local_dir, monkeypatch):
    _build(local_dir)
    _no_server(monkeypatch, [1.0, 0.0, 0.0])
    # 로컬에 없는 컬렉션은 (닿지 않는) 서버로 가고, 실패는 빈 결과로 흡수한다.
    assert adapter.search_reference("x", top_k=2, collection_names=["nae_ref_commentary_v1"]) == []
    # 있는 컬렉션과 섞어도 있는 쪽 결과는 나온다.
    out = adapter.search_reference("x", top_k=2, collection_names=["nae_ref_v1", "nae_ref_commentary_v1"])
    assert len(out) == 2


def test_locked_store_falls_back(local_dir, monkeypatch):
    _build(local_dir)
    held = QdrantClient(path=str(local_dir))        # 다른 "프로세스"가 폴더를 잡고 있는 상황
    try:
        assert store.get_local_client() is None
    finally:
        held.close()

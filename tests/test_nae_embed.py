from pathlib import Path
from unittest.mock import patch

from NAE.pipeline.embed import client, hashing
from NAE.pipeline.embed.similarity import cosine_similarity


def test_tsu_hash_deterministic():
    h1 = hashing.tsu_hash(schema_version="1", claim="Faith alone justifies.", book="Body of Divinity", page=12, scriptures=["Rom 3:24"])
    h2 = hashing.tsu_hash(schema_version="1", claim="Faith alone justifies.", book="Body of Divinity", page=12, scriptures=["Rom 3:24"])
    assert h1 == h2
    assert len(h1) == 64


def test_tsu_hash_scripture_order_independent():
    h1 = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=["A", "B"])
    h2 = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=["B", "A"])
    assert h1 == h2


def test_tsu_hash_changes_with_content():
    h1 = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=[])
    h2 = hashing.tsu_hash(schema_version="1", claim="Y", book="B", page=1, scriptures=[])
    assert h1 != h2


def test_tsu_hash_changes_with_schema_version():
    h1 = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=[])
    h2 = hashing.tsu_hash(schema_version="2", claim="X", book="B", page=1, scriptures=[])
    assert h1 != h2


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_zero_vector_returns_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_mismatched_length_returns_zero():
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@patch("NAE.pipeline.embed.client.ollama.embeddings")
def test_embed_text_caches_result(mock_embeddings, tmp_path: Path):
    mock_embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
    cache_root = tmp_path / "cache"
    h = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=[])

    v1 = client.embed_text("X", content_hash=h, cache_root=cache_root)
    v2 = client.embed_text("X", content_hash=h, cache_root=cache_root)

    assert v1 == [0.1, 0.2, 0.3]
    assert v2 == [0.1, 0.2, 0.3]
    mock_embeddings.assert_called_once()  # second call served from cache


@patch("NAE.pipeline.embed.client.ollama.embeddings")
def test_embed_text_returns_none_on_failure(mock_embeddings, tmp_path: Path):
    mock_embeddings.side_effect = RuntimeError("connection refused")
    cache_root = tmp_path / "cache"
    h = hashing.tsu_hash(schema_version="1", claim="X", book="B", page=1, scriptures=[])
    result = client.embed_text("X", content_hash=h, cache_root=cache_root)
    assert result is None
